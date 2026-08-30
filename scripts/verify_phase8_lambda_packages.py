#!/usr/bin/env python3
"""Verify local Phase 8 Lambda ZIP checksums and manifests without AWS access."""

from __future__ import annotations

import argparse
import hashlib
import json
import zipfile
from pathlib import Path
from typing import Any

from package_phase8_lambdas import DEFAULT_OUTPUT_ROOT, PACKAGE_SPECS


def verify_component(root: Path, output_directory: str, artifact_name: str) -> dict[str, Any]:
    directory = root / output_directory
    artifact = directory / artifact_name
    checksum = directory / f"{artifact_name}.sha256"
    manifest = directory / "package-manifest.json"
    member_manifest = directory / f"{artifact_name}.manifest.txt"
    if not all(path.is_file() for path in (artifact, checksum, manifest, member_manifest)):
        raise RuntimeError(f"Incomplete package artifacts in {directory}")
    digest = hashlib.sha256(artifact.read_bytes()).hexdigest()
    expected_digest, expected_name = checksum.read_text(encoding="utf-8").strip().split("  ")
    if expected_digest != digest or expected_name != artifact_name:
        raise RuntimeError(f"Checksum mismatch for {artifact}")
    metadata = json.loads(manifest.read_text(encoding="utf-8"))
    if metadata["artifact_sha256"] != digest:
        raise RuntimeError(f"Manifest checksum mismatch for {artifact}")
    with zipfile.ZipFile(artifact) as archive:
        members = sorted(archive.namelist())
    if members != metadata["members"]:
        raise RuntimeError(f"Manifest member mismatch for {artifact}")
    return {"artifact": str(artifact), "sha256": digest, "members": len(members)}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    arguments = parser.parse_args()
    results = [
        verify_component(arguments.output_root, spec.output_directory, spec.artifact_name)
        for spec in PACKAGE_SPECS
    ]
    print(json.dumps(results, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
