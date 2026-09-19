"""Opt-in live HTTPS validation for pre-provisioned synthetic identities.

This module is validation infrastructure only.  It never provisions or deletes
accounts, tenants, credentials, or MFA state.  Read-only checks may use one
pre-provisioned synthetic identity.  Mutating checks require a separately
reviewed disposable runtime with one isolated identity per test case and an
external reset/teardown contract.
"""

from __future__ import annotations

import concurrent.futures
import os
import re
from dataclasses import dataclass
from urllib.parse import urlparse

import pyotp
import pytest
import requests


LIVE_ENABLED = os.getenv("SENTINEL_DNA_LIVE_AUTH_ENABLE") == "1"
pytestmark = pytest.mark.live_auth
if not LIVE_ENABLED:
    pytestmark = [pytest.mark.live_auth, pytest.mark.skip(reason="opt-in live HTTPS suite")]


BASE_URL_ENV = "SENTINEL_DNA_LIVE_AUTH_BASE_URL"
REQUIRED = (
    BASE_URL_ENV,
    "SENTINEL_DNA_LIVE_AUTH_ENVIRONMENT",
    "SENTINEL_DNA_LIVE_AUTH_SCOPE",
    "SENTINEL_DNA_LIVE_AUTH_RUN_ID",
    "SENTINEL_DNA_LIVE_AUTH_USERNAME",
    "SENTINEL_DNA_LIVE_AUTH_PASSWORD",
    "SENTINEL_DNA_LIVE_AUTH_TOTP_SECRET",
    "SENTINEL_DNA_LIVE_AUTH_EXPECTED_USER_ID",
    "SENTINEL_DNA_LIVE_AUTH_EXPECTED_TENANT_ID",
    "SENTINEL_DNA_LIVE_AUTH_EXPECTED_ACTOR_ID",
)

MUTATION_CASES = {
    "valid_totp": "VALID_TOTP",
    "replay": "REPLAY",
    "concurrent": "CONCURRENT",
    "logout": "LOGOUT",
}
RESET_CONTRACT = "reviewed_external_teardown_v1"


@dataclass(frozen=True)
class LiveConfig:
    base_url: str
    verify: bool | str
    run_id: str
    username: str
    password: str
    totp_secret: str
    expected_user_id: str
    expected_tenant_id: str
    expected_actor_id: str
    allow_state_mutation: bool


