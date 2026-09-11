import threading
from datetime import date, timedelta
import requests
from werkzeug.serving import make_server
from services.auth.providers import TestEmailProvider
from tests.credential_helpers import random_password

def test_canonical_wsgi_http_v3_journey(tmp_path, monkeypatch):
    monkeypatch.setenv("SENTINEL_DNA_DB_PATH", str(tmp_path / "http-v3.sqlite")); monkeypatch.setenv("SENTINEL_DNA_ENV", "testing")
    from app import create_app
    application = create_app(); email = TestEmailProvider(); application.config.update(TESTING=True, EMAIL_PROVIDER=email)
    server = make_server("127.0.0.1", 5000, application); thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
    try:
        client = requests.Session(); base = "http://127.0.0.1:5000"
        password = random_password()
        assert client.get(base + "/login").status_code == 200
        assert client.get(base + "/signup").status_code == 200
        csrf = client.get(base + "/api/auth/csrf").json()["csrf_token"]
        email_request = client.post(base + "/api/auth/email/send-registration-code", json={"email":"http-v3@example.test"}, headers={"X-CSRF-Token":csrf}); assert email_request.status_code == 202
        email_code = email.messages[-1]["code"]
        email_challenge = application.container.require("auth_service").db.connect().execute("SELECT id FROM otp_challenges WHERE purpose='registration_email' ORDER BY created_at DESC LIMIT 1").fetchone()["id"]
        assert client.post(base + "/api/auth/email/verify-registration-code", json={"challenge_id":email_challenge,"code":email_code}, headers={"X-CSRF-Token":csrf}).status_code == 200
        payload={"username":"http-v3","email":"http-v3@example.test","password":password,"country":"GB","email_challenge_id":email_challenge,"date_of_birth":"2000-01-02","role":"admin","tenant_id":"attacker"}
        assert client.post(base + "/api/auth/register", json=payload, headers={"X-CSRF-Token":csrf}).status_code == 201
        assert client.post(base + "/api/auth/login", json={"username":"http-v3","password":password,"remember_me":True}, headers={"X-CSRF-Token":client.get(base+"/api/auth/csrf").json()["csrf_token"]}).status_code == 200
        assert client.get(base + "/profile").status_code == 200
        assert client.get(base + "/workspace/").status_code == 200
        assert client.post(base + "/api/auth/logout").status_code == 403
        assert client.post(base + "/api/auth/logout", headers={"X-CSRF-Token":client.get(base+"/api/auth/csrf").json()["csrf_token"]}).status_code == 200
        assert client.get(base + "/profile").status_code == 401
    finally:
        server.shutdown(); thread.join(timeout=5); server.server_close()
