# Release process

1. Inspect `git status`, the branch, and the diff; preserve unrelated work.
2. Run focused security, tenancy, operations, browser, and changed-contract tests.
3. Run the full regression and production-readiness CLI.
4. Run AST, template, dependency, migration, and container checks where the environment supports them.
5. Record `PASS`, `WARN`, `BLOCKED`, or `FAIL`; never convert an unavailable tool into a pass.
6. Review changed files, run `git diff --check`, and create a focused milestone commit only.
7. For deployment, inject secrets, validate health/readiness, verify backups and restore, and perform the authenticated browser release journey.

The release classification is `PRODUCTION READY` only when critical and environment-dependent gates have explicit passing evidence. Otherwise use `PRODUCTION CANDIDATE`, `PILOT READY`, or `BLOCKED`.
