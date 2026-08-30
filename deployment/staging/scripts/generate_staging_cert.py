"""Generate and validate the self-signed Sentinel DNA staging certificate.

The certificate is intentionally staging-only. Its identity contract is kept
in the checked-in staging-cert-config.json file; the LAN IP is supplied by the
external staging environment so it can change without changing application
code or the repository's production configuration.
"""

from __future__ import annotations

import argparse
import ipaddress
import json
import os
import stat
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID


SCRIPT_DIR = Path(__file__).resolve().parent
CONFIG_PATH = SCRIPT_DIR.parent / "staging-cert-config.json"
REPOSITORY_ROOT = SCRIPT_DIR.parents[2]


class CertificateConfigurationError(RuntimeError):
    """Raised when the external staging certificate configuration is unsafe."""


def _load_config() -> dict[str, object]:
    try:
        config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CertificateConfigurationError("staging certificate configuration is unavailable") from exc
    if not isinstance(config, dict):
        raise CertificateConfigurationError("staging certificate configuration must be an object")
    required = {
        "common_name",
        "dns_sans",
        "fixed_ip_sans",
        "lan_ip_environment_variable",
        "certificate_filename",
        "private_key_filename",
        "key_algorithm",
        "key_size",
        "signature_hash",
        "validity_days",
    }
    if set(config) != required:
        raise CertificateConfigurationError("staging certificate configuration fields are invalid")
    if config["key_algorithm"] != "RSA" or config["key_size"] != 3072:
        raise CertificateConfigurationError("staging certificate key configuration is invalid")
    if config["signature_hash"] != "SHA-256":
        raise CertificateConfigurationError("staging certificate signature configuration is invalid")
    return config


