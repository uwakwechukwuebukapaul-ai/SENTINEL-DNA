"""Canonical Authentication V3 HTTP boundary."""
from datetime import datetime, timedelta, timezone
import secrets
import hashlib
from uuid import uuid4
from flask import Blueprint, current_app, g, jsonify, redirect, request, session, url_for
from database.errors import DatabaseError
from database.portability import integrity_error
from .age import validate_minimum_age
from .oauth import GoogleOIDC
from .phone import country_options, normalize_phone
from .providers import email_provider
from .security import csrf_token
from .security import verify_password
from .onboarding import OnboardingState
from .mfa import decrypt_totp_secret, encrypt_totp_secret, generate_totp_secret, provisioning_uri, verify_totp
from .webauthn import WebAuthnError, WebAuthnService

auth_api = Blueprint("auth_api", __name__, url_prefix="/api/auth")
REMEMBER_COOKIE = "sentinel_remember"
def _service(): return current_app.container.require("auth_service")
def _audit(event, *, user_id=None, method=None, outcome=None, reason=None):
    try:
        _service().audit_event(event, user_id=user_id, actor_id=session.get("actor_id"), tenant_id=session.get("organization_id"), method=method, outcome=outcome, reason=reason, source_ip=request.remote_addr)
    except Exception:
        current_app.logger.warning("authentication audit write failed", exc_info=True)
def _allowed(bucket, limit, window):
    allowed = _service().rate_allow(
        bucket,
        limit=limit,
        window_seconds=window,
        tenant_id=session.get("organization_id"),
        actor_id=session.get("actor_id"),
        ip_address=request.remote_addr,
        endpoint="/api/auth",
        operation=bucket,
        cost_class="authentication",
    )
    if not allowed: _audit("rate_limit_triggered", method=bucket.split("|", 1)[0], outcome="rejected", reason="limit_exceeded")
    return allowed
def _csrf_ok():
    expected = session.get("csrf_token"); supplied = request.headers.get("X-CSRF-Token") or request.form.get("csrf_token")
    if expected and supplied and secrets.compare_digest(str(expected), str(supplied)): return True
    # JSON API compatibility is deliberately limited to requests that cannot be
    # browser CSRF submissions: JSON content type and no cross-origin metadata.
    # Browser UI requests still send the synchronizer token explicitly.
    return bool(request.is_json and not request.headers.get("Origin") and not request.headers.get("Referer"))
def _ensure_csrf():
    if "csrf_token" not in session: session["csrf_token"] = csrf_token()
    return session["csrf_token"]

def _strict_csrf():
    expected = session.get("csrf_token")
    supplied = request.headers.get("X-CSRF-Token") or request.form.get("csrf_token")
    return bool(expected and supplied and secrets.compare_digest(str(expected), str(supplied)))

def _webauthn_service() -> WebAuthnService:
    return WebAuthnService(_service().db)

def _mfa_user():
    return _service().session_user(session.get("user_id"), session.get("session_version"))

def _mfa_authenticated():
    user = _mfa_user()
    return user if user and (not _service().mfa_enabled(user.id) or session.get("mfa_verified")) else None

def _organization_service():
    return current_app.container.get("organization_membership_service")

def _otp_binding():
    """Bind browser OTP challenges to the current signed auth flow."""
    binding = session.get("auth_otp_binding")
    if not binding:
        binding = secrets.token_urlsafe(32)
        session["auth_otp_binding"] = binding
    return binding
def _bind(user):
    authority = current_app.container.require("canonical_authority")
    identity = authority.identities.get_by_email(user.email) or authority.identities.create(user.email, display_name=user.username, actor_id=user.actor_id or f"user-{user.id}")
    memberships = [m for m in authority.memberships.list_for_actor(identity.actor_id) if m.status == "active"]
    if not memberships:
        tenant = authority.tenants.create(f"{user.username} workspace", tenant_id=user.tenant_id or f"tenant-{user.id}")
        memberships = [authority.memberships.add(tenant.tenant_id, identity.actor_id, str(user.role).lower())]
    membership = sorted(memberships, key=lambda item: item.tenant_id)[0]
    with _service().db.session() as connection:
        connection.execute("UPDATE users SET actor_id=?, tenant_id=? WHERE id=?", (identity.actor_id, membership.tenant_id, user.id))
    return identity, membership
