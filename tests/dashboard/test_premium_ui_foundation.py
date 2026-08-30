"""Static contracts for the canonical TRUST-PREMIUM browser foundation."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
TEMPLATES = ROOT / "dashboard" / "templates"
STATIC = ROOT / "dashboard" / "static"


def read_template(name: str) -> str:
    return (TEMPLATES / name).read_text(encoding="utf-8")


def test_canonical_shell_uses_shared_assets_and_confirmed_navigation():
    shell = read_template("base.html")
    shell_css = (STATIC / "css" / "sentinel-dna-shell.css").read_text(encoding="utf-8")
    shell_js = (STATIC / "js" / "sentinel-dna-shell.js").read_text(encoding="utf-8")

    assert "sentinel-dna-tokens.css" in shell
    assert "sentinel-dna-shell.css" in shell
    assert "sentinel-dna-components.css" in shell
    assert "sentinel-dna-shell.js" in shell
    assert "sentinel-dna-command-palette.js" in shell
    assert 'href="/"' in shell
    assert 'href="/workspace/"' in shell
    assert 'href="/profile"' in shell
    assert "aria-current=\"page\"" in shell
    assert "csrf_token" in shell
    assert "calc(var(--sdna-z-sidebar) - 1)" in shell_css
    assert "restoreFocus" in shell_js


def test_command_palette_contract_is_keyboard_first_and_accessible():
    shell = read_template("base.html")
    script = (STATIC / "js" / "sentinel-dna-command-palette.js").read_text(encoding="utf-8")

    assert 'role="dialog"' in shell
    assert 'aria-modal="true"' in shell
    assert "data-command-open" in shell
    assert "ctrlKey" in script
    assert "metaKey" in script
    assert 'event.key === "Escape"' in script
    assert 'event.key === "ArrowDown"' in script
    assert 'event.key === "ArrowUp"' in script
    assert 'event.key === "Tab"' in script


def test_design_tokens_include_trust_and_reduced_motion_states():
    tokens = (STATIC / "css" / "sentinel-dna-tokens.css").read_text(encoding="utf-8")
    shell = (STATIC / "css" / "sentinel-dna-shell.css").read_text(encoding="utf-8")
    components = (STATIC / "css" / "sentinel-dna-components.css").read_text(encoding="utf-8")

    for token in ("--sdna-accent", "--sdna-intelligence", "--sdna-success", "--sdna-warning", "--sdna-danger", "--sdna-confidence", "--sdna-focus", "--sdna-motion-base"):
        assert token in tokens
    assert "prefers-reduced-motion" in tokens
    assert "prefers-reduced-motion" in shell
    assert ".trust-badge.observed" in components
    assert ".trust-badge.derived" in components
    assert ".trust-badge.recommended" in components
    assert ".trust-badge.analyst" in components
    assert "min-height: 44px" in components


def test_investigation_template_preserves_truth_boundaries_and_csrf_action():
    investigation = read_template("investigation_detail_v3.html")

    for label in ("Observed", "Derived", "ANALYST JUDGMENT", "Provenance", "Uncertainty", "Evidence relationships"):
        assert label in investigation
    assert 'name="csrf_token"' in investigation
    assert "/feedback" in investigation
    assert "No evidence has been persisted" in investigation
    assert "No IOC intelligence is available" in investigation
    assert "No evidence-backed ATT&CK mappings are available" in investigation


def test_workspace_and_report_use_authoritative_projection_language():
    workspace = read_template("workspace_v2.html")
    report = read_template("investigation_report_v4.html")

    assert "NEXT BEST INVESTIGATION" in workspace
    assert "Tenant-scoped investigations" in workspace
    assert "priority.risk_score" in workspace
    assert "OBSERVED EVIDENCE" in report
    assert "DERIVED ANALYSIS" in report
    assert "ANALYST JUDGMENT" in report
    assert "Missing intelligence remains unavailable rather than inferred" in report
    assert "report.execution_status" in report
    assert "evidence_collection.evidence_ids" in report
    assert "evidence_summary['items']|default([], true)" in report
