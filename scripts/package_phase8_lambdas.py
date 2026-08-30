#!/usr/bin/env python3
"""Build deterministic, local-only Phase 8 Lambda package artifacts."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_ROOT = ROOT / ".artifacts"
SOURCE_ROOT = ROOT / "src"
SCHEMA_ROOT = ROOT / "schemas" / "remediation"
FORBIDDEN_PARTS = {
    ".git",
    ".terraform",
    ".venv",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
}


@dataclass(frozen=True)
class PackageSpec:
    component: str
    output_directory: str
    artifact_name: str
    entrypoint: str
    role_boundary: str
    source_files: tuple[str, ...]
    schema_files: tuple[str, ...]


PACKAGE_SPECS = (
    PackageSpec(
        component="approval",
        output_directory="phase8-approval-lambda",
        artifact_name="phase8-approval-lambda.zip",
        entrypoint="agentic_aws_network_ops.adapters.approval_lambda:handler",
        role_boundary="agentic-aws-network-ops-lab-phase8-approval-lambda",
        source_files=(
            "agentic_aws_network_ops/__init__.py",
            "agentic_aws_network_ops/adapters/__init__.py",
            "agentic_aws_network_ops/adapters/phase8_common.py",
            "agentic_aws_network_ops/adapters/phase8_identity.py",
            "agentic_aws_network_ops/adapters/phase8_runtime.py",
            "agentic_aws_network_ops/adapters/approval_lambda.py",
            "agentic_aws_network_ops/approval/__init__.py",
            "agentic_aws_network_ops/approval/dynamodb_repository.py",
            "agentic_aws_network_ops/approval/lambda_interface.py",
            "agentic_aws_network_ops/approval/repository.py",
            "agentic_aws_network_ops/approval/service.py",
        ),
        schema_files=(
            "approval-lambda-event.schema.json",
            "approval.schema.json",
            "proposal.schema.json",
        ),
    ),
    PackageSpec(
        component="remediation",
        output_directory="phase8-remediation-lambda",
        artifact_name="phase8-remediation-lambda.zip",
        entrypoint="agentic_aws_network_ops.adapters.remediation_lambda:handler",
        role_boundary="agentic-aws-network-ops-lab-phase8-remediation-lambda",
        source_files=(
            "agentic_aws_network_ops/__init__.py",
            "agentic_aws_network_ops/adapters/__init__.py",
            "agentic_aws_network_ops/adapters/phase8_common.py",
            "agentic_aws_network_ops/adapters/phase8_identity.py",
            "agentic_aws_network_ops/adapters/phase8_aws.py",
            "agentic_aws_network_ops/adapters/phase8_runtime.py",
            "agentic_aws_network_ops/adapters/remediation_lambda.py",
            "agentic_aws_network_ops/approval/__init__.py",
            "agentic_aws_network_ops/approval/dynamodb_repository.py",
            "agentic_aws_network_ops/approval/repository.py",
            "agentic_aws_network_ops/approval/service.py",
            "agentic_aws_network_ops/remediation/__init__.py",
            "agentic_aws_network_ops/remediation/aws_executor.py",
            "agentic_aws_network_ops/remediation/lambda_interface.py",
            "agentic_aws_network_ops/remediation/manifest.py",
            "agentic_aws_network_ops/remediation/workflow.py",
        ),
        schema_files=(
            "execution-result.schema.json",
            "proposal.schema.json",
            "remediation-lambda-event.schema.json",
            "request.schema.json",
            "verification-result.schema.json",
        ),
    ),
)


def copy_member(source: Path, staging: Path, member: str) -> None:
    destination = staging / member
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)


def prepare_staging(spec: PackageSpec, staging: Path) -> None:
    for source_file in spec.source_files:
        copy_member(SOURCE_ROOT / source_file, staging, source_file)
    for schema_file in spec.schema_files:
        copy_member(SCHEMA_ROOT / schema_file, staging, f"schemas/remediation/{schema_file}")


def iter_files(staging: Path) -> list[Path]:
    return sorted(path for path in staging.rglob("*") if path.is_file())


def validate_staging(staging: Path, spec: PackageSpec) -> list[Path]:
    files = iter_files(staging)
    members = {path.relative_to(staging).as_posix() for path in files}
    required = set(spec.source_files) | {
        f"schemas/remediation/{schema}" for schema in spec.schema_files
    }
    missing = required - members
    if missing:
        raise RuntimeError(f"{spec.component} package is missing: {sorted(missing)}")
    for member in members:
        if any(part in FORBIDDEN_PARTS for part in Path(member).parts):
            raise RuntimeError(f"Forbidden package member: {member}")
        if member.endswith((".pyc", ".pyo")):
            raise RuntimeError(f"Compiled Python member is not allowed: {member}")
    return files


def build_zip(staging: Path, artifact: Path, spec: PackageSpec) -> list[str]:
    files = validate_staging(staging, spec)
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


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_member_manifest(staging: Path, members: list[str], path: Path) -> None:
    lines = [
        f"{hashlib.sha256((staging / member).read_bytes()).hexdigest()}  {member}"
        for member in members
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def smoke_test(artifact: Path, spec: PackageSpec) -> None:
    if spec.component == "approval":
        smoke_code = """