def _login_session(user, remember=False, auth_method="password"):
    identity, membership = _bind(user); session.clear(); session.update(user_id=user.id, session_version=user.session_version, actor_id=identity.actor_id, organization_id=membership.tenant_id, canonical_principal={"actor_id": identity.actor_id, "tenant_id": membership.tenant_id}, csrf_token=csrf_token(), auth_time=datetime.now(timezone.utc).isoformat(), mfa_verified=not _service().mfa_enabled(user.id))
    if remember:
        raw = secrets.token_urlsafe(48); sid = secrets.token_urlsafe(18); expires = datetime.now(timezone.utc) + timedelta(days=30)
        _service().create_persistent_session(user, raw, membership.tenant_id, sid, expires.isoformat(), user_agent=request.user_agent.string[:256], ip_address=request.remote_addr, auth_method=auth_method); session["persistent_session_id"] = sid; session.permanent = True
        g.remember_cookie = f"{sid}.{raw}"
        _audit("persistent_session_created", user_id=user.id, method="remember_me", outcome="success")
    else:
        g.clear_remember_cookie = True
    _audit("login_success", user_id=user.id, method=auth_method, outcome="success")
    payload = user.public()
    if _service().mfa_enabled(user.id): payload["mfa_required"] = True
    return payload

def restore_persistent_session():
    if session.get("user_id") or not request.cookies.get(REMEMBER_COOKIE): return
    value = request.cookies.get(REMEMBER_COOKIE, "")
    if "." not in value:
        g.clear_remember_cookie = True
        return
    sid, raw = value.split(".", 1)
    user = _service().resolve_persistent_session(sid, raw)
    if not user:
        g.clear_remember_cookie = True
        g.session_revoked = True
        return
    _service().revoke_persistent_session(sid)
    _login_session(user, remember=True, auth_method="remember_me")
    _audit("remember_me_authentication", user_id=user.id, method="remember_me", outcome="success")


def enforce_current_session():
    """Reject signed sessions whose user authentication epoch is stale."""
    user_id = session.get("user_id")
    if user_id and _service().session_user(user_id, session.get("session_version")) is None:
        g.clear_remember_cookie = True
        session.clear()

def _mfa_secret_row(user_id):
    with _service().db.session() as connection:
        return connection.execute("SELECT secret_encrypted FROM auth_mfa WHERE user_id=?", (user_id,)).fetchone()

@auth_api.post("/mfa/setup/start")
def mfa_setup_start():
    if not _strict_csrf(): return jsonify({"error": "csrf_validation_failed"}), 403
    user = _mfa_user()
    if user is None or _service().mfa_enabled(user.id): return jsonify({"error": "forbidden"}), 403
    secret = generate_totp_secret(); now = datetime.now(timezone.utc).isoformat()
    with _service().db.session() as connection:
        connection.execute("INSERT INTO auth_mfa(user_id,secret_encrypted,enabled,created_at,updated_at) VALUES(?,?,?,?,?) ON CONFLICT(user_id) DO UPDATE SET secret_encrypted=excluded.secret_encrypted,enabled=0,updated_at=excluded.updated_at", (user.id, encrypt_totp_secret(secret, current_app.config["SECRET_KEY"]), 0, now, now))
    session["mfa_enrollment_pending"] = True
    return jsonify({"provisioning_uri": provisioning_uri(secret, account_name=user.email)})

@auth_api.post("/mfa/setup/verify")
def mfa_setup_verify():
    if not _strict_csrf(): return jsonify({"error": "csrf_validation_failed"}), 403
    user = _mfa_user(); code = str((request.get_json(silent=True) or {}).get("code", ""))
    row = _mfa_secret_row(user.id) if user and session.get("mfa_enrollment_pending") else None
    if not row or not verify_totp(decrypt_totp_secret(row["secret_encrypted"], current_app.config["SECRET_KEY"]), code): return jsonify({"error": "mfa_verification_failed"}), 401
    now = datetime.now(timezone.utc).isoformat(); recovery_codes = [secrets.token_urlsafe(8) for _ in range(10)]
    with _service().db.session() as connection:
        connection.execute("UPDATE auth_mfa SET enabled=1,updated_at=? WHERE user_id=?", (now, user.id))
        for recovery in recovery_codes: connection.execute("INSERT INTO auth_mfa_recovery_codes(id,user_id,code_hash,created_at) VALUES(?,?,?,?)", (str(uuid4()), user.id, hashlib.sha256(recovery.encode()).hexdigest(), now))
        connection.execute("UPDATE users SET session_version=session_version+1 WHERE id=?", (user.id,))
        connection.execute("UPDATE persistent_sessions SET revoked_at=? WHERE user_id=? AND revoked_at IS NULL", (now, user.id))
    session["mfa_enrollment_pending"] = False; session["mfa_verified"] = False
    return jsonify({"mfa_enrollment_verified": True, "recovery_codes": recovery_codes})

