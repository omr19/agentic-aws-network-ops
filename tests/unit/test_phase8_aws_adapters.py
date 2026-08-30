"""Mocked tests for the local Phase 8 AWS-backed adapters."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

import pytest
from boto3.dynamodb.types import TypeDeserializer, TypeSerializer  # type: ignore[import-untyped]
from botocore.exceptions import ClientError  # type: ignore[import-untyped]

from agentic_aws_network_ops.approval.dynamodb_repository import (
    DynamoDBApprovalError,
    DynamoDBApprovalRepository,
)
from agentic_aws_network_ops.approval.repository import ConsumeResult, InMemoryApprovalRepository
from agentic_aws_network_ops.approval.service import ApprovalService
from agentic_aws_network_ops.remediation.aws_executor import (
    AwsRemediationExecutor,
    RemediationAdapterError,
    TrustedPhase8Resources,
)
from agentic_aws_network_ops.remediation.manifest import resolve_manifest
from agentic_aws_network_ops.remediation.workflow import request_hash

NOW = datetime(2026, 9, 5, 12, 0, tzinfo=UTC)
TABLE = "phase8-approvals"
PRINCIPAL = "arn:aws:iam::000000000000:user/operator"


def aws_error(code: str, operation: str) -> ClientError:
    return ClientError({"Error": {"Code": code, "Message": "redacted"}}, operation)


class FakeDynamoClient:
    def __init__(self) -> None:
        self.items: dict[str, dict[str, dict[str, Any]]] = {}
        self.serializer = TypeSerializer()
        self.deserializer = TypeDeserializer()
        self.fail_operation: str | None = None

    def _maybe_fail(self, operation: str) -> None:
        if self.fail_operation == operation:
            raise aws_error("AccessDeniedException", operation)

    def put_item(self, **kwargs: Any) -> dict[str, Any]:
        self._maybe_fail("PutItem")
        key = str(self.deserializer.deserialize(kwargs["Item"]["approval_id"]))
        if key in self.items:
            raise aws_error("ConditionalCheckFailedException", "PutItem")
        self.items[key] = dict(kwargs["Item"])
        return {}

    def get_item(self, **kwargs: Any) -> dict[str, Any]:
        self._maybe_fail("GetItem")
        key = str(self.deserializer.deserialize(kwargs["Key"]["approval_id"]))
        return {"Item": dict(self.items[key])} if key in self.items else {}

    def update_item(self, **kwargs: Any) -> dict[str, Any]:
        self._maybe_fail("UpdateItem")
        key = str(self.deserializer.deserialize(kwargs["Key"]["approval_id"]))
        item = self.items[key]
        values = kwargs["ExpressionAttributeValues"]
        if "attribute_not_exists(execution_id)" in kwargs.get("ConditionExpression", ""):
            if "execution_id" in item:
                raise aws_error("ConditionalCheckFailedException", "UpdateItem")
            item["execution_id"] = values[":execution_id"]
            item["execution_status"] = values[":executing"]
            item["consumed"] = values[":true"]
            return {"Attributes": dict(item)}
        expected = self.deserializer.deserialize(values[":execution_id"])
        actual = self.deserializer.deserialize(item.get("execution_id", {"NULL": True}))
        if actual != expected:
            raise aws_error("ConditionalCheckFailedException", "UpdateItem")
        item["execution_status"] = values[":status"]
        item["execution_result"] = values[":result"]
        return {}


def approval_record(
    *,
    approval_id: str,
    decision: str = "APPROVED",
    expires_at: datetime = NOW + timedelta(minutes=5),
    execution_id: str | None = None,
) -> dict[str, Any]:
    record: dict[str, Any] = {
        "schema_version": "1.0.0",
        "approval_id": approval_id,
        "proposal_id": str(uuid4()),
        "correlation_id": str(uuid4()),
        "policy_session_id": str(uuid4()),
        "request_hash": "a" * 64,
        "action": "restore_security_group_ingress",
        "resource": "${destination_security_group_id}",
        "operation": "AuthorizeSecurityGroupIngress",
        "approver_principal": PRINCIPAL,
        "decision": decision,
        "approved_at": NOW.isoformat().replace("+00:00", "Z"),
        "expires_at": expires_at.isoformat().replace("+00:00", "Z"),
        "consumed": execution_id is not None,
        "execution_status": "EXECUTING" if execution_id else "PENDING",
    }
    if execution_id:
        record["execution_id"] = execution_id
    return record


def test_dynamodb_repository_conditionally_saves_claims_replays_and_records() -> None:
    client = FakeDynamoClient()
    repository = DynamoDBApprovalRepository(client, table_name=TABLE)
    approval_id = str(uuid4())
    record = approval_record(approval_id=approval_id)

    repository.save(record)
    with pytest.raises(ValueError, match="already exists"):
        repository.save(record)
    claimed = repository.consume(approval_id, str(uuid4()), NOW)
    assert claimed.status == "CLAIMED"
    assert claimed.record is not None
    execution_id = str(claimed.record["execution_id"])
    replay = repository.consume(approval_id, execution_id, NOW)
    assert replay.status == "REPLAY_SAME_EXECUTION"
    with pytest.raises(ValueError, match="execution does not own"):
        repository.record_execution_result(approval_id, str(uuid4()), {"status": "failed"})
    repository.record_execution_result(
        approval_id, execution_id, {"status": "completed", "write_performed": True}
    )
    repository.record_execution_result(
        approval_id, execution_id, {"status": "completed", "write_performed": True}
    )
    assert repository.get(approval_id)["execution_result"]["status"] == "completed"  # type: ignore[index]


def test_dynamodb_repository_rejects_denied_and_expired_approvals() -> None:
    client = FakeDynamoClient()
    repository = DynamoDBApprovalRepository(client, table_name=TABLE)
    denied_id = str(uuid4())
    expired_id = str(uuid4())
    repository.save(approval_record(approval_id=denied_id, decision="DENIED"))
    repository.save(
        approval_record(
            approval_id=expired_id,
            expires_at=NOW - timedelta(seconds=1),
        )
    )
    assert repository.consume(denied_id, str(uuid4()), NOW).status == "NOT_APPROVED"
    assert repository.consume(expired_id, str(uuid4()), NOW).status == "EXPIRED"


def test_dynamodb_repository_maps_aws_errors_without_raw_details() -> None:
    client = FakeDynamoClient()
    client.fail_operation = "GetItem"
    repository = DynamoDBApprovalRepository(client, table_name=TABLE)
    with pytest.raises(DynamoDBApprovalError) as error:
        repository.get(str(uuid4()))
    assert error.value.code == "AccessDeniedException"
    assert "redacted" not in str(error.value)


def request_for(record: dict[str, Any]) -> dict[str, Any]:
    scenarios = {
        "restore_security_group_ingress": "security_group_rule",
        "restore_vpc_peering_route": "route_table_entry",
        "restore_network_acl_entry": "nacl_rule",
    }
    request = {
        "schema_version": "1.0.0",
        "scenario_id": scenarios[record["action"]],
        "approval_id": record["approval_id"],
        "correlation_id": record["correlation_id"],
        "policy_session_id": record["policy_session_id"],
    }
    request["request_hash"] = request_hash(request)
    record["request_hash"] = request["request_hash"]
    return request


class FakeApprovalRepository:
    def __init__(self, record: dict[str, Any], claim: str = "CLAIMED") -> None:
        self.record = record
        self.claim = claim
        self.result: dict[str, Any] | None = None
        self.consume_calls = 0

    def save(self, record: Mapping[str, Any]) -> None:
        del record

    def get(self, approval_id: str) -> dict[str, Any] | None:
        return self.record if approval_id == self.record["approval_id"] else None

    def consume(self, approval_id: str, execution_id: str, now: datetime) -> ConsumeResult:
        self.consume_calls += 1
        if self.claim == "REPLAY_SAME_EXECUTION":
            return ConsumeResult(self.claim, {**self.record, "execution_result": self.result})
        if self.claim != "CLAIMED":
            return ConsumeResult(self.claim, self.record)
        self.record["execution_id"] = execution_id
        return ConsumeResult("CLAIMED", self.record)

    def record_execution_result(
        self, approval_id: str, execution_id: str, result: Mapping[str, Any]
    ) -> None:
        self.result = dict(result)
        self.record["execution_result"] = dict(result)


class FakeEc2Client:
    def __init__(self, *, wrong_vpc: bool = False, verification_failure: bool = False) -> None:
        self.written = False
        self.verification_failure = verification_failure
        self.wrong_vpc = wrong_vpc
        self.raise_on_write = False
        self.calls: list[str] = []

    def describe_security_groups(self, **kwargs: Any) -> dict[str, Any]:
        self.calls.append("describe_security_groups")
        healthy = self.written and not self.verification_failure
        return {
            "SecurityGroups": [
                {
                    "VpcId": "vpc-wrong" if self.wrong_vpc else "vpc-destination",
                    "Tags": [
                        {"Key": "Project", "Value": "agentic-aws-network-ops"},
                        {"Key": "Environment", "Value": "lab"},
                        {"Key": "ManagedBy", "Value": "terraform"},
                    ],
                    "IpPermissions": (
                        [
                            {
                                "IpProtocol": "tcp",
                                "FromPort": 443,
                                "ToPort": 443,
                                "IpRanges": [{"CidrIp": "10.10.0.0/16"}],
                            }
                        ]
                        if healthy
                        else []
                    ),
                }
            ]
        }

    def authorize_security_group_ingress(self, **kwargs: Any) -> dict[str, Any]:
        self.calls.append("authorize_security_group_ingress")
        if self.raise_on_write:
            raise aws_error("UnauthorizedOperation", "AuthorizeSecurityGroupIngress")
        self.written = True
        return {}


def executor_for(
    record: dict[str, Any], ec2: FakeEc2Client, claim: str = "CLAIMED"
) -> tuple[AwsRemediationExecutor, FakeApprovalRepository]:
    repository = FakeApprovalRepository(record, claim=claim)
    return (
        AwsRemediationExecutor(
            ec2_client=ec2,
            approval_repository=repository,
            resources=TrustedPhase8Resources(
                destination_security_group_id="sg-destination",
                destination_vpc_id="vpc-destination",
            ),
        ),
        repository,
    )


def test_remediation_executor_success_uses_manifest_and_verifies_independently() -> None:
    record = approval_record(approval_id=str(uuid4()))
    request = request_for(record)
    ec2 = FakeEc2Client()
    executor, repository = executor_for(record, ec2)
    result = executor.execute(
        spec=resolve_manifest("restore_security_group_ingress", "security_group_rule"),
        request=request,
        execution_id=str(uuid4()),
        now=NOW,
    )
    assert result["status"] == "completed"
    assert result["write_performed"] is True
    assert result["terraform_drift"] is True
    assert repository.result == result
    assert ec2.calls == [
        "describe_security_groups",
        "authorize_security_group_ingress",
        "describe_security_groups",
    ]


def test_remediation_executor_rejects_wrong_resource_before_claim_or_write() -> None:
    record = approval_record(approval_id=str(uuid4()))
    request = request_for(record)
    ec2 = FakeEc2Client(wrong_vpc=True)
    executor, repository = executor_for(record, ec2)
    with pytest.raises(RemediationAdapterError, match="VPC binding"):
        executor.execute(
            spec=resolve_manifest("restore_security_group_ingress", "security_group_rule"),
            request=request,
            execution_id=str(uuid4()),
            now=NOW,
        )
    assert repository.consume_calls == 0
    assert "authorize_security_group_ingress" not in ec2.calls


def test_remediation_executor_handles_aws_error_and_verification_failure() -> None:
    record = approval_record(approval_id=str(uuid4()))
    request = request_for(record)
    ec2 = FakeEc2Client()
    ec2.raise_on_write = True
    executor, repository = executor_for(record, ec2)
    result = executor.execute(
        spec=resolve_manifest("restore_security_group_ingress", "security_group_rule"),
        request=request,
        execution_id=str(uuid4()),
        now=NOW,
    )
    assert result["status"] == "failed"
    assert repository.result is not None

    record = approval_record(approval_id=str(uuid4()))
    request = request_for(record)
    ec2 = FakeEc2Client(verification_failure=True)
    executor, repository = executor_for(record, ec2)
    result = executor.execute(
        spec=resolve_manifest("restore_security_group_ingress", "security_group_rule"),
        request=request,
        execution_id=str(uuid4()),
        now=NOW,
    )
    assert result["status"] == "failed"
    assert result["reconciliation_required"] is True
    assert repository.result == result


def test_remediation_executor_same_execution_replay_returns_result_without_ec2_write() -> None:
    record = approval_record(approval_id=str(uuid4()))
    request = request_for(record)
    execution_id = str(uuid4())
    record["execution_id"] = execution_id
    repository = FakeApprovalRepository(record, claim="REPLAY_SAME_EXECUTION")
    repository.result = {
        "schema_version": "1.0.0",
        "execution_id": execution_id,
        "correlation_id": record["correlation_id"],
        "approval_id": record["approval_id"],
        "status": "completed",
        "write_performed": True,
        "terraform_drift": True,
        "reconciliation_required": True,
    }
    record["execution_result"] = repository.result
    ec2 = FakeEc2Client()
    executor = AwsRemediationExecutor(
        ec2_client=ec2,
        approval_repository=repository,
        resources=TrustedPhase8Resources("sg-destination", "vpc-destination"),
    )
    result = executor.execute(
        spec=resolve_manifest("restore_security_group_ingress", "security_group_rule"),
        request=request,
        execution_id=execution_id,
        now=NOW,
    )
    assert result == repository.result
    assert ec2.calls == []


def test_approval_service_rejects_wrong_principal_with_dynamodb_repository() -> None:
    service = ApprovalService(InMemoryApprovalRepository(), {PRINCIPAL})
    with pytest.raises(ValueError, match="unauthorized"):
        service.submit(
            {
                "operation": "approve",
                "proposal_id": str(uuid4()),
                "approval_id": str(uuid4()),
                "correlation_id": str(uuid4()),
                "policy_session_id": str(uuid4()),
                "request_hash": "a" * 64,
                "action": "restore_security_group_ingress",
                "resource": "${destination_security_group_id}",
                "remediation_operation": "AuthorizeSecurityGroupIngress",
                "approver_principal": "arn:aws:iam::000000000000:user/wrong",
            },
            now=NOW,
        )


class FakeRouteEc2Client:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, Any]]] = []
        self.routes: dict[str, dict[str, str]] = {
            "rtb-0f1e30ea77719b740": {
                "DestinationCidrBlock": "10.20.0.0/16",
                "VpcPeeringConnectionId": "pcx-wrong",
            }
        }

    def describe_route_tables(self, **kwargs: Any) -> dict[str, Any]:
        self.calls.append(("describe_route_tables", kwargs))
        spec = resolve_manifest("restore_vpc_peering_route", "route_table_entry")
        tables = []
        for target in spec.route_targets:
            for route_table_id in target.route_table_ids:
                route = self.routes.get(route_table_id)
                tables.append(
                    {
                        "RouteTableId": route_table_id,
                        "Tags": [
                            {"Key": "Project", "Value": "agentic-aws-network-ops"},
                            {"Key": "Environment", "Value": "lab"},
                            {"Key": "ManagedBy", "Value": "terraform"},
                        ],
                        "Routes": [route] if route else [],
                    }
                )
        return {"RouteTables": tables}

    def create_route(self, **kwargs: Any) -> dict[str, Any]:
        self.calls.append(("create_route", kwargs))
        self.routes[kwargs["RouteTableId"]] = {
            "DestinationCidrBlock": kwargs["DestinationCidrBlock"],
            "VpcPeeringConnectionId": kwargs["VpcPeeringConnectionId"],
            "State": "active",
        }
        return {}

    def replace_route(self, **kwargs: Any) -> dict[str, Any]:
        self.calls.append(("replace_route", kwargs))
        self.routes[kwargs["RouteTableId"]] = {
            "DestinationCidrBlock": kwargs["DestinationCidrBlock"],
            "VpcPeeringConnectionId": kwargs["VpcPeeringConnectionId"],
            "State": "active",
        }
        return {}


class FakeNaclEc2Client:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, Any]]] = []
        self.entries: list[dict[str, Any]] = []

    def describe_network_acls(self, **kwargs: Any) -> dict[str, Any]:
        self.calls.append(("describe_network_acls", kwargs))
        return {
            "NetworkAcls": [
                {
                    "NetworkAclId": "acl-09bd99df7314e97fd",
                    "Tags": [
                        {"Key": "Project", "Value": "agentic-aws-network-ops"},
                        {"Key": "Environment", "Value": "lab"},
                        {"Key": "ManagedBy", "Value": "terraform"},
                    ],
                    "Entries": list(self.entries),
                }
            ]
        }

    def replace_network_acl_entry(self, **kwargs: Any) -> dict[str, Any]:
        self.calls.append(("replace_network_acl_entry", kwargs))
        self.entries = [
            {
                "RuleNumber": kwargs["RuleNumber"],
                "Egress": kwargs["Egress"],
                "Protocol": kwargs["Protocol"],
                "RuleAction": kwargs["RuleAction"],
                "CidrBlock": kwargs["CidrBlock"],
                "PortRange": kwargs["PortRange"],
            }
        ]
        return {}


def test_remediation_executor_uses_only_manifest_route_mappings() -> None:
    spec = resolve_manifest("restore_vpc_peering_route", "route_table_entry")
    record = approval_record(approval_id=str(uuid4()))
    record.update(
        action=spec.action,
        resource=spec.resource_id,
        operation=spec.operation,
    )
    request = request_for(record)
    ec2 = FakeRouteEc2Client()
    executor, repository = executor_for(record, ec2)  # type: ignore[arg-type]
    result = executor.execute(spec=spec, request=request, execution_id=str(uuid4()), now=NOW)
    assert result["status"] == "completed"
    assert result["write_performed"] is True
    assert repository.result == result
    assert [call[0] for call in ec2.calls].count("replace_route") == 1
    assert [call[0] for call in ec2.calls].count("create_route") == 3
    assert all(
        call[1]["DestinationCidrBlock"] in {"10.10.0.0/16", "10.20.0.0/16"}
        for call in ec2.calls
        if call[0] in {"create_route", "replace_route"}
    )


def test_remediation_executor_uses_fixed_nacl_entry_and_verifies() -> None:
    spec = resolve_manifest("restore_network_acl_entry", "nacl_rule")
    record = approval_record(approval_id=str(uuid4()))
    record.update(
        action=spec.action,
        resource=spec.resource_id,
        operation=spec.operation,
    )
    request = request_for(record)
    ec2 = FakeNaclEc2Client()
    executor, repository = executor_for(record, ec2)  # type: ignore[arg-type]
    result = executor.execute(spec=spec, request=request, execution_id=str(uuid4()), now=NOW)
    assert result["status"] == "completed"
    assert result["terraform_drift"] is True
    assert repository.result == result
    writes = [call for call in ec2.calls if call[0] == "replace_network_acl_entry"]
    assert len(writes) == 1
    assert writes[0][1]["RuleNumber"] == 100
    assert writes[0][1]["Protocol"] == "6"
    assert writes[0][1]["CidrBlock"] == "10.10.0.0/16"