def _required_environment(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value or value.startswith("__"):
        raise CertificateConfigurationError(f"{name} must be set to an external staging value")
    return value


def _tls_directory() -> Path:
    raw = _required_environment("SENTINEL_DNA_STAGING_TLS_DIR")
    directory = Path(raw).expanduser()
    if not directory.is_absolute():
        raise CertificateConfigurationError("SENTINEL_DNA_STAGING_TLS_DIR must be an absolute path")
    resolved = directory.resolve()
    try:
        resolved.relative_to(REPOSITORY_ROOT)
    except ValueError:
        return resolved
    raise CertificateConfigurationError("SENTINEL_DNA_STAGING_TLS_DIR must be outside the repository")


def _staging_ip(config: dict[str, object]) -> ipaddress.IPv4Address | ipaddress.IPv6Address:
    variable = config["lan_ip_environment_variable"]
    if not isinstance(variable, str):
        raise CertificateConfigurationError("LAN IP environment variable configuration is invalid")
    value = _required_environment(variable)
    try:
        address = ipaddress.ip_address(value)
    except ValueError as exc:
        raise CertificateConfigurationError(f"{variable} must contain an IP address") from exc
    if address.is_unspecified or address.is_multicast:
        raise CertificateConfigurationError(f"{variable} must contain a usable staging LAN address")
    return address


def _paths(config: dict[str, object]) -> tuple[Path, Path]:
    directory = _tls_directory()
    cert_name = config["certificate_filename"]
    key_name = config["private_key_filename"]
    if not isinstance(cert_name, str) or not isinstance(key_name, str):
        raise CertificateConfigurationError("staging certificate output filenames are invalid")
    cert_path = (directory / cert_name).resolve()
    key_path = (directory / key_name).resolve()
    if cert_path.parent != directory or key_path.parent != directory:
        raise CertificateConfigurationError("staging certificate output filenames must stay in the TLS directory")
    return cert_path, key_path


def _expected_sans(config: dict[str, object], staging_ip: object) -> set[tuple[str, str]]:
    dns_sans = config["dns_sans"]
    fixed_ip_sans = config["fixed_ip_sans"]
    if not isinstance(dns_sans, list) or not isinstance(fixed_ip_sans, list):
        raise CertificateConfigurationError("staging certificate SAN configuration is invalid")
    expected = {("DNS", name) for name in dns_sans if isinstance(name, str)}
    expected.update(("IP", value) for value in fixed_ip_sans if isinstance(value, str))
    expected.add(("IP", str(staging_ip)))
    if ("DNS", config["common_name"]) not in expected:
        raise CertificateConfigurationError("staging hostname must be present in SAN configuration")
    return expected


def _certificate_sans(certificate: x509.Certificate) -> set[tuple[str, str]]:
    try:
        extension = certificate.extensions.get_extension_for_class(x509.SubjectAlternativeName)
    except x509.ExtensionNotFound as exc:
        raise CertificateConfigurationError("certificate has no Subject Alternative Name extension") from exc
    names = extension.value
    return {
        ("DNS", value)
        for value in names.get_values_for_type(x509.DNSName)
    } | {
        ("IP", str(value))
        for value in names.get_values_for_type(x509.IPAddress)
    }


def _load_existing(cert_path: Path, key_path: Path) -> tuple[x509.Certificate, object]:
    try:
        certificate = x509.load_pem_x509_certificate(cert_path.read_bytes())
        key = serialization.load_pem_private_key(key_path.read_bytes(), password=None)
    except (OSError, ValueError, TypeError) as exc:
        raise CertificateConfigurationError("existing staging certificate or key is unreadable") from exc
    if not isinstance(key, rsa.RSAPrivateKey) or not isinstance(certificate.public_key(), rsa.RSAPublicKey):
        raise CertificateConfigurationError("existing staging certificate and key must use RSA")
    if certificate.public_key().public_numbers() != key.public_key().public_numbers():
        raise CertificateConfigurationError("existing staging certificate and key do not match")
    return certificate, key


def _existing_certificate_is_current(cert_path: Path, key_path: Path, expected_sans: set[tuple[str, str]]) -> bool:
    if not cert_path.is_file() or not key_path.is_file():
        return False
    certificate, _ = _load_existing(cert_path, key_path)
    now = datetime.now(timezone.utc)
    not_before = getattr(certificate, "not_valid_before_utc", certificate.not_valid_before.replace(tzinfo=timezone.utc))
    not_after = getattr(certificate, "not_valid_after_utc", certificate.not_valid_after.replace(tzinfo=timezone.utc))
    return (
        expected_sans == _certificate_sans(certificate)
        and not_before <= now <= not_after
    )


def _atomic_write(path: Path, data: bytes, mode: int) -> None:
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary_path = Path(temporary_name)
    try:
        if hasattr(os, "fchmod"):
            os.fchmod(descriptor, mode)
        else:
            os.chmod(temporary_path, mode)
        temporary_file = os.fdopen(descriptor, "wb")
        descriptor = -1
        with temporary_file:
            temporary_file.write(data)
            temporary_file.flush()
            os.fsync(temporary_file.fileno())
        os.replace(temporary_path, path)
        os.chmod(path, mode)
    except Exception:
        if descriptor >= 0:
            os.close(descriptor)
        temporary_path.unlink(missing_ok=True)
        raise


def _prepare_tls_directory(directory: Path, key_path: Path) -> None:
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    try:
        os.chmod(directory, stat.S_IRWXU)
        if key_path.exists():
            os.chmod(key_path, 0o600)
    except OSError as exc:
        raise CertificateConfigurationError("unable to enforce staging TLS file permissions") from exc


def _generate(config: dict[str, object], staging_ip: object, cert_path: Path, key_path: Path) -> None:
    directory = cert_path.parent
    _prepare_tls_directory(directory, key_path)

    common_name = config["common_name"]
    dns_sans = config["dns_sans"]
    fixed_ip_sans = config["fixed_ip_sans"]
    validity_days = config["validity_days"]
    if not isinstance(common_name, str) or not isinstance(dns_sans, list) or not isinstance(fixed_ip_sans, list):
        raise CertificateConfigurationError("staging certificate identity configuration is invalid")
    if not isinstance(validity_days, int) or validity_days <= 0:
        raise CertificateConfigurationError("staging certificate validity configuration is invalid")

    key = rsa.generate_private_key(public_exponent=65537, key_size=3072)
    subject = issuer = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, common_name)])
    now = datetime.now(timezone.utc)
    san_names = [x509.DNSName(name) for name in dns_sans]
    san_names.append(x509.IPAddress(staging_ip))
    san_names.extend(x509.IPAddress(ipaddress.ip_address(value)) for value in fixed_ip_sans)
    certificate = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(minutes=5))
        .not_valid_after(now + timedelta(days=validity_days))
        .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
        .add_extension(
            x509.KeyUsage(
                digital_signature=True,
                content_commitment=False,
                key_encipherment=True,
                data_encipherment=False,
                key_agreement=False,
                key_cert_sign=False,
                crl_sign=False,
                encipher_only=False,
                decipher_only=False,
            ),
            critical=True,
        )
        .add_extension(x509.ExtendedKeyUsage([ExtendedKeyUsageOID.SERVER_AUTH]), critical=False)
        .add_extension(x509.SubjectAlternativeName(san_names), critical=False)
        .add_extension(x509.SubjectKeyIdentifier.from_public_key(key.public_key()), critical=False)
        .sign(private_key=key, algorithm=hashes.SHA256())
    )
    _atomic_write(
        key_path,
        key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        ),
        0o600,
    )
    _atomic_write(cert_path, certificate.public_bytes(serialization.Encoding.PEM), 0o644)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--rotate",
        action="store_true",
        help="replace existing staging certificate material after validating configuration",
    )
    args = parser.parse_args(argv)
    try:
        config = _load_config()
        staging_ip = _staging_ip(config)
        expected_sans = _expected_sans(config, staging_ip)
        cert_path, key_path = _paths(config)
        _prepare_tls_directory(cert_path.parent, key_path)
        if cert_path.exists() != key_path.exists():
            raise CertificateConfigurationError("staging certificate and key must be created or absent together")
        if cert_path.exists() and not args.rotate:
            if _existing_certificate_is_current(cert_path, key_path, expected_sans):
                print(f"staging TLS certificate is current: {cert_path}")
                return 0
            raise CertificateConfigurationError(
                "existing staging certificate does not satisfy the SAN contract; rerun with --rotate"
            )
        _generate(config, staging_ip, cert_path, key_path)
        certificate, _ = _load_existing(cert_path, key_path)
        if _certificate_sans(certificate) != expected_sans:
            raise CertificateConfigurationError("generated certificate SAN contract could not be verified")
        print(f"generated staging TLS certificate and private key in {cert_path.parent}")
        return 0
    except CertificateConfigurationError as exc:
        print(f"staging TLS generation failed: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
