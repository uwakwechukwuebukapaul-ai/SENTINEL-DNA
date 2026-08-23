"""Canonical JSON and browser authentication routes."""
from datetime import date
from flask import Blueprint, current_app, jsonify, request, session, render_template, redirect, url_for, make_response
from sqlite3 import IntegrityError
from .auth_service import AuthService
from .security import csrf_token
from .phone import COUNTRIES, normalize_phone
from .otp import build_provider

auth_api = Blueprint("auth_api", __name__, url_prefix="/api/auth")
auth_web = Blueprint("auth_web", __name__)

@auth_web.app_context_processor
def auth_template_context():
    return {"today": date.today().isoformat()}

def _service(): return current_app.container.get("auth_service")
def _csrf_ok():
    supplied = request.headers.get("X-CSRF-Token") or request.form.get("csrf_token")
    return bool(session.get("csrf_token") and supplied and supplied == session.get("csrf_token"))
def _ensure_csrf():
    if "csrf_token" not in session: session["csrf_token"] = csrf_token()

@auth_api.post("/register")
def register():
    data = request.get_json(silent=True) or {}; phone = data.get("phone") or data.get("phone_number")
    if phone and not _csrf_ok() and session.get("csrf_token"): return jsonify({"error":"csrf_validation_failed"}), 403
    try:
        if phone:
            pending_id, normalized = _service().create_pending(data.get("username", ""), data.get("email", ""), data.get("password", ""), data.get("country", ""), phone, data.get("date_of_birth", ""))
            provider = current_app.config.get("OTP_PROVIDER") or build_provider(testing=current_app.testing, production=current_app.config.get("ENVIRONMENT") == "production")
            _id, secret = _service().issue_otp(normalized, provider=provider, pending_id=pending_id)
            session["pending_registration"], session["otp_secret"] = pending_id, secret
            return jsonify({"status":"phone_verification_required", "phone_number": f"{normalized[:4]}   {normalized[-4:]}"}), 202
        user = _service().register(data.get("username", ""), data.get("email", ""), data.get("password", ""))
    except IntegrityError: return jsonify({"error":"registration_unavailable"}), 409
    except ValueError: return jsonify({"error":"invalid_registration"}), 400
    return jsonify(user.public()), 201

@auth_api.post("/login")
def login():
    data = request.get_json(silent=True) or {}; user = _service().authenticate(data.get("username", ""), data.get("password", ""))
    if not user:
        current_app.container.get("audit_service").record("FAILED_LOGIN", details={"username":"provided"}); return jsonify({"error":"invalid_credentials"}), 401
    session.clear(); session["user_id"] = user.id; session["actor_id"] = user.actor_id; session["organization_id"] = user.tenant_id; session["csrf_token"] = csrf_token()
    response = make_response(jsonify({**user.public(), "csrf_token": session["csrf_token"]}))
    if data.get("remember_me"):
        value, expires = _service().create_persistent_session(user); response.set_cookie("sentinel_remember", value, max_age=30*86400, expires=expires, httponly=True, secure=current_app.config.get("SESSION_COOKIE_SECURE", False), samesite="Lax", path="/")
    current_app.container.get("audit_service").record("USER_LOGIN", user_id=user.id); return response

@auth_api.get("/csrf")
def csrf(): _ensure_csrf(); return jsonify({"csrf_token": session["csrf_token"]})

@auth_api.post("/logout")
def logout():
    if not _csrf_ok(): return jsonify({"error":"csrf_validation_failed"}), 403
    user_id = session.get("user_id");
    if user_id: _service().revoke_persistent_sessions(user_id)
    current_app.container.get("audit_service").record("USER_LOGOUT", user_id=user_id); session.clear(); response = make_response(jsonify({"status":"logged_out"})); response.delete_cookie("sentinel_remember", path="/"); return response

@auth_api.get("/me")
def me():
    user = _service().get_by_id(session.get("user_id"))
    return jsonify(user.profile()) if user else (jsonify({"error":"authentication_required"}), 401)

@auth_api.post("/phone/send-code")
def send_phone_code():
    if not _csrf_ok(): return jsonify({"error":"csrf_validation_failed"}), 403
    try:
        normalized = normalize_phone((request.get_json(silent=True) or {}).get("country"), (request.get_json(silent=True) or {}).get("phone"))
        provider = current_app.config.get("OTP_PROVIDER") or build_provider(testing=current_app.testing, production=current_app.config.get("ENVIRONMENT") == "production")
        _id, secret = _service().issue_otp(normalized, provider=provider)
        session["otp_phone"], session["otp_secret"] = normalized, secret
        return jsonify({"status":"code_sent", "phone_number":f"{normalized[:4]}   {normalized[-4:]}"})
    except ValueError as exc: return jsonify({"error":str(exc) if str(exc) in {"otp_cooldown","otp_rate_limited"} else "invalid_phone"}), 429 if str(exc) in {"otp_cooldown","otp_rate_limited"} else 400

@auth_api.post("/phone/verify-code")
def verify_phone_code():
    if not _csrf_ok(): return jsonify({"error":"csrf_validation_failed"}), 403
    data = request.get_json(silent=True) or {}
    ok = _service().verify_otp(session.get("otp_phone"), data.get("code", ""), secret=session.get("otp_secret", ""))
    if not ok: return jsonify({"error":"invalid_or_expired_code"}), 400
    session["phone_verified"] = True
    pending_id = session.get("pending_registration")
    if pending_id:
        _service().finalize_pending(pending_id, canonical_authority=current_app.container.get("canonical_authority")); session.pop("pending_registration", None)
    session.pop("otp_secret", None); return jsonify({"status":"verified"})

