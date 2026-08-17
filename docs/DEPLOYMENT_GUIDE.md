# Sentinel DNA V1 Deployment Guide

Set `SENTINEL_DNA_ENV` to `development`, `testing`, or `production`. Production requires a random secret of at least 32 characters in `SENTINEL_DNA_SECRET_KEY`, `SENTINEL_DNA_SECURE_COOKIES=1`, and an explicit writable `SENTINEL_DNA_DB_PATH`.

Copy `.env.example` to a protected `.env`, replace the placeholder secret, then run `docker compose up --build`. The container runs as a non-root `sentinel` user and persists data under `/var/lib/sentinel`. V1 uses one Gunicorn worker because SQLite is the current persistence boundary.

`GET /health` checks application and database availability. `GET /ready` additionally validates required registered services.