@auth_api.post("/mfa/verify")
def mfa_verify():
    if not _strict_csrf(): return jsonify({"error": "csrf_validation_failed"}), 403
    user = _mfa_user(); row = _mfa_secret_row(user.id) if user else None
    code = str((request.get_json(silent=True) or {}).get("code", ""))
    if not row or not _service().mfa_enabled(user.id) or not verify_totp(decrypt_totp_secret(row["secret_encrypted"], current_app.config["SECRET_KEY"]), code): return jsonify({"error": "mfa_verification_failed"}), 401
    session["mfa_verified"] = True
    return jsonify({"mfa_verified": True})

@auth_api.post("/mfa/recovery")
def mfa_recovery():
    if not _strict_csrf(): return jsonify({"error": "csrf_validation_failed"}), 403
    user = _mfa_user(); code = str((request.get_json(silent=True) or {}).get("code", ""))
    if not user: return jsonify({"error": "authentication_required"}), 401
    now = datetime.now(timezone.utc).isoformat(); digest = hashlib.sha256(code.encode()).hexdigest()
    with _service().db.session() as connection:
        row = connection.execute("SELECT id FROM auth_mfa_recovery_codes WHERE user_id=? AND code_hash=? AND used_at IS NULL", (user.id, digest)).fetchone()
        if not row: return jsonify({"error": "mfa_recovery_invalid"}), 401
        connection.execute("UPDATE auth_mfa_recovery_codes SET used_at=? WHERE id=?", (now, row["id"]))
    session["mfa_verified"] = True
    return jsonify({"mfa_verified": True})

@auth_api.post("/mfa/disable")
def mfa_disable():
    if not _strict_csrf(): return jsonify({"error": "csrf_validation_failed"}), 403
    user = _mfa_user(); data = request.get_json(silent=True) or {}; row = _mfa_secret_row(user.id) if user else None
    if not user or not row or not verify_password(user.password_hash, str(data.get("password", ""))) or not verify_totp(decrypt_totp_secret(row["secret_encrypted"], current_app.config["SECRET_KEY"]), str(data.get("code", ""))): return jsonify({"error": "mfa_disable_failed"}), 401
    with _service().db.session() as connection:
        connection.execute("UPDATE auth_mfa SET enabled=0,updated_at=? WHERE user_id=?", (datetime.now(timezone.utc).isoformat(), user.id))
        connection.execute("DELETE FROM auth_mfa_recovery_codes WHERE user_id=?", (user.id,))
    session["mfa_verified"] = True
    return jsonify({"mfa_enabled": False})

