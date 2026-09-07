"""Framework-independent implementations of the nine diagnostic READ tools."""

from __future__ import annotations

import re
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import UTC, date, datetime
from ipaddress import IPv4Address, ip_address
from typing import Any

from botocore.exceptions import BotoCoreError, ClientError  # type: ignore[import-untyped]

from .contracts import ContractError, ContractValidator

JsonObject = dict[str, Any]
AwsClient = Any

APPROVED_TOOLS = (
    "describe_vpcs",
    "describe_subnets",
    "describe_route_tables",
    "describe_security_groups",
    "describe_network_acls",
    "describe_vpc_endpoints",
    "analyze_reachability",
    "query_flow_logs",
    "get_cloudwatch_metrics",
)

AUTHORIZATION_CODES = {
    "AccessDenied",
    "AccessDeniedException",
    "AuthorizationError",
    "Client.UnauthorizedOperation",
    "UnauthorizedOperation",
}
TIMEOUT_CODES = {"RequestTimeout", "RequestTimeoutException", "TimeoutError"}
THROTTLING_CODES = {
    "RequestLimitExceeded",
    "Throttling",
    "ThrottlingException",
    "TooManyRequestsException",
}
CORRELATION_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{7,127}$")
REGION_PATTERN = re.compile(r"^[a-z]{2}(?:-gov)?-[a-z]+-\d$")


@dataclass(frozen=True)
class DiagnosticClients:
    """Dependency-injected AWS clients used by the diagnostic service."""

    ec2: AwsClient
    logs: AwsClient
    cloudwatch: AwsClient


def _json_safe(value: Any) -> Any:
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    return value


