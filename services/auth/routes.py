"""Canonical Authentication V3 HTTP boundary."""
from datetime import datetime, timedelta, timezone
import secrets
from flask import Blueprint, current_app, g, jsonify, redirect, request, session, url_for
from database.errors import DatabaseError
from database.portability import integrity_error
from .age import validate_minimum_age
from .oauth import GoogleOIDC
from .phone import country_options, normalize_phone
from .providers import email_provider
from .security import csrf_token
from .onboarding import OnboardingState

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
def _strict_csrf_ok():
    """Require the synchronizer token for the browser registration flow."""
    expected = session.get("csrf_token"); supplied = request.headers.get("X-CSRF-Token") or request.form.get("csrf_token")
    return bool(expected and supplied and secrets.compare_digest(str(expected), str(supplied)))
def _ensure_csrf():
    if "csrf_token" not in session: session["csrf_token"] = csrf_token()
    return session["csrf_token"]

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
    if user.onboarding_state != OnboardingState.AUTHENTICATED:
        raise ValueError("onboarding_required")
    identity, membership = _bind(user); session.clear(); session.update(user_id=user.id, session_version=user.session_version, actor_id=identity.actor_id, organization_id=membership.tenant_id, canonical_principal={"actor_id": identity.actor_id, "tenant_id": membership.tenant_id}, csrf_token=csrf_token(), auth_time=datetime.now(timezone.utc).isoformat())
    if remember:
        raw = secrets.token_urlsafe(48); sid = secrets.token_urlsafe(18); expires = datetime.now(timezone.utc) + timedelta(days=30)
        _service().create_persistent_session(user, raw, membership.tenant_id, sid, expires.isoformat(), user_agent=request.user_agent.string[:256], ip_address=request.remote_addr, auth_method=auth_method); session["persistent_session_id"] = sid; session.permanent = True
        g.remember_cookie = f"{sid}.{raw}"
        _audit("persistent_session_created", user_id=user.id, method="remember_me", outcome="success")
    else:
        g.clear_remember_cookie = True
    _audit("login_success", user_id=user.id, method=auth_method, outcome="success")
    return user.public()

def _mfa_pending_session(user):
    """Create a non-authorized pre-auth session for MFA ceremony only."""
    identity, membership = _bind(user)
    session.clear()
    session.update(mfa_pending_user_id=user.id, mfa_pending_session_version=user.session_version,
                   actor_id=identity.actor_id, organization_id=membership.tenant_id,
                   canonical_principal={"actor_id": identity.actor_id, "tenant_id": membership.tenant_id},
                   auth_otp_binding=secrets.token_urlsafe(32), csrf_token=csrf_token(), auth_time=datetime.now(timezone.utc).isoformat())
    return {"status": "mfa_required", "mfa_enrollment_required": user.onboarding_state == OnboardingState.MFA_ENROLLMENT_REQUIRED}

def _mfa_pending_user():
    user = _service().get_by_id(session.get("mfa_pending_user_id"))
    if (not user or not user.is_active or user.revocation_status != "active" or
            user.session_version != session.get("mfa_pending_session_version") or
            user.actor_id != session.get("actor_id") or user.tenant_id != session.get("organization_id")):
        return None
    return user

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

