"""Reject changed repository artifacts that imitate external governance evidence."""

from __future__ import annotations

import argparse
import subprocess
from pathlib import Path

FORBIDDEN_NAME_PARTS = {"private-key", "private_key", "credentials", "credential", "cloudtrail-public-key"}
EXTERNAL_REFERENCE_MARKERS = ("custody_reference", "external_reference", "evidence_reference")


def changed_paths(root: Path) -> list[Path]:
    result = subprocess.run(
        ["git", "diff", "--name-only", "--diff-filter=AMR", "HEAD^", "HEAD"],
        cwd=root, check=True, capture_output=True, text=True,
    )
    return [root / line.strip() for line in result.stdout.splitlines() if line.strip()]


def violations(root: Path, paths: list[Path]) -> list[str]:
    errors: list[str] = []
    for path in paths:
        relative = path.relative_to(root).as_posix().lower()
        name = path.name.lower()
        if any(marker in name for marker in FORBIDDEN_NAME_PARTS) or name.endswith((".pem", ".key", ".p12", ".pfx")):
            errors.append(f"{relative}:credential_or_private_key_artifact")
            continue
        try:
            lowered = path.read_text(encoding="utf-8").lower()
        except (OSError, UnicodeDecodeError):
            continue
        if "sentinel_dna_trusted_browser_activation_manifest" in lowered and "file:" in lowered:
            errors.append(f"{relative}:repository_local_activation_custody_reference")
        if '"status": "verified"' in lowered and "pilot-evidence/" in relative:
            if not any(marker in lowered for marker in EXTERNAL_REFERENCE_MARKERS):
                errors.append(f"{relative}:verified_pilot_evidence_without_external_reference")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("paths", nargs="*", type=Path)
    args = parser.parse_args()
    root = args.root.resolve()
    paths = [p if p.is_absolute() else root / p for p in args.paths] or changed_paths(root)
    errors = violations(root, paths)
    if errors:
        for error in errors:
            print(f"GOVERNANCE_BOUNDARY=BLOCKED {error}")
        return 1
    print(f"GOVERNANCE_BOUNDARY=PASS checked={len(paths)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
