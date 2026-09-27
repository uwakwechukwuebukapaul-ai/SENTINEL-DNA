"""Deterministic offline builder for a separately parameterized provider.

The current Trust-pinned source is deliberately rejected. A disposable build
is valid only after the provider source itself has an explicit disposable
configuration path and contains no Trust resource identifiers.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
from typing import Iterable
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

from .disposable_provider_config import DisposableProviderConfig, config_from_mapping
from .safety import SafetyError


SOURCE_FILES = (
    "services/__init__.py",
    "services/auth/__init__.py",
    "services/auth/custody_binding.py",
    "services/auth/external_replay_custody.py",
    "services/auth/custody_provider_boundary.py",
)
TRUST_MARKERS = (
    "634176594969",
    "SentinelDNA-Trust-ReplayCustody",
    "sentinel-dna-trust-evidence-634176594969-eu-west-1",
    "SentinelDNA-Trust-CustodyProvider",
    "bc44ab05-34e1-4a02-a792-4ce97c1164eb",
)


class DisposableBuildError(RuntimeError):
    pass


def _file_bytes(source_root: Path, relative: str) -> bytes:
    path = source_root / relative
    if not path.is_file():
        raise DisposableBuildError(f"required provider source missing: {relative}")
    return path.read_bytes()


def validate_source(source_root: Path) -> dict[str, str]:
    hashes: dict[str, str] = {}
    for relative in SOURCE_FILES:
        data = _file_bytes(source_root, relative)
        text = data.decode("utf-8")
        if any(marker in text for marker in TRUST_MARKERS):
            raise DisposableBuildError(f"Trust-pinned identifier found in disposable provider source: {relative}")
        hashes[relative] = hashlib.sha256(data).hexdigest()
    return hashes


def build_package(source_root: Path, output_zip: Path, manifest_path: Path,
                  source_revision: str, config: DisposableProviderConfig) -> dict[str, object]:
    source_hashes = validate_source(source_root)
    output_zip.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(output_zip, "w", compression=ZIP_DEFLATED, compresslevel=9) as archive:
        for relative in SOURCE_FILES:
            info = ZipInfo(relative, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, _file_bytes(source_root, relative))
    package_bytes = output_zip.read_bytes()
    manifest = {
        "schema": "sentinel-dna-b3-disposable-provider-manifest-v1",
        "source_revision": source_revision,
        "source_files": source_hashes,
        "package_sha256": hashlib.sha256(package_bytes).hexdigest().upper(),
        "lambda_code_sha256": base64.b64encode(hashlib.sha256(package_bytes).digest()).decode("ascii"),
        "configuration_contract": config.contract(),
    }
    manifest_path.write_bytes(json.dumps(manifest, sort_keys=True, indent=2).encode("utf-8") + b"\n")
    return manifest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build a deterministic disposable B3 provider package")
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--output-zip", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--source-revision", required=True)
    args = parser.parse_args(argv)
    config = config_from_mapping(os.environ)
    manifest = build_package(args.source_root, args.output_zip, args.manifest, args.source_revision, config)
    print(json.dumps(manifest, sort_keys=True, indent=2))
    return 0


__all__ = ["DisposableBuildError", "SOURCE_FILES", "build_package", "validate_source"]
