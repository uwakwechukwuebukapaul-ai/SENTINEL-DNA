# Sentinel DNA v0.1 Deployment Guide

Set `SENTINEL_DNA_ENV` to `development`, `testing`, or `production`. Production requires a secret of at least 32 characters in `SENTINEL_DNA_SECRET_KEY`. SQLite uses `SENTINEL_DNA_DB_PATH`.

Copy `.env.example` to a protected `.env`, replace placeholder secrets, then run `docker compose up --build`. The container runs as a non-root `sentinel` user and persists data under `/var/lib/sentinel`.

`GET /health` checks application and database availability. `GET /ready` additionally validates required registered services.
