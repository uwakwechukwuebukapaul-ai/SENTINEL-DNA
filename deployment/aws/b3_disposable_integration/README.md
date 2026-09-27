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

The production Trust provider remains unchanged and hard-pinned to its own
scope. The disposable path is a separate five-file source tree under
`provider_source/`, selected only by the explicit
`sentinel-dna-b3-disposable-provider-v1` contract. Its table, bucket, KMS ARN,
region, and environment are supplied through the disposable configuration
contract; missing or Trust-scoped values fail closed. The deterministic
builder rejects Trust identifiers and emits the same five-file Lambda package
shape used by the reviewed packaging contract. The resulting ZIP is a local
artifact only and is not deployed by this source change.

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

The disposable provider source preserves `RESERVE`, `RECONCILE`, `INSPECT`,
`VERIFY`, `CONSUME`, and `ABORT`, together with binding normalization,
conditional replay protection, idempotent consume handling, KMS integrity
checks, S3 Object Lock evidence, and fail-closed configuration. Production
environment names do not enable this source: the disposable marker and all
resource settings must be present before client construction.