@auth_api.post("/register")
def register():
    if current_app.config.get("PILOT_ACCESS_REQUIRED", False):
        return jsonify({"error": "registration_unavailable"}), 403
    if not _csrf_ok(): return jsonify({"error": "csrf_validation_failed"}), 403
    data = request.get_json(silent=True) or {}
    organizations = _organization_service()
    organization_decision = organizations.inspect_email(str(data.get("email", ""))) if organizations else None
    organization_pending = bool(organization_decision and organization_decision.existing_verified_active and organization_decision.enrollment_policy != "VERIFIED_DOMAIN_AUTO_JOIN")
    if organization_pending and not (data.get("date_of_birth") or data.get("phone")):
        return jsonify({"error": "organization_approval_required"}), 400
    if not _allowed("signup", 12, 3600): return jsonify({"error": "registration_unavailable"}), 429
    _audit("signup_started", method="password", outcome="started")
    try:
        # Explicit migration boundary: legacy JSON callers remain compatible
        # until a versioned API contract replaces this path. Browser-style
        # registration always requires email and phone verification below.
        legacy_api = (current_app.config.get("AUTH_LEGACY_JSON_COMPAT", True) and request.is_json and not data.get("date_of_birth") and not data.get("phone")) or organization_pending
        dob = validate_minimum_age(data.get("date_of_birth")) if data.get("date_of_birth") else None
        phone = normalize_phone(data.get("country", ""), data.get("phone", "")) if data.get("phone") else None
        email_verified_at = None
        if not legacy_api:
            email_challenge_id = data.get("email_challenge_id")
            if email_challenge_id == "pending": email_challenge_id = session.get("registration_email_challenge_id")
            expected_email = str(data.get("email", "")).strip().lower()
            if session.get("registration_email_verified") != expected_email:
                raise ValueError("verification_required")
            if session.get("registration_phone_verified") != phone:
                raise ValueError("verification_required")
            with _service().db.session() as connection:
                binding = _otp_binding()
                verified = connection.execute("SELECT 1 FROM otp_challenges WHERE id=? AND purpose='registration_phone' AND consumed_at IS NOT NULL AND destination=? AND session_binding=?", (data.get("phone_challenge_id"), phone, binding)).fetchone()
                email_verified = connection.execute("SELECT 1 FROM otp_challenges WHERE id=? AND purpose='registration_email' AND consumed_at IS NOT NULL AND destination=? AND session_binding=?", (email_challenge_id, expected_email, binding)).fetchone()
            if not verified or not email_verified: raise ValueError("verification_required")
            email_verified_at = datetime.now(timezone.utc).isoformat()
        user = _service().register(
            data.get("username", ""), data.get("email", ""), data.get("password", ""),
            "analyst", phone_number=phone, date_of_birth=dob,
            email_verified_at=email_verified_at,
            phone_verified_at=(datetime.now(timezone.utc).isoformat() if not legacy_api else None),
            onboarding_state=(OnboardingState.AUTHENTICATED if legacy_api else OnboardingState.NEW),
        )
    except DatabaseError: return jsonify({"error": "registration_unavailable"}), 409
    except Exception as exc:
        if integrity_error(exc): return jsonify({"error": "registration_unavailable"}), 409
        _audit("signup_failed", method="password", outcome="failure", reason="invalid_registration")
        return jsonify({"error": "invalid_registration"}), 400
    try:
        if organization_pending:
            with _service().db.session() as connection:
                connection.execute("UPDATE users SET onboarding_state=? WHERE id=?", (OnboardingState.ORGANIZATION_MEMBERSHIP_PENDING, user.id))
            if organizations:
                organizations.ensure_user_identity(user.id)
                organizations.create_join_request(user.id, organization_decision.tenant_id)
            for key in ("auth_otp_binding", "registration_email_challenge_id", "registration_email_verified", "registration_phone_verified"):
                session.pop(key, None)
            return jsonify({"status": "organization_approval_required"}), 202
        _bind(user)
        if not legacy_api:
            user = _service().complete_verified_onboarding(user.id)
            if user is None or user.onboarding_state != OnboardingState.AUTHENTICATED:
                raise RuntimeError("onboarding_completion_failed")
    except Exception:
        with _service().db.session() as connection: connection.execute("DELETE FROM users WHERE id=?", (user.id,))
        return jsonify({"error": "registration_unavailable"}), 500
    for key in ("auth_otp_binding", "registration_email_challenge_id", "registration_email_verified", "registration_phone_verified"):
        session.pop(key, None)
    _audit("signup_verified", user_id=user.id, method="password", outcome="success")
    return jsonify(user.public()), 201

@auth_api.post("/login")
def login():
    if not _csrf_ok(): return jsonify({"error": "csrf_validation_failed"}), 403
    data = request.get_json(silent=True) or {}
    if not _allowed(f"login|{str(data.get('username', '')).strip().lower()}", 10, 300): return jsonify({"error": "invalid_credentials"}), 429
    user = _service().authenticate(data.get("username", ""), data.get("password", ""))
    if not user:
        _audit("login_failure", method="password", outcome="failure", reason="invalid_credentials")
        return jsonify({"error": "invalid_credentials"}), 401
    return jsonify(_login_session(user, bool(data.get("remember_me"))))

@auth_api.get("/csrf")
def csrf(): return jsonify({"csrf_token": _ensure_csrf()})

@auth_api.post("/logout")
def logout():
    if not _csrf_ok(): return jsonify({"error": "csrf_validation_failed"}), 403
    remembered = session.get("persistent_session_id")
    if remembered: _service().revoke_persistent_session(remembered)
    g.clear_remember_cookie = True
    _audit("logout", user_id=session.get("user_id"), method="session", outcome="success")
    session.clear()
    if request.form.get("csrf_token") is not None: return redirect(url_for("browser.login_page", signed_out="true"))
    return jsonify({"status": "logged_out"})

@auth_api.get("/me")
def me():
    user = _service().session_user(session.get("user_id"), session.get("session_version"))
    return jsonify(user.public()) if user and _mfa_authenticated() else (jsonify({"error": "authentication_required"}), 401)

