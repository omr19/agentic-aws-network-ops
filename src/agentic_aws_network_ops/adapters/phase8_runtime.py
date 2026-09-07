"""Trusted AWS-backed runtime factories for the Phase 8 Lambda wrappers.

The factories read only non-secret deployment configuration from the Lambda
environment and rely on the execution role for credentials. Wrapper dispatch
still obtains the authenticated principal from trusted invocation context; an
event field is never used to establish identity or authorization.
"""

from __future__ import annotations

import json
import os
import re
from collections.abc import Callable, Mapping
from typing import Any

import boto3  # type: ignore[import-untyped]

from agentic_aws_network_ops.approval.dynamodb_repository import DynamoDBApprovalRepository
from agentic_aws_network_ops.approval.service import ApprovalService

EXPECTED_REGION = "eu-west-1"
AUTHORIZED_APPROVERS_ENV = "PHASE8_AUTHORIZED_APPROVERS_JSON"
REGION_ENV = "PHASE8_AWS_REGION"
TABLE_ENV = "PHASE8_APPROVAL_TABLE_NAME"
DESTINATION_SECURITY_GROUP_ENV = "PHASE8_DESTINATION_SECURITY_GROUP_ID"
DESTINATION_VPC_ENV = "PHASE8_DESTINATION_VPC_ID"
SOURCE_VPC_ENV = "PHASE8_SOURCE_VPC_ID"

ClientFactory = Callable[..., Any]


class RuntimeConfigurationError(ValueError):
    """Raised when trusted deployment configuration is absent or invalid."""


def _required(environ: Mapping[str, str], name: str) -> str:
    value = environ.get(name)
    if not isinstance(value, str) or not value.strip():
        raise RuntimeConfigurationError(f"{name} is required")
    return value.strip()


def _region(environ: Mapping[str, str]) -> str:
    region = _required(environ, REGION_ENV)
    if region != EXPECTED_REGION:
        raise RuntimeConfigurationError(f"{REGION_ENV} must be {EXPECTED_REGION}")
    return region


def _table_name(environ: Mapping[str, str]) -> str:
    table_name = _required(environ, TABLE_ENV)
    if not re.fullmatch(r"agentic-aws-network-ops-[a-z0-9-]+-phase8-approvals", table_name):
        raise RuntimeConfigurationError(f"{TABLE_ENV} is outside the Phase 8 table boundary")
    return table_name


def _authorized_principals(environ: Mapping[str, str]) -> frozenset[str]:
    encoded = _required(environ, AUTHORIZED_APPROVERS_ENV)
    try:
        values = json.loads(encoded)
    except json.JSONDecodeError as error:
        raise RuntimeConfigurationError(f"{AUTHORIZED_APPROVERS_ENV} must be valid JSON") from error
    if not isinstance(values, list) or not values:
        raise RuntimeConfigurationError(
            f"{AUTHORIZED_APPROVERS_ENV} must be a non-empty JSON array"
        )
    if any(not isinstance(value, str) or not value.strip() for value in values):
        raise RuntimeConfigurationError(
            f"{AUTHORIZED_APPROVERS_ENV} must contain non-empty principal strings"
        )
    principals = frozenset(value.strip() for value in values)
    if len(principals) != len(values):
        raise RuntimeConfigurationError(f"{AUTHORIZED_APPROVERS_ENV} must not contain duplicates")
    if any(
        not re.fullmatch(r"arn:aws:iam::[0-9]{12}:(?:user|role)/.+", principal)
        for principal in principals
    ):
        raise RuntimeConfigurationError(
            f"{AUTHORIZED_APPROVERS_ENV} must contain IAM user or role principal ARNs"
        )
    return principals


def _resource_id(environ: Mapping[str, str], name: str, prefix: str) -> str:
    value = _required(environ, name)
    if not re.fullmatch(rf"{re.escape(prefix)}[0-9a-f]+", value):
        raise RuntimeConfigurationError(f"{name} is not a valid trusted {prefix} identifier")
    return value


def _client(client_factory: ClientFactory | None, service: str, region: str) -> Any:
    factory = client_factory or boto3.client
    return factory(service, region_name=region)


def build_approval_service(
    *,
    principal: str,
    context: Any,
    environ: Mapping[str, str] | None = None,
    client_factory: ClientFactory | None = None,
) -> ApprovalService:
    """Construct the approval service from role-backed, deployment-time settings."""
    del context
    settings = environ if environ is not None else os.environ
    region = _region(settings)
    table_name = _table_name(settings)
    authorized = _authorized_principals(settings)
    if principal not in authorized:
        raise RuntimeConfigurationError("authenticated principal is not an authorized approver")
    dynamodb = _client(client_factory, "dynamodb", region)
    return ApprovalService(
        DynamoDBApprovalRepository(dynamodb, table_name=table_name),
        authorized,
    )


def build_remediation_executor(
    *,
    principal: str,
    context: Any,
    environ: Mapping[str, str] | None = None,
    client_factory: ClientFactory | None = None,
) -> Any:
    """Construct the remediation executor from trusted deployment resource IDs."""
    del context
    if not isinstance(principal, str) or not principal.strip():
        raise RuntimeConfigurationError("authenticated principal is required")
    settings = environ if environ is not None else os.environ
    region = _region(settings)
    table_name = _table_name(settings)
    from agentic_aws_network_ops.remediation.aws_executor import TrustedPhase8Resources

    resources = TrustedPhase8Resources(
        destination_security_group_id=_resource_id(settings, DESTINATION_SECURITY_GROUP_ENV, "sg-"),
        destination_vpc_id=_resource_id(settings, DESTINATION_VPC_ENV, "vpc-"),
        source_vpc_id=_resource_id(settings, SOURCE_VPC_ENV, "vpc-"),
    )
    dynamodb = _client(client_factory, "dynamodb", region)
    ec2 = _client(client_factory, "ec2", region)
    # Import lazily so the approval package does not need remediation write code.
    from .phase8_aws import build_remediation_executor as compose_executor

    return compose_executor(
        ec2_client=ec2,
        dynamodb_client=dynamodb,
        table_name=table_name,
        resources=resources,
    )
