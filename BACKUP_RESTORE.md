# Backup and Restore Procedure

Back up PostgreSQL with point-in-time recovery enabled and encrypt backup storage. Snapshot Redis only when durable job/session recovery requires it; PostgreSQL remains the authority for SaaS sessions. Test restores in an isolated environment monthly: restore database, apply required migrations, start API, validate readiness, verify a tenant-scoped audit export, and record elapsed recovery time. Do not restore investigation data outside its approved tenant/data-retention scope.
