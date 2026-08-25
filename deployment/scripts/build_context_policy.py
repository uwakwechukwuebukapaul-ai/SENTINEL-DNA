"""Fail-closed policy checks for the production Docker build context.

This module validates only filenames and ignore rules. It never opens or
prints the contents of secret-bearing files.
"""

from __future__ import annotations

import argparse
import fnmatch
from pathlib import Path, PurePosixPath


REQUIRED_DOCKERIGNORE_RULES = (
    ".env", ".env.*", "*.env", "*.env.*", "production.env", "production.env.*",
    "**/.env", "**/.env.*", "**/*.env", "**/*.env.*",
    "**/production.env", "**/production.env.*",
    "*.pem", "**/*.pem", "*.key", "**/*.key", "*.crt", "**/*.crt",
    "*.p12", "**/*.p12", "*.pfx", "**/*.pfx",
    "secret", "secret/**", "**/secret", "**/secret/**",
    "secrets", "secrets/**", "**/secrets", "**/secrets/**",
    "credentials", "credentials/**", "**/credentials", "**/credentials/**",
)

_SENSITIVE_SUFFIXES = (".pem", ".key", ".crt", ".p12", ".pfx")
_SENSITIVE_EXACT_NAMES = {".env", "production.env", "secret", "secrets", "credential", "credentials"}


def dockerignore_rules(path: Path) -> frozenset[str]:
    rules: set[str] = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        rule = line.strip()
        if rule and not rule.startswith("#"):
            rules.add(rule)
    return frozenset(rules)


def validate_dockerignore(path: Path) -> tuple[str, ...]:
    rules = dockerignore_rules(path)
    return tuple(rule for rule in REQUIRED_DOCKERIGNORE_RULES if rule not in rules)


def is_sensitive_build_context_path(relative_path: str | Path) -> bool:
    normalized = PurePosixPath(str(relative_path).replace("\\", "/"))
    parts = normalized.parts
    name = normalized.name.lower()
    if name in _SENSITIVE_EXACT_NAMES:
        return True
    if name.startswith(".env.") or name.endswith(".env") or ".env." in name:
        return True
    if name.startswith("production.env.") or name.endswith(_SENSITIVE_SUFFIXES):
        return True
    return any(part.lower() in {"secret", "secrets", "credential", "credentials"} for part in parts[:-1])


def matching_rules(relative_path: str | Path, rules: frozenset[str]) -> tuple[str, ...]:
    normalized = str(relative_path).replace("\\", "/")
    if normalized.startswith("./"):
        normalized = normalized[2:]
    basename = PurePosixPath(normalized).name
    return tuple(sorted(
        rule for rule in rules
        if fnmatch.fnmatch(normalized, rule)
        or fnmatch.fnmatch(basename, rule)
        or (rule.startswith("**/") and fnmatch.fnmatch(normalized, rule[3:]))
    ))


def validate_policy(repository_root: Path) -> tuple[str, ...]:
    dockerignore = repository_root / ".dockerignore"
    missing = validate_dockerignore(dockerignore)
    if missing:
        return tuple(f"missing_dockerignore_rule:{rule}" for rule in missing)
    rules = dockerignore_rules(dockerignore)
    if any(rule.startswith("!") and is_sensitive_build_context_path(rule[1:]) for rule in rules):
        return ("sensitive_reinclude_rule_present",)
    return ()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository-root", type=Path, default=Path.cwd())
    args = parser.parse_args()
    errors = validate_policy(args.repository_root.resolve())
    if errors:
        print("Build context policy invalid: " + ", ".join(errors))
        return 2
    print("Build context policy valid: sensitive artifact rules present")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
