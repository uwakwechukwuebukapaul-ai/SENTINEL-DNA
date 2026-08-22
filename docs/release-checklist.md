# Enterprise release checklist

- [ ] Production secret injected outside source control.
- [ ] Secure cookies enabled and debug disabled.
- [ ] Database migration/upgrade plan reviewed.
- [ ] Backup and restore procedure executed successfully.
- [ ] `/health` and `/ready` pass in the target environment.
- [ ] Security and tenant-isolation tests pass.
- [ ] Operations lease/retry/dead-letter checks pass.
- [ ] Browser login, workspace, authorization, redaction, and visual checks pass.
- [ ] Representative performance baseline recorded.
- [ ] Production readiness report contains no critical `BLOCKED` or `FAIL` gates.
- [ ] Only milestone files are staged and `git diff --check` passes.