class DiagnosticService:
    """Dispatch only the approved tools and return a consistent result envelope."""

    def __init__(
        self,
        clients: DiagnosticClients,
        validator: ContractValidator | None = None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._clients = clients
        self._validator = validator or ContractValidator()
        self._clock = clock or (lambda: datetime.now(UTC))

    def execute(self, tool: str, payload: JsonObject) -> JsonObject:
        supplied_correlation = str(payload.get("correlation_id", ""))
        supplied_region = str(payload.get("region", ""))
        correlation_id = (
            supplied_correlation
            if CORRELATION_PATTERN.fullmatch(supplied_correlation)
            else "invalid-request"
        )
        region = supplied_region if REGION_PATTERN.fullmatch(supplied_region) else "unknown"
        if tool not in APPROVED_TOOLS:
            return self._error(
                tool,
                correlation_id,
                region,
                "invalid_request",
                "UNKNOWN_TOOL",
                "Tool is not in the approved diagnostic boundary",
            )
        try:
            self._validator.validate_input(tool, payload)
            data, evidence, status, completeness = getattr(self, f"_{tool}")(payload)
            result = self._envelope(
                tool, correlation_id, region, status, data, evidence, completeness
            )
            self._validator.validate_output(tool, result)
            return result
        except ContractError as error:
            return self._error(
                tool, correlation_id, region, "invalid_request", "INVALID_REQUEST", str(error)
            )
        except ClientError as error:
            response_error = error.response.get("Error", {})
            code = str(response_error.get("Code", "AWS_API_ERROR"))
            if code in AUTHORIZATION_CODES:
                return self._error(
                    tool,
                    correlation_id,
                    region,
                    "authorization_denied",
                    code,
                    "AWS authorization denied; evidence is incomplete",
                    missing_actions=[str(error.operation_name)],
                )
            status = "timeout" if code in TIMEOUT_CODES else "api_error"
            return self._error(
                tool,
                correlation_id,
                region,
                status,
                code,
                "AWS diagnostic request failed",
                retryable=status == "timeout" or code in THROTTLING_CODES,
            )
        except BotoCoreError:
            return self._error(
                tool,
                correlation_id,
                region,
                "api_error",
                "AWS_CLIENT_ERROR",
                "AWS diagnostic client failed",
                retryable=True,
            )

    def _describe_vpcs(self, payload: JsonObject) -> tuple[JsonObject, list[JsonObject], str, str]:
        response = self._clients.ec2.describe_vpcs(
            Filters=[{"Name": "tag:Project", "Values": [payload["project_tag"]]}]
        )
        return self._resources("ec2:DescribeVpcs", response.get("Vpcs", []))

    def _describe_subnets(
        self, payload: JsonObject
    ) -> tuple[JsonObject, list[JsonObject], str, str]:
        response = self._clients.ec2.describe_subnets(
            Filters=[{"Name": "vpc-id", "Values": [payload["vpc_id"]]}]
        )
        return self._resources("ec2:DescribeSubnets", response.get("Subnets", []))

    def _describe_route_tables(
        self, payload: JsonObject
    ) -> tuple[JsonObject, list[JsonObject], str, str]:
        filters = [{"Name": "vpc-id", "Values": [payload["vpc_id"]]}]
        if "subnet_id" in payload:
            filters.append({"Name": "association.subnet-id", "Values": [payload["subnet_id"]]})
        response = self._clients.ec2.describe_route_tables(Filters=filters)
        return self._resources("ec2:DescribeRouteTables", response.get("RouteTables", []))

    def _describe_security_groups(
        self, payload: JsonObject
    ) -> tuple[JsonObject, list[JsonObject], str, str]:
        params: JsonObject = {"Filters": [{"Name": "vpc-id", "Values": [payload["vpc_id"]]}]}
        if payload.get("group_ids"):
            params["GroupIds"] = payload["group_ids"]
        response = self._clients.ec2.describe_security_groups(**params)
        return self._resources("ec2:DescribeSecurityGroups", response.get("SecurityGroups", []))

    def _describe_network_acls(
        self, payload: JsonObject
    ) -> tuple[JsonObject, list[JsonObject], str, str]:
        filters = [{"Name": "vpc-id", "Values": [payload["vpc_id"]]}]
        if "subnet_id" in payload:
            filters.append({"Name": "association.subnet-id", "Values": [payload["subnet_id"]]})
        response = self._clients.ec2.describe_network_acls(Filters=filters)
        return self._resources("ec2:DescribeNetworkAcls", response.get("NetworkAcls", []))

    def _describe_vpc_endpoints(
        self, payload: JsonObject
    ) -> tuple[JsonObject, list[JsonObject], str, str]:
        response = self._clients.ec2.describe_vpc_endpoints(
            Filters=[{"Name": "vpc-id", "Values": [payload["vpc_id"]]}]
        )
        return self._resources("ec2:DescribeVpcEndpoints", response.get("VpcEndpoints", []))

    def _analyze_reachability(
        self, payload: JsonObject
    ) -> tuple[JsonObject, list[JsonObject], str, str]:
        params: JsonObject = {"NetworkInsightsPathId": payload["network_insights_path_id"]}
        if "analysis_id" in payload:
            params = {"NetworkInsightsAnalysisIds": [payload["analysis_id"]]}
        response = self._clients.ec2.describe_network_insights_analyses(**params)
        analyses = response.get("NetworkInsightsAnalyses", [])
        if not analyses:
            return (
                {"analysis_status": "unknown", "path_found": None, "explanations": []},
                [],
                "no_finding",
                "complete",
            )
        analysis = analyses[0]
        requested_path_id = payload["network_insights_path_id"]
        if "analysis_id" in payload and analysis.get("NetworkInsightsPathId") != requested_path_id:
            raise ContractError("analysis_id does not belong to network_insights_path_id")
        state = str(analysis.get("Status", "unknown")).lower()
        path_found = analysis.get("NetworkPathFound")
        status = "unreachable" if state == "succeeded" and path_found is False else "success"
        data = {
            "analysis_status": state
            if state in {"pending", "running", "succeeded", "failed"}
            else "unknown",
            "path_found": path_found,
            "explanations": _json_safe(analysis.get("Explanations", [])),
        }
        return (
            data,
            [
                {
                    "source": "ec2:DescribeNetworkInsightsAnalyses",
                    "fact": f"analysis status={data['analysis_status']}; path_found={path_found}",
                }
            ],
            status,
            "partial" if state in {"pending", "running"} else "complete",
        )

    @staticmethod
    def _validated_ipv4(value: str) -> str:
        address = ip_address(value)
        if not isinstance(address, IPv4Address):
            raise ContractError("flow-log address filters must be IPv4 addresses")
        return str(address)

    def _query_flow_logs(
        self, payload: JsonObject
    ) -> tuple[JsonObject, list[JsonObject], str, str]:
        query = (
            "fields @timestamp, interfaceId, srcAddr, dstAddr, dstPort, action "
            "| sort @timestamp desc"
        )
        filters: list[str] = []
        if "source_address" in payload:
            filters.append(f"srcAddr = '{self._validated_ipv4(payload['source_address'])}'")
        if "destination_address" in payload:
            filters.append(f"dstAddr = '{self._validated_ipv4(payload['destination_address'])}'")
        if "destination_port" in payload:
            destination_port = int(payload["destination_port"])
            if not 1 <= destination_port <= 65535:
                raise ContractError("destination_port must be between 1 and 65535")
            filters.append(f"dstPort = {destination_port}")
        if filters:
            query += " | filter " + " and ".join(filters)
        response = self._clients.logs.start_query(
            logGroupName=payload["log_group_name"],
            startTime=int(
                datetime.fromisoformat(payload["start_time"].replace("Z", "+00:00")).timestamp()
            ),
            endTime=int(
                datetime.fromisoformat(payload["end_time"].replace("Z", "+00:00")).timestamp()
            ),
            queryString=query,
            limit=payload.get("limit", 50),
        )
        result = self._clients.logs.get_query_results(queryId=response["queryId"])
        state = str(result.get("status", "Failed")).lower()
        records = _json_safe(result.get("results", []))
        return (
            {
                "query_status": state if state in {"running", "complete", "failed"} else "failed",
                "records": records,
            },
            [
                {
                    "source": "logs:GetQueryResults",
                    "fact": f"query status={state}; records={len(records)}",
                }
            ],
            "success" if state == "complete" else "no_finding",
            "complete" if state == "complete" else "partial",
        )

    def _get_cloudwatch_metrics(
        self, payload: JsonObject
    ) -> tuple[JsonObject, list[JsonObject], str, str]:
        parameters: JsonObject = {
            "Namespace": payload["namespace"],
            "MetricName": payload["metric_name"],
            "StartTime": datetime.fromisoformat(payload["start_time"].replace("Z", "+00:00")),
            "EndTime": datetime.fromisoformat(payload["end_time"].replace("Z", "+00:00")),
            "Period": payload["period"],
            "Statistics": [payload["statistic"]],
        }
        if payload.get("dimensions"):
            parameters["Dimensions"] = [
                {"Name": item["name"], "Value": item["value"]} for item in payload["dimensions"]
            ]
        response = self._clients.cloudwatch.get_metric_statistics(**parameters)
        datapoints = _json_safe(response.get("Datapoints", []))
        return (
            {"datapoints": datapoints, "unit": str(response.get("Label", ""))},
            [{"source": "cloudwatch:GetMetricStatistics", "fact": f"datapoints={len(datapoints)}"}],
            "success" if datapoints else "no_finding",
            "complete",
        )

    @staticmethod
    def _resources(
        source: str, resources: list[JsonObject]
    ) -> tuple[JsonObject, list[JsonObject], str, str]:
        safe = _json_safe(resources)
        return (
            {"resources": safe},
            [{"source": source, "fact": f"resources={len(resources)}"}],
            "success" if resources else "no_finding",
            "complete",
        )

    def _envelope(
        self,
        tool: str,
        correlation_id: str,
        region: str,
        status: str,
        data: JsonObject,
        evidence: list[JsonObject],
        evidence_completeness: str,
    ) -> JsonObject:
        return {
            "schema_version": "1.0.0",
            "tool": tool,
            "status": status,
            "correlation_id": correlation_id,
            "observed_at": self._clock().astimezone(UTC).isoformat().replace("+00:00", "Z"),
            "region": region,
            "authorization": {"decision": "allowed", "missing_actions": []},
            "evidence_completeness": evidence_completeness,
            "evidence": evidence,
            "limitations": [],
            "errors": [],
            "data": data,
        }

    def _error(
        self,
        tool: str,
        correlation_id: str,
        region: str,
        status: str,
        code: str,
        message: str,
        *,
        retryable: bool = False,
        missing_actions: list[str] | None = None,
    ) -> JsonObject:
        result = {
            "schema_version": "1.0.0",
            "tool": tool,
            "status": status,
            "correlation_id": correlation_id,
            "observed_at": self._clock().astimezone(UTC).isoformat().replace("+00:00", "Z"),
            "region": region,
            "authorization": {
                "decision": "denied" if status == "authorization_denied" else "unknown",
                "missing_actions": missing_actions or [],
            },
            "evidence_completeness": "none",
            "evidence": [],
            "limitations": ["No network root cause can be concluded from incomplete evidence."],
            "errors": [{"code": code, "message": message, "retryable": retryable}],
            "data": {},
        }
        if tool in APPROVED_TOOLS:
            self._validator.validate_output(tool, result)
        return result
