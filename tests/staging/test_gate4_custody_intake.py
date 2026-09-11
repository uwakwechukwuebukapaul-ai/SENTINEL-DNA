from deployment.staging.scripts.validate_gate4_custody_intake import validate


def complete_intake():
    values = {}
    for name in (
        "SENTINEL_DNA_STAGING_APP_SECRET_FILE",
        "SENTINEL_DNA_STAGING_POSTGRES_PASSWORD_FILE",
        "SENTINEL_DNA_STAGING_SMTP_USERNAME_FILE",
        "SENTINEL_DNA_STAGING_SMTP_PASSWORD_FILE",
        "SENTINEL_DNA_STAGING_TRUSTED_BROWSER_SERVICE_KEY_FILE",
        "SENTINEL_DNA_STAGING_EDGE_CONFIG_FILE",
        "SENTINEL_DNA_STAGING_TLS_DIR",
        "SENTINEL_DNA_EGRESS_POLICY_FILE",
        "SENTINEL_DNA_TRUSTED_BROWSER_ACTIVATION_MANIFEST",
        "SENTINEL_DNA_APPROVED_PLAYWRIGHT_RUNTIME",
        "SENTINEL_DNA_BROWSER_EXECUTABLE",
        "SENTINEL_DNA_BROWSER_AUTH_BRIDGE",
    ):
        values[name] = "C:\\approved\\" + name.lower()
    values.update({
        "SENTINEL_DNA_CERTIFIED_ORIGIN": "https://approved.test",
        "SENTINEL_DNA_CERTIFIED_HOSTNAME": "approved.test",
        "SENTINEL_DNA_TRUSTED_BROWSER_SERVICE_HOST": "trusted-browser",
        "SENTINEL_DNA_TRUSTED_BROWSER_SERVICE_PORT": "3000",
        "SENTINEL_DNA_TRUSTED_BROWSER_EGRESS_READY": "true",
        "SENTINEL_DNA_TRUSTED_BROWSER_EGRESS_PROXY": "egress-gateway:8443",
        "SENTINEL_DNA_EGRESS_GATEWAY_BIND": "0.0.0.0",
        "SENTINEL_DNA_EGRESS_GATEWAY_PORT": "8443",
        "SENTINEL_DNA_TRUSTED_BROWSER_GATEWAY_UPLINK_NETWORK": "approved-uplink",
        "SENTINEL_DNA_STAGING_APP_IMAGE": "registry.example/staging-app@sha256:" + "d" * 64,
        "SENTINEL_DNA_STAGING_EDGE_IMAGE": "registry.example/nginx@sha256:" + "e" * 64,
        "SENTINEL_DNA_IMAGE_TAG": "gate4-reviewed",
        "SENTINEL_DNA_TRUSTED_BROWSER_IMAGE": "registry.example/trusted-browser@sha256:" + "a" * 64,
        "SENTINEL_DNA_EGRESS_GATEWAY_IMAGE": "registry.example/egress-gateway@sha256:" + "b" * 64,
        "SENTINEL_DNA_POSTGRES_IMAGE": "registry.example/postgres@sha256:" + "1" * 64,
        "SENTINEL_DNA_REDIS_IMAGE": "registry.example/redis@sha256:" + "2" * 64,
        "SENTINEL_DNA_EGRESS_POLICY_REFERENCE": "custody:egress-policy:gate4",
        "SENTINEL_DNA_IMAGE_REVISION_FULL": "f" * 40,
        "SENTINEL_DNA_IMAGE_CREATED": "2026-09-06T00:00:00Z",
        "SENTINEL_DNA_IMAGE_DIGEST": "sha256:" + "c" * 64,
        "SENTINEL_DNA_APPROVED_RUNTIME_DIGEST": "sha256:" + "d" * 64,
        "SENTINEL_DNA_EGRESS_POLICY_DIGEST": "sha256:" + "e" * 64,
        "SENTINEL_DNA_BROWSER_EXECUTABLE_SHA256": "sha256:" + "f" * 64,
        "SENTINEL_DNA_TRUSTED_BROWSER_CLIENT": "reviewed-client",
        "SENTINEL_DNA_TRUSTED_BROWSER_UPSTREAM_CLIENT": "reviewed-upstream",
        "PLAYWRIGHT_BASE_IMAGE": "mcr.microsoft.com/playwright@sha256:" + "1" * 64,
    })
    return values


def test_missing_intake_is_blocked_and_redacted():
    result = validate({})
    assert result["status"] == "BLOCKED"
    assert "SENTINEL_DNA_IMAGE_DIGEST" in result["missing"]
    assert result["secret_values_logged"] is False
    assert result["secret_contents_read"] is False
    assert result["live_operations_performed"] is False


def test_complete_shape_passes_without_reading_secret_contents():
    result = validate(complete_intake())
    assert result["status"] == "PASS"
    assert result["missing"] == []
    assert result["invalid"] == []


def test_mutable_images_placeholders_and_bad_digests_fail_closed():
    values = complete_intake()
    values["SENTINEL_DNA_STAGING_APP_IMAGE"] = "staging-app:latest"
    values["SENTINEL_DNA_STAGING_EDGE_IMAGE"] = "nginx:stable"
    values["SENTINEL_DNA_TRUSTED_BROWSER_IMAGE"] = "trusted-browser:latest"
    values["SENTINEL_DNA_POSTGRES_IMAGE"] = "postgres:16-alpine"
    values["SENTINEL_DNA_REDIS_IMAGE"] = "redis:7-alpine"
    values["SENTINEL_DNA_EGRESS_POLICY_DIGEST"] = "not-a-digest"
    values["SENTINEL_DNA_CERTIFIED_ORIGIN"] = "__CERTIFIED_ORIGIN__"
    result = validate(values)
    assert result["status"] == "BLOCKED"
    reasons = {(item["name"], item["reason"]) for item in result["invalid"]}
    assert ("SENTINEL_DNA_TRUSTED_BROWSER_IMAGE", "immutable_sha256_reference_required") in reasons
    assert ("SENTINEL_DNA_STAGING_APP_IMAGE", "immutable_sha256_reference_required") in reasons
    assert ("SENTINEL_DNA_STAGING_EDGE_IMAGE", "immutable_sha256_reference_required") in reasons
    assert ("SENTINEL_DNA_POSTGRES_IMAGE", "immutable_sha256_reference_required") in reasons
    assert ("SENTINEL_DNA_REDIS_IMAGE", "immutable_sha256_reference_required") in reasons
    assert ("SENTINEL_DNA_EGRESS_POLICY_DIGEST", "sha256_required") in reasons
    assert ("SENTINEL_DNA_CERTIFIED_ORIGIN", "placeholder_value") in reasons


def test_developer_paths_are_not_accepted():
    values = complete_intake()
    values["SENTINEL_DNA_TRUSTED_BROWSER_ACTIVATION_MANIFEST"] = r"C:\Users\developer\manifest.json"
    result = validate(values)
    assert result["status"] == "BLOCKED"
    assert any(item["name"] == "SENTINEL_DNA_TRUSTED_BROWSER_ACTIVATION_MANIFEST" for item in result["invalid"])
