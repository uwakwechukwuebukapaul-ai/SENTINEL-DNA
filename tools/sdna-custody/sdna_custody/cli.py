from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .core import CERTIFIED_ORIGIN, CustodyError, default_state_root, verify_manifest
from .workflow import Authority, actor


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="sdna-custody")
    p.add_argument("--state-root", type=Path, default=default_state_root())
    p.add_argument("--actor")
    sub = p.add_subparsers(dest="command", required=True)
    sub.add_parser("init-root")
    env = sub.add_parser("init-environment")
    env.add_argument("--environment", required=True)
    sub.add_parser("key-list")
    key_status = sub.add_parser("key-status")
    key_status.add_argument("--key-id", required=True)
    key_status.add_argument("--status", choices=["ACTIVE", "GRACE", "REVOKED", "RETIRED"], required=True)
    key_status.add_argument("--reason", required=True)
    req = sub.add_parser("approval-request")
    req_sub = req.add_subparsers(dest="request_command", required=True)
    create = req_sub.add_parser("create")
    create.add_argument("--runtime", type=Path, required=True)
    create.add_argument("--lockfile", type=Path, required=True)
    create.add_argument("--bridge", type=Path)
    create.add_argument("--bridge-identity", required=True)
    create.add_argument("--image-digest", required=True)
    create.add_argument("--image-reference", required=True)
    create.add_argument("--image-verification-reference", required=True)
    create.add_argument("--origin", default=CERTIFIED_ORIGIN)
    approve = sub.add_parser("approval")
    approve_sub = approve.add_subparsers(dest="approval_command", required=True)
    approve_action = approve_sub.add_parser("approve")
    approve_action.add_argument("--approval-id", required=True)
    approve_action.add_argument("--valid-days", type=int, default=30)
    manifest = sub.add_parser("manifest")
    manifest_sub = manifest.add_subparsers(dest="manifest_command", required=True)
    export = manifest_sub.add_parser("export")
    export.add_argument("--approval-id", required=True)
    export.add_argument("--output", type=Path, required=True)
    verify = manifest_sub.add_parser("verify")
    verify.add_argument("--manifest", type=Path, required=True)
    evidence = sub.add_parser("evidence")
    evidence_sub = evidence.add_subparsers(dest="evidence_command", required=True)
    evidence_export = evidence_sub.add_parser("export")
    evidence_export.add_argument("--approval-id", required=True)
    evidence_export.add_argument("--output", type=Path)
    revoke = sub.add_parser("revoke")
    revoke.add_argument("--approval-id", required=True)
    revoke.add_argument("--reason", required=True)
    audit = sub.add_parser("audit")
    audit_sub = audit.add_subparsers(dest="audit_command", required=True)
    audit_export = audit_sub.add_parser("export")
    audit_export.add_argument("--approval-id", required=True)
    audit_export.add_argument("--output", type=Path, required=True)
    return p


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    authority = Authority(args.state_root)
    try:
        actor_id = actor(args.actor)
        if args.command == "init-root":
            result = authority.init_root(actor_id)
        elif args.command == "init-environment":
            result = authority.init_environment(args.environment, actor_id)
        elif args.command == "key-list":
            result = authority.keys()
        elif args.command == "key-status":
            result = authority.signer.set_key_status(args.key_id, args.status, actor_id, args.reason)
        elif args.command == "approval-request" and args.request_command == "create":
            result = authority.create_request(runtime=args.runtime, lockfile=args.lockfile, bridge=args.bridge, bridge_identity=args.bridge_identity, image_digest=args.image_digest, image_reference=args.image_reference, image_verification_reference=args.image_verification_reference, origin=args.origin, requester=actor_id)
        elif args.command == "approval" and args.approval_command == "approve":
            result = authority.approve(args.approval_id, actor_id, args.valid_days)
        elif args.command == "manifest" and args.manifest_command == "export":
            result = authority.export_manifest(args.approval_id, args.output)
        elif args.command == "manifest" and args.manifest_command == "verify":
            result = verify_manifest(json.loads(args.manifest.read_text(encoding="utf-8")), authority.ledger, authority.signer)
        elif args.command == "evidence" and args.evidence_command == "export":
            result = {"path": str(authority.export_evidence(args.approval_id, args.output, actor_id))}
        elif args.command == "revoke":
            result = authority.revoke(args.approval_id, args.reason, actor_id)
        elif args.command == "audit" and args.audit_command == "export":
            result = {"path": str(authority.export_audit(args.approval_id, args.output, actor_id))}
        else:
            raise CustodyError("CUSTODY_COMMAND_INVALID", "unsupported command")
        print(json.dumps(result, sort_keys=True, indent=2))
        return 0
    except CustodyError as exc:
        print(json.dumps({"status": "BLOCKED_WITH_REASON", "code": exc.code, "message": str(exc)}), file=sys.stderr)
        return 2
    finally:
        authority.close()


if __name__ == "__main__":
    raise SystemExit(main())
