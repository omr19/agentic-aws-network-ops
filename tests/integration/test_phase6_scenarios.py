"""Offline verification of the Phase 6 scenario contract and lifecycle.

These tests exercise the local scenario harness only. They do not run Terraform, contact
AWS, change IAM, or require credentials.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

import pytest

HARNESS_PATH = Path(__file__).parents[2] / "scripts" / "phase6_scenario_harness.py"

ALL_SCENARIOS = [
    "healthy",
    "broken_sg",
    "broken_route",
    "broken_nacl",
    "broken_dns",
    "broken_peering",
]


def _load_harness() -> ModuleType:
    spec = importlib.util.spec_from_file_location("phase6_scenario_harness", HARNESS_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


HARNESS = _load_harness()


def test_scenario_catalog_matches_terraform_allowed_values() -> None:
    assert sorted(HARNESS.SCENARIOS) == sorted(ALL_SCENARIOS)
    assert "healthy" in HARNESS.SCENARIOS


@pytest.mark.parametrize("scenario", ALL_SCENARIOS)
def test_each_scenario_injects_diagnoses_restores_and_verifies(scenario: str) -> None:
    result = HARNESS.run_scenario(scenario)
    assert result["passed"] is True
    assert result["verified_healthy_after_restore"] is True
    assert result["deviation_count"] == result["expected_deviation_count"]
    assert result["diagnosis"]["root_cause"]
    assert result["vpc_endpoints"] == "not_applicable_no_project_endpoints"
    assert result["transit_gateway"] == "out_of_scope"


def test_healthy_has_no_deviation() -> None:
    result = HARNESS.run_scenario("healthy")
    assert result["deviation_count"] == 0
    assert result["diagnosis"]["root_cause"] == "none"


@pytest.mark.parametrize("scenario", [s for s in ALL_SCENARIOS if s != "healthy"])
def test_broken_scenarios_have_a_deterministic_root_cause(scenario: str) -> None:
    result = HARNESS.run_scenario(scenario)
    assert result["diagnosis"]["root_cause"] != "none"
    assert result["deviation_count"] >= 1


def test_broken_sg_uses_unroutable_ingress_cidr() -> None:
    result = HARNESS.run_scenario("broken_sg")
    assert result["injected_signature"]["sg_source_cidr"] == HARNESS.BLOCKED_SG_CIDR


def test_broken_peering_disables_both_directions_and_dns() -> None:
    result = HARNESS.run_scenario("broken_peering")
    signature = result["injected_signature"]
    assert signature["enable_source_route"] is False
    assert signature["enable_destination_route"] is False
    assert signature["enable_peering_dns"] is False
    assert result["deviation_count"] == 3


def test_broken_route_disables_only_source_direction() -> None:
    result = HARNESS.run_scenario("broken_route")
    signature = result["injected_signature"]
    assert signature["enable_source_route"] is False
    assert signature["enable_destination_route"] is True
    assert signature["enable_peering_dns"] is True
    assert result["deviation_count"] == 1


def test_restore_returns_exact_healthy_baseline() -> None:
    for scenario in ALL_SCENARIOS:
        restored = HARNESS.restore_to_healthy(scenario)
        assert restored == HARNESS.HEALTHY
