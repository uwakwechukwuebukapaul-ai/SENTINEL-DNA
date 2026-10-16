import threading
from datetime import date, timedelta
import requests
from werkzeug.serving import make_server
from services.auth.providers import TestSMSProvider, TestEmailProvider
from tests.credential_helpers import random_password
import dashboard.app as dashboard_app
import wsgi
from database.connection import DatabaseConnection, database
from database.migration_runner import MigrationRunner
from services.auth.auth_service import AuthService
from services.auth.mfa import MFAService
from services.identity.canonical_authority import CanonicalAuthorityService

def test_canonical_wsgi_http_v3_journey(tmp_path, monkeypatch):
    db_path = tmp_path / "http-v3.sqlite"
    monkeypatch.setenv("SENTINEL_DNA_DB_PATH", str(db_path)); monkeypatch.setenv("SENTINEL_DNA_ENV", "testing")
    monkeypatch.setattr(dashboard_app, "DB_PATH", db_path)
    application = wsgi.application
    registry = application.container
    keys = ("auth_service", "canonical_authority", "mfa_service")
    previous = {key: registry.get(key) for key in keys}
    old_path = database.database_path
    db = DatabaseConnection(db_path); MigrationRunner(db).run()
    auth = AuthService(db)
    registry.register("auth_service", auth)
    registry.register("canonical_authority", CanonicalAuthorityService(db, auth=auth))
    registry.register("mfa_service", MFAService(db, secret_key_provider=lambda: application.secret_key))
    old_config = {key: application.config.get(key) for key in ("TESTING", "PILOT_ACCESS_REQUIRED", "SMS_PROVIDER", "EMAIL_PROVIDER")}
    sms = TestSMSProvider(); email = TestEmailProvider(); application.config.update(TESTING=True, PILOT_ACCESS_REQUIRED=False, SMS_PROVIDER=sms, EMAIL_PROVIDER=email)
    server = make_server("127.0.0.1", 5000, application); thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
    try:
        client = requests.Session(); base = "http://127.0.0.1:5000"
        password = random_password()
        assert client.get(base + "/login").status_code == 200
        assert client.get(base + "/signup").status_code == 200
        csrf = client.get(base + "/api/auth/csrf").json()["csrf_token"]
        email_request = client.post(base + "/api/auth/email/send-registration-code", json={"email":"http-v3@example.test"}, headers={"X-CSRF-Token":csrf}); assert email_request.status_code == 202
        email_code = email.messages[-1]["code"]
        email_challenge = email_request.json()["challenge_id"]
        assert client.post(base + "/api/auth/email/verify-registration-code", json={"challenge_id":email_challenge,"email":"http-v3@example.test","code":email_code}, headers={"X-CSRF-Token":csrf}).status_code == 200
        send = client.post(base + "/api/auth/phone/send-code", json={"country":"GB","phone":"07911123456"}, headers={"X-CSRF-Token":csrf}); assert send.status_code == 202
        challenge = send.json()["challenge_id"]; code = sms.messages[-1]["code"]
        assert client.post(base + "/api/auth/phone/verify-code", json={"challenge_id":challenge,"code":code}, headers={"X-CSRF-Token":csrf}).status_code == 200
        payload={"username":"http-v3","email":"http-v3@example.test","password":password,"country":"GB","phone":"07911123456","phone_challenge_id":challenge,"email_challenge_id":email_challenge,"date_of_birth":"2000-01-02","role":"admin","tenant_id":"attacker"}
        assert client.post(base + "/api/auth/register", json=payload, headers={"X-CSRF-Token":csrf}).status_code == 201
        assert client.post(base + "/api/auth/login", json={"username":"http-v3","password":password,"remember_me":True}, headers={"X-CSRF-Token":client.get(base+"/api/auth/csrf").json()["csrf_token"]}).status_code == 200
        assert client.get(base + "/profile").status_code == 200
        assert client.get(base + "/workspace/").status_code == 200
        assert client.post(base + "/api/auth/logout").status_code == 403
        assert client.post(base + "/api/auth/logout", headers={"X-CSRF-Token":client.get(base+"/api/auth/csrf").json()["csrf_token"]}).status_code == 200
        assert client.get(base + "/profile").status_code == 401
    finally:
        server.shutdown(); thread.join(timeout=5); server.server_close()
        for key, value in previous.items(): registry.register(key, value)
        application.config.update(old_config)
        database.database_path = old_path
