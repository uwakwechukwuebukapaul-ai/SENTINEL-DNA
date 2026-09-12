"""Generate a private staging CA and a separately signed HTTPS leaf.

The CA is staging-only signing material. Only the leaf certificate and its
private key are consumed by Nginx; the CA private key stays in the protected
staging TLS directory and is never mounted into a container.
"""

from __future__ import annotations

import argparse
import ipaddress
import json
import os
import stat
import subprocess
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
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
        "ca_common_name", "server_common_name", "dns_sans", "fixed_ip_sans",
        "lan_ip_environment_variable", "ca_certificate_filename", "ca_private_key_filename",
        "certificate_filename", "fullchain_certificate_filename", "private_key_filename", "key_algorithm", "key_size",
        "signature_hash", "ca_validity_days", "validity_days",
    }
    if set(config) != required:
        raise CertificateConfigurationError("staging certificate configuration fields are invalid")
    if config["key_algorithm"] != "RSA" or config["key_size"] != 3072:
        raise CertificateConfigurationError("staging certificate key configuration is invalid")
    if config["signature_hash"] != "SHA-256":
        raise CertificateConfigurationError("staging certificate signature configuration is invalid")
    for field in ("ca_common_name", "server_common_name", "lan_ip_environment_variable"):
        if not isinstance(config[field], str) or not config[field].strip():
            raise CertificateConfigurationError("staging certificate identity configuration is invalid")
    for field in ("ca_validity_days", "validity_days"):
        if not isinstance(config[field], int) or config[field] <= 0:
            raise CertificateConfigurationError("staging certificate validity configuration is invalid")
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


def _paths(config: dict[str, object]) -> tuple[Path, Path, Path, Path, Path]:
    directory = _tls_directory()
    names = (config["ca_certificate_filename"], config["ca_private_key_filename"],
             config["certificate_filename"], config["fullchain_certificate_filename"],
             config["private_key_filename"])
    if not all(isinstance(name, str) and name for name in names):
        raise CertificateConfigurationError("staging certificate output filenames are invalid")
    paths = tuple((directory / name).resolve() for name in names)
    if any(path.parent != directory for path in paths) or len(set(paths)) != len(paths):
        raise CertificateConfigurationError("staging certificate output filenames must stay in the TLS directory")
    return paths  # type: ignore[return-value]


def _expected_sans(config: dict[str, object], staging_ip: object) -> set[tuple[str, str]]:
    dns_sans = config["dns_sans"]
    fixed_ip_sans = config["fixed_ip_sans"]
    server_common_name = config["server_common_name"]
    if not isinstance(dns_sans, list) or not isinstance(fixed_ip_sans, list) or not isinstance(server_common_name, str):
        raise CertificateConfigurationError("staging certificate SAN configuration is invalid")
    expected = {("DNS", name) for name in dns_sans if isinstance(name, str)}
    expected.update(("IP", value) for value in fixed_ip_sans if isinstance(value, str))
    expected.add(("IP", str(staging_ip)))
    if ("DNS", server_common_name) not in expected:
        raise CertificateConfigurationError("staging hostname must be present in SAN configuration")
    return expected


def _certificate_sans(certificate: x509.Certificate) -> set[tuple[str, str]]:
    try:
        names = certificate.extensions.get_extension_for_class(x509.SubjectAlternativeName).value
    except x509.ExtensionNotFound as exc:
        raise CertificateConfigurationError("server certificate has no Subject Alternative Name extension") from exc
    return {("DNS", value) for value in names.get_values_for_type(x509.DNSName)} | {
        ("IP", str(value)) for value in names.get_values_for_type(x509.IPAddress)
    }


