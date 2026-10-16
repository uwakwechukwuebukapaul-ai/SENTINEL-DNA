"""Canonical Authentication V3 HTTP boundary."""
from datetime import datetime, timedelta, timezone
from pathlib import Path
import re
import secrets
from flask import Blueprint, current_app, g, jsonify, redirect, request, session, url_for
from database.errors import DatabaseError
from database.portability import integrity_error
from .age import validate_minimum_age
from .oauth import GoogleOIDC
from .phone import country_options, normalize_phone
from .providers import email_provider
from .security import csrf_token
from .mfa import MFAError

auth_api = Blueprint("auth_api", __name__, url_prefix="/api/auth")
REMEMBER_COOKIE = "sentinel_remember"
def _service(): return current_app.container.require("auth_service")
def _mfa_service(): return current_app.container.require("mfa_service")
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

def _normalized_registration_email(value):
    email = str(value or "").strip().lower()
    if len(email) > 254 or not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", email):
        raise ValueError("invalid_registration")
    return email

def _same_database_target(left, right):
    """Allow shared-connection registration only when both services share storage."""
    if left is right:
        return True
    backend = getattr(left, "backend_name", None)
    if backend != getattr(right, "backend_name", None):
        return False
    if backend == "sqlite":
        left_path = getattr(left, "database_path", None)
        right_path = getattr(right, "database_path", None)
        if not left_path or not right_path or ":memory:" in {str(left_path), str(right_path)}:
            return False
        return Path(left_path).resolve() == Path(right_path).resolve()
    if backend == "postgresql":
        return (
            getattr(left, "database_url", None) == getattr(right, "database_url", None)
            and getattr(left, "password_file", "") == getattr(right, "password_file", "")
        )
    return False

def _registration_challenge(challenge_id, purpose, destination, *, require_consumed=True):
    """Return a destination-bound, unexpired registration challenge."""
    if not isinstance(challenge_id, str) or not challenge_id:
        return None
    with _service().db.session() as connection:
        row = connection.execute(
            "SELECT destination,consumed_at,expires_at FROM otp_challenges WHERE id=? AND purpose=?",
            (challenge_id, purpose),
        ).fetchone()
    if (not row or row["destination"] != destination
            or bool(row["consumed_at"]) != require_consumed):
        return None
    try:
        if datetime.fromisoformat(row["expires_at"]) <= datetime.now(timezone.utc):
            return None
    except (TypeError, ValueError):
        return None
    return row
def _bind(user, *, new_public_registration=False, connection=None):
    authority = current_app.container.require("canonical_authority")
    identity = authority.identities.get_by_email(user.email, connection=connection)
    if new_public_registration and identity:
        # Never let public self-registration attach an existing canonical
        # identity or inherit its tenant memberships.
        raise ValueError("registration_identity_conflict")
    identity = identity or authority.identities.create(
        user.email,
        display_name=user.username,
        actor_id=user.actor_id or f"user-{user.id}",
        connection=connection,
    )
    memberships = [m for m in authority.memberships.list_for_actor(identity.actor_id, connection=connection) if m.status == "active"]
    if new_public_registration and memberships:
        raise ValueError("registration_membership_conflict")
    if not memberships:
        tenant = authority.tenants.create(
            f"{user.username} workspace",
            tenant_id=user.tenant_id or f"tenant-{user.id}",
            connection=connection,
        )
        memberships = [authority.memberships.add(
            tenant.tenant_id,
            identity.actor_id,
            str(user.role).lower(),
            connection=connection,
        )]
    membership = sorted(memberships, key=lambda item: item.tenant_id)[0]
    if connection is None:
        with _service().db.session() as connection:
            connection.execute("UPDATE users SET actor_id=?, tenant_id=? WHERE id=?", (identity.actor_id, membership.tenant_id, user.id))
    else:
        connection.execute("UPDATE users SET actor_id=?, tenant_id=? WHERE id=?", (identity.actor_id, membership.tenant_id, user.id))
    return identity, membership
