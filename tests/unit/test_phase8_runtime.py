from __future__ import annotations

import json
from types import SimpleNamespace
from typing import Any, cast

import pytest

from agentic_aws_network_ops.adapters import phase8_runtime
from agentic_aws_network_ops.approval.service import ApprovalService
from agentic_aws_network_ops.remediation.aws_executor import AwsRemediationExecutor

PRINCIPAL = "arn:aws:iam::000000000000:user/approved-operator"
BASE_ENV = {
    "PHASE8_AWS_REGION": "eu-west-1",
    "PHASE8_APPROVAL_TABLE_NAME": "agentic-aws-network-ops-lab-phase8-approvals",
}


def approval_env(*principals: str) -> dict[str, str]:
    return {
        **BASE_ENV,
        "PHASE8_AUTHORIZED_APPROVERS_JSON": json.dumps(list(principals)),
    }


def remediation_env() -> dict[str, str]:
    return {
        **BASE_ENV,
        "PHASE8_DESTINATION_SECURITY_GROUP_ID": "sg-0123456789abcdef0",
        "PHASE8_DESTINATION_VPC_ID": "vpc-0123456789abcdef0",
        "PHASE8_SOURCE_VPC_ID": "vpc-0fedcba9876543210",
    }


class ClientFactory:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []

    def __call__(self, service: str, *, region_name: str) -> object:
        self.calls.append((service, region_name))
        return SimpleNamespace(service=service)


def test_approval_factory_constructs_role_backed_service_from_strict_config() -> None:
    clients = ClientFactory()
    service = phase8_runtime.build_approval_service(
        principal=PRINCIPAL,
        context=object(),
        environ=approval_env(PRINCIPAL),
        client_factory=clients,
    )

    assert isinstance(service, ApprovalService)
    assert clients.calls == [("dynamodb", "eu-west-1")]
    repository = cast(Any, service)._repository
    assert repository._table_name == BASE_ENV["PHASE8_APPROVAL_TABLE_NAME"]
    assert service._authorized_approvers == {PRINCIPAL}


def test_approval_factory_rejects_unconfigured_authenticated_principal_before_aws() -> None:
    clients = ClientFactory()

    with pytest.raises(phase8_runtime.RuntimeConfigurationError, match="authorized approver"):
        phase8_runtime.build_approval_service(
            principal="arn:aws:iam::000000000000:user/not-authorized",
            context=object(),
            environ=approval_env(PRINCIPAL),
            client_factory=clients,
        )

    assert clients.calls == []


@pytest.mark.parametrize(
    "environment",
    [
        {**BASE_ENV, "PHASE8_AUTHORIZED_APPROVERS_JSON": "not-json"},
        {**BASE_ENV, "PHASE8_AUTHORIZED_APPROVERS_JSON": "[]"},
        {**BASE_ENV, "PHASE8_AUTHORIZED_APPROVERS_JSON": json.dumps([PRINCIPAL, PRINCIPAL])},
        {**BASE_ENV, "PHASE8_AUTHORIZED_APPROVERS_JSON": json.dumps(["not-an-arn"])},
    ],
)
def test_approval_factory_rejects_malformed_configuration_before_client_creation(
    environment: dict[str, str],
) -> None:
    clients = ClientFactory()

    with pytest.raises(phase8_runtime.RuntimeConfigurationError):
        phase8_runtime.build_approval_service(
            principal=PRINCIPAL,
            context=object(),
            environ=environment,
            client_factory=clients,
        )

    assert clients.calls == []


def test_remediation_factory_constructs_executor_from_trusted_resource_config() -> None:
    clients = ClientFactory()
    executor = phase8_runtime.build_remediation_executor(
        principal=PRINCIPAL,
        context=object(),
        environ=remediation_env(),
        client_factory=clients,
    )

    assert isinstance(executor, AwsRemediationExecutor)
    assert clients.calls == [("dynamodb", "eu-west-1"), ("ec2", "eu-west-1")]
    assert executor._resources.destination_security_group_id == "sg-0123456789abcdef0"
    assert executor._resources.destination_vpc_id == "vpc-0123456789abcdef0"
    assert executor._resources.source_vpc_id == "vpc-0fedcba9876543210"


def test_remediation_factory_rejects_invalid_trusted_ids_before_client_creation() -> None:
    clients = ClientFactory()
    environment = {**remediation_env(), "PHASE8_DESTINATION_VPC_ID": "not-a-vpc"}

    with pytest.raises(phase8_runtime.RuntimeConfigurationError):
        phase8_runtime.build_remediation_executor(
            principal=PRINCIPAL,
            context=object(),
            environ=environment,
            client_factory=clients,
        )

    assert clients.calls == []
