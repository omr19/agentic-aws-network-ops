"""Offline AWS Stubber tests for the shared diagnostic READ service."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import boto3  # type: ignore[import-untyped]
import pytest
from botocore.exceptions import EndpointConnectionError  # type: ignore[import-untyped]
from botocore.stub import Stubber  # type: ignore[import-untyped]

from agentic_aws_network_ops.diagnostics.service import DiagnosticClients, DiagnosticService

REGION = "eu-west-1"
BASE = {"schema_version": "1.0.0", "correlation_id": "corr-test-0001", "region": REGION}
FIXED_TIME = datetime(2026, 8, 29, 1, 0, tzinfo=UTC)


def client(service: str) -> Any:
    return boto3.client(
        service,
        region_name=REGION,
        aws_access_key_id="testing",
        aws_secret_access_key="testing",  # noqa: S106 - inert Stubber credential
        aws_session_token="testing",  # noqa: S106 - inert Stubber credential
    )


@pytest.fixture
def aws_clients() -> DiagnosticClients:
    return DiagnosticClients(
        ec2=client("ec2"), logs=client("logs"), cloudwatch=client("cloudwatch")
    )


def service(clients: DiagnosticClients) -> DiagnosticService:
    return DiagnosticService(clients, clock=lambda: FIXED_TIME)


@pytest.mark.parametrize(
    ("tool", "payload", "operation", "response", "expected_params"),
    [
        (
            "describe_vpcs",
            {**BASE, "project_tag": "agentic-aws-network-ops"},
            "describe_vpcs",
            {"Vpcs": [{"VpcId": "vpc-0123456789abcdef0"}]},
            {"Filters": [{"Name": "tag:Project", "Values": ["agentic-aws-network-ops"]}]},
        ),
        (
            "describe_subnets",
            {**BASE, "vpc_id": "vpc-0123456789abcdef0"},
            "describe_subnets",
            {"Subnets": [{"SubnetId": "subnet-0123456789abcdef0"}]},
            {"Filters": [{"Name": "vpc-id", "Values": ["vpc-0123456789abcdef0"]}]},
        ),
        (
            "describe_route_tables",
            {**BASE, "vpc_id": "vpc-0123456789abcdef0"},
            "describe_route_tables",
            {"RouteTables": []},
            {"Filters": [{"Name": "vpc-id", "Values": ["vpc-0123456789abcdef0"]}]},
        ),
        (
            "describe_security_groups",
            {**BASE, "vpc_id": "vpc-0123456789abcdef0"},
            "describe_security_groups",
            {"SecurityGroups": []},
            {"Filters": [{"Name": "vpc-id", "Values": ["vpc-0123456789abcdef0"]}]},
        ),
        (
            "describe_network_acls",
            {**BASE, "vpc_id": "vpc-0123456789abcdef0"},
            "describe_network_acls",
            {"NetworkAcls": []},
            {"Filters": [{"Name": "vpc-id", "Values": ["vpc-0123456789abcdef0"]}]},
        ),
        (
            "describe_vpc_endpoints",
            {**BASE, "vpc_id": "vpc-0123456789abcdef0"},
            "describe_vpc_endpoints",
            {"VpcEndpoints": []},
            {"Filters": [{"Name": "vpc-id", "Values": ["vpc-0123456789abcdef0"]}]},
        ),
    ],
)
def test_ec2_inventory_tools_use_expected_read_api(
    aws_clients: DiagnosticClients,
    tool: str,
    payload: dict[str, Any],
    operation: str,
    response: dict[str, Any],
    expected_params: dict[str, Any],
) -> None:
    with Stubber(aws_clients.ec2) as stubber:
        stubber.add_response(operation, response, expected_params)
        result = service(aws_clients).execute(tool, payload)
    assert result["status"] == ("success" if result["data"]["resources"] else "no_finding")
    assert result["correlation_id"] == BASE["correlation_id"]
    assert result["evidence_completeness"] == "complete"


def test_reachability_returns_deterministic_unreachable_status(
    aws_clients: DiagnosticClients,
) -> None:
    payload = {**BASE, "network_insights_path_id": "nip-0123456789abcdef0"}
    response = {
        "NetworkInsightsAnalyses": [
            {
                "NetworkInsightsAnalysisId": "nia-0123456789abcdef0",
                "NetworkInsightsPathId": "nip-0123456789abcdef0",
                "Status": "succeeded",
                "NetworkPathFound": False,
                "Explanations": [{"Direction": "ingress"}],
            }
        ]
    }
    with Stubber(aws_clients.ec2) as stubber:
        stubber.add_response(
            "describe_network_insights_analyses",
            response,
            {"NetworkInsightsPathId": "nip-0123456789abcdef0"},
        )
        result = service(aws_clients).execute("analyze_reachability", payload)
    assert result["status"] == "unreachable"
    assert result["data"]["path_found"] is False


def test_pending_reachability_evidence_is_partial(aws_clients: DiagnosticClients) -> None:
    payload = {**BASE, "network_insights_path_id": "nip-0123456789abcdef0"}
    response = {
        "NetworkInsightsAnalyses": [
            {
                "NetworkInsightsAnalysisId": "nia-0123456789abcdef0",
                "NetworkInsightsPathId": "nip-0123456789abcdef0",
                "Status": "pending",
            }
        ]
    }
    with Stubber(aws_clients.ec2) as stubber:
        stubber.add_response(
            "describe_network_insights_analyses",
            response,
            {"NetworkInsightsPathId": "nip-0123456789abcdef0"},
        )
        result = service(aws_clients).execute("analyze_reachability", payload)
    assert result["evidence_completeness"] == "partial"


def test_explicit_analysis_must_belong_to_requested_path(aws_clients: DiagnosticClients) -> None:
    payload = {
        **BASE,
        "network_insights_path_id": "nip-0123456789abcdef0",
        "analysis_id": "nia-0123456789abcdef0",
    }
    response = {
        "NetworkInsightsAnalyses": [
            {
                "NetworkInsightsAnalysisId": "nia-0123456789abcdef0",
                "NetworkInsightsPathId": "nip-fffffffffffffffff",
                "Status": "succeeded",
                "NetworkPathFound": True,
            }
        ]
    }
    with Stubber(aws_clients.ec2) as stubber:
        stubber.add_response(
            "describe_network_insights_analyses",
            response,
            {"NetworkInsightsAnalysisIds": ["nia-0123456789abcdef0"]},
        )
        result = service(aws_clients).execute("analyze_reachability", payload)
    assert result["status"] == "invalid_request"
    assert "does not belong" in result["errors"][0]["message"]


def test_flow_logs_query_uses_only_logs_insights_read_path(aws_clients: DiagnosticClients) -> None:
    payload = {
        **BASE,
        "log_group_name": "/aws/vpc/flowlogs/agentic-aws-network-ops/lab",
        "start_time": "2026-08-29T01:00:00Z",
        "end_time": "2026-08-29T01:05:00Z",
    }
    with Stubber(aws_clients.logs) as stubber:
        stubber.add_response(
            "start_query",
            {"queryId": "00000000-0000-0000-0000-000000000001"},
            {
                "logGroupName": payload["log_group_name"],
                "startTime": 1787965200,
                "endTime": 1787965500,
                "queryString": (
                    "fields @timestamp, interfaceId, srcAddr, dstAddr, dstPort, action "
                    "| sort @timestamp desc"
                ),
                "limit": 50,
            },
        )
        stubber.add_response(
            "get_query_results",
            {"status": "Complete", "results": []},
            {"queryId": "00000000-0000-0000-0000-000000000001"},
        )
        result = service(aws_clients).execute("query_flow_logs", payload)
    assert result["status"] == "success"
    assert result["data"]["query_status"] == "complete"


def test_running_flow_log_query_has_partial_evidence(aws_clients: DiagnosticClients) -> None:
    payload = {
        **BASE,
        "log_group_name": "/aws/vpc/flowlogs/agentic-aws-network-ops/lab",
        "start_time": "2026-08-29T01:00:00Z",
        "end_time": "2026-08-29T01:05:00Z",
    }
    with Stubber(aws_clients.logs) as stubber:
        stubber.add_response(
            "start_query",
            {"queryId": "00000000-0000-0000-0000-000000000001"},
            {
                "logGroupName": payload["log_group_name"],
                "startTime": 1787965200,
                "endTime": 1787965500,
                "queryString": (
                    "fields @timestamp, interfaceId, srcAddr, dstAddr, dstPort, action "
                    "| sort @timestamp desc"
                ),
                "limit": 50,
            },
        )
        stubber.add_response(
            "get_query_results",
            {"status": "Running", "results": []},
            {"queryId": "00000000-0000-0000-0000-000000000001"},
        )
        result = service(aws_clients).execute("query_flow_logs", payload)
    assert result["evidence_completeness"] == "partial"


def test_cloudwatch_metric_uses_get_metric_statistics(aws_clients: DiagnosticClients) -> None:
    payload = {
        **BASE,
        "namespace": "AWS/EC2",
        "metric_name": "NetworkPacketsIn",
        "start_time": "2026-08-29T01:00:00Z",
        "end_time": "2026-08-29T01:05:00Z",
        "period": 60,
        "statistic": "Sum",
    }
    expected = {
        "Namespace": "AWS/EC2",
        "MetricName": "NetworkPacketsIn",
        "StartTime": datetime(2026, 8, 29, 1, 0, tzinfo=UTC),
        "EndTime": datetime(2026, 8, 29, 1, 5, tzinfo=UTC),
        "Period": 60,
        "Statistics": ["Sum"],
    }
    with Stubber(aws_clients.cloudwatch) as stubber:
        stubber.add_response(
            "get_metric_statistics",
            {"Label": "NetworkPacketsIn", "Datapoints": []},
            expected,
        )
        result = service(aws_clients).execute("get_cloudwatch_metrics", payload)
    assert result["status"] == "no_finding"


def test_authorization_denial_is_a_limitation_not_root_cause(
    aws_clients: DiagnosticClients,
) -> None:
    with Stubber(aws_clients.ec2) as stubber:
        stubber.add_client_error(
            "describe_vpcs",
            service_error_code="UnauthorizedOperation",
            service_message="sensitive provider message",
            expected_params={
                "Filters": [{"Name": "tag:Project", "Values": ["agentic-aws-network-ops"]}]
            },
        )
        result = service(aws_clients).execute(
            "describe_vpcs", {**BASE, "project_tag": "agentic-aws-network-ops"}
        )
    assert result["status"] == "authorization_denied"
    assert result["evidence_completeness"] == "none"
    assert "sensitive provider message" not in str(result)
    assert result["limitations"]


@pytest.mark.parametrize(
    ("error_code", "expected_status", "retryable"),
    [
        ("RequestTimeout", "timeout", True),
        ("ThrottlingException", "api_error", True),
    ],
)
def test_transient_aws_errors_are_retryable(
    aws_clients: DiagnosticClients,
    error_code: str,
    expected_status: str,
    retryable: bool,
) -> None:
    with Stubber(aws_clients.ec2) as stubber:
        stubber.add_client_error(
            "describe_vpcs",
            service_error_code=error_code,
            service_message="sensitive provider message",
            expected_params={
                "Filters": [{"Name": "tag:Project", "Values": ["agentic-aws-network-ops"]}]
            },
        )
        result = service(aws_clients).execute(
            "describe_vpcs", {**BASE, "project_tag": "agentic-aws-network-ops"}
        )
    assert result["status"] == expected_status
    assert result["errors"][0]["retryable"] is retryable
    assert "sensitive provider message" not in str(result)


def test_botocore_transport_error_is_sanitized_and_retryable(
    aws_clients: DiagnosticClients, monkeypatch: Any
) -> None:
    def fail(**_: Any) -> None:
        raise EndpointConnectionError(endpoint_url="https://sensitive.example")

    monkeypatch.setattr(aws_clients.ec2, "describe_vpcs", fail)
    result = service(aws_clients).execute(
        "describe_vpcs", {**BASE, "project_tag": "agentic-aws-network-ops"}
    )
    assert result["status"] == "api_error"
    assert result["errors"][0]["retryable"] is True
    assert "sensitive.example" not in str(result)


def test_flow_log_query_rejects_filter_injection_without_aws_call(
    aws_clients: DiagnosticClients,
) -> None:
    result = service(aws_clients).execute(
        "query_flow_logs",
        {
            **BASE,
            "log_group_name": "/aws/vpc/flowlogs/agentic-aws-network-ops/lab",
            "start_time": "2026-08-29T01:00:00Z",
            "end_time": "2026-08-29T01:05:00Z",
            "source_address": "10.0.0.1' or action = 'ACCEPT",
        },
    )
    assert result["status"] == "invalid_request"


def test_unknown_generic_tool_is_rejected_without_aws_call(
    aws_clients: DiagnosticClients,
) -> None:
    result = service(aws_clients).execute(
        "execute_boto3", {**BASE, "correlation_id": "potential secret with spaces"}
    )
    assert result["status"] == "invalid_request"
    assert result["errors"][0]["code"] == "UNKNOWN_TOOL"
    assert result["correlation_id"] == "invalid-request"