def _login_session(user, remember=False, auth_method="password"):
    identity, membership = _bind(user); session.clear(); session.update(user_id=user.id, session_version=user.session_version, actor_id=identity.actor_id, organization_id=membership.tenant_id, canonical_principal={"actor_id": identity.actor_id, "tenant_id": membership.tenant_id}, csrf_token=csrf_token(), auth_time=datetime.now(timezone.utc).isoformat())
    if user.mfa_required:
        session["auth_stage"] = "MFA_REQUIRED"
        session.pop("mfa_session_token", None)
        _audit("password_authenticated", user_id=user.id, method=auth_method, outcome="mfa_required")
        return user.public()
    session["auth_stage"] = "SOC_AUTHENTICATED"
    if remember:
        raw = secrets.token_urlsafe(48); sid = secrets.token_urlsafe(18); expires = datetime.now(timezone.utc) + timedelta(days=30)
        _service().create_persistent_session(user, raw, membership.tenant_id, sid, expires.isoformat(), user_agent=request.user_agent.string[:256], ip_address=request.remote_addr, auth_method=auth_method); session["persistent_session_id"] = sid; session.permanent = True
        g.remember_cookie = f"{sid}.{raw}"
        _audit("persistent_session_created", user_id=user.id, method="remember_me", outcome="success")
    else:
        g.clear_remember_cookie = True
    _audit("login_success", user_id=user.id, method=auth_method, outcome="success")
    return user.public()

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
    data = request.get_json(silent=True)
    if not isinstance(data, dict): return jsonify({"error": "invalid_registration"}), 400
    if not _allowed("signup", 12, 3600): return jsonify({"error": "registration_unavailable"}), 429
    _audit("signup_started", method="password", outcome="started")
    try:
        email = _normalized_registration_email(data.get("email"))
        # Date of birth remains required because the existing public signup
        # contract enforces the minimum-age policy.
        dob = validate_minimum_age(data.get("date_of_birth"))
        email_challenge_id = data.get("email_challenge_id")
        if (not isinstance(email_challenge_id, str)
                or email_challenge_id != session.get("registration_email_challenge_id")
                or email_challenge_id != session.get("registration_email_verified_challenge_id")
                or email != session.get("registration_email")
                or email != session.get("registration_email_verified")):
            raise ValueError("verification_required")
        email_challenge = _registration_challenge(email_challenge_id, "registration_email", email)
        if not email_challenge: raise ValueError("verification_required")
        email_verified_at = email_challenge["consumed_at"]

        phone = normalize_phone(data.get("country", ""), data.get("phone", "")) if data.get("phone") else None
        phone_verified_at = None
        if phone:
            phone_challenge_id = data.get("phone_challenge_id")
            if (not isinstance(phone_challenge_id, str)
                    or phone_challenge_id != session.get("registration_phone_challenge_id")
                    or phone_challenge_id != session.get("registration_phone_verified_challenge_id")
                    or phone != session.get("registration_phone")
                    or phone != session.get("registration_phone_verified")):
                raise ValueError("verification_required")
            phone_challenge = _registration_challenge(phone_challenge_id, "registration_phone", phone)
            if not phone_challenge: raise ValueError("verification_required")
            phone_verified_at = phone_challenge["consumed_at"]
        auth_service = _service()
        authority = current_app.container.require("canonical_authority")
        if not _same_database_target(authority.db, auth_service.db):
            _audit("signup_failed", method="password", outcome="failure", reason="registration_authority_unavailable")
            return jsonify({"error": "registration_unavailable"}), 500
        if authority.identities.get_by_email(email):
            return jsonify({"error": "registration_unavailable"}), 409
    except DatabaseError: return jsonify({"error": "registration_unavailable"}), 409
    except Exception as exc:
        if integrity_error(exc): return jsonify({"error": "registration_unavailable"}), 409
        _audit("signup_failed", method="password", outcome="failure", reason="invalid_registration")
        return jsonify({"error": "invalid_registration"}), 400

    auth_registration_completed = False
    try:
        with auth_service.db.session() as connection:
            user = auth_service.register(
                data.get("username", ""), email, data.get("password", ""), "analyst",
                phone_number=phone, phone_verified_at=phone_verified_at,
                date_of_birth=dob, email_verified_at=email_verified_at,
                connection=connection,
            )
            auth_registration_completed = True
            _bind(user, new_public_registration=True, connection=connection)
    except DatabaseError as exc:
        if integrity_error(exc): return jsonify({"error": "registration_unavailable"}), 409
        if not auth_registration_completed: return jsonify({"error": "registration_unavailable"}), 409
        _audit("signup_failed", method="password", outcome="failure", reason="registration_unavailable")
        return jsonify({"error": "registration_unavailable"}), 500
    except Exception as exc:
        if integrity_error(exc): return jsonify({"error": "registration_unavailable"}), 409
        _audit("signup_failed", method="password", outcome="failure", reason="registration_unavailable")
        return jsonify({"error": "registration_unavailable"}), 500
    _audit("signup_verified", user_id=user.id, method="password", outcome="success")
    for key in ("registration_email_challenge_id", "registration_email", "registration_email_verified_challenge_id", "registration_email_verified", "registration_phone_challenge_id", "registration_phone", "registration_phone_verified_challenge_id", "registration_phone_verified"):
        session.pop(key, None)
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
    result = _login_session(user, bool(data.get("remember_me")))
    result["mfa_required"] = bool(user.mfa_required)
    result["mfa_verified"] = not bool(user.mfa_required)
    return jsonify(result)

