#!/usr/bin/env python3
"""Build a deterministic, local-only diagnostic Lambda ZIP artifact."""

from __future__ import annotations

import argparse
import hashlib
import os
import platform
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE_PACKAGE = ROOT / "src" / "agentic_aws_network_ops"
SCHEMA_ROOT = ROOT / "schemas"
DEFAULT_OUTPUT = ROOT / ".artifacts" / "diagnostic-lambda"
ARTIFACT_NAME = "diagnostic-lambda.zip"
REQUIRED_MEMBERS = {
    "agentic_aws_network_ops/adapters/diagnostic_lambda.py",
    "schemas/common/result-envelope.schema.json",
    "schemas/diagnostic/read-tools.schema.json",
}
FORBIDDEN_PARTS = {
    ".terraform",
    ".venv",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "__pycache__",
    ".coverage",
    "coverage.xml",
}


def run(command: list[str], *, cwd: Path = ROOT) -> None:
    subprocess.run(command, cwd=cwd, check=True)  # noqa: S603 - fixed local build commands


def copy_tree(source: Path, destination: Path) -> None:
    shutil.copytree(
        source,
        destination,
        dirs_exist_ok=True,
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyo", ".DS_Store"),
    )


def export_runtime_requirements(path: Path) -> None:
    run(
        [
            "uv",
            "export",
            "--frozen",
            "--no-dev",
            "--no-emit-project",
            "--format",
            "requirements-txt",
            "--output-file",
            str(path),
        ]
    )


def install_runtime_dependencies(requirements: Path, target: Path) -> None:
    run(
        [
            "uv",
            "pip",
            "install",
            "--target",
            str(target),
            "--python-version",
            "3.13",
            "--python-platform",
            "x86_64-manylinux2014",
            "--only-binary",
            ":all:",
            "--no-compile",
            "--requirement",
            str(requirements),
        ]
    )


def iter_files(root: Path) -> list[Path]:
    return sorted(path for path in root.rglob("*") if path.is_file())


def validate_staging(staging: Path) -> list[Path]:
    files = iter_files(staging)
    members = {path.relative_to(staging).as_posix() for path in files}
    missing = REQUIRED_MEMBERS - members
    if missing:
        raise RuntimeError(f"Artifact is missing required members: {sorted(missing)}")
    for member in members:
        if any(part in FORBIDDEN_PARTS for part in Path(member).parts):
            raise RuntimeError(f"Forbidden packaging member: {member}")
        if member.endswith((".pyc", ".pyo")):
            raise RuntimeError(f"Compiled Python member is not allowed: {member}")
    return files


def build_zip(staging: Path, artifact: Path) -> list[str]:
    files = validate_staging(staging)
    members: list[str] = []
    with zipfile.ZipFile(
        artifact, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9
    ) as archive:
        for path in files:
            member = path.relative_to(staging).as_posix()
            info = zipfile.ZipInfo(member, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, path.read_bytes())
            members.append(member)
    return members


def write_manifest(staging: Path, members: list[str], manifest: Path) -> None:
    lines = []
    for member in members:
        digest = hashlib.sha256((staging / member).read_bytes()).hexdigest()
        lines.append(f"{digest}  {member}")
    manifest.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_checksum(artifact: Path, checksum: Path) -> str:
    digest = hashlib.sha256(artifact.read_bytes()).hexdigest()
    checksum.write_text(f"{digest}  {artifact.name}\n", encoding="utf-8")
    return digest


def smoke_test(artifact: Path) -> None:
    smoke_code = """
from agentic_aws_network_ops.adapters import diagnostic_lambda

class FakeService:
    def execute(self, tool, payload):
        assert tool == "describe_vpcs"
        assert payload["region"] == "eu-west-1"
        return {
            "tool": tool,
            "status": "success",
            "correlation_id": payload["correlation_id"],
            "evidence_completeness": "complete",
        }

diagnostic_lambda.build_service = lambda region: FakeService()
result = diagnostic_lambda.handler(
    {
        "tool": "describe_vpcs",
        "arguments": {
            "schema_version": "1.0.0",
            "correlation_id": "corr-package-0001",
            "region": "eu-west-1",
            "project_tag": "agentic-aws-network-ops",
        },
    },
    None,
)
assert result["status"] == "success"
assert result["correlation_id"] == "corr-package-0001"
"""
    with tempfile.TemporaryDirectory(prefix="diagnostic-lambda-smoke-") as directory:
        extracted = Path(directory) / "artifact"
        extracted.mkdir()
        with zipfile.ZipFile(artifact) as archive:
            archive.extractall(extracted)
        smoke_root = extracted
        target_compatible = platform.system() == "Linux" and platform.machine() in {
            "x86_64",
            "amd64",
        }
        if not target_compatible:
            # macOS cannot import the Linux rpds-py wheel. Keep package/schema files from
            # the artifact and resolve dependencies from this host's compatible venv.
            smoke_root = Path(directory) / "host-compatible"
            copy_tree(extracted / "agentic_aws_network_ops", smoke_root / "agentic_aws_network_ops")
            copy_tree(extracted / "schemas", smoke_root / "schemas")
        environment = os.environ.copy()
        environment["PYTHONPATH"] = str(smoke_root)
        environment["AWS_EC2_METADATA_DISABLED"] = "true"
        subprocess.run(  # noqa: S603 - fixed local smoke-test interpreter
            [sys.executable, "-c", smoke_code],
            cwd=smoke_root,
            env=environment,
            check=True,
        )


def build(output: Path, run_smoke: bool) -> tuple[Path, str, Path, list[str]]:
    output.mkdir(parents=True, exist_ok=True)
    artifact = output / ARTIFACT_NAME
    checksum = output / f"{ARTIFACT_NAME}.sha256"
    manifest = output / f"{ARTIFACT_NAME}.manifest.txt"
    for path in (artifact, checksum, manifest):
        path.unlink(missing_ok=True)
    with tempfile.TemporaryDirectory(prefix="diagnostic-lambda-stage-") as directory:
        staging = Path(directory)
        requirements = staging.parent / "runtime-requirements.txt"
        export_runtime_requirements(requirements)
        install_runtime_dependencies(requirements, staging)
        copy_tree(SOURCE_PACKAGE, staging / "agentic_aws_network_ops")
        copy_tree(SCHEMA_ROOT, staging / "schemas")
        members = build_zip(staging, artifact)
        write_manifest(staging, members, manifest)
    digest = write_checksum(artifact, checksum)
    if run_smoke:
        smoke_test(artifact)
    return artifact, digest, manifest, members


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--no-smoke-test", action="store_true")
    arguments = parser.parse_args()
    artifact, digest, manifest, members = build(arguments.output_dir, not arguments.no_smoke_test)
    print(f"artifact={artifact}")
    print(f"sha256={digest}")
    print(f"checksum={artifact}.sha256")
    print(f"manifest={manifest}")
    print(f"members={len(members)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
