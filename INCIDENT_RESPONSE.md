# Incident Response Guide

Triage: preserve JSON logs, audit exports, job records, and database/Redis snapshots. Revoke impacted tokens and disable affected users. Contain tenant exposure by blocking ingress and rotating integration/encryption secrets through the secret manager. Notify the security lead, assess tenant scope from immutable stored audit records, and document recovery actions. Restore only verified backups and perform a post-incident access review.