from datetime import UTC, datetime
from uuid import uuid4
from agentic_aws_network_ops.approval.lambda_interface import handle_approval_event
from agentic_aws_network_ops.approval.repository import InMemoryApprovalRepository
from agentic_aws_network_ops.approval.service import ApprovalService

principal = "arn:aws:iam::000000000000:user/offline-smoke"
event = {
    "operation": "approve",
    "proposal_id": str(uuid4()),
    "approval_id": str(uuid4()),
    "correlation_id": str(uuid4()),
    "policy_session_id": str(uuid4()),
    "request_hash": "a" * 64,
    "action": "restore_security_group_ingress",
    "resource": "${destination_security_group_id}",
    "remediation_operation": "AuthorizeSecurityGroupIngress",
    "approver_principal": principal,
}
result = handle_approval_event(
    event,
    service=ApprovalService(InMemoryApprovalRepository(), {principal}),
    now=datetime(2026, 1, 1, tzinfo=UTC),
)
assert result["decision"] == "APPROVED"
assert result["execution_id"] is None
"""
    else:
        smoke_code = """
from datetime import UTC, datetime
from uuid import uuid4
from agentic_aws_network_ops.remediation.lambda_interface import handle_remediation_event

class FakeExecutor:
    def execute(self, *, spec, request, execution_id, now):
        assert spec.action == "restore_network_acl_entry"
        assert spec.nacl_rule_number == 100
        return {"status": "completed", "write_performed": False}

request = {
    "schema_version": "1.0.0",
    "scenario_id": "nacl_rule",
    "approval_id": str(uuid4()),
    "request_hash": "b" * 64,
    "correlation_id": str(uuid4()),
    "policy_session_id": str(uuid4()),
}
result = handle_remediation_event(
    {"action": "restore_network_acl_entry", "request": request, "execution_id": str(uuid4())},
    executor=FakeExecutor(),
    now=datetime(2026, 1, 1, tzinfo=UTC),
)
assert result["status"] == "completed"
"""
    with tempfile.TemporaryDirectory(prefix=f"phase8-{spec.component}-smoke-") as directory:
        extracted = Path(directory) / "artifact"
        extracted.mkdir()
        with zipfile.ZipFile(artifact) as archive:
            archive.extractall(extracted)
        environment = os.environ.copy()
        environment["PYTHONPATH"] = str(extracted)
        environment["AWS_EC2_METADATA_DISABLED"] = "true"
        subprocess.run(  # noqa: S603 - fixed local smoke-test interpreter
            [sys.executable, "-c", smoke_code],
            cwd=extracted,
            env=environment,
            check=True,
        )


def build_component(output_root: Path, spec: PackageSpec, run_smoke: bool) -> dict[str, Any]:
    output = output_root / spec.output_directory
    output.mkdir(parents=True, exist_ok=True)
    artifact = output / spec.artifact_name
    checksum = output / f"{spec.artifact_name}.sha256"
    member_manifest = output / f"{spec.artifact_name}.manifest.txt"
    package_manifest = output / "package-manifest.json"
    for path in (artifact, checksum, member_manifest, package_manifest):
        path.unlink(missing_ok=True)
    with tempfile.TemporaryDirectory(prefix=f"phase8-{spec.component}-stage-") as directory:
        staging = Path(directory)
        prepare_staging(spec, staging)
        members = build_zip(staging, artifact, spec)
        write_member_manifest(staging, members, member_manifest)
    digest = sha256(artifact)
    checksum.write_text(f"{digest}  {artifact.name}\n", encoding="utf-8")
    if run_smoke:
        smoke_test(artifact, spec)
    package_manifest.write_text(
        json.dumps(
            {
                "schema_version": "1.0.0",
                "component": spec.component,
                "artifact": spec.artifact_name,
                "artifact_sha256": digest,
                "entrypoint_contract": spec.entrypoint,
                "iam_role_boundary": spec.role_boundary,
                "runtime": "python3.13",
                "dependencies": "source-only; no native runtime dependencies bundled",
                "members": members,
                "smoke_test": run_smoke,
                "generated_at": "fixed-deterministic-build",
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    return {
        "component": spec.component,
        "artifact": str(artifact),
        "sha256": digest,
        "checksum": str(checksum),
        "manifest": str(package_manifest),
        "member_manifest": str(member_manifest),
        "members": len(members),
    }


def build_all(output_root: Path, run_smoke: bool) -> list[dict[str, Any]]:
    return [build_component(output_root, spec, run_smoke) for spec in PACKAGE_SPECS]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--no-smoke-test", action="store_true")
    arguments = parser.parse_args()
    results = build_all(arguments.output_root, not arguments.no_smoke_test)
    print(json.dumps(results, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