@auth_api.get("/csrf")
def csrf(): return jsonify({"csrf_token": _ensure_csrf()})

@auth_api.post("/logout")
def logout():
    if not _csrf_ok(): return jsonify({"error": "csrf_validation_failed"}), 403
    _mfa_service().revoke_session(session.get("mfa_session_token"))
    remembered = session.get("persistent_session_id")
    if remembered: _service().revoke_persistent_session(remembered)
    g.clear_remember_cookie = True
    _audit("logout", user_id=session.get("user_id"), method="session", outcome="success")
    session.clear()
    if request.form.get("csrf_token") is not None: return redirect(url_for("login_page", signed_out="true"))
    return jsonify({"status": "logged_out"})

@auth_api.get("/me")
def me():
    user = _service().session_user(session.get("user_id"), session.get("session_version"))
    if user and user.mfa_required and not _mfa_service().session_verified(
        user.id,
        session.get("mfa_session_token"),
        session_version=session.get("session_version"),
        tenant_id=session.get("organization_id"),
    ):
        return jsonify({"error": "mfa_required"}), 401
    return jsonify(user.public()) if user else (jsonify({"error": "authentication_required"}), 401)


@auth_api.post("/mfa/enroll")
def mfa_enroll():
    if not _csrf_ok(): return jsonify({"error": "csrf_validation_failed"}), 403
    user = _service().session_user(session.get("user_id"), session.get("session_version"))
    if user is None: return jsonify({"error": "authentication_required"}), 401
    try:
        provisioning_uri = _mfa_service().start_enrollment(user.id)
    except MFAError:
        return jsonify({"error": "mfa_enrollment_unavailable"}), 400
    return jsonify({"status": "mfa_enrollment_started", "provisioning_uri": provisioning_uri}), 200


def _complete_mfa(*, enrollment: bool):
    if not _csrf_ok(): return jsonify({"error": "csrf_validation_failed"}), 403
    user = _service().session_user(session.get("user_id"), session.get("session_version"))
    if user is None: return jsonify({"error": "authentication_required"}), 401
    if not _allowed("mfa-verify|" + str(user.id), 5, 600):
        return jsonify({"error": "mfa_verification_failed"}), 429
    code = (request.get_json(silent=True) or {}).get("code")
    try:
        token = (_mfa_service().complete_enrollment if enrollment else _mfa_service().verify)(user.id, code)
    except MFAError:
        return jsonify({"error": "mfa_verification_failed"}), 400
    session["mfa_session_token"] = token
    session["auth_stage"] = "SOC_AUTHENTICATED"
    return jsonify({"status": "mfa_verified", "mfa_verified": True}), 200


