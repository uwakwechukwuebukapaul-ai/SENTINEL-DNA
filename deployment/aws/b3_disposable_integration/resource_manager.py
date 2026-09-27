"""Bounded disposable resource creation and cleanup.

This module deliberately does not deploy Lambda. The reviewed provider source
is hard-pinned to the existing Trust resource graph; a separate disposable
provider build/deployment review is therefore required before live execution.
"""

from __future__ import annotations

import json
from typing import Any

from .safety import DisposableConfig, SafetyError, assert_safe_name


class ResourceManager:
    def __init__(self, config: DisposableConfig, session: Any):
        self.config = config
        self.session = session
        self.ddb = session.client("dynamodb", region_name=config.region)
        self.s3 = session.client("s3", region_name=config.region)
        self.kms = session.client("kms", region_name=config.region)
        self.iam = session.client("iam", region_name=config.region)
        self.created: list[dict[str, str]] = []

    def _track(self, kind: str, name: str, arn: str = "") -> None:
        assert_safe_name(name, self.config)
        self.created.append({"kind": kind, "name": name, "arn": arn})

    def create_table(self) -> dict[str, Any]:
        name = self.config.names["table"]
        assert_safe_name(name, self.config)
        result = self.ddb.create_table(
            TableName=name,
            BillingMode="PAY_PER_REQUEST",
            AttributeDefinitions=[{"AttributeName": "custody_id", "AttributeType": "S"}],
            KeySchema=[{"AttributeName": "custody_id", "KeyType": "HASH"}],
            Tags=[{"Key": "System", "Value": "SentinelDNA-B3-Disposable"}, {"Key": "RunId", "Value": self.config.run_id}],
        )
        arn = result["TableDescription"]["TableArn"]
        self._track("dynamodb_table", name, arn)
        return {"name": name, "arn": arn}

    def create_bucket(self) -> dict[str, Any]:
        name = self.config.names["bucket"]
        assert_safe_name(name, self.config)
        args: dict[str, Any] = {"Bucket": name, "ObjectLockEnabledForBucket": True}
        if self.config.region != "us-east-1":
            args["CreateBucketConfiguration"] = {"LocationConstraint": self.config.region}
        self.s3.create_bucket(**args)
        self.s3.put_bucket_versioning(Bucket=name, VersioningConfiguration={"Status": "Enabled"})
        self.s3.put_object_lock_configuration(
            Bucket=name,
            ObjectLockConfiguration={
                "ObjectLockEnabled": "Enabled",
                "Rule": {"DefaultRetention": {"Mode": "GOVERNANCE", "Days": 30}},
            },
        )
        self.s3.put_public_access_block(
            Bucket=name,
            PublicAccessBlockConfiguration={
                "BlockPublicAcls": True,
                "IgnorePublicAcls": True,
                "BlockPublicPolicy": True,
                "RestrictPublicBuckets": True,
            },
        )
        self.s3.put_bucket_ownership_controls(
            Bucket=name,
            OwnershipControls={"Rules": [{"ObjectOwnership": "BucketOwnerEnforced"}]},
        )
        self._track("s3_bucket", name, f"arn:aws:s3:::{name}")
        return {"name": name, "arn": f"arn:aws:s3:::{name}"}

    def create_signing_key(self, role_arn: str | None = None) -> dict[str, Any]:
        alias = self.config.names["kms_alias"]
        if not alias.startswith(f"alias/{self.config.resource_prefix}-{self.config.run_id}-"):
            raise SafetyError("KMS alias is outside this run prefix")
        response = self.kms.create_key(
            Description=f"Sentinel DNA B3 disposable signing key {self.config.run_id}",
            KeyUsage="SIGN_VERIFY",
            KeySpec="ECC_NIST_P256",
            Tags=[{"TagKey": "System", "TagValue": "SentinelDNA-B3-Disposable"}, {"TagKey": "RunId", "TagValue": self.config.run_id}],
        )
        key_id = response["KeyMetadata"]["KeyId"]
        self.kms.create_alias(AliasName=alias, TargetKeyId=key_id)
        self._track("kms_key", key_id, response["KeyMetadata"]["Arn"])
        self._track("kms_alias", alias)
        return {"key_id": key_id, "arn": response["KeyMetadata"]["Arn"], "alias": alias, "role_arn": role_arn}

    def create_provider_role(self, key_arn: str) -> dict[str, str]:
        """Create the exact disposable provider role boundary.

        This only creates a role whose resources are the resources tracked by
        this run. It does not attach the role to Lambda; deployment remains a
        separately reviewed dependency.
        """
        role_name = self.config.names["role"]
        policy_name = self.config.names["policy"]
        table_arn = f"arn:aws:dynamodb:{self.config.region}:{self.config.account_id}:table/{self.config.names['table']}"
        bucket_arn = f"arn:aws:s3:::{self.config.names['bucket']}"
        self.iam.create_role(
            RoleName=role_name,
            AssumeRolePolicyDocument='{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Principal":{"Service":"lambda.amazonaws.com"},"Action":"sts:AssumeRole"}]}',
            Description=f"Disposable Sentinel DNA B3 provider role {self.config.run_id}",
            Tags=[{"Key": "System", "Value": "SentinelDNA-B3-Disposable"}, {"Key": "RunId", "Value": self.config.run_id}],
        )
        policy = {
            "Version": "2012-10-17",
            "Statement": [
                {"Sid": "CustodyStateRead", "Effect": "Allow", "Action": "dynamodb:GetItem", "Resource": table_arn},
                {"Sid": "CustodyStateTransitions", "Effect": "Allow", "Action": ["dynamodb:TransactWriteItems", "dynamodb:UpdateItem"], "Resource": table_arn},
                {"Sid": "EvidenceWriteOnly", "Effect": "Allow", "Action": ["s3:PutObject", "s3:PutObjectRetention"], "Resource": f"{bucket_arn}/replay-custody/*"},
                {"Sid": "EvidenceIntegrity", "Effect": "Allow", "Action": ["kms:Sign", "kms:Verify"], "Resource": key_arn},
                {"Sid": "EvidenceBucketPreflight", "Effect": "Allow", "Action": ["s3:ListBucket", "s3:GetBucketLocation", "s3:GetBucketVersioning", "s3:GetBucketObjectLockConfiguration", "s3:GetBucketOwnershipControls", "s3:GetBucketPublicAccessBlock"], "Resource": bucket_arn},
            ],
        }
        self.iam.put_role_policy(RoleName=role_name, PolicyName=policy_name, PolicyDocument=json.dumps(policy, separators=(",", ":")))
        role = self.iam.get_role(RoleName=role_name)["Role"]
        self._track("iam_role", role_name, role["Arn"])
        return {"name": role_name, "policy": policy_name, "arn": role["Arn"]}

    def cleanup(self) -> list[dict[str, str]]:
        """Delete only resources tracked by this manager and this run prefix."""
        failures: list[dict[str, str]] = []
        for resource in reversed(self.created):
            try:
                kind, name = resource["kind"], resource["name"]
                assert_safe_name(name, self.config)
                if kind == "dynamodb_table":
                    self.ddb.delete_table(TableName=name)
                elif kind == "s3_bucket":
                    # Object Lock means objects must be reconciled/retained before
                    # deletion; never enumerate or delete outside this run.
                    self.s3.delete_bucket(Bucket=name)
                elif kind == "kms_alias":
                    self.kms.delete_alias(AliasName=name)
                elif kind == "kms_key":
                    self.kms.schedule_key_deletion(KeyId=name, PendingWindowInDays=7)
                elif kind == "iam_role":
                    self.iam.delete_role_policy(RoleName=name, PolicyName=self.config.names["policy"])
                    self.iam.delete_role(RoleName=name)
            except Exception as exc:  # noqa: BLE001 - report every cleanup failure
                failures.append({"kind": resource["kind"], "name": resource["name"], "error": type(exc).__name__})
        return failures