@auth_api.post("/passkey/options")
def passkey_options():
    """Start a server-bound WebAuthn ceremony; no browser assertion is trusted."""
    if not _strict_csrf(): return jsonify({"error": "csrf_validation_failed"}), 403
    user = _mfa_user()
    if not user: return jsonify({"error": "authentication_required"}), 401
    purpose = str((request.get_json(silent=True) or {}).get("purpose", "registration"))
    try: challenge = _webauthn_service().create_challenge(user.id, purpose)
    except WebAuthnError: return jsonify({"error": "webauthn_unavailable"}), 503
    _audit("passkey_ceremony_started", user_id=user.id, method="webauthn", outcome="started", reason=purpose)
    return jsonify({"challenge": challenge, "credentials": _webauthn_service().credentials_for_user(user.id)})

@auth_api.post("/passkey/register")
def passkey_register():
    if not _strict_csrf(): return jsonify({"error": "csrf_validation_failed"}), 403
    user = _mfa_user(); data = request.get_json(silent=True) or {}
    if not user: return jsonify({"error": "authentication_required"}), 401
    if not _webauthn_service().consume_challenge(user.id, "registration", str(data.get("challenge", ""))): return jsonify({"error": "webauthn_challenge_invalid"}), 400
    verifier = current_app.config.get("WEBAUTHN_REGISTRATION_VERIFIER")
    if not callable(verifier): return jsonify({"error": "webauthn_unavailable"}), 503
    try:
        credential = verifier(data, user)
        _webauthn_service().register_credential(user.id, str(credential["credential_id"]), str(credential["public_key"]), int(credential.get("sign_count", 0)))
    except Exception:
        _audit("passkey_registration_failed", user_id=user.id, method="webauthn", outcome="failure", reason="assertion_invalid")
        return jsonify({"error": "webauthn_registration_failed"}), 400
    _audit("passkey_registered", user_id=user.id, method="webauthn", outcome="success")
    return jsonify({"status": "registered"}), 201

@auth_api.post("/passkey/authenticate")
def passkey_authenticate():
    if not _strict_csrf(): return jsonify({"error": "csrf_validation_failed"}), 403
    data = request.get_json(silent=True) or {}; username = str(data.get("username", "")).strip()
    user = _service().get_by_username(username) or _service().get_by_email(username)
    if not user or not user.is_active: return jsonify({"error": "authentication_failed"}), 401
    if not _webauthn_service().consume_challenge(user.id, "authentication", str(data.get("challenge", ""))): return jsonify({"error": "webauthn_challenge_invalid"}), 400
    verifier = current_app.config.get("WEBAUTHN_AUTHENTICATION_VERIFIER")
    if not callable(verifier): return jsonify({"error": "webauthn_unavailable"}), 503
    try:
        credential_id = str(verifier(data, user))
        if not any(item["credential_id"] == credential_id and not item["revoked_at"] for item in _webauthn_service().credentials_for_user(user.id)): raise ValueError("credential_denied")
    except Exception:
        _audit("passkey_authentication_failed", user_id=user.id, method="webauthn", outcome="failure", reason="assertion_invalid")
        return jsonify({"error": "authentication_failed"}), 401
    _audit("passkey_authentication_success", user_id=user.id, method="webauthn", outcome="success")
    return jsonify(_login_session(user, auth_method="webauthn"))

@auth_api.get("/sessions")
def sessions():
    user_id = session.get("user_id")
    if not user_id or _mfa_authenticated() is None: return jsonify({"error": "authentication_required"}), 401
    current = session.get("persistent_session_id")
    result = []
    for item in _service().list_sessions(user_id):
        item["current"] = item["id"] == current
        item.pop("id", None); item.pop("user_id", None); item.pop("tenant_id", None); item.pop("ip_address", None)
        result.append(item)
    return jsonify({"sessions": result})

@auth_api.post("/sessions/revoke")
def revoke_session():
    if not _csrf_ok(): return jsonify({"error": "csrf_validation_failed"}), 403
    user_id = session.get("user_id")
    if not user_id: return jsonify({"error": "authentication_required"}), 401
    session_id = str((request.get_json(silent=True) or {}).get("session_id", ""))
    if not session_id or session_id == session.get("persistent_session_id"): return jsonify({"error": "current_session_protected"}), 409
    if not _service().revoke_owned_session(user_id, session_id): return jsonify({"error": "session_not_found"}), 404
    _audit("persistent_session_revoked", user_id=user_id, method="session_management", outcome="success")
    return jsonify({"status": "revoked"})

