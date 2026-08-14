# Sentinel DNA production readiness

The platform keeps storage, queue, and object persistence behind service boundaries so deployments can provide PostgreSQL, Redis, and S3-compatible implementations without changing domain contracts. Configure `SENTINEL_DNA_DB_PATH` for the current database adapter, `SENTINEL_DNA_SECRET_KEY` for sessions, and run streaming/connector workers under the deployment supervisor. Production deployments should use managed PostgreSQL, Redis Streams, encrypted object storage, TLS, secret-manager-backed credentials, and independent worker processes.
