"""Unit tests for the immutable Phase 8 remediation manifest."""

from __future__ import annotations

import pytest

from agentic_aws_network_ops.remediation.manifest import DEFAULT_MANIFEST, resolve_manifest


@pytest.mark.parametrize(
    "action,scenario",
    [
        ("restore_security_group_ingress", "security_group_rule"),
        ("restore_vpc_peering_route", "route_table_entry"),
        ("restore_network_acl_entry", "nacl_rule"),
    ],
)
def test_manifest_resolves_exact_action_scenarios(action: str, scenario: str) -> None:
    spec = resolve_manifest(action, scenario)
    assert spec.region == "eu-west-1"
    assert spec.required_tags.as_dict() == {
        "Project": "agentic-aws-network-ops",
        "Environment": "lab",
        "ManagedBy": "terraform",
    }
    assert spec.protocol == "tcp"
    assert spec.from_port == 443
    assert spec.to_port == 443
    assert spec.expected_post_state
    if action == "restore_vpc_peering_route":
        assert [target.vpc_role for target in spec.route_targets] == ["source", "destination"]
    else:
        assert spec.expected_vpc_role == "destination"


def test_manifest_rejects_unsupported_scenario_action_pairs() -> None:
    with pytest.raises(ValueError):
        resolve_manifest("restore_network_acl_entry", "security_group_rule")
    with pytest.raises(ValueError):
        resolve_manifest("restore_peering_dns", "peering_routes_dns")


def test_manifest_nested_values_are_immutable() -> None:
    spec = DEFAULT_MANIFEST["restore_vpc_peering_route"]
    with pytest.raises((AttributeError, TypeError)):
        spec.route_targets[0].route_table_ids += ("attacker-table",)  # type: ignore[misc]
    with pytest.raises(TypeError):
        spec.required_tags.as_dict()["Project"] = "attacker"  # type: ignore[index]
    with pytest.raises(TypeError):
        spec.parameters()["destination_cidr"] = "0.0.0.0/0"  # type: ignore[index]
