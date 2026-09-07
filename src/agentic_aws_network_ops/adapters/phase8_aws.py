"""Composition helpers for injecting the Phase 8 AWS-backed adapters."""

from __future__ import annotations

from collections.abc import Set
from typing import Any

from agentic_aws_network_ops.approval.dynamodb_repository import DynamoDBApprovalRepository
from agentic_aws_network_ops.approval.service import ApprovalService
from agentic_aws_network_ops.remediation.aws_executor import (
    AwsRemediationExecutor,
    TrustedPhase8Resources,
)


def build_approval_service(
    *,
    dynamodb_client: Any,
    table_name: str,
    authorized_principals: Set[str],
) -> ApprovalService:
    """Compose ApprovalService with an injected DynamoDB repository."""
    return ApprovalService(
        DynamoDBApprovalRepository(dynamodb_client, table_name=table_name),
        authorized_principals,
    )


def build_remediation_executor(
    *,
    ec2_client: Any,
    dynamodb_client: Any,
    table_name: str,
    resources: TrustedPhase8Resources,
) -> AwsRemediationExecutor:
    """Compose the executor with injected EC2 and DynamoDB-style clients."""
    repository = DynamoDBApprovalRepository(dynamodb_client, table_name=table_name)
    return AwsRemediationExecutor(
        ec2_client=ec2_client,
        approval_repository=repository,
        resources=resources,
    )