@auth_web.before_app_request
def restore_remembered_session():
    if session.get("user_id") or request.path.startswith("/api/auth"): return
    value = request.cookies.get("sentinel_remember")
    if value:
        user = _service().resolve_persistent_session(value)
        if user:
            session["user_id"], session["actor_id"], session["organization_id"], session["csrf_token"] = user.id, user.actor_id, user.tenant_id, csrf_token()

@auth_web.get("/login")
def login_page(): _ensure_csrf(); return render_template("auth/login.html", csrf_token=session["csrf_token"])

@auth_web.post("/login")
def login_page_post():
    if not _csrf_ok(): return render_template("auth/login.html", error="Your session expired. Please try again.", csrf_token=session.get("csrf_token")), 403
    data = request.form; user = _service().authenticate(data.get("username", ""), data.get("password", ""))
    if not user: return render_template("auth/login.html", error="Sign-in failed. Check your credentials and try again.", csrf_token=session["csrf_token"]), 401
    session.clear(); session.update(user_id=user.id, actor_id=user.actor_id, organization_id=user.tenant_id, csrf_token=csrf_token())
    response = make_response(redirect("/workspace/"))
    if data.get("remember_me"):
        value, expires = _service().create_persistent_session(user); response.set_cookie("sentinel_remember", value, max_age=30*86400, expires=expires, httponly=True, secure=current_app.config.get("SESSION_COOKIE_SECURE", False), samesite="Lax", path="/")
    return response

@auth_web.get("/signup")
def signup_page(): _ensure_csrf(); return render_template("auth/signup.html", countries=COUNTRIES, csrf_token=session["csrf_token"])

@auth_web.post("/signup")
def signup_post():
    if not _csrf_ok(): return render_template("auth/signup.html", countries=COUNTRIES, csrf_token=session.get("csrf_token"), error="Your session expired. Please try again."), 403
    data = request.form
    try:
        if not session.get("pending_registration"):
            if data.get("password") != data.get("confirm_password"):
                raise ValueError("password_mismatch")
            pending_id, normalized = _service().create_pending(data.get("username",""), data.get("email",""), data.get("password",""), data.get("country",""), data.get("phone",""), data.get("date_of_birth",""))
            provider = current_app.config.get("OTP_PROVIDER")
            if provider is None: provider = build_provider(testing=current_app.testing, production=current_app.config.get("ENVIRONMENT") == "production")
            _id, secret = _service().issue_otp(normalized, provider=provider, pending_id=pending_id)
            session["pending_registration"], session["otp_secret"] = pending_id, secret
            return render_template("auth/signup.html", countries=COUNTRIES, csrf_token=session["csrf_token"], otp_sent=True, phone_number=normalized)
        pending_id = session["pending_registration"]
        with _service().db.session() as c: row = c.execute("SELECT phone_number FROM pending_registrations WHERE id=?", (pending_id,)).fetchone()
        if not row or not _service().verify_otp(row["phone_number"], data.get("otp",""), secret=session.get("otp_secret","")):
            return render_template("auth/signup.html", countries=COUNTRIES, csrf_token=session["csrf_token"], otp_sent=True, error="That verification code is invalid or expired."), 400
        user = _service().finalize_pending(pending_id, canonical_authority=current_app.container.get("canonical_authority")); session.pop("pending_registration", None); session.pop("otp_secret", None)
        return redirect(url_for("auth_web.login_page"))
    except (ValueError, IntegrityError):
        return render_template("auth/signup.html", countries=COUNTRIES, csrf_token=session["csrf_token"], error="We could not complete registration. Check the details and try again."), 400

@auth_web.post("/signup/resend")
def signup_resend():
    if not _csrf_ok() or not session.get("pending_registration"): return jsonify({"error":"csrf_validation_failed"}), 403
    with _service().db.session() as c: row = c.execute("SELECT phone_number FROM pending_registrations WHERE id=?", (session["pending_registration"],)).fetchone()
    if not row: return jsonify({"error":"registration_expired"}), 400
    try:
        provider = current_app.config.get("OTP_PROVIDER") or build_provider(testing=current_app.testing, production=current_app.config.get("ENVIRONMENT") == "production")
        _id, secret = _service().issue_otp(row["phone_number"], provider=provider, pending_id=session["pending_registration"]); session["otp_secret"] = secret
        return jsonify({"status":"code_sent"})
    except ValueError as exc: return jsonify({"error":str(exc)}), 429

@auth_web.post("/logout")
def web_logout():
    if not _csrf_ok(): return jsonify({"error":"csrf_validation_failed"}), 403
    user_id = session.get("user_id")
    if user_id: _service().revoke_persistent_sessions(user_id)
    session.clear(); response = make_response(redirect(url_for("auth_web.login_page"))); response.delete_cookie("sentinel_remember", path="/"); return response

@auth_web.get("/profile")
def profile_page():
    user = _service().get_by_id(session.get("user_id"))
    if not user: return jsonify({"error":"authentication_required"}), 401
    tenant = None
    if user.tenant_id and user.actor_id:
        try:
            tenant, _identity, _membership = current_app.container.get("canonical_authority").resolve(user.tenant_id, user.actor_id)
        except (LookupError, PermissionError, ValueError):
            tenant = None
    return render_template("auth/profile.html", user=user.profile(), tenant=tenant)
