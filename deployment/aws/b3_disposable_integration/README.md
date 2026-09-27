# B3 disposable AWS integration harness

This harness is a security-validation tool for real DynamoDB, S3 Object Lock,
KMS, and IAM semantics in an explicitly disposable AWS account. It must never
be run against the Sentinel DNA Trust account (`634176594969`) or its existing
resources.

## Safety gates

The runner refuses to execute unless all of these are set:

```text
SENTINEL_DNA_RUN_AWS_CUSTODY_TESTS=1
SENTINEL_DNA_DISPOSABLE_AWS_ACCOUNT_ID=<12-digit disposable account>
SENTINEL_DNA_DISPOSABLE_AWS_REGION=<region>
SENTINEL_DNA_DISPOSABLE_RESOURCE_PREFIX=sentinel-dna-b3-disposable-<unique-suffix>
SENTINEL_DNA_DISPOSABLE_ACCOUNT_ACK=I_UNDERSTAND_THIS_IS_A_DISPOSABLE_ACCOUNT
SENTINEL_DNA_DISPOSABLE_RESOURCE_ACK=I_UNDERSTAND_UNIQUE_DISPOSABLE_RESOURCES
```

The harness calls STS before creating anything and requires the returned
account to equal the configured disposable account. Account `634176594969` is
always refused. Generated names are scoped to the configured prefix and run
ID; cleanup operates only on the in-memory resources created by that run.

## Planned resources

The resource manager can create a unique pay-per-request DynamoDB table,
versioned/Object-Lock-enabled S3 bucket with 30-day GOVERNANCE retention, and
an ECC P-256 KMS signing key plus unique alias. IAM/provider resources are not
created by default.

The reviewed provider implementation is hard-pinned to the existing Trust
table, bucket, KMS key, and B3 environment. The disposable provider contract
is therefore a separate, identifiable configuration (`sentinel-dna-b3-
disposable-provider-v1`) and the deterministic builder rejects source that
contains Trust identifiers. The current Trust-pinned source is intentionally
rejected; a separately reviewed parameterized provider source is required
before a disposable Lambda package can be built or deployed. The live provider
boundary is reported as `PENDING_REVIEWED_DISPOSABLE_PROVIDER_BUILD` in that
state.

## Evidence and cleanup

Evidence is canonical JSON and rejects fields whose names indicate secrets,
credentials, tokens, passwords, access keys, session material, or private
keys. It records only run/account/region/resource identifiers, safe response
metadata, test results, and cleanup status. Object-Lock evidence is retained
and is never force-deleted. Any cleanup failure is reported with the exact
tracked resource and the harness stops; it never guesses or broadens cleanup.

## Running safely

Offline safety tests:

```text
python -m pytest deployment/aws/b3_disposable_integration/tests -q
```

Gate/plan check (safe without configuration):

```text
python -m deployment.aws.b3_disposable_integration.run_b3_aws_integration --plan
```

No generated AWS artifacts are committed. This harness does not close Gate 5,
does not claim independent authority validation, and does not claim a live AWS
custody lifecycle passed.

## Disposable provider build contract

The future package must be built with explicit values for account, region,
environment, table, bucket, KMS key, function name, and role name. The builder
requires the exact five provider source files, rejects all known Trust account,
resource, and key identifiers, writes a deterministic ZIP, and emits a
source-revision/package/configuration manifest. ZIP and runtime evidence remain
uncommitted artifacts.
