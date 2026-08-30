"""Offline reproducibility and smoke tests for Phase 8 Lambda packages."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).parents[2]
PACKAGE_SCRIPT = ROOT / "scripts/package_phase8_lambdas.py"
VERIFY_SCRIPT = ROOT / "scripts/verify_phase8_lambda_packages.py"


def test_phase8_packages_build_verify_and_rebuild_identically(tmp_path: Path) -> None:
    first = tmp_path / "first"
    second = tmp_path / "second"
    for output in (first, second):
        subprocess.run(  # noqa: S603 - fixed local packaging script path
            [sys.executable, str(PACKAGE_SCRIPT), "--output-root", str(output)],
            cwd=ROOT,
            check=True,
        )
        subprocess.run(  # noqa: S603 - fixed local verifier script path
            [sys.executable, str(VERIFY_SCRIPT), "--output-root", str(output)],
            cwd=ROOT,
            check=True,
        )
    for component in ("phase8-approval-lambda", "phase8-remediation-lambda"):
        first_zip = next((first / component).glob("*.zip"))
        second_zip = next((second / component).glob("*.zip"))
        assert (
            hashlib.sha256(first_zip.read_bytes()).hexdigest()
            == hashlib.sha256(second_zip.read_bytes()).hexdigest()
        )
        with zipfile.ZipFile(first_zip) as archive:
            assert all(
                "__pycache__" not in name and not name.endswith(".pyc")
                for name in archive.namelist()
            )
        metadata = json.loads((first / component / "package-manifest.json").read_text())
        assert metadata["smoke_test"] is True
        assert metadata["runtime"] == "python3.13"


def test_artifact_root_is_ignored() -> None:
    result = subprocess.run(  # noqa: S603, S607 - fixed local git check-ignore command
        ["git", "check-ignore", ".artifacts/phase8-approval-lambda/example.zip"],  # noqa: S607
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