@auth_api.post("/sessions/revoke-others")
def revoke_other_sessions():
    if not _csrf_ok(): return jsonify({"error": "csrf_validation_failed"}), 403
    user_id = session.get("user_id")
    if not user_id: return jsonify({"error": "authentication_required"}), 401
    count = _service().revoke_other_sessions(user_id, session.get("persistent_session_id"))
    _audit("all_sessions_revoked", user_id=user_id, method="session_management", outcome="success")
    return jsonify({"revoked": count})

@auth_api.post("/email/send-code")
def email_send_code():
    if not _csrf_ok(): return jsonify({"error": "csrf_validation_failed"}), 403
    destination = str((request.get_json(silent=True) or {}).get("email", "")).strip().lower()
    if not _allowed(f"email-otp|{destination}", 5, 3600): return jsonify({"message": "If the account is eligible, a verification code has been sent."}), 202
    try:
        provider = current_app.config.get("EMAIL_PROVIDER") or email_provider(testing=current_app.testing)
        user = _service().get_by_id(None)
        with _service().db.session() as connection:
            row = connection.execute("SELECT id FROM users WHERE email=? AND is_active=1", (destination,)).fetchone()
        challenge, code = _service().issue_otp(destination, "login_email_otp", user_id=row["id"] if row else None, secret=current_app.secret_key, session_binding=_otp_binding())
        # Keep the opaque challenge server-side.  The response remains generic
        # to avoid account enumeration and never exposes a challenge handle.
        session["login_email_challenge_id"] = challenge
        delivery = provider.send_code(destination, code, "login_email_otp")
        if not delivery.accepted: raise RuntimeError("email_delivery_failed")
        with _service().db.session() as connection: connection.execute("UPDATE otp_challenges SET provider_request_id=? WHERE id=?", (delivery.provider_request_id, challenge))
        _audit("email_otp_requested", user_id=row["id"] if row else None, method="email_otp", outcome="success")
    except Exception: pass
    return jsonify({"message": "If the account is eligible, a verification code has been sent."}), 202

@auth_api.post("/email/send-registration-code")
def email_send_registration_code():
    if not _csrf_ok(): return jsonify({"error": "csrf_validation_failed"}), 403
    destination = str((request.get_json(silent=True) or {}).get("email", "")).strip().lower()
    if not _allowed(f"email-registration|{destination}", 5, 3600): return jsonify({"message": "If eligible, a verification code has been sent."}), 202
    try:
        provider = current_app.config.get("EMAIL_PROVIDER") or email_provider(testing=current_app.testing)
        challenge, code = _service().issue_otp(destination, "registration_email", secret=current_app.secret_key, session_binding=_otp_binding())
        delivery = provider.send_code(destination, code, "registration_email")
        if not delivery.accepted: raise RuntimeError("email_delivery_failed")
        with _service().db.session() as connection: connection.execute("UPDATE otp_challenges SET provider_request_id=? WHERE id=?", (delivery.provider_request_id, challenge))
        session["registration_email_challenge_id"] = challenge
    except Exception: return jsonify({"message": "If eligible, a verification code has been sent."}), 202
    _audit("email_verification_requested", method="email_otp", outcome="success")
    return jsonify({"message": "If eligible, a verification code has been sent.", "challenge_id": challenge}), 202

@auth_api.post("/email/verify-registration-code")
def email_verify_registration_code():
    if not _csrf_ok(): return jsonify({"error": "csrf_validation_failed"}), 403
    data = request.get_json(silent=True) or {}; challenge_id = data.get("challenge_id") or session.get("registration_email_challenge_id")
    if not _allowed("email-registration-verify", 10, 600): return jsonify({"error": "verification_failed"}), 400
    _service().verify_otp(challenge_id, data.get("code", ""), secret=current_app.secret_key, session_binding=_otp_binding())
    with _service().db.session() as connection: row = connection.execute("SELECT destination,consumed_at FROM otp_challenges WHERE id=? AND purpose='registration_email' AND session_binding=?", (challenge_id, _otp_binding())).fetchone()
    verified = bool(row and row["consumed_at"])
    if verified: session["registration_email_verified"] = row["destination"]; _audit("email_verified", method="email_otp", outcome="success")
    else: _audit("email_verification_failed", method="email_otp", outcome="failure", reason="invalid_or_expired")
    return jsonify({"verified": verified}), 200 if verified else 400