@auth_api.post("/mfa/verify-enrollment")
def mfa_verify_enrollment():
    return _complete_mfa(enrollment=True)


@auth_api.post("/mfa/verify")
def mfa_verify():
    return _complete_mfa(enrollment=False)

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
        challenge, code = _service().issue_otp(destination, "login_email_otp", user_id=row["id"] if row else None, secret=current_app.secret_key)
        delivery = provider.send_code(destination, code, "login_email_otp")
        if not delivery.accepted: raise RuntimeError("email_delivery_failed")
        with _service().db.session() as connection: connection.execute("UPDATE otp_challenges SET provider_request_id=? WHERE id=?", (delivery.provider_request_id, challenge))
        _audit("email_otp_requested", user_id=row["id"] if row else None, method="email_otp", outcome="success")
    except Exception: pass
    return jsonify({"message": "If the account is eligible, a verification code has been sent."}), 202

@auth_api.post("/email/send-registration-code")
def email_send_registration_code():
    if not _csrf_ok(): return jsonify({"error": "csrf_validation_failed"}), 403
    data = request.get_json(silent=True)
    try:
        if not isinstance(data, dict): raise ValueError("invalid_registration")
        destination = _normalized_registration_email(data.get("email"))
    except ValueError:
        return jsonify({"message": "If eligible, a verification code has been sent."}), 202
    if not _allowed(f"email-registration|{destination}", 5, 3600): return jsonify({"message": "If eligible, a verification code has been sent."}), 202
    for key in ("registration_email_challenge_id", "registration_email", "registration_email_verified_challenge_id", "registration_email_verified"):
        session.pop(key, None)
    try:
        provider = current_app.config.get("EMAIL_PROVIDER") or email_provider(testing=current_app.testing)
        challenge, code = _service().issue_otp(destination, "registration_email", secret=current_app.secret_key)
        delivery = provider.send_code(destination, code, "registration_email")
        if not delivery.accepted: raise RuntimeError("email_delivery_failed")
        with _service().db.session() as connection: connection.execute("UPDATE otp_challenges SET provider_request_id=? WHERE id=?", (delivery.provider_request_id, challenge))
        session["registration_email_challenge_id"] = challenge
        session["registration_email"] = destination
    except Exception: return jsonify({"message": "If eligible, a verification code has been sent."}), 202
    _audit("email_verification_requested", method="email_otp", outcome="success")
    return jsonify({"message": "If eligible, a verification code has been sent.", "challenge_id": challenge}), 202

@auth_api.post("/email/verify-registration-code")
def email_verify_registration_code():
    if not _csrf_ok(): return jsonify({"error": "csrf_validation_failed"}), 403
    data = request.get_json(silent=True)
    if not isinstance(data, dict): return jsonify({"error": "verification_failed"}), 400
    challenge_id = data.get("challenge_id")
    destination = session.get("registration_email")
    if (not isinstance(challenge_id, str)
            or challenge_id != session.get("registration_email_challenge_id")
            or not destination
            or (data.get("email") is not None and data.get("email") != destination)):
        return jsonify({"error": "verification_failed"}), 400
    if not _registration_challenge(challenge_id, "registration_email", destination, require_consumed=False):
        return jsonify({"error": "verification_failed"}), 400
    if not _allowed("email-registration-verify", 10, 600): return jsonify({"error": "verification_failed"}), 400
    try:
        consumed, _user_id = _service().verify_otp_challenge(challenge_id, data.get("code", ""), secret=current_app.secret_key)
    except (DatabaseError, TypeError, ValueError):
        return jsonify({"error": "verification_failed"}), 400
    if not consumed: return jsonify({"error": "verification_failed"}), 400
    row = _registration_challenge(challenge_id, "registration_email", destination)
    verified = bool(row)
    if verified:
        session["registration_email_verified"] = destination
        session["registration_email_verified_challenge_id"] = challenge_id
        _audit("email_verified", method="email_otp", outcome="success")
    else:
        _audit("email_verification_failed", method="email_otp", outcome="failure", reason="invalid_or_expired")
    return jsonify({"verified": verified}), 200 if verified else 400