@auth_api.post("/register")
def register():
    if current_app.config.get("PILOT_ACCESS_REQUIRED", False):
        return jsonify({"error": "registration_unavailable"}), 403
    if not _csrf_ok(): return jsonify({"error": "csrf_validation_failed"}), 403
    data = request.get_json(silent=True) or {}
    if not _allowed("signup", 12, 3600): return jsonify({"error": "registration_unavailable"}), 429
    _audit("signup_started", method="password", outcome="started")
    try:
        legacy_api = current_app.config.get("AUTH_LEGACY_JSON_COMPAT", True) and request.is_json and not data.get("date_of_birth") and not data.get("phone")
        legacy_dual = bool(data.get("email_challenge_id") and data.get("phone_challenge_id") and session.get("registration_email_verified") and session.get("registration_phone_verified"))
        dob = validate_minimum_age(data.get("date_of_birth")) if data.get("date_of_birth") else None
        method = str(session.get("registration_verification_method") or "").strip().lower()
        if not legacy_api and not legacy_dual and method not in {"email", "phone"}:
            raise ValueError("verification_required")
        phone = normalize_phone(data.get("country", ""), data.get("phone", "")) if data.get("phone") else None
        email_verified_at = None
        phone_verified_at = None
        if not legacy_api and not legacy_dual:
            expected_email = str(data.get("email", "")).strip().lower()
            session_email = str(session.get("registration_email") or "").strip().lower()
            session_phone = session.get("registration_phone")
            if method == "email" and session_email != expected_email:
                raise ValueError("verification_required")
            if method == "phone" and (not phone or session_phone != phone):
                raise ValueError("verification_required")
            with _service().db.session() as connection:
                binding = _otp_binding()
                challenge_id = session.get("registration_verification_challenge_id")
                verified = connection.execute("SELECT 1 FROM otp_challenges WHERE id=? AND purpose=? AND consumed_at IS NOT NULL AND destination=? AND session_binding=?", (challenge_id, f"registration_{method}", expected_email if method == "email" else phone, binding)).fetchone()
            if not verified or session.get("registration_verified") is not True: raise ValueError("verification_required")
            now = datetime.now(timezone.utc).isoformat()
            email_verified_at = now if method == "email" else None
            phone_verified_at = now if method == "phone" else None
        user = _service().register(
            data.get("username", ""), data.get("email", ""), data.get("password", ""),
            "analyst", phone_number=phone, date_of_birth=dob,
            email_verified_at=email_verified_at,
            phone_verified_at=phone_verified_at,
            verification_method=(method if not legacy_api and not legacy_dual else None),
            onboarding_state=(OnboardingState.AUTHENTICATED if legacy_api or legacy_dual else OnboardingState.NEW),
        )
    except DatabaseError: return jsonify({"error": "registration_unavailable"}), 409
    except Exception as exc:
        if integrity_error(exc): return jsonify({"error": "registration_unavailable"}), 409
        _audit("signup_failed", method="password", outcome="failure", reason="invalid_registration")
        return jsonify({"error": "invalid_registration"}), 400
    try:
        _bind(user)
        if not legacy_api and not legacy_dual:
            user = _service().complete_verified_onboarding(user.id)
            if user is None or user.onboarding_state != OnboardingState.MFA_ENROLLMENT_REQUIRED:
                raise RuntimeError("onboarding_completion_failed")
    except Exception:
        with _service().db.session() as connection: connection.execute("DELETE FROM users WHERE id=?", (user.id,))
        return jsonify({"error": "registration_unavailable"}), 500
    for key in ("auth_otp_binding", "registration_email_challenge_id", "registration_email_verified", "registration_phone_verified", "registration_verification_method", "registration_verification_challenge_id", "registration_verified", "registration_email", "registration_phone"):
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
    if user.onboarding_state == OnboardingState.MFA_ENROLLMENT_REQUIRED:
        return jsonify(_mfa_pending_session(user)), 200
    if user.mfa_enabled:
        return jsonify(_mfa_pending_session(user)), 200
    return jsonify(_login_session(user, bool(data.get("remember_me"))))

@auth_api.post("/mfa/enroll")
def mfa_enroll():
    if not _strict_csrf_ok(): return jsonify({"error": "csrf_validation_failed"}), 403
    user = _mfa_pending_user()
    if not user or user.onboarding_state != OnboardingState.MFA_ENROLLMENT_REQUIRED:
        return jsonify({"error": "mfa_enrollment_required"}), 403
    if not _allowed(f"mfa-enroll|{user.id}", 5, 3600): return jsonify({"error": "mfa_rate_limited"}), 429
    try:
        challenge_id, uri = _service().create_mfa_enrollment(user.id, session_binding=_otp_binding(), secret=current_app.secret_key)
        _audit("mfa_enrollment_started", user_id=user.id, method="totp", outcome="success")
        return jsonify({"challenge_id": challenge_id, "provisioning_uri": uri, "method": "totp"}), 201
    except ValueError:
        return jsonify({"error": "mfa_enrollment_unavailable"}), 409