def _load_pair(cert_path: Path, key_path: Path, role: str) -> tuple[x509.Certificate, rsa.RSAPrivateKey]:
    try:
        certificate = x509.load_pem_x509_certificate(cert_path.read_bytes())
        key = serialization.load_pem_private_key(key_path.read_bytes(), password=None)
    except (OSError, ValueError, TypeError) as exc:
        raise CertificateConfigurationError(f"existing staging {role} certificate or key is unreadable") from exc
    if not isinstance(key, rsa.RSAPrivateKey) or not isinstance(certificate.public_key(), rsa.RSAPublicKey):
        raise CertificateConfigurationError(f"existing staging {role} certificate and key must use RSA")
    if certificate.public_key().public_numbers() != key.public_key().public_numbers():
        raise CertificateConfigurationError(f"existing staging {role} certificate and key do not match")
    return certificate, key


def _extension(certificate: x509.Certificate, extension_type: type):
    try:
        return certificate.extensions.get_extension_for_class(extension_type).value
    except x509.ExtensionNotFound as exc:
        raise CertificateConfigurationError("staging certificate is missing a required extension") from exc


def _verify_rsa_signature(certificate: x509.Certificate, issuer: x509.Certificate) -> None:
    try:
        issuer.public_key().verify(certificate.signature, certificate.tbs_certificate_bytes,
                                   padding.PKCS1v15(), certificate.signature_hash_algorithm)
    except Exception as exc:  # cryptography exposes backend-specific verification errors
        raise CertificateConfigurationError("staging server certificate is not signed by the staging CA") from exc


def _validate_ca(certificate: x509.Certificate, key: rsa.RSAPrivateKey) -> None:
    constraints = _extension(certificate, x509.BasicConstraints)
    if not constraints.ca or constraints.path_length != 0 or certificate.subject != certificate.issuer:
        raise CertificateConfigurationError(
            "staging CA certificate must be self-signed with CA=true and path length 0"
        )
    usage = _extension(certificate, x509.KeyUsage)
    if not usage.key_cert_sign or not usage.crl_sign:
        raise CertificateConfigurationError("staging CA certificate must be allowed to sign certificates")
    _verify_rsa_signature(certificate, certificate)
    if certificate.public_key().public_numbers() != key.public_key().public_numbers():
        raise CertificateConfigurationError("staging CA certificate and key do not match")


def _validate_leaf(certificate: x509.Certificate, key: rsa.RSAPrivateKey,
                   ca_certificate: x509.Certificate, expected_sans: set[tuple[str, str]]) -> None:
    constraints = _extension(certificate, x509.BasicConstraints)
    if constraints.ca:
        raise CertificateConfigurationError("staging server certificate must be a leaf certificate with CA=false")
    usage = _extension(certificate, x509.KeyUsage)
    if not usage.digital_signature or not usage.key_encipherment or usage.key_cert_sign:
        raise CertificateConfigurationError("staging server certificate has invalid key usage")
    eku = _extension(certificate, x509.ExtendedKeyUsage)
    if ExtendedKeyUsageOID.SERVER_AUTH not in eku:
        raise CertificateConfigurationError("staging server certificate must include serverAuth")
    if certificate.issuer != ca_certificate.subject:
        raise CertificateConfigurationError("staging server certificate issuer is not the staging CA")
    _verify_rsa_signature(certificate, ca_certificate)
    if _certificate_sans(certificate) != expected_sans:
        raise CertificateConfigurationError("staging server certificate SAN contract is not satisfied")
    if certificate.public_key().public_numbers() != key.public_key().public_numbers():
        raise CertificateConfigurationError("staging server certificate and key do not match")


def _valid_now(certificate: x509.Certificate) -> bool:
    now = datetime.now(timezone.utc)
    not_before = getattr(certificate, "not_valid_before_utc", certificate.not_valid_before.replace(tzinfo=timezone.utc))
    not_after = getattr(certificate, "not_valid_after_utc", certificate.not_valid_after.replace(tzinfo=timezone.utc))
    return not_before <= now <= not_after


