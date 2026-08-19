# Pilot Deployment Guide

Use the existing production-readiness guidance before a pilot. Set a unique `SENTINEL_DNA_SECRET_KEY`, a persistent writable `SENTINEL_DNA_DB_PATH`, secure cookies, and production environment settings. Run a single Gunicorn worker while SQLite remains the shared persistence boundary.

Before a session, verify application startup, `/health`, `/ready`, tenant membership, and analyst permissions. Do not put tokens, credentials, raw evidence, or provider responses in sample data or logs.