@auth_api.post("/mfa/enroll/verify")
def mfa_enroll_verify():
    if not _strict_csrf_ok(): return jsonify({"error": "csrf_validation_failed"}), 403
    user = _mfa_pending_user(); data = request.get_json(silent=True) or {}
    if not user or user.onboarding_state != OnboardingState.MFA_ENROLLMENT_REQUIRED: return jsonify({"error": "mfa_enrollment_required"}), 403
    if not _allowed(f"mfa-enroll-verify|{user.id}", 10, 600): return jsonify({"error": "mfa_rate_limited"}), 429
    codes = _service().verify_mfa_enrollment(data.get("challenge_id"), user.id, data.get("code", ""), secret=current_app.secret_key, session_binding=_otp_binding())
    if not codes:
        _audit("mfa_enrollment_failed", user_id=user.id, method="totp", outcome="failure", reason="invalid_or_expired")
        return jsonify({"error": "mfa_verification_failed"}), 400
    user = _service().get_by_id(user.id)
    result = _login_session(user, auth_method="totp_enrollment")
    _audit("mfa_enrollment_success", user_id=user.id, method="totp", outcome="success")
    return jsonify({"account": result, "recovery_codes": codes}), 200

@auth_api.post("/mfa/verify")
def mfa_verify():
    if not _strict_csrf_ok(): return jsonify({"error": "csrf_validation_failed"}), 403
    user = _mfa_pending_user(); data = request.get_json(silent=True) or {}
    if not user or not user.mfa_enabled: return jsonify({"error": "mfa_verification_required"}), 403
    if not _allowed(f"mfa-verify|{user.id}", 10, 600): return jsonify({"error": "mfa_rate_limited"}), 429
    recovery = str(data.get("recovery_code") or "").strip()
    valid = _service().consume_mfa_recovery_code(user.id, recovery, secret=current_app.secret_key) if recovery else _service().verify_mfa_code(user.id, data.get("code", ""), secret=current_app.secret_key)
    if not valid:
        _audit("mfa_recovery_failed" if recovery else "mfa_verification_failed", user_id=user.id, method="recovery_code" if recovery else "totp", outcome="failure", reason="invalid")
        return jsonify({"error": "mfa_verification_failed"}), 401
    _audit("mfa_recovery_success" if recovery else "mfa_verification_success", user_id=user.id, method="recovery_code" if recovery else "totp", outcome="success")
    return jsonify(_login_session(user, auth_method="recovery_code" if recovery else "totp")), 200

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
    return jsonify(user.public()) if user else (jsonify({"error": "authentication_required"}), 401)

@auth_api.get("/sessions")
def sessions():
    user_id = session.get("user_id")
    if not user_id: return jsonify({"error": "authentication_required"}), 401
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

@auth_api.post("/verification/send-code")
def verification_send_code():
    """Start exactly one contact-verification flow for browser registration."""
    if not _strict_csrf_ok(): return jsonify({"error": "csrf_validation_failed"}), 403
    data = request.get_json(silent=True) or {}
    method = str(data.get("method") or "").strip().lower()
    # Primary browser registration is email-first. SMS remains available only
    # through the separately governed recovery/legacy boundary.
    if method != "email":
        return jsonify({"error": "invalid_verification_method"}), 400
    if not _allowed(f"registration-verification|{method}", 5, 3600):
        return jsonify({"error": "verification_rate_limited"}), 429
    try:
        if method == "email":
            destination = str(data.get("email") or "").strip().lower()
            if "@" not in destination: raise ValueError("invalid_email")
            provider = current_app.config.get("EMAIL_PROVIDER") or email_provider(testing=current_app.testing)
        else:
            # The region is explicit input; normalize_phone validates it and
            # produces the only phone identity stored in the registration flow.
            destination = normalize_phone(data.get("country", ""), data.get("phone", ""))
            provider = current_app.config.get("SMS_PROVIDER")
            if provider is None:
                from .providers import sms_provider
                provider = sms_provider(testing=current_app.testing)
        challenge, code = _service().issue_otp(destination, f"registration_{method}", secret=current_app.secret_key, session_binding=_otp_binding())
        delivery = provider.send_code(destination, code, f"registration_{method}")
        if not delivery.accepted: raise RuntimeError("verification_delivery_failed")
        with _service().db.session() as connection:
            connection.execute("UPDATE otp_challenges SET provider_request_id=? WHERE id=?", (delivery.provider_request_id, challenge))
        session["registration_verification_method"] = method
        session["registration_verification_challenge_id"] = challenge
        session["registration_verified"] = False
        session["registration_onboarding_state"] = OnboardingState.VERIFICATION_SENT
        if method == "email": session["registration_email"] = destination
        else: session["registration_phone"] = destination
        _audit("registration_verification_requested", method=method, outcome="success")
        return jsonify({"challenge_id": challenge, "method": method}), 202
    except ValueError as exc:
        _audit("registration_verification_failed", method=method, outcome="failure", reason=str(exc)[:64])
        return jsonify({"error": "verification_unavailable" if str(exc) == "otp_cooldown" else "invalid_registration_destination"}), 400
    except Exception:
        _audit("registration_verification_failed", method=method, outcome="failure", reason="provider_unavailable")
        return jsonify({"error": "verification_unavailable"}), 400

