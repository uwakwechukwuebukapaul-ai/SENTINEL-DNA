"""Compatibility exports for deployment validation."""

from .contract import (
    DeploymentContractReport,
    DeploymentContractValidator,
    replay_digest,
    write_immutable_report,
)


class DeploymentValidationSuite:
    """Legacy boolean facade plus the evidence-only contract validator."""

    TESTS = ("fresh_installation", "upgrade", "rollback", "backup_restore")

    def run(self, checks=None):
        checks = checks or {}
        return {name: {"passed": bool(checks.get(name, False)), "required": True} for name in self.TESTS}

    def ready(self, checks=None):
        return all(item["passed"] for item in self.run(checks).values())


__all__ = [
    "DeploymentContractReport",
    "DeploymentContractValidator",
    "DeploymentValidationSuite",
    "replay_digest",
    "write_immutable_report",
]