@auth_api.post("/email/verify-code")
def email_verify_code():
    if not _csrf_ok(): return jsonify({"error": "csrf_validation_failed"}), 403
    if not _allowed("email-otp-verify", 10, 600): return jsonify({"error": "verification_failed"}), 400
    data = request.get_json(silent=True) or {}; challenge_id = data.get("challenge_id") or session.get("login_email_challenge_id"); user_id = _service().verify_otp(challenge_id, data.get("code", ""), secret=current_app.secret_key, session_binding=_otp_binding())
    if not user_id: return jsonify({"error": "verification_failed"}), 400
    user = _service().get_by_id(user_id)
    if not user: _audit("email_otp_failed", method="email_otp", outcome="failure", reason="invalid_or_expired")
    else: _audit("email_otp_verified", user_id=user.id, method="email_otp", outcome="success")
    if not user: return jsonify({"error": "verification_failed"}), 400
    session.pop("login_email_challenge_id", None)
    return jsonify(_login_session(user, bool(data.get("remember_me"))))

@auth_api.post("/password-reset/request")
def password_reset_request():
    if not _csrf_ok(): return jsonify({"error": "csrf_validation_failed"}), 403
    destination = str((request.get_json(silent=True) or {}).get("email", "")).strip().lower()
    if not _allowed(f"password-reset|{destination}", 5, 3600): return jsonify({"message": "If the account is eligible, recovery instructions have been sent."}), 202
    try:
        with _service().db.session() as connection: row = connection.execute("SELECT id FROM users WHERE email=? AND is_active=1", (destination,)).fetchone()
        provider = current_app.config.get("EMAIL_PROVIDER") or email_provider(testing=current_app.testing)
        challenge, code = _service().issue_otp(destination, "password_reset", user_id=row["id"] if row else None, secret=current_app.secret_key, session_binding=_otp_binding())
        session["recovery_challenge_id"] = challenge
        delivery = provider.send_code(destination, code, "password_reset")
        with _service().db.session() as connection: connection.execute("UPDATE otp_challenges SET provider_request_id=? WHERE id=?", (delivery.provider_request_id, challenge))
        _audit("password_reset_requested", user_id=row["id"] if row else None, method="email_otp", outcome="success")
    except Exception: pass
    return jsonify({"message": "If the account is eligible, recovery instructions have been sent."}), 202

@auth_api.post("/password-reset/confirm")
def password_reset_confirm():
    if not _csrf_ok(): return jsonify({"error": "csrf_validation_failed"}), 403
    if not _allowed("password-reset-verify", 10, 600): return jsonify({"error": "recovery_failed"}), 400
    data = request.get_json(silent=True) or {}; user_id = _service().verify_otp(data.get("challenge_id") or session.get("recovery_challenge_id"), data.get("code", ""), secret=current_app.secret_key, session_binding=_otp_binding())
    if not user_id: return jsonify({"error": "recovery_failed"}), 400
    try: _service().reset_password(user_id, data.get("password", ""))
    except ValueError: return jsonify({"error": "recovery_failed"}), 400
    _audit("password_reset_success", user_id=user_id, method="email_otp", outcome="success")
    session.pop("recovery_challenge_id", None)
    g.clear_remember_cookie = True
    session.clear()
    session["csrf_token"] = csrf_token()
    return jsonify({"status": "password_reset"})

@auth_api.post("/phone/send-code")
def phone_send_code():
    if not _csrf_ok(): return jsonify({"error": "csrf_validation_failed"}), 403
    data = request.get_json(silent=True) or {}
    if not _allowed("phone-otp", 5, 3600): return jsonify({"error": "verification_unavailable"}), 429
    try:
        phone = normalize_phone(data.get("country", ""), data.get("phone", "")); provider = current_app.config.get("SMS_PROVIDER")
        if provider is None: from .providers import sms_provider; provider = sms_provider(testing=current_app.testing)
        challenge, code = _service().issue_otp(phone, "registration_phone", secret=current_app.secret_key, session_binding=_otp_binding())
        delivery = provider.send_code(phone, code, "registration_phone")
        with _service().db.session() as connection: connection.execute("UPDATE otp_challenges SET provider_request_id=? WHERE id=?", (delivery.provider_request_id, challenge))
        return jsonify({"challenge_id": challenge, "phone": phone}), 202
    except Exception: return jsonify({"error": "verification_unavailable"}), 400

