# Disposable PostgreSQL rehearsal

This package is for an explicitly authorized, local PostgreSQL 16 rehearsal.
It is not a deployment path and never reads `DATABASE_URL`. The database uses
an in-container `tmpfs`, contains synthetic data only, and is destroyed with
`docker compose down --volumes --remove-orphans`.

The scripts require both:

- `SENTINEL_DNA_REHEARSAL_POSTGRES_URL`, pointing to the disposable database;
- `SENTINEL_DNA_POSTGRES_REHEARSAL_APPROVED=I_UNDERSTAND_DISPOSABLE_POSTGRES_ONLY`.

The URL and approval value are never written to evidence. Evidence output must
be outside the repository, for example in a temporary directory.

## Operator flow

From the repository root, create the isolated environment outside the
repository and install only `rehearsal/postgresql/requirements.txt` into it.
This keeps `psycopg` out of the application/test environment:

```powershell
$rehearsalVenv = Join-Path $env:TEMP 'sentinel-dna-postgres-rehearsal-venv'
python -m venv $rehearsalVenv
& "$rehearsalVenv\Scripts\python.exe" -m pip install -r rehearsal/postgresql/requirements.txt
```

Use separate disposable database lifecycles for the standalone migration
report and the full rehearsal. The migration runner intentionally leaves its
target populated, while the full rehearsal intentionally requires an empty
target. Do not add an automatic reset or point both runs at the same target.

Run the standalone migration lifecycle first:

```powershell
$composeFile = 'rehearsal/postgresql/docker-compose.yml'
$migrationProject = 'sentinel-dna-postgres-migration'
$env:SENTINEL_DNA_REHEARSAL_PORT = '55432'

$env:SENTINEL_DNA_REHEARSAL_PASSWORD = '<random-disposable-password>'
docker compose -p $migrationProject -f $composeFile up -d --wait
$env:SENTINEL_DNA_REHEARSAL_POSTGRES_URL = 'postgresql://sentinel_rehearsal:<password>@127.0.0.1:55432/sentinel_dna_rehearsal'
$env:SENTINEL_DNA_POSTGRES_REHEARSAL_APPROVED = 'I_UNDERSTAND_DISPOSABLE_POSTGRES_ONLY'
& "$rehearsalVenv\Scripts\python.exe" rehearsal/postgresql/run_migration.py --output C:\Temp\sentinel-dna-postgresql-migration.json
docker compose -p $migrationProject -f $composeFile down --volumes --remove-orphans
```

Start a new lifecycle for the full rehearsal:

```powershell
$fullProject = 'sentinel-dna-postgres-full-rehearsal'
$env:SENTINEL_DNA_REHEARSAL_PORT = '55433'
docker compose -p $fullProject -f $composeFile up -d --wait
$env:SENTINEL_DNA_REHEARSAL_POSTGRES_URL = 'postgresql://sentinel_rehearsal:<password>@127.0.0.1:55433/sentinel_dna_rehearsal'
& "$rehearsalVenv\Scripts\python.exe" rehearsal/postgresql/run_rehearsal.py --output C:\Temp\sentinel-dna-postgresql-full-rehearsal.json
docker compose -p $fullProject -f $composeFile down --volumes --remove-orphans
```

The generated report is a bounded rehearsal record. A successful report proves
only the checks named in that report against that disposable database. It does
not prove production backup/restore, monitoring ownership, credential
rotation, or release readiness.