def _load_pem_chain(data: bytes) -> list[x509.Certificate]:
    begin = b"-----BEGIN CERTIFICATE-----"
    end = b"-----END CERTIFICATE-----"
    certificates: list[x509.Certificate] = []
    remainder = data
    while begin in remainder:
        prefix, remainder = remainder.split(begin, 1)
        if prefix.strip():
            raise CertificateConfigurationError("staging fullchain contains unexpected data")
        body, remainder = remainder.split(end, 1) if end in remainder else (b"", b"")
        if not body:
            raise CertificateConfigurationError("staging fullchain contains an incomplete certificate")
        pem = begin + body + end + b"\n"
        try:
            certificates.append(x509.load_pem_x509_certificate(pem))
        except ValueError as exc:
            raise CertificateConfigurationError("staging fullchain contains an unreadable certificate") from exc
    if remainder.strip():
        raise CertificateConfigurationError("staging fullchain contains unexpected data")
    if not certificates:
        raise CertificateConfigurationError("staging fullchain contains no certificates")
    return certificates


def _validate_fullchain(fullchain_path: Path, leaf_certificate: x509.Certificate,
                        ca_certificate: x509.Certificate) -> None:
    try:
        certificates = _load_pem_chain(fullchain_path.read_bytes())
    except OSError as exc:
        raise CertificateConfigurationError("staging fullchain certificate is unreadable") from exc
    if len(certificates) != 2 or certificates[0] != leaf_certificate or certificates[1] != ca_certificate:
        raise CertificateConfigurationError("staging fullchain must contain the leaf certificate followed by the staging CA")


def _existing_material_is_current(paths: tuple[Path, Path, Path, Path, Path], expected_sans: set[tuple[str, str]]) -> bool:
    ca_cert_path, ca_key_path, leaf_cert_path, fullchain_path, leaf_key_path = paths
    if not all(path.is_file() for path in paths):
        return False
    ca_certificate, ca_key = _load_pair(ca_cert_path, ca_key_path, "CA")
    leaf_certificate, leaf_key = _load_pair(leaf_cert_path, leaf_key_path, "server")
    _validate_ca(ca_certificate, ca_key)
    _validate_leaf(leaf_certificate, leaf_key, ca_certificate, expected_sans)
    _validate_fullchain(fullchain_path, leaf_certificate, ca_certificate)
    return _valid_now(ca_certificate) and _valid_now(leaf_certificate)


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


def _atomic_publish(artifacts: list[tuple[Path, bytes, int]]) -> None:
    """Publish a prepared artifact set, restoring old files on write failure."""
    staged: list[tuple[Path, Path, int]] = []
    backups: dict[Path, Path] = {}
    published: list[Path] = []
    try:
        for path, data, mode in artifacts:
            descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
            temporary_path = Path(temporary_name)
            try:
                if hasattr(os, "fchmod"):
                    os.fchmod(descriptor, mode)
                else:
                    os.chmod(temporary_path, mode)
                with os.fdopen(descriptor, "wb") as temporary_file:
                    descriptor = -1
                    temporary_file.write(data)
                    temporary_file.flush()
                    os.fsync(temporary_file.fileno())
                staged.append((path, temporary_path, mode))
            except Exception:
                if descriptor >= 0:
                    os.close(descriptor)
                temporary_path.unlink(missing_ok=True)
                raise

        for path, temporary_path, mode in staged:
            if path.exists():
                descriptor, backup_name = tempfile.mkstemp(prefix=f".{path.name}.backup.", dir=path.parent)
                os.close(descriptor)
                backup_path = Path(backup_name)
                backup_path.unlink()
                os.replace(path, backup_path)
                backups[path] = backup_path
            os.replace(temporary_path, path)
            published.append(path)
            os.chmod(path, mode)

        for backup_path in backups.values():
            backup_path.unlink(missing_ok=True)
    except Exception:
        for path in published:
            path.unlink(missing_ok=True)
        for path, backup_path in backups.items():
            if backup_path.exists():
                os.replace(backup_path, path)
        for _, temporary_path, _ in staged:
            temporary_path.unlink(missing_ok=True)
        raise


