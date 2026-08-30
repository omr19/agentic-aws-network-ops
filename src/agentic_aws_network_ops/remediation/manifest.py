"""Immutable local remediation manifest derived from the approved Phase 6 baseline."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Final

REGION: Final = "eu-west-1"
PROJECT: Final = "agentic-aws-network-ops"
ENVIRONMENT: Final = "lab"


@dataclass(frozen=True)
class RequiredTags:
    project: str = PROJECT
    environment: str = ENVIRONMENT
    managed_by: str = "terraform"

    def as_dict(self) -> Mapping[str, str]:
        return MappingProxyType(
            {"Project": self.project, "Environment": self.environment, "ManagedBy": self.managed_by}
        )


@dataclass(frozen=True)
class RouteTarget:
    route_table_ids: tuple[str, ...]
    destination_cidr: str
    peering_connection_id: str


@dataclass(frozen=True)
class RemediationSpec:
    scenario_id: str
    action: str
    region: str
    resource_id: str
    operation: str
    protocol: str
    from_port: int
    to_port: int
    source_cidr: str
    route_targets: tuple[RouteTarget, ...]
    nacl_rule_number: int | None
    nacl_egress: bool | None
    nacl_action: str | None
    required_tags: RequiredTags
    expected_post_state: str

    def parameters(self) -> Mapping[str, object]:
        if self.action == "restore_security_group_ingress":
            return MappingProxyType(
                {
                    "protocol": self.protocol,
                    "from_port": self.from_port,
                    "to_port": self.to_port,
                    "cidr_ip": self.source_cidr,
                }
            )
        if self.action == "restore_vpc_peering_route":
            return MappingProxyType(
                {
                    "route_targets": [
                        {
                            "route_table_ids": list(target.route_table_ids),
                            "destination_cidr": target.destination_cidr,
                            "vpc_peering_connection_id": target.peering_connection_id,
                        }
                        for target in self.route_targets
                    ],
                    "protocol": self.protocol,
                }
            )
        return MappingProxyType(
            {
                "rule_number": self.nacl_rule_number,
                "egress": self.nacl_egress,
                "protocol": self.protocol,
                "from_port": self.from_port,
                "to_port": self.to_port,
                "cidr_block": self.source_cidr,
                "rule_action": self.nacl_action,
            }
        )


_REQUIRED_TAGS = RequiredTags()
_EMPTY_ROUTES: tuple[RouteTarget, ...] = ()

DEFAULT_MANIFEST: Mapping[str, RemediationSpec] = MappingProxyType(
    {
        "restore_security_group_ingress": RemediationSpec(
            scenario_id="security_group_rule",
            action="restore_security_group_ingress",
            region=REGION,
            resource_id="${destination_security_group_id}",
            operation="AuthorizeSecurityGroupIngress",
            protocol="tcp",
            from_port=443,
            to_port=443,
            source_cidr="10.10.0.0/16",
            route_targets=_EMPTY_ROUTES,
            nacl_rule_number=None,
            nacl_egress=None,
            nacl_action=None,
            required_tags=_REQUIRED_TAGS,
            expected_post_state=(
                "Destination security group permits TCP/443 ingress from 10.10.0.0/16."
            ),
        ),
        "restore_vpc_peering_route": RemediationSpec(
            scenario_id="route_table_entry",
            action="restore_vpc_peering_route",
            region=REGION,
            resource_id="${source_and_destination_route_table_ids}",
            operation="CreateRouteOrReplaceRoute",
            protocol="tcp",
            from_port=443,
            to_port=443,
            source_cidr="10.10.0.0/16",
            route_targets=(
                RouteTarget(
                    ("rtb-0f1e30ea77719b740", "rtb-032520fd18e9125d7"),
                    "10.20.0.0/16",
                    "pcx-05b83a5ce62cc74a9",
                ),
                RouteTarget(
                    ("rtb-05105982ccee2a69d", "rtb-0af09ea83c79d902a"),
                    "10.10.0.0/16",
                    "pcx-05b83a5ce62cc74a9",
                ),
            ),
            nacl_rule_number=None,
            nacl_egress=None,
            nacl_action=None,
            required_tags=_REQUIRED_TAGS,
            expected_post_state=(
                "All four project route tables have the approved active peering routes."
            ),
        ),
        "restore_network_acl_entry": RemediationSpec(
            scenario_id="nacl_rule",
            action="restore_network_acl_entry",
            region=REGION,
            resource_id="acl-09bd99df7314e97fd",
            operation="ReplaceNetworkAclEntry",
            protocol="tcp",
            from_port=443,
            to_port=443,
            source_cidr="10.10.0.0/16",
            route_targets=_EMPTY_ROUTES,
            nacl_rule_number=100,
            nacl_egress=False,
            nacl_action="allow",
            required_tags=_REQUIRED_TAGS,
            expected_post_state=(
                "Destination NACL rule 100 allows ingress TCP/443 from 10.10.0.0/16."
            ),
        ),
    }
)


def resolve_manifest(action: str, scenario_id: str) -> RemediationSpec:
    """Resolve one exact action/scenario pair; callers cannot supply resource facts."""

    spec = DEFAULT_MANIFEST.get(action)
    if spec is None or spec.scenario_id != scenario_id:
        raise ValueError("unsupported remediation action or scenario")
    return spec