def _required(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        pytest.fail(f"missing required live-auth guard: {name}")
    return value


def _validated_base_url(raw: str) -> str:
    parsed = urlparse(raw.rstrip("/"))
    try:
        port = parsed.port
    except ValueError:
        pytest.fail("live-auth target has an invalid port")
    if (
        parsed.scheme != "https"
        or parsed.hostname != "127.0.0.1"
        or port != 18443
        or parsed.username is not None
        or parsed.password is not None
        or parsed.path not in ("", "/")
        or parsed.params
        or parsed.query
        or parsed.fragment
    ):
        pytest.fail(
            "live-auth target must be exactly https://127.0.0.1:18443 "
            "without userinfo, path, query, or fragment"
        )
    return "https://127.0.0.1:18443"


def _validate_identity_markers(*, username: str, tenant_id: str, actor_id: str) -> None:
    if not (username.endswith(".test") or "synthetic" in username.lower()):
        pytest.fail("live-auth username is not visibly synthetic")
    if not tenant_id.startswith("synthetic-"):
        pytest.fail("live-auth tenant must use a synthetic marker")
    if not actor_id.startswith("synthetic-"):
        pytest.fail("live-auth actor must use a synthetic marker")
    forbidden = ("gate5", "production", "external", "frozen", "evaluation")
    if any(marker in value.lower() for value in (username, tenant_id, actor_id) for marker in forbidden):
        pytest.fail("live-auth identity is associated with a forbidden environment")


def _validate_identity_values(*, username: str, expected_user_id: str, tenant_id: str, actor_id: str) -> None:
    _validate_identity_markers(username=username, tenant_id=tenant_id, actor_id=actor_id)
    if not re.fullmatch(r"[1-9][0-9]*", expected_user_id):
        pytest.fail("expected live-auth user id must be a positive numeric user id")


def _preflight() -> LiveConfig:
    values = {name: _required(name) for name in REQUIRED}

    if values["SENTINEL_DNA_LIVE_AUTH_ENVIRONMENT"] != "staging":
        pytest.fail("live-auth environment must be exactly staging")
    if values["SENTINEL_DNA_LIVE_AUTH_SCOPE"] != "disposable_synthetic":
        pytest.fail("live-auth scope must be exactly disposable_synthetic")
    if not re.fullmatch(r"live-synthetic-[A-Za-z0-9_-]+", values["SENTINEL_DNA_LIVE_AUTH_RUN_ID"]):
        pytest.fail("live-auth run identifier is not a synthetic disposable marker")

    base_url = _validated_base_url(values[BASE_URL_ENV])
    _validate_identity_values(
        username=values["SENTINEL_DNA_LIVE_AUTH_USERNAME"],
        expected_user_id=values["SENTINEL_DNA_LIVE_AUTH_EXPECTED_USER_ID"],
        tenant_id=values["SENTINEL_DNA_LIVE_AUTH_EXPECTED_TENANT_ID"],
        actor_id=values["SENTINEL_DNA_LIVE_AUTH_EXPECTED_ACTOR_ID"],
    )

    try:
        pyotp.TOTP(values["SENTINEL_DNA_LIVE_AUTH_TOTP_SECRET"])
    except Exception as exc:  # pragma: no cover - defensive guard
        pytest.fail(f"invalid synthetic TOTP configuration: {type(exc).__name__}")

    ca_bundle = os.getenv("SENTINEL_DNA_LIVE_AUTH_CA_BUNDLE", "").strip()
    verify: bool | str = ca_bundle or True
    if isinstance(verify, str) and not os.path.isfile(verify):
        pytest.fail("configured live-auth CA bundle does not exist")

    return LiveConfig(
        base_url=base_url,
        verify=verify,
        run_id=values["SENTINEL_DNA_LIVE_AUTH_RUN_ID"],
        username=values["SENTINEL_DNA_LIVE_AUTH_USERNAME"],
        password=values["SENTINEL_DNA_LIVE_AUTH_PASSWORD"],
        totp_secret=values["SENTINEL_DNA_LIVE_AUTH_TOTP_SECRET"],
        expected_user_id=values["SENTINEL_DNA_LIVE_AUTH_EXPECTED_USER_ID"],
        expected_tenant_id=values["SENTINEL_DNA_LIVE_AUTH_EXPECTED_TENANT_ID"],
        expected_actor_id=values["SENTINEL_DNA_LIVE_AUTH_EXPECTED_ACTOR_ID"],
        allow_state_mutation=os.getenv("SENTINEL_DNA_LIVE_AUTH_ALLOW_STATE_MUTATION") == "1",
    )


def _mutation_case(config: LiveConfig, case_name: str) -> LiveConfig:
    if not config.allow_state_mutation:
        pytest.skip("live state-mutating checks require an explicitly disposable runtime")
    contract = _required("SENTINEL_DNA_LIVE_AUTH_DISPOSABLE_RESET_CONTRACT")
    if contract != RESET_CONTRACT:
        pytest.fail("live mutating checks require the reviewed external reset/teardown contract")

    prefix = f"SENTINEL_DNA_LIVE_AUTH_CASE_{MUTATION_CASES[case_name]}_"
    case_run_id = _required(prefix + "RUN_ID")
    if not re.fullmatch(r"live-synthetic-[A-Za-z0-9_-]+", case_run_id):
        pytest.fail("mutation case run identifier is not a synthetic disposable marker")
    username = _required(prefix + "USERNAME")
    password = _required(prefix + "PASSWORD")
    totp_secret = _required(prefix + "TOTP_SECRET")
    expected_user_id = _required(prefix + "EXPECTED_USER_ID")
    tenant_id = _required(prefix + "EXPECTED_TENANT_ID")
    actor_id = _required(prefix + "EXPECTED_ACTOR_ID")
    _validate_identity_values(
        username=username,
        expected_user_id=expected_user_id,
        tenant_id=tenant_id,
        actor_id=actor_id,
    )
    if case_run_id == config.run_id or username == config.username or expected_user_id == config.expected_user_id:
        pytest.fail("mutating live case must not reuse the read-only identity")
    try:
        pyotp.TOTP(totp_secret)
    except Exception as exc:  # pragma: no cover - defensive guard
        pytest.fail(f"invalid mutation-case TOTP configuration: {type(exc).__name__}")
    return LiveConfig(
        base_url=config.base_url,
        verify=config.verify,
        run_id=case_run_id,
        username=username,
        password=password,
        totp_secret=totp_secret,
        expected_user_id=expected_user_id,
        expected_tenant_id=tenant_id,
        expected_actor_id=actor_id,
        allow_state_mutation=True,
    )


def _all_mutation_cases(config: LiveConfig) -> dict[str, LiveConfig]:
    cases = {name: _mutation_case(config, name) for name in MUTATION_CASES}
    for field in ("run_id", "username", "expected_user_id", "expected_tenant_id", "expected_actor_id"):
        values = [getattr(case, field) for case in cases.values()]
        if len(set(values)) != len(values):
            pytest.fail("mutation cases must use distinct disposable identities and tenants")
    return cases


@pytest.fixture(scope="module")
def live_config() -> LiveConfig:
    return _preflight()


@pytest.fixture(scope="module")
def mutation_cases(live_config: LiveConfig) -> dict[str, LiveConfig]:
    if not live_config.allow_state_mutation:
        return {}
    return _all_mutation_cases(live_config)


class _SessionTracker:
    def __init__(self) -> None:
        self._sessions: list[tuple[requests.Session, LiveConfig]] = []

    def create(self, config: LiveConfig) -> requests.Session:
        client = requests.Session()
        client.verify = config.verify
        self._sessions.append((client, config))
        return client

    def cleanup(self) -> None:
        failures: list[str] = []
        for client, config in reversed(self._sessions):
            try:
                failure = _logout_client(client, config)
                if failure:
                    failures.append(failure)
            except Exception as exc:  # pragma: no cover - exercised by live runtime
                failures.append(f"logout_{type(exc).__name__}")
            finally:
                client.close()
        if failures:
            pytest.fail("live disposable-session cleanup failed: " + ",".join(failures))


@pytest.fixture
def disposable_sessions(request):
    tracker = _SessionTracker()
    request.addfinalizer(tracker.cleanup)
    return tracker


def _csrf(client: requests.Session, config: LiveConfig) -> str:
    response = client.get(f"{config.base_url}/api/auth/csrf", timeout=10)
    assert response.status_code == 200
    token = response.json().get("csrf_token")
    assert isinstance(token, str) and token
    return token


def _logout_client(client: requests.Session, config: LiveConfig) -> str | None:
    if not client.cookies:
        return None
    response = client.post(
        f"{config.base_url}/api/auth/logout",
        headers={"X-CSRF-Token": _csrf(client, config)},
        timeout=10,
    )
    return None if response.status_code == 200 else "logout_status"


def _login(client: requests.Session, config: LiveConfig) -> dict:
    response = client.post(
        f"{config.base_url}/api/auth/login",
        json={"username": config.username, "password": config.password},
        headers={"X-CSRF-Token": _csrf(client, config)},
        timeout=10,
    )
    assert response.status_code == 200
    result = response.json()
    assert str(result.get("id")) == config.expected_user_id
    return result


def _protected(client: requests.Session, config: LiveConfig) -> requests.Response:
    return client.get(f"{config.base_url}/api/pilot-authorizations/current", timeout=10)


def _assert_bound_authorization(response: requests.Response, config: LiveConfig) -> None:
    assert response.status_code == 200
    authorization = response.json()
    assert authorization.get("analyst_id") == config.expected_actor_id
    assert authorization.get("tenant_id") == config.expected_tenant_id
    assert authorization.get("role") == "analyst"


@pytest.fixture
def live_client(live_config: LiveConfig) -> requests.Session:
    client = requests.Session()
    client.verify = live_config.verify
    try:
        yield client
    finally:
        try:
            failure = _logout_client(client, live_config)
            if failure:
                pytest.fail(f"live read-only session cleanup failed: {failure}")
        finally:
            client.close()


def test_live_preflight_reaches_verified_https_edge(live_client, live_config):
    response = live_client.get(f"{live_config.base_url}/ready", timeout=10)
    assert response.status_code == 200


def test_password_only_session_cannot_access_protected_soc(live_client, live_config):
    result = _login(live_client, live_config)
    assert result.get("mfa_required") is True
    assert _protected(live_client, live_config).status_code in {401, 403}


def test_valid_totp_establishes_bound_mfa_session(live_config, mutation_cases, disposable_sessions):
    config = mutation_cases["valid_totp"]
    client = disposable_sessions.create(config)
    result = _login(client, config)
    assert result.get("mfa_required") is True
    response = client.post(
        f"{config.base_url}/api/auth/mfa/verify",
        json={"code": pyotp.TOTP(config.totp_secret).now()},
        headers={"X-CSRF-Token": _csrf(client, config)},
        timeout=10,
    )
    assert response.status_code == 200
    me = client.get(f"{config.base_url}/api/auth/me", timeout=10)
    assert me.status_code == 200
    assert me.json().get("role") == "analyst"
    _assert_bound_authorization(_protected(client, config), config)


def test_replayed_totp_is_rejected(live_config, mutation_cases, disposable_sessions):
    config = mutation_cases["replay"]
    client = disposable_sessions.create(config)
    _login(client, config)
    code = pyotp.TOTP(config.totp_secret).now()
    endpoint = f"{config.base_url}/api/auth/mfa/verify"
    headers = {"X-CSRF-Token": _csrf(client, config)}
    assert client.post(endpoint, json={"code": code}, headers=headers, timeout=10).status_code == 200
    assert client.post(endpoint, json={"code": code}, headers=headers, timeout=10).status_code == 400


def test_concurrent_totp_reuse_has_one_success(live_config, mutation_cases, disposable_sessions):
    config = mutation_cases["concurrent"]
    clients = [disposable_sessions.create(config), disposable_sessions.create(config)]
    for client in clients:
        _login(client, config)
    code = pyotp.TOTP(config.totp_secret).now()

    def verify(client: requests.Session) -> int:
        response = client.post(
            f"{config.base_url}/api/auth/mfa/verify",
            json={"code": code},
            headers={"X-CSRF-Token": _csrf(client, config)},
            timeout=10,
        )
        return response.status_code

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        statuses = list(pool.map(verify, clients))
    assert sorted(statuses) == [200, 400]


def test_logout_invalidates_mfa_authorization(live_config, mutation_cases, disposable_sessions):
    config = mutation_cases["logout"]
    client = disposable_sessions.create(config)
    _login(client, config)
    assert client.post(
        f"{config.base_url}/api/auth/mfa/verify",
        json={"code": pyotp.TOTP(config.totp_secret).now()},
        headers={"X-CSRF-Token": _csrf(client, config)},
        timeout=10,
    ).status_code == 200
    assert client.post(
        f"{config.base_url}/api/auth/logout",
        headers={"X-CSRF-Token": _csrf(client, config)},
        timeout=10,
    ).status_code == 200
    assert _protected(client, config).status_code in {401, 403}


def test_forged_client_state_cannot_bypass_mfa(live_client, live_config):
    _login(live_client, live_config)
    live_client.cookies.set("session", "forged-live-validation-state")
    assert _protected(live_client, live_config).status_code in {401, 403}


def test_unsupported_mutating_capabilities_fail_closed(live_config):
    """Document capabilities requiring a reviewed multi-identity fixture."""

    pytest.skip("cross-user, cross-tenant, recovery, and privileged live cases require a reviewed fixture")
