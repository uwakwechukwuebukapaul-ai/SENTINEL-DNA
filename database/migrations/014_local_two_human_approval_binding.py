"""Add approval payload binding fields for the local staging ceremony."""

from __future__ import annotations

import os


VERSION = 14
NAMESPACE = "staging-two-human-ceremony"
DESCRIPTION = "Local two-human approval payload binding"


def upgrade(connection) -> None:
    if os.environ.get("SENTINEL_DNA_ENV", "").strip().lower() != "staging":
        raise RuntimeError("local_two_human_approval_binding_requires_staging")
    connection.execute("ALTER TABLE staging_two_human_approvals ADD COLUMN counterparty_subject TEXT NOT NULL DEFAULT ''")
    connection.execute("ALTER TABLE staging_two_human_approvals ADD COLUMN counterparty_key_id TEXT NOT NULL DEFAULT ''")
    connection.execute("ALTER TABLE staging_two_human_approvals ADD COLUMN signed_payload_hash TEXT NOT NULL DEFAULT ''")
