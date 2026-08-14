# Connector Development Guide

Implement the connector adapter contract: `connect()`, `authenticate()`, `health_check()`, `collect()`, and `normalize()`. Every normalized event must retain `organization_id`; credentials must never be returned from public serializers. Register new providers through the connector registry and add health/tenant-isolation tests.