@auth_api.post("/phone/verify-code")
def phone_verify_code():
    if not _csrf_ok(): return jsonify({"error": "csrf_validation_failed"}), 403
    if not _allowed("phone-otp-verify", 10, 600): return jsonify({"error": "verification_failed"}), 400
    data = request.get_json(silent=True) or {}; _service().verify_otp(data.get("challenge_id"), data.get("code", ""), secret=current_app.secret_key, session_binding=_otp_binding())
    with _service().db.session() as connection: row = connection.execute("SELECT destination,consumed_at FROM otp_challenges WHERE id=? AND purpose='registration_phone' AND session_binding=?", (data.get("challenge_id"), _otp_binding())).fetchone()
    verified = bool(row and row["consumed_at"])
    if verified: session["registration_phone_verified"] = row["destination"]
    _audit("phone_otp_success" if verified else "phone_otp_failed", method="phone_otp", outcome="success" if verified else "failure")
    return jsonify({"verified": verified}), 200 if verified else 400

@auth_api.get("/countries")
def countries(): return jsonify({"countries": country_options()})

@auth_api.get("/google/start")
def google_start():
    if not _allowed("google-start", 20, 300): return jsonify({"error": "google_authentication_unavailable"}), 429
    _audit("google_login_started", method="google", outcome="started")
    try:
        location, state, nonce = GoogleOIDC().begin()
        session["google_state"], session["google_nonce"] = state, nonce
        return redirect(location)
    except RuntimeError:
        _audit("google_login_failure", method="google", outcome="failure", reason="provider_unavailable")
        return jsonify({"error": "google_authentication_unavailable"}), 503

@auth_api.post("/google/link")
def google_link():
    if not _csrf_ok(): return jsonify({"error": "csrf_validation_failed"}), 403
    if not session.get("user_id"): return jsonify({"error": "authentication_required"}), 401
    try:
        location, state, nonce = GoogleOIDC().begin(); session["google_state"], session["google_nonce"], session["google_link_user"] = state, nonce, session["user_id"]; return redirect(location)
    except RuntimeError: return jsonify({"error": "google_authentication_unavailable"}), 503

@auth_api.post("/google/unlink")
def google_unlink():
    if not _csrf_ok(): return jsonify({"error": "csrf_validation_failed"}), 403
    user_id = session.get("user_id")
    if not user_id: return jsonify({"error": "authentication_required"}), 401
    identities = _service().identities_for_user(user_id)
    google = [item for item in identities if item["provider"] == "google"]
    if not google: return jsonify({"error": "identity_not_linked"}), 404
    usable = [item for item in identities if item["provider"] in {"password", "email_otp", "phone_otp"}]
    user = _service().get_by_id(user_id)
    if not usable and not (user and user.phone_verified_at):
        return jsonify({"error": "authentication_method_required"}), 409
    _service().remove_identity(user_id, "google", google[0]["provider_subject"])
    _audit("google_identity_unlinked", user_id=user_id, method="google", outcome="success")
    return jsonify({"status": "unlinked"})

@auth_api.get("/google/callback")
def google_callback():
    try:
        state = session.pop("google_state", ""); nonce = session.pop("google_nonce", "")
        claims = GoogleOIDC().complete(request.args.get("code"), request.args.get("state"), state, nonce, nonce)
        user = _service().identity_user("google", claims.subject)
        link_user_id = session.pop("google_link_user", None)
        if link_user_id:
            if user and user.id != session.get("user_id"): return jsonify({"error": "identity_linking_denied"}), 409
            if user and user.id == link_user_id: return jsonify({"error": "identity_already_linked"}), 409
            try: _service().add_identity(link_user_id, "google", claims.subject, claims.email)
            except IntegrityError: return jsonify({"error": "identity_linking_denied"}), 409
            _audit("google_identity_linked", user_id=link_user_id, method="google", outcome="success")
            return redirect("/profile")
        if not user:
            existing = _service().get_by_email(claims.email)
            if existing: return jsonify({"error": "account_linking_required"}), 409
            base = "".join(ch.lower() if ch.isalnum() else "-" for ch in claims.name).strip("-") or "analyst"
            username = base[:24]
            suffix = 1
            while True:
                try:
                    user = _service().register(username if suffix == 1 else f"{username[:20]}-{suffix}", claims.email, secrets.token_urlsafe(32), "analyst")
                    break
                except IntegrityError:
                    suffix += 1
            _service().add_identity(user.id, "google", claims.subject, claims.email)
            _audit("google_login_success", user_id=user.id, method="google", outcome="account_created")
            return redirect("/") if _login_session(user) else (jsonify({"error": "authentication_failed"}), 401)
        return redirect("/") if _login_session(user) else (jsonify({"error": "authentication_failed"}), 401)
    except Exception:
        _audit("google_login_failure", method="google", outcome="failure", reason="oidc_validation_failed")
        return jsonify({"error": "authentication_failed"}), 401