def _protect_private_key(path: Path) -> None:
    """Keep private key ACLs limited on Windows, where chmod is advisory."""
    if os.name != "nt" or not path.exists():
        return
    try:
        result = subprocess.run(
            [
                "icacls", str(path), "/inheritance:r", "/grant:r",
                "*S-1-5-32-544:(F)",  # BUILTIN\\Administrators
                "*S-1-5-18:(F)",       # NT AUTHORITY\\SYSTEM
            ],
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError as exc:
        raise CertificateConfigurationError("unable to enforce staging private-key ACLs") from exc
    if result.returncode != 0:
        raise CertificateConfigurationError("unable to enforce staging private-key ACLs")


def _prepare_tls_directory(directory: Path, key_paths: tuple[Path, Path]) -> None:
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    try:
        os.chmod(directory, stat.S_IRWXU)
        for key_path in key_paths:
            if key_path.exists():
                os.chmod(key_path, 0o600)
                _protect_private_key(key_path)
    except OSError as exc:
        raise CertificateConfigurationError("unable to enforce staging TLS file permissions") from exc


def _generate(config: dict[str, object], staging_ip: object, paths: tuple[Path, Path, Path, Path, Path],
              ca_material: tuple[x509.Certificate, rsa.RSAPrivateKey] | None = None) -> None:
    ca_cert_path, ca_key_path, leaf_cert_path, fullchain_path, leaf_key_path = paths
    _prepare_tls_directory(ca_cert_path.parent, (ca_key_path, leaf_key_path))
    ca_common_name = config["ca_common_name"]
    server_common_name = config["server_common_name"]
    dns_sans = config["dns_sans"]
    fixed_ip_sans = config["fixed_ip_sans"]
    ca_validity_days = config["ca_validity_days"]
    leaf_validity_days = config["validity_days"]
    if (not isinstance(ca_common_name, str) or not isinstance(server_common_name, str)
            or not isinstance(dns_sans, list) or not isinstance(fixed_ip_sans, list)
            or not isinstance(ca_validity_days, int) or not isinstance(leaf_validity_days, int)):
        raise CertificateConfigurationError("staging certificate identity or validity configuration is invalid")

    now = datetime.now(timezone.utc)
    if ca_material is None:
        ca_key = rsa.generate_private_key(public_exponent=65537, key_size=3072)
        ca_subject = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, ca_common_name)])
        ca_certificate = (x509.CertificateBuilder().subject_name(ca_subject).issuer_name(ca_subject)
            .public_key(ca_key.public_key()).serial_number(x509.random_serial_number())
            .not_valid_before(now - timedelta(minutes=5)).not_valid_after(now + timedelta(days=ca_validity_days))
            .add_extension(x509.BasicConstraints(ca=True, path_length=0), critical=True)
            .add_extension(x509.KeyUsage(digital_signature=True, content_commitment=False, key_encipherment=False,
                         data_encipherment=False, key_agreement=False, key_cert_sign=True, crl_sign=True,
                         encipher_only=False, decipher_only=False), critical=True)
            .add_extension(x509.SubjectKeyIdentifier.from_public_key(ca_key.public_key()), critical=False)
            .sign(ca_key, hashes.SHA256()))
    else:
        ca_certificate, ca_key = ca_material
        ca_subject = ca_certificate.subject

    leaf_key = rsa.generate_private_key(public_exponent=65537, key_size=3072)
    leaf_subject = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, server_common_name)])
    san_names = [x509.DNSName(name) for name in dns_sans if isinstance(name, str)]
    san_names.append(x509.IPAddress(staging_ip))
    san_names.extend(x509.IPAddress(ipaddress.ip_address(value)) for value in fixed_ip_sans if isinstance(value, str))
    leaf_certificate = (x509.CertificateBuilder().subject_name(leaf_subject).issuer_name(ca_subject)
        .public_key(leaf_key.public_key()).serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(minutes=5)).not_valid_after(now + timedelta(days=leaf_validity_days))
        .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
        .add_extension(x509.KeyUsage(digital_signature=True, content_commitment=False, key_encipherment=True,
                     data_encipherment=False, key_agreement=False, key_cert_sign=False, crl_sign=False,
                     encipher_only=False, decipher_only=False), critical=True)
        .add_extension(x509.ExtendedKeyUsage([ExtendedKeyUsageOID.SERVER_AUTH]), critical=False)
        .add_extension(x509.SubjectAlternativeName(san_names), critical=False)
        .add_extension(x509.AuthorityKeyIdentifier.from_issuer_public_key(ca_key.public_key()), critical=False)
        .sign(ca_key, hashes.SHA256()))

    # Validate the complete in-memory chain before replacing any runtime file.
    _validate_ca(ca_certificate, ca_key)
    _validate_leaf(leaf_certificate, leaf_key, ca_certificate, _expected_sans(config, staging_ip))
    ca_certificate_bytes = ca_certificate.public_bytes(serialization.Encoding.PEM)
    leaf_certificate_bytes = leaf_certificate.public_bytes(serialization.Encoding.PEM)
    fullchain_bytes = leaf_certificate_bytes + ca_certificate_bytes
    _load_pem_chain(fullchain_bytes)
    if ca_material is None:
        artifacts = [
            (ca_key_path, ca_key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
                                               serialization.NoEncryption()), 0o600),
            (ca_cert_path, ca_certificate_bytes, 0o644),
        ]
    else:
        artifacts = []
    # The leaf key and certificate are serialized from the same in-memory key,
    # and all three leaf outputs are staged before any one is replaced.
    artifacts.extend([
        (leaf_key_path, leaf_key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
                                               serialization.NoEncryption()), 0o600),
        (leaf_cert_path, leaf_certificate_bytes, 0o644),
        (fullchain_path, fullchain_bytes, 0o644),
    ])
    _atomic_publish(artifacts)
    if ca_material is None:
        _protect_private_key(ca_key_path)
    _protect_private_key(leaf_key_path)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rotate", action="store_true",
                        help="replace the server certificate while retaining the existing staging CA")
    parser.add_argument("--rotate-ca", action="store_true",
                        help="replace both the staging CA and server certificate material")
    args = parser.parse_args(argv)
    try:
        config = _load_config()
        staging_ip = _staging_ip(config)
        expected_sans = _expected_sans(config, staging_ip)
        paths = _paths(config)
        ca_cert_path, ca_key_path, leaf_cert_path, fullchain_path, leaf_key_path = paths
        _prepare_tls_directory(ca_cert_path.parent, (ca_key_path, leaf_key_path))
        present = [path.exists() for path in paths]
        if any(present) and not all(present):
            raise CertificateConfigurationError("staging CA and server certificate material must be created together")
        if all(present) and not args.rotate and not args.rotate_ca:
            try:
                current = _existing_material_is_current(paths, expected_sans)
            except CertificateConfigurationError:
                current = False
            if current:
                print(f"staging CA and server TLS material are current: {leaf_cert_path}")
                return 0
            raise CertificateConfigurationError(
                "existing staging CA or server certificate does not satisfy the contract; rerun with --rotate")
        ca_material = None
        if all(present) and args.rotate and not args.rotate_ca:
            ca_certificate, ca_key = _load_pair(ca_cert_path, ca_key_path, "CA")
            _validate_ca(ca_certificate, ca_key)
            ca_material = (ca_certificate, ca_key)
        _generate(config, staging_ip, paths, ca_material)
        if not _existing_material_is_current(paths, expected_sans):
            raise CertificateConfigurationError("generated staging certificate chain could not be verified")
        print(f"generated staging CA and server certificate material in {leaf_cert_path.parent}")
        return 0
    except CertificateConfigurationError as exc:
        print(f"staging TLS generation failed: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