@auth_api.post("/verification/verify-code")
def verification_verify_code():
    """Consume the server-bound registration challenge; never trust client verification flags."""
    if not _strict_csrf_ok(): return jsonify({"error": "csrf_validation_failed"}), 403
    if not _allowed("registration-verification-verify", 10, 600):
        return jsonify({"error": "verification_rate_limited"}), 429
    data = request.get_json(silent=True) or {}
    method = session.get("registration_verification_method")
    challenge_id = data.get("challenge_id")
    if method not in {"email", "phone"} or not challenge_id or challenge_id != session.get("registration_verification_challenge_id"):
        return jsonify({"error": "invalid_challenge"}), 400
    destination = session.get("registration_email") if method == "email" else session.get("registration_phone")
    try:
        _service().verify_otp(challenge_id, data.get("code", ""), secret=current_app.secret_key, session_binding=_otp_binding())
        with _service().db.session() as connection:
            row = connection.execute("SELECT destination, purpose, consumed_at FROM otp_challenges WHERE id=? AND session_binding=?", (challenge_id, _otp_binding())).fetchone()
        verified = bool(row and row["purpose"] == f"registration_{method}" and row["destination"] == destination and row["consumed_at"])
        if not verified:
            _audit("registration_verification_failed", method=method, outcome="failure", reason="invalid_or_expired")
            return jsonify({"error": "verification_failed"}), 400
        session["registration_verified"] = True
        session["registration_onboarding_state"] = OnboardingState.VERIFIED
        _audit("registration_contact_verified", method=method, outcome="success")
        return jsonify({"verified": True, "method": method}), 200
    except Exception:
        _audit("registration_verification_failed", method=method, outcome="failure", reason="invalid_or_expired")
        return jsonify({"error": "verification_failed"}), 400

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
            # Google proves the provider identity, but it does not complete
            # Sentinel DNA's required email/phone/password onboarding flow.
            # Do not create a passwordless pending user or establish a
            # session from an incomplete onboarding state.
            _audit("google_login_failure", method="google", outcome="failure", reason="onboarding_required")
            return jsonify({"error": "onboarding_required"}), 403
        if user.onboarding_state != OnboardingState.AUTHENTICATED:
            _audit("google_login_failure", user_id=user.id, method="google", outcome="failure", reason="onboarding_required")
            return jsonify({"error": "onboarding_required"}), 403
        if user.mfa_enabled:
            _mfa_pending_session(user)
            _audit("mfa_challenge_started", user_id=user.id, method="google", outcome="success")
            return redirect("/mfa/verify")
        return redirect("/") if _login_session(user) else (jsonify({"error": "authentication_failed"}), 401)
    except Exception:
        _audit("google_login_failure", method="google", outcome="failure", reason="oidc_validation_failed")
        return jsonify({"error": "authentication_failed"}), 401
