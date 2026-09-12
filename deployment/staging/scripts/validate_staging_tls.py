"""Validate the private staging TLS chain and HTTPS health endpoint.

This validator deliberately uses a caller-supplied CA file as the only trust
anchor. It never disables certificate verification and never falls back to a
system-wide or insecure trust store.
"""

from __future__ import annotations

import argparse
import http.client
import ipaddress
import json
import socket
import ssl
import sys
from datetime import datetime, timezone
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.x509.oid import ExtendedKeyUsageOID


class StagingTLSValidationError(ValueError):
    """Raised when staging TLS material or the HTTPS endpoint is unsafe."""


def _not_before(certificate: x509.Certificate) -> datetime:
    if hasattr(certificate, "not_valid_before_utc"):
        return certificate.not_valid_before_utc
    return certificate.not_valid_before.replace(tzinfo=timezone.utc)


def _not_after(certificate: x509.Certificate) -> datetime:
    if hasattr(certificate, "not_valid_after_utc"):
        return certificate.not_valid_after_utc
    return certificate.not_valid_after.replace(tzinfo=timezone.utc)


def _extension(certificate: x509.Certificate, extension_type: type):
    try:
        return certificate.extensions.get_extension_for_class(extension_type).value
    except x509.ExtensionNotFound as exc:
        raise StagingTLSValidationError(
            f"certificate is missing {extension_type.__name__}"
        ) from exc


def _verify_signature(certificate: x509.Certificate, issuer: x509.Certificate) -> None:
    if not isinstance(issuer.public_key(), rsa.RSAPublicKey):
        raise StagingTLSValidationError("staging certificates must use RSA keys")
    try:
        issuer.public_key().verify(
            certificate.signature,
            certificate.tbs_certificate_bytes,
            padding.PKCS1v15(),
            certificate.signature_hash_algorithm,
        )
    except Exception as exc:  # cryptography backends expose different exceptions
        raise StagingTLSValidationError(
            "server certificate signature does not chain to the staging CA"
        ) from exc


def _validate_trust_anchor(ca_file: Path) -> x509.Certificate:
    """Validate that *ca_file* is the intended self-signed staging root."""
    try:
        certificate = x509.load_pem_x509_certificate(ca_file.read_bytes())
    except (OSError, ValueError) as exc:
        raise StagingTLSValidationError(
            "CA file must contain a readable PEM CA certificate"
        ) from exc

    constraints = _extension(certificate, x509.BasicConstraints)
    key_usage = _extension(certificate, x509.KeyUsage)
    if (
        not constraints.ca
        or constraints.path_length != 0
        or certificate.subject != certificate.issuer
        or not key_usage.key_cert_sign
    ):
        raise StagingTLSValidationError(
            "CA file must contain the self-signed staging root CA, not a server leaf"
        )
    _verify_signature(certificate, certificate)
    now = datetime.now(timezone.utc)
    if not _not_before(certificate) <= now <= _not_after(certificate):
        raise StagingTLSValidationError("staging root CA is outside its validity period")
    return certificate


def _load_private_key(private_key_file: Path) -> rsa.RSAPrivateKey:
    try:
        key = serialization.load_pem_private_key(
            private_key_file.read_bytes(), password=None
        )
    except (OSError, ValueError, TypeError) as exc:
        raise StagingTLSValidationError(
            "server private key must be a readable unencrypted PEM RSA key"
        ) from exc
    if not isinstance(key, rsa.RSAPrivateKey):
        raise StagingTLSValidationError("server private key must use RSA")
    return key


def _load_pem_chain(certificate_file: Path) -> list[x509.Certificate]:
    """Load the PEM certificates in a leaf-first chain file."""
    begin = b"-----BEGIN CERTIFICATE-----"
    end = b"-----END CERTIFICATE-----"
    try:
        data = certificate_file.read_bytes()
    except OSError as exc:
        raise StagingTLSValidationError(
            "server certificate must be a readable PEM certificate"
        ) from exc
    parts = data.split(begin)
    if parts[0].strip():
        raise StagingTLSValidationError("server certificate chain contains unexpected data")
    certificates: list[x509.Certificate] = []
    for part in parts[1:]:
        body, marker, suffix = part.partition(end)
        if not marker or suffix.strip():
            raise StagingTLSValidationError("server certificate chain is malformed")
        try:
            certificates.append(x509.load_pem_x509_certificate(begin + body + end))
        except ValueError as exc:
            raise StagingTLSValidationError(
                "server certificate chain contains an unreadable certificate"
            ) from exc
    if not certificates:
        raise StagingTLSValidationError("server certificate chain contains no certificates")
    return certificates


