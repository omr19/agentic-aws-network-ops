"""Contract tests for the closed immutable remediation manifest."""

from __future__ import annotations

from agentic_aws_network_ops.remediation.manifest import DEFAULT_MANIFEST


def test_manifest_contains_only_approved_actions_and_scenarios() -> None:
    assert set(DEFAULT_MANIFEST) == {
        "restore_security_group_ingress",
        "restore_vpc_peering_route",
        "restore_network_acl_entry",
    }
    assert {spec.scenario_id for spec in DEFAULT_MANIFEST.values()} == {
        "security_group_rule",
        "route_table_entry",
        "nacl_rule",
    }
    assert all(spec.region == "eu-west-1" for spec in DEFAULT_MANIFEST.values())


def test_manifest_contains_exact_approved_network_facts() -> None:
    security_group = DEFAULT_MANIFEST["restore_security_group_ingress"]
    assert security_group.operation == "AuthorizeSecurityGroupIngress"
    assert security_group.resource_id == "${destination_security_group_id}"
    assert security_group.source_cidr == "10.10.0.0/16"

    routes = DEFAULT_MANIFEST["restore_vpc_peering_route"]
    assert routes.operation == "CreateRouteOrReplaceRoute"
    assert [target.destination_cidr for target in routes.route_targets] == [
        "10.20.0.0/16",
        "10.10.0.0/16",
    ]
    assert all(
        target.peering_connection_id == "pcx-05b83a5ce62cc74a9" for target in routes.route_targets
    )
    assert tuple(routes.route_targets[0].route_table_ids) == (
        "rtb-0f1e30ea77719b740",
        "rtb-032520fd18e9125d7",
    )
    assert tuple(routes.route_targets[1].route_table_ids) == (
        "rtb-05105982ccee2a69d",
        "rtb-0af09ea83c79d902a",
    )

    nacl = DEFAULT_MANIFEST["restore_network_acl_entry"]
    assert nacl.operation == "ReplaceNetworkAclEntry"
    assert nacl.resource_id == "acl-09bd99df7314e97fd"
    assert (nacl.nacl_rule_number, nacl.nacl_egress, nacl.nacl_action) == (100, False, "allow")
