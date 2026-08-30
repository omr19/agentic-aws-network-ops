"""Mockable AWS-backed Phase 8 remediation executor.

Only injected boto3-style clients are used. The event supplies bindings, not
AWS resource IDs or write parameters; all executable values come from the
immutable manifest and trusted deployment resource configuration.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from typing import Any, cast
from uuid import UUID

from botocore.exceptions import BotoCoreError, ClientError  # type: ignore[import-untyped]

from agentic_aws_network_ops.approval.repository import ApprovalRepository, ConsumeResult

from .lambda_interface import RemediationExecutor
from .manifest import RemediationSpec, resolve_manifest
from .workflow import RemediationContractError, validate_request


class RemediationAdapterError(ValueError):
    """Safe, fail-closed adapter error without raw AWS request details."""

    def __init__(
        self,
        message: str,
        *,
        code: str = "ADAPTER_ERROR",
        retryable: bool = False,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.retryable = retryable


@dataclass(frozen=True)
class TrustedPhase8Resources:
    """Deployment-supplied IDs; never populated from a Lambda event."""

    destination_security_group_id: str
    destination_vpc_id: str
    source_vpc_id: str

    def __post_init__(self) -> None:
        if not self.destination_security_group_id.startswith("sg-"):
            raise ValueError("destination_security_group_id must be a security-group ID")
        if not self.destination_vpc_id.startswith("vpc-"):
            raise ValueError("destination_vpc_id must be a VPC ID")
        if not self.source_vpc_id.startswith("vpc-"):
            raise ValueError("source_vpc_id must be a VPC ID")


@dataclass(frozen=True)
class _Preflight:
    healthy: bool
    route_operations: tuple[tuple[str, str, str, str], ...] = ()


class AwsRemediationExecutor(RemediationExecutor):
    """Execute one approved manifest action through injected AWS clients."""

    def __init__(
        self,
        *,
        ec2_client: Any,
        approval_repository: ApprovalRepository,
        resources: TrustedPhase8Resources,
    ) -> None:
        self._ec2 = ec2_client
        self._approvals = approval_repository
        self._resources = resources

    def execute(
        self,
        *,
        spec: RemediationSpec,
        request: Mapping[str, Any],
        execution_id: str,
        now: datetime,
    ) -> dict[str, Any]:
        try:
            validate_request(request)
            self._validate_execution_id(execution_id)
            resolved = resolve_manifest(spec.action, str(request["scenario_id"]))
            if resolved != spec:
                raise RemediationAdapterError("remediation manifest binding is invalid")
            approval = self._approvals.get(str(request["approval_id"]))
            self._validate_approval(approval, request, resolved)
            if approval is not None and approval.get("execution_id") is not None:
                if approval.get("execution_id") != execution_id:
                    raise RemediationAdapterError(
                        "approval belongs to a different execution",
                        code="REPLAY_DIFFERENT_EXECUTION",
                    )
                existing_result = approval.get("execution_result")
                if isinstance(existing_result, Mapping):
                    return dict(existing_result)
                raise RemediationAdapterError(
                    "same execution is already in progress; manual reconciliation is required",
                    code="EXECUTION_IN_PROGRESS",
                )
            preflight = self._preflight(resolved)
        except RemediationAdapterError:
            raise
        except (ValueError, KeyError, TypeError) as error:
            raise RemediationAdapterError("remediation binding is invalid") from error
        except (ClientError, BotoCoreError) as error:
            raise self._aws_error("preflight", error) from error

        claim = self._consume(request, execution_id, now)
        replay = self._replay_result(claim, execution_id)
        if replay is not None:
            return replay
        if claim.status != "CLAIMED":
            raise RemediationAdapterError("approval was not claimed", code=claim.status)

        if preflight.healthy:
            result = self._result(
                request=request,
                execution_id=execution_id,
                status="already_healthy",
                write_performed=False,
                terraform_drift=False,
                reconciliation_required=False,
                message="Approved manifest state was already present; no write was needed.",
            )
            self._record_result(request, execution_id, result)
            return result

        try:
            self._write(resolved, preflight)
            verified = self._verify(resolved)
            if not verified:
                result = self._result(
                    request=request,
                    execution_id=execution_id,
                    status="failed",
                    write_performed=True,
                    terraform_drift=True,
                    reconciliation_required=True,
                    message=(
                        "Independent post-write verification failed; "
                        "reconcile Terraform source."
                    ),
                )
            else:
                result = self._result(
                    request=request,
                    execution_id=execution_id,
                    status="completed",
                    write_performed=True,
                    terraform_drift=True,
                    reconciliation_required=True,
                    message="Approved runtime correction verified; reconcile Terraform source.",
                )
        except (ClientError, BotoCoreError) as error:
            result = self._result(
                request=request,
                execution_id=execution_id,
                status="failed",
                write_performed=True,
                terraform_drift=True,
                reconciliation_required=True,
                message=self._safe_failure_message(error),
            )
        except RemediationAdapterError as error:
            result = self._result(
                request=request,
                execution_id=execution_id,
                status="failed",
                write_performed=True,
                terraform_drift=True,
                reconciliation_required=True,
                message=str(error),
            )

        self._record_result(request, execution_id, result)
        return result

    def _preflight(self, spec: RemediationSpec) -> _Preflight:
        if spec.action == "restore_security_group_ingress":
            response = self._call_ec2(
                "describe_security_groups",
                GroupIds=[self._resources.destination_security_group_id],
            )
            groups = response.get("SecurityGroups", [])
            if len(groups) != 1:
                raise RemediationAdapterError(
                    "security-group preflight returned an unexpected resource"
                )
            group = groups[0]
            self._require_tags(group)
            if group.get("VpcId") != self._resources.destination_vpc_id:
                raise RemediationAdapterError("security-group VPC binding is invalid")
            return _Preflight(self._security_group_healthy(group, spec))

        if spec.action == "restore_vpc_peering_route":
            route_ids = [
                route_table_id
                for target in spec.route_targets
                for route_table_id in target.route_table_ids
            ]
            response = self._call_ec2("describe_route_tables", RouteTableIds=route_ids)
            tables = {
                str(table.get("RouteTableId")): table
                for table in response.get("RouteTables", [])
            }
            if set(tables) != set(route_ids):
                raise RemediationAdapterError(
                    "route-table preflight returned an unexpected resource"
                )
            operations: list[tuple[str, str, str, str]] = []
            for target in spec.route_targets:
                for route_table_id in target.route_table_ids:
                    table = tables[route_table_id]
                    self._require_tags(table)
                    if table.get("VpcId") != self._expected_vpc_id(target.vpc_role):
                        raise RemediationAdapterError("route-table VPC binding is invalid")
                    route = next(
                        (
                            candidate
                            for candidate in table.get("Routes", [])
                            if candidate.get("DestinationCidrBlock") == target.destination_cidr
                        ),
                        None,
                    )
                    healthy = bool(
                        route
                        and route.get("VpcPeeringConnectionId") == target.peering_connection_id
                        and route.get("State", "active") == "active"
                    )
                    if not healthy:
                        operations.append(
                            (
                                "ReplaceRoute" if route else "CreateRoute",
                                route_table_id,
                                target.destination_cidr,
                                target.peering_connection_id,
                            )
                        )
            return _Preflight(not operations, tuple(operations))

        if spec.action == "restore_network_acl_entry":
            response = self._call_ec2(
                "describe_network_acls", NetworkAclIds=[spec.resource_id]
            )
            acls = response.get("NetworkAcls", [])
            if len(acls) != 1:
                raise RemediationAdapterError(
                    "network ACL preflight returned an unexpected resource"
                )
            acl = acls[0]
            self._require_tags(acl)
            if acl.get("VpcId") != self._expected_vpc_id(spec.expected_vpc_role):
                raise RemediationAdapterError("network ACL VPC binding is invalid")
            return _Preflight(self._nacl_healthy(acl, spec))

        raise RemediationAdapterError("action is not manifest-approved")

    def _write(self, spec: RemediationSpec, preflight: _Preflight) -> None:
        if spec.action == "restore_security_group_ingress":
            self._call_ec2(
                "authorize_security_group_ingress",
                GroupId=self._resources.destination_security_group_id,
                IpPermissions=[
                    {
                        "IpProtocol": spec.protocol,
                        "FromPort": spec.from_port,
                        "ToPort": spec.to_port,
                        "IpRanges": [{"CidrIp": spec.source_cidr}],
                    }
                ],
            )
            return
        if spec.action == "restore_vpc_peering_route":
            for operation, route_table_id, destination_cidr, peering_id in (
                preflight.route_operations
            ):
                self._call_ec2(
                    self._ec2_method(operation),
                    RouteTableId=route_table_id,
                    DestinationCidrBlock=destination_cidr,
                    VpcPeeringConnectionId=peering_id,
                )
            return
        if spec.action == "restore_network_acl_entry":
            self._call_ec2(
                "replace_network_acl_entry",
                NetworkAclId=spec.resource_id,
                RuleNumber=spec.nacl_rule_number,
                Protocol="6",
                RuleAction=spec.nacl_action,
                Egress=spec.nacl_egress,
                CidrBlock=spec.source_cidr,
                PortRange={"From": spec.from_port, "To": spec.to_port},
            )
            return
        raise RemediationAdapterError("action is not manifest-approved")

    def _verify(self, spec: RemediationSpec) -> bool:
        return self._preflight(spec).healthy

    def _consume(
        self, request: Mapping[str, Any], execution_id: str, now: datetime
    ) -> ConsumeResult:
        try:
            return self._approvals.consume(str(request["approval_id"]), execution_id, now)
        except (ClientError, BotoCoreError) as error:
            raise self._aws_error("approval claim", error) from error

    def _record_result(
        self, request: Mapping[str, Any], execution_id: str, result: Mapping[str, Any]
    ) -> None:
        try:
            self._approvals.record_execution_result(
                str(request["approval_id"]), execution_id, result
            )
        except (ClientError, BotoCoreError) as error:
            raise self._aws_error("result persistence", error) from error

    def _validate_approval(
        self,
        approval: Mapping[str, Any] | None,
        request: Mapping[str, Any],
        spec: RemediationSpec,
    ) -> None:
        if approval is None or approval.get("decision") != "APPROVED":
            raise RemediationAdapterError(
                "explicit approved record is required", code="NOT_APPROVED"
            )
        expected = {
            "approval_id": request["approval_id"],
            "request_hash": request["request_hash"],
            "correlation_id": request["correlation_id"],
            "policy_session_id": request["policy_session_id"],
            "action": spec.action,
            "resource": spec.resource_id,
            "operation": spec.operation,
        }
        if any(approval.get(field) != value for field, value in expected.items()):
            raise RemediationAdapterError(
                "approval binding does not match manifest", code="BINDING_MISMATCH"
            )

    @staticmethod
    def _replay_result(claim: ConsumeResult, execution_id: str) -> dict[str, Any] | None:
        if claim.status != "REPLAY_SAME_EXECUTION":
            if claim.status == "REPLAY_DIFFERENT_EXECUTION":
                raise RemediationAdapterError(
                    "approval belongs to a different execution", code=claim.status
                )
            return None
        record = claim.record or {}
        result = record.get("execution_result")
        if isinstance(result, Mapping):
            return dict(result)
        raise RemediationAdapterError(
            "same execution is already in progress; manual reconciliation is required",
            code="EXECUTION_IN_PROGRESS",
        )

    def _record_base(self, request: Mapping[str, Any], execution_id: str) -> dict[str, Any]:
        return {
            "schema_version": "1.0.0",
            "execution_id": execution_id,
            "correlation_id": str(request["correlation_id"]),
            "approval_id": str(request["approval_id"]),
        }

    def _result(
        self,
        *,
        request: Mapping[str, Any],
        execution_id: str,
        status: str,
        write_performed: bool,
        terraform_drift: bool,
        reconciliation_required: bool,
        message: str,
    ) -> dict[str, Any]:
        result = self._record_base(request, execution_id)
        result.update(
            {
                "status": status,
                "write_performed": write_performed,
                "terraform_drift": terraform_drift,
                "reconciliation_required": reconciliation_required,
                "message": message,
            }
        )
        return result

    def _call_ec2(self, operation: str, **kwargs: Any) -> dict[str, Any]:
        try:
            return cast(dict[str, Any], getattr(self._ec2, operation)(**kwargs))
        except (ClientError, BotoCoreError):
            raise

    @staticmethod
    def _ec2_method(operation: str) -> str:
        if operation == "CreateRoute":
            return "create_route"
        if operation == "ReplaceRoute":
            return "replace_route"
        raise RemediationAdapterError("EC2 operation is not allowlisted")

    def _expected_vpc_id(self, role: str | None) -> str:
        if role == "source":
            return self._resources.source_vpc_id
        if role == "destination":
            return self._resources.destination_vpc_id
        raise RemediationAdapterError("manifest VPC binding is invalid")

    def _require_tags(self, resource: Mapping[str, Any]) -> None:
        tags = {
            str(tag.get("Key")): str(tag.get("Value"))
            for tag in resource.get("Tags", [])
            if isinstance(tag, Mapping)
        }
        required = {
            "Project": "agentic-aws-network-ops",
            "Environment": "lab",
            "ManagedBy": "terraform",
        }
        if any(tags.get(key) != value for key, value in required.items()):
            raise RemediationAdapterError("resource ownership tags do not match manifest")

    @staticmethod
    def _security_group_healthy(group: Mapping[str, Any], spec: RemediationSpec) -> bool:
        for permission in group.get("IpPermissions", []):
            if (
                permission.get("IpProtocol") == spec.protocol
                and permission.get("FromPort") == spec.from_port
                and permission.get("ToPort") == spec.to_port
                and any(
                    entry.get("CidrIp") == spec.source_cidr
                    for entry in permission.get("IpRanges", [])
                )
            ):
                return True
        return False

    @staticmethod
    def _nacl_healthy(acl: Mapping[str, Any], spec: RemediationSpec) -> bool:
        for entry in acl.get("Entries", []):
            port_range = entry.get("PortRange", {})
            if (
                entry.get("RuleNumber") == spec.nacl_rule_number
                and bool(entry.get("Egress")) is bool(spec.nacl_egress)
                and str(entry.get("Protocol")) in {"6", "tcp"}
                and entry.get("RuleAction", "").lower() == spec.nacl_action
                and entry.get("CidrBlock") == spec.source_cidr
                and port_range.get("From") == spec.from_port
                and port_range.get("To") == spec.to_port
            ):
                return True
        return False

    @staticmethod
    def _validate_execution_id(execution_id: str) -> None:
        try:
            UUID(execution_id)
        except (ValueError, AttributeError) as error:
            raise RemediationContractError("execution_id must be a UUID") from error

    @staticmethod
    def _aws_error(operation: str, error: ClientError | BotoCoreError) -> RemediationAdapterError:
        code = "BOTOCORE_ERROR"
        retryable = isinstance(error, BotoCoreError)
        if isinstance(error, ClientError):
            code = str(error.response.get("Error", {}).get("Code", "AWS_ERROR"))
            retryable = code in {
                "InternalError",
                "RequestLimitExceeded",
                "ServiceUnavailable",
                "Throttling",
                "ThrottlingException",
            }
        return RemediationAdapterError(
            f"AWS {operation} failed", code=code, retryable=retryable
        )

    @staticmethod
    def _safe_failure_message(error: ClientError | BotoCoreError) -> str:
        if isinstance(error, ClientError):
            code = str(error.response.get("Error", {}).get("Code", "AWS_ERROR"))
            return f"AWS write failed ({code}); reconcile Terraform source before retrying."
        return "AWS write failed; reconcile Terraform source before retrying."