def _validate_server_material(
    certificate_file: Path,
    private_key_file: Path,
    ca_certificate: x509.Certificate,
    server_name: str,
    require_fullchain: bool = False,
) -> x509.Certificate:
    """Validate the leaf chain, identity, EKU, and key/certificate pairing."""
    certificates = _load_pem_chain(certificate_file)
    if require_fullchain and len(certificates) != 2:
        raise StagingTLSValidationError(
            "server certificate must contain the leaf followed by the staging CA"
        )
    if len(certificates) > 2:
        raise StagingTLSValidationError("server certificate chain must contain only leaf and staging CA")
    certificate = certificates[0]
    private_key = _load_private_key(private_key_file)

    constraints = _extension(certificate, x509.BasicConstraints)
    if constraints.ca:
        raise StagingTLSValidationError("server certificate must be a leaf, not a CA")
    eku = _extension(certificate, x509.ExtendedKeyUsage)
    if ExtendedKeyUsageOID.SERVER_AUTH not in eku:
        raise StagingTLSValidationError(
            "server certificate must include the Server Authentication EKU"
        )
    if certificate.issuer != ca_certificate.subject:
        raise StagingTLSValidationError("server certificate issuer is not the staging CA")
    if len(certificates) == 2 and certificates[1] != ca_certificate:
        raise StagingTLSValidationError("server certificate chain does not contain the staging CA")
    _verify_signature(certificate, ca_certificate)
    if certificate.public_key().public_numbers() != private_key.public_key().public_numbers():
        raise StagingTLSValidationError("server private key does not match the certificate")
    now = datetime.now(timezone.utc)
    if not _not_before(certificate) <= now <= _not_after(certificate):
        raise StagingTLSValidationError("server certificate is outside its validity period")

    san = _extension(certificate, x509.SubjectAlternativeName)
    try:
        requested_ip = ipaddress.ip_address(server_name)
    except ValueError:
        if server_name not in san.get_values_for_type(x509.DNSName):
            raise StagingTLSValidationError(
                f"server certificate SAN does not contain {server_name!r}"
            )
    else:
        if requested_ip not in san.get_values_for_type(x509.IPAddress):
            raise StagingTLSValidationError(
                f"server certificate SAN does not contain IP {server_name!r}"
            )
    return certificate


def _resolved_addresses(hostname: str, port: int) -> set[str]:
    try:
        results = socket.getaddrinfo(
            hostname, port, family=socket.AF_UNSPEC, type=socket.SOCK_STREAM
        )
    except OSError as exc:
        raise StagingTLSValidationError(
            f"staging hostname {hostname!r} does not resolve"
        ) from exc
    addresses = {result[4][0] for result in results}
    if not addresses:
        raise StagingTLSValidationError(f"staging hostname {hostname!r} does not resolve")
    return addresses


def _https_health_check(
    tls_socket: ssl.SSLSocket, server_name: str, health_path: str
) -> dict[str, object]:
    if not health_path.startswith("/") or any(char in health_path for char in "\r\n"):
        raise StagingTLSValidationError("health path must start with '/'")
    request = (
        f"GET {health_path} HTTP/1.1\r\n"
        f"Host: {server_name}\r\n"
        "Connection: close\r\n\r\n"
    ).encode("ascii")
    tls_socket.sendall(request)
    response = http.client.HTTPResponse(tls_socket)
    response.begin()
    body = response.read()
    if response.status != 200:
        raise StagingTLSValidationError(
            f"HTTPS {health_path} returned HTTP {response.status}, expected 200"
        )
    try:
        payload = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise StagingTLSValidationError("HTTPS health response is not valid JSON") from exc
    if not isinstance(payload, dict) or payload.get("status") != "ok":
        raise StagingTLSValidationError("HTTPS health response must contain status=ok")
    return payload


def validate(
    ca_file: Path,
    certificate_file: Path,
    private_key_file: Path,
    connect_host: str,
    server_name: str,
    port: int,
    timeout: float,
    health_path: str,
) -> dict[str, object]:
    if not server_name or any(char in server_name for char in "\r\n"):
        raise StagingTLSValidationError("server name must be a non-empty hostname")
    ca_certificate = _validate_trust_anchor(ca_file)
    _validate_server_material(
        certificate_file, private_key_file, ca_certificate, server_name, require_fullchain=True
    )

    hostname_addresses = _resolved_addresses(server_name, port)
    connect_addresses = _resolved_addresses(connect_host, port)
    if not hostname_addresses.intersection(connect_addresses):
        raise StagingTLSValidationError(
            f"connect host {connect_host!r} is not an address of {server_name!r}"
        )

    context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH, cafile=str(ca_file))
    context.minimum_version = ssl.TLSVersion.TLSv1_2
    context.maximum_version = ssl.TLSVersion.TLSv1_3
    if context.verify_mode != ssl.CERT_REQUIRED or not context.check_hostname:
        raise StagingTLSValidationError("TLS certificate verification must remain enabled")
    try:
        with socket.create_connection((connect_host, port), timeout=timeout) as raw_socket:
            with context.wrap_socket(raw_socket, server_hostname=server_name) as tls_socket:
                protocol = tls_socket.version()
                if protocol not in {"TLSv1.2", "TLSv1.3"}:
                    raise StagingTLSValidationError(
                        f"unexpected negotiated TLS protocol: {protocol}"
                    )
                health = _https_health_check(tls_socket, server_name, health_path)
    except StagingTLSValidationError:
        raise
    except (OSError, ssl.SSLError, http.client.HTTPException) as exc:
        raise StagingTLSValidationError(f"verified HTTPS validation failed: {exc}") from exc
    return {
        "status": "ok",
        "tls_protocol": protocol,
        "server_name": server_name,
        "connect_host": connect_host,
        "health": health,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ca-file", required=True, type=Path)
    parser.add_argument("--certificate-file", type=Path)
    parser.add_argument("--private-key-file", type=Path)
    parser.add_argument("--connect-host", default="127.0.0.1")
    parser.add_argument("--server-name", default="sentinel-dna-staging")
    parser.add_argument("--port", type=int, default=18443)
    parser.add_argument("--timeout", type=float, default=10.0)
    parser.add_argument("--health-path", default="/health")
    args = parser.parse_args(argv)
    certificate_file = args.certificate_file or args.ca_file.with_name("staging-server-fullchain.crt")
    private_key_file = args.private_key_file or args.ca_file.with_name("staging-server.key")
    try:
        result = validate(
            ca_file=args.ca_file,
            certificate_file=certificate_file,
            private_key_file=private_key_file,
            connect_host=args.connect_host,
            server_name=args.server_name,
            port=args.port,
            timeout=args.timeout,
            health_path=args.health_path,
        )
    except (OSError, StagingTLSValidationError) as exc:
        print(f"staging TLS validation failed: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
