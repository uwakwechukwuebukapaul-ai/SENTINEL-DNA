"""Safety and bounded-evidence helpers for the PostgreSQL rehearsal."""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import os
import subprocess
from typing import Any, Mapping
from urllib.parse import urlparse


APPROVAL_ENV = "SENTINEL_DNA_POSTGRES_REHEARSAL_APPROVED"
APPROVAL_VALUE = "I_UNDERSTAND_DISPOSABLE_POSTGRES_ONLY"
URL_ENV = "SENTINEL_DNA_REHEARSAL_POSTGRES_URL"


def repository_root() -> Path:
    return Path(__file__).resolve().parents[2]


def require_authorized_url(environ: Mapping[str, str] | None = None) -> str:
    values = os.environ if environ is None else environ
    if values.get(APPROVAL_ENV, "") != APPROVAL_VALUE:
        raise RuntimeError("postgres_rehearsal_authorization_required")
    url = values.get(URL_ENV, "").strip()
    parsed = urlparse(url)
    if parsed.scheme not in {"postgres", "postgresql"} or not parsed.netloc:
        raise RuntimeError("disposable_postgresql_url_required")
    return url


def canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str)


def digest(value: Any) -> str:
    return hashlib.sha256((canonical(value) + "\n").encode("utf-8")).hexdigest()


def git_identity(root: Path | None = None) -> dict[str, Any]:
    root = (root or repository_root()).resolve()
    try:
        head = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=root, check=True,
            capture_output=True, text=True,
        ).stdout.strip()
        dirty = bool(subprocess.run(
            ["git", "status", "--porcelain", "--untracked-files=all"],
            cwd=root, check=True, capture_output=True, text=True,
        ).stdout.strip())
    except (OSError, subprocess.CalledProcessError) as exc:
        raise RuntimeError("git_identity_unavailable") from exc
    return {"head": head, "worktree_dirty": dirty}


def output_path(path: str | Path, root: Path | None = None) -> Path:
    root = (root or repository_root()).resolve()
    target = Path(path).expanduser().resolve()
    if target == root or root in target.parents:
        raise ValueError("evidence_output_must_be_outside_repository")
    target.parent.mkdir(parents=True, exist_ok=True)
    return target


def write_report(report: Mapping[str, Any], path: str | Path, root: Path | None = None) -> Path:
    target = output_path(path, root)
    target.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return target


def report_metadata(root: Path | None = None) -> dict[str, Any]:
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "repository": git_identity(root),
        "production_database_touched": False,
        "customer_data_used": False,
        "secrets_serialized": False,
    }