@auth_api.post("/email/verify-code")
def email_verify_code():
    if not _csrf_ok(): return jsonify({"error": "csrf_validation_failed"}), 403
    if not _allowed("email-otp-verify", 10, 600): return jsonify({"error": "verification_failed"}), 400
    data = request.get_json(silent=True) or {}; user_id = _service().verify_otp(data.get("challenge_id"), data.get("code", ""), secret=current_app.secret_key)
    if not user_id: return jsonify({"error": "verification_failed"}), 400
    user = _service().get_by_id(user_id)
    if not user: _audit("email_otp_failed", method="email_otp", outcome="failure", reason="invalid_or_expired")
    else: _audit("email_otp_verified", user_id=user.id, method="email_otp", outcome="success")
    return jsonify(_login_session(user, bool(data.get("remember_me")))) if user else (jsonify({"error": "verification_failed"}), 400)

@auth_api.post("/password-reset/request")
def password_reset_request():
    if not _csrf_ok(): return jsonify({"error": "csrf_validation_failed"}), 403
    destination = str((request.get_json(silent=True) or {}).get("email", "")).strip().lower()
    if not _allowed(f"password-reset|{destination}", 5, 3600): return jsonify({"message": "If the account is eligible, recovery instructions have been sent."}), 202
    try:
        with _service().db.session() as connection: row = connection.execute("SELECT id FROM users WHERE email=? AND is_active=1", (destination,)).fetchone()
        provider = current_app.config.get("EMAIL_PROVIDER") or email_provider(testing=current_app.testing)
        challenge, code = _service().issue_otp(destination, "password_reset", user_id=row["id"] if row else None, secret=current_app.secret_key)
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
    data = request.get_json(silent=True) or {}; user_id = _service().verify_otp(data.get("challenge_id") or session.get("recovery_challenge_id"), data.get("code", ""), secret=current_app.secret_key)
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
        for key in ("registration_phone_challenge_id", "registration_phone", "registration_phone_verified_challenge_id", "registration_phone_verified"):
            session.pop(key, None)
        challenge, code = _service().issue_otp(phone, "registration_phone", secret=current_app.secret_key)
        delivery = provider.send_code(phone, code, "registration_phone")
        if not delivery.accepted: raise RuntimeError("sms_delivery_failed")
        with _service().db.session() as connection: connection.execute("UPDATE otp_challenges SET provider_request_id=? WHERE id=?", (delivery.provider_request_id, challenge))
        session["registration_phone_challenge_id"] = challenge
        session["registration_phone"] = phone
        return jsonify({"challenge_id": challenge, "phone": phone}), 202
    except Exception: return jsonify({"error": "verification_unavailable"}), 400

@auth_api.post("/phone/verify-code")
def phone_verify_code():
    if not _csrf_ok(): return jsonify({"error": "csrf_validation_failed"}), 403
    if not _allowed("phone-otp-verify", 10, 600): return jsonify({"error": "verification_failed"}), 400
    data = request.get_json(silent=True)
    if not isinstance(data, dict): return jsonify({"error": "verification_failed"}), 400
    challenge_id = data.get("challenge_id")
    destination = session.get("registration_phone")
    if (not isinstance(challenge_id, str)
            or challenge_id != session.get("registration_phone_challenge_id")
            or not destination):
        return jsonify({"error": "verification_failed"}), 400
    if not _registration_challenge(challenge_id, "registration_phone", destination, require_consumed=False):
        return jsonify({"error": "verification_failed"}), 400
    try:
        consumed, _user_id = _service().verify_otp_challenge(challenge_id, data.get("code", ""), secret=current_app.secret_key)
    except (DatabaseError, TypeError, ValueError):
        return jsonify({"error": "verification_failed"}), 400
    if not consumed: return jsonify({"error": "verification_failed"}), 400
    row = _registration_challenge(challenge_id, "registration_phone", destination)
    verified = bool(row)
    if verified:
        session["registration_phone_verified"] = destination
        session["registration_phone_verified_challenge_id"] = challenge_id
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
