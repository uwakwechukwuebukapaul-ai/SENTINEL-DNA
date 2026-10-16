# Sentinel DNA Synthetic Analyst MVP — Windows Runner Handoff

## Execution status

**PENDING — not executed on an authorized runner for the current dirty worktree.**
An existing GitHub Actions Linux run for the expected HEAD completed successfully
(test run [38594149280](https://github.com/uwakwechukwuebukapaul-ai/SENTINEL-DNA/actions/runs/38594149280):
3,175 passed, 12 skipped on Ubuntu 24.04), but it checked out merge commit
`f3ccc3da7581d0889eede4e3ff1172558773510c`, not this local worktree with its
uncommitted and untracked files. It is supporting evidence only. No authorized
runner that can execute this exact dirty Windows checkout is exposed to this
session. The available Codex Windows sandbox blocks loopback with
`WinError 10013` and Git/MSYS subprocess setup with
`NtCreateDirectoryObject ... 0xC0000022`. Do not treat the local blocked HTTP
test as a pass. No elevated privileges or host-security changes are requested
by this handoff.

Current-session preflight (2026-10-15) confirmed this sandbox is Windows 11
10.0.26220, running non-elevated with Python 3.12.10, pytest 9.1.1, Flask
3.1.3, and Requests 2.34.2. It is not a capable test runner: writing under
the configured TEMP path was denied; a loopback bind/connect on port 5000 was
denied with `WinError 10013`; a minimal local `git clone --no-local` failed
with Git/MSYS `NtCreateDirectoryObject ... 0xC0000022`; and `os.link` failed
with `WinError 5` even in the writable Documents area. These were capability
probes only; neither focused nor broad pytest selection was run in this turn.

The test source must be the existing, intentionally dirty worktree at:

```text
C:\Users\HP\Documents\Codex\sentinel-dna-pr26-fixture-fix-136c8aa
```

Expected branch: `fix/signup-registration-security-20261014`
Expected HEAD: `980a1bcdda07a422ad9b4ae4000389a295083149`

The runner must have this same worktree content, including its modified and
untracked files. Do not reset, clean, checkout another revision, or replace
these files with the committed HEAD. Review `git status --short` before running.

## Runner prerequisites

- Authorized Windows host/runner using a standard, non-elevated user account.
- Python **3.12.10** and pytest **9.1.1**, using the existing isolated
  environment at
  `C:\Users\HP\Documents\Codex\sentinel-dna-venv-diagnostic-20261014\Scripts\python.exe`.
- Flask and Requests must import successfully; the run records their installed
  versions as a dependency check.
- Writable temporary storage for pytest basetemp, logs, and XML reports. Keep
  `TEMP` and `TMP` pointed there for the run.
- Local loopback bind/connect permission for `127.0.0.1:5000`, with that port
  unused before the HTTP test.
- Git for Windows and its MSYS subprocesses must be permitted to create their
  normal per-process named objects and local `git clone --no-local` fixtures.
- Filesystem support for hard links within the temporary volume. Do not bypass
  a denial with elevated privileges.
- Test fixtures create synthetic test users and disposable local test databases
  only. No live credentials or manual account setup are required.

The broad selection initializes schemas with `MigrationRunner` only against
test-created `tmp_path` SQLite files. It does not target a shared database.
Deployment-adapter tests use a fake command runner; the staging contract test
that invokes `docker compose ... config` is explicitly excluded. No deployment,
container, or shared-database action is part of this handoff.

If the runner cannot use the exact Python path above, set `$Python` to an
existing isolated Python 3.12.10 / pytest 9.1.1 executable before running; do
not install dependencies or modify the repository as part of this handoff.

## Previously observed local sandbox results

These are historical results from the restricted Codex Windows sandbox, not
authorized-runner validation:

| Selection | Result | Exit code | Captured artifacts |
|---|---|---:|---|
| Focused selection listed below, including the HTTP test | 87 passed, 1 failed at `sock.connect()` with `WinError 10013` before Flask; 0 skipped | 1 | `C:\Users\HP\Documents\Codex\sentinel-dna-python-temp-20261014\sentinel-focused.log`; `sentinel-focused.xml` |
| Broad selection: `-m 'not postgresql and not live_auth'`, ignore HTTP module and Docker Compose staging contract | 3,079 passed, 30 failed, 58 errors, 6 skipped, 10 deselected | 1 | `C:\Users\HP\Documents\Codex\sentinel-dna-python-temp-20261014\sentinel-broad-final.log`; `sentinel-broad-final.xml` |

The environment used Python **3.12.10**, pytest **9.1.1**, Flask **3.1.3**,
and Requests **2.34.2**. The broad run's 88 remaining outcomes are classified
in [`SYNTHETIC_ANALYST_MVP_FAILURE_CLASSIFICATION.md`](SYNTHETIC_ANALYST_MVP_FAILURE_CLASSIFICATION.md);
that record is diagnostic history and must be replaced or reconciled using
fresh runner evidence.

## Copy-paste PowerShell run

Run from PowerShell. This checks the repository identity without requiring a
clean worktree, records the environment, runs the focused selection including
the real localhost journey, and then runs the broad selection. It preserves
each pytest exit code and writes artifacts outside the repository.

```powershell
$ErrorActionPreference = 'Stop'
$Repo = 'C:\Users\HP\Documents\Codex\sentinel-dna-pr26-fixture-fix-136c8aa'
$Python = 'C:\Users\HP\Documents\Codex\sentinel-dna-venv-diagnostic-20261014\Scripts\python.exe'
$RunId = Get-Date -Format 'yyyyMMdd-HHmmss'
$ArtifactRoot = Join-Path $env:TEMP "sentinel-dna-mvp-authorized-runner-$RunId"
New-Item -ItemType Directory -Path $ArtifactRoot -Force | Out-Null
$env:TEMP = $ArtifactRoot
$env:TMP = $ArtifactRoot

$ActualRoot = [System.IO.Path]::GetFullPath((& git -C $Repo rev-parse --show-toplevel).Trim()).TrimEnd('\', '/')
$ExpectedRoot = [System.IO.Path]::GetFullPath($Repo).TrimEnd('\', '/')
$ActualBranch = (& git -C $Repo branch --show-current).Trim()
$ActualHead = (& git -C $Repo rev-parse HEAD).Trim()
if ($ActualRoot -ine $ExpectedRoot -or
    $ActualBranch -ne 'fix/signup-registration-security-20261014' -or
    $ActualHead -ne '980a1bcdda07a422ad9b4ae4000389a295083149') {
    throw "Unexpected repository identity: $ActualRoot / $ActualBranch / $ActualHead"
}
git -C $Repo status --short
git -C $Repo diff --check
if ($LASTEXITCODE -ne 0) { throw "git diff --check failed: $LASTEXITCODE" }

$Version = (& $Python -c "import sys,pytest; print(f'{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}|{pytest.__version__}')").Trim()
if ($LASTEXITCODE -ne 0) { throw "Could not inspect Python/pytest: $LASTEXITCODE" }
if ($Version -ne '3.12.10|9.1.1') { throw "Expected Python 3.12.10 and pytest 9.1.1; found $Version" }
$Dependencies = (& $Python -c "from importlib.metadata import version; import flask,requests; print('Flask|' + version('Flask') + '; Requests|' + version('requests'))").Trim()
if ($LASTEXITCODE -ne 0) { throw "Required Flask/Requests imports failed: $LASTEXITCODE" }
$Windows = Get-CimInstance Win32_OperatingSystem | Select-Object -First 1
$StartedAt = (Get-Date).ToUniversalTime().ToString('o')
"Python|pytest: $Version`n$Dependencies`nWindows: $($Windows.Caption) $($Windows.Version) build $($Windows.BuildNumber)`nStarted UTC: $StartedAt" |
    Tee-Object -FilePath (Join-Path $ArtifactRoot 'environment.txt')
"Repository: $ActualRoot`nBranch: $ActualBranch`nHEAD: $ActualHead`nArtifacts: $ArtifactRoot" |
    Add-Content -Path (Join-Path $ArtifactRoot 'environment.txt')

Push-Location $Repo
try {
    $FocusedArgs = @(
        '-m', 'pytest', '-p', 'no:cacheprovider',
        "--basetemp=$ArtifactRoot\pytest-focused",
        "--junitxml=$ArtifactRoot\focused.xml",
        'tests/auth/test_auth_security.py',
        'tests/auth/test_auth_v3.py',
        'tests/auth/test_http_v3.py',
        'tests/auth/test_mfa.py',
        'tests/dashboard/test_auth_experience.py',
        'tests/security/test_production_entrypoint_reconciliation.py',
        'tests/security/test_analyst_demo_workflow.py',
        'tests/security/test_logout_navigation.py',
        'tests/security/test_pilot_route_boundary.py',
        'tests/dashboard/test_analyst_workspace_security.py',
        'tests/intelligence/investigation/test_analyst_feedback_pilot.py',
        'tests/audit/test_audit_api.py',
        '-q', '--tb=long'
    )
    $FocusedStartedAt = (Get-Date).ToUniversalTime().ToString('o')
    & $Python @FocusedArgs 2>&1 | Tee-Object -FilePath (Join-Path $ArtifactRoot 'focused.log')
    $FocusedExit = $LASTEXITCODE
    $FocusedEndedAt = (Get-Date).ToUniversalTime().ToString('o')
    "Started UTC: $FocusedStartedAt`nEnded UTC: $FocusedEndedAt`npytest exit code: $FocusedExit" |
        Add-Content -Path (Join-Path $ArtifactRoot 'focused.log')

    $BroadArgs = @(
        '-m', 'pytest', '-p', 'no:cacheprovider',
        "--basetemp=$ArtifactRoot\pytest-broad",
        "--junitxml=$ArtifactRoot\broad.xml",
        '-m', 'not postgresql and not live_auth',
        '--ignore=tests/staging/test_staging_security_contract.py',
        '-q', '--tb=long'
    )
    $BroadStartedAt = (Get-Date).ToUniversalTime().ToString('o')
    & $Python @BroadArgs 2>&1 | Tee-Object -FilePath (Join-Path $ArtifactRoot 'broad.log')
    $BroadExit = $LASTEXITCODE
    $BroadEndedAt = (Get-Date).ToUniversalTime().ToString('o')
    "Started UTC: $BroadStartedAt`nEnded UTC: $BroadEndedAt`npytest exit code: $BroadExit" |
        Add-Content -Path (Join-Path $ArtifactRoot 'broad.log')
}
finally {
    Pop-Location
}

"Focused exit: $FocusedExit`nBroad exit: $BroadExit`nArtifacts: $ArtifactRoot"
if ($FocusedExit -ne 0 -or $BroadExit -ne 0) { exit 1 }
exit 0
```

### Selection and exclusions

- The focused command explicitly includes
  `tests/auth/test_http_v3.py::test_canonical_wsgi_http_v3_journey`. Its
  localhost HTTP journey must execute; it is not ignored or deselected.
- The broad command uses `-m 'not postgresql and not live_auth'` as in the
  previous broad run.
- The broad command ignores only
  `tests/staging/test_staging_security_contract.py`, which invokes Docker
  Compose. It does **not** ignore the HTTP module.
- Do not add skips, markers, environment switches, or security exceptions to
  make failures disappear. Record every failure with node ID, traceback,
  category, and exit code.
- Each test's temporary database/schema setup is disposable and local. Do not
  point the suite at a shared or deployed database.

## Evidence to return

Return the actual PowerShell and pytest exit codes, terminal summaries,
Python/pytest versions, and all four files:

```text
<ArtifactRoot>\environment.txt
<ArtifactRoot>\focused.log
<ArtifactRoot>\focused.xml
<ArtifactRoot>\broad.log
<ArtifactRoot>\broad.xml
```

Inspect the XML and tracebacks before changing statuses in the acceptance
matrix. A test that fails before reaching Flask or its assertions remains
`BLOCKED`/`NOT VERIFIED`; it must not be counted as passed. Reconcile results
with [`SYNTHETIC_ANALYST_MVP_ACCEPTANCE.md`](SYNTHETIC_ANALYST_MVP_ACCEPTANCE.md)
and [`SYNTHETIC_ANALYST_MVP_FAILURE_CLASSIFICATION.md`](SYNTHETIC_ANALYST_MVP_FAILURE_CLASSIFICATION.md).

## Current decision

The test-client synthetic journey is proven locally. Authorized-runner
validation is still pending. The prior localhost socket and Git/MSYS/hard-link
results remain environment-blocked, and no deployment/trust verification or
release readiness is claimed.
