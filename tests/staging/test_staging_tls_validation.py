import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import shutil
import subprocess
import sys
from threading import Thread
import ssl

import pytest
from cryptography import x509
from cryptography.hazmat.primitives import serialization
from cryptography.x509.oid import ExtendedKeyUsageOID

from deployment.staging.scripts.validate_staging_tls import (
    StagingTLSValidationError,
    _validate_server_material,
    _validate_trust_anchor,
    validate,
)


ROOT = Path(__file__).resolve().parents[2]
GENERATOR = ROOT / "deployment" / "staging" / "scripts" / "generate_staging_cert.py"


def _generate_material(tmp_path: Path) -> tuple[Path, Path, Path, Path, Path]:
    environment = os.environ.copy()
    environment["SENTINEL_DNA_STAGING_TLS_DIR"] = str(tmp_path)
    environment["SENTINEL_DNA_STAGING_TLS_IP"] = "192.168.1.115"
    result = subprocess.run(
        [sys.executable, str(GENERATOR)],
        cwd=ROOT,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    return (
        tmp_path / "staging-ca.crt",
        tmp_path / "staging-server.crt",
        tmp_path / "staging-server.key",
        tmp_path / "staging-ca.key",
        tmp_path / "staging-server-fullchain.crt",
    )


class _HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):  # noqa: N802 - required HTTP server hook
        if self.path != "/health":
            self.send_response(404)
            self.end_headers()
            return
        body = b'{"status":"ok"}'
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *_args):
        return


def test_validator_checks_chain_hostname_key_and_health(tmp_path):
    ca_file, certificate_file, private_key_file, _, fullchain_file = _generate_material(tmp_path)
    server = ThreadingHTTPServer(("127.0.0.1", 0), _HealthHandler)
    server_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    server_context.load_cert_chain(str(fullchain_file), str(private_key_file))
    server.socket = server_context.wrap_socket(server.socket, server_side=True)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        result = validate(
            ca_file=ca_file,
            certificate_file=fullchain_file,
            private_key_file=private_key_file,
            connect_host="127.0.0.1",
            server_name="localhost",
            port=server.server_address[1],
            timeout=5,
            health_path="/health",
        )
        curl_executable = shutil.which("curl.exe") or shutil.which("curl")
        if curl_executable:
            curl_result = subprocess.run(
                [
                    curl_executable,
                    "--fail-with-body",
                    "--silent",
                    "--show-error",
                    "--ssl-revoke-best-effort",
                    "--cacert",
                    str(ca_file),
                    f"https://localhost:{server.server_address[1]}/health",
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            assert curl_result.returncode == 0, curl_result.stderr
            assert json.loads(curl_result.stdout)["status"] == "ok"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)

    assert result["status"] == "ok"
    assert result["health"] == {"status": "ok"}
    assert result["tls_protocol"] in {"TLSv1.2", "TLSv1.3"}


def test_validator_rejects_a_mismatched_server_key(tmp_path):
    ca_file, _, _, ca_key_file, fullchain_file = _generate_material(tmp_path)
    ca_certificate = _validate_trust_anchor(ca_file)
    with pytest.raises(StagingTLSValidationError, match="does not match"):
        _validate_server_material(fullchain_file, ca_key_file, ca_certificate, "localhost")


def test_generator_publishes_matching_leaf_pair_and_leaf_first_fullchain(tmp_path):
    ca_file, certificate_file, private_key_file, _, fullchain_file = _generate_material(tmp_path)
    ca_certificate = x509.load_pem_x509_certificate(ca_file.read_bytes())
    certificate = x509.load_pem_x509_certificate(certificate_file.read_bytes())
    private_key = serialization.load_pem_private_key(private_key_file.read_bytes(), password=None)
    fullchain_parts = fullchain_file.read_bytes().split(b"-----END CERTIFICATE-----")
    chain = [
        x509.load_pem_x509_certificate(part + b"-----END CERTIFICATE-----")
        for part in fullchain_parts
        if part.strip()
    ]

    assert len(chain) == 2
    assert chain == [certificate, ca_certificate]
    assert fullchain_file.read_bytes() == certificate_file.read_bytes() + ca_file.read_bytes()
    assert certificate.public_key().public_numbers() == private_key.public_key().public_numbers()
    eku = certificate.extensions.get_extension_for_class(x509.ExtendedKeyUsage).value
    assert ExtendedKeyUsageOID.SERVER_AUTH in eku
    san = certificate.extensions.get_extension_for_class(x509.SubjectAlternativeName).value
    assert "sentinel-dna-staging" in san.get_values_for_type(x509.DNSName)


def test_staging_nginx_mount_sources_the_fullchain_at_its_certificate_path():
    compose = (ROOT / "deployment" / "staging" / "docker-compose.yml").read_text()
    nginx = (ROOT / "deployment" / "staging" / "nginx.conf").read_text()
    assert "staging-server-fullchain.crt" in compose
    assert "target: /etc/nginx/tls/staging-server.crt" in compose
    assert "ssl_certificate /etc/nginx/tls/staging-server.crt;" in nginx
