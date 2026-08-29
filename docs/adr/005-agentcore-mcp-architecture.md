# ADR 005 — AgentCore and MCP Architecture

## Status
Accepted

## Decision
Use one operational agent in AgentCore Runtime, Gateway as the preferred integration
boundary, MCP for strict contracts, and Python/Boto3 for AWS execution. Use Lambda
selectively rather than once per logical tool. Use one non-VPC diagnostic Lambda target
and one separate non-VPC remediation Lambda target.

## Consequences
The MVP avoids artificial multi-agent/Lambda complexity and preserves a hard deployment
boundary between READ and WRITE capabilities. Neither Lambda requires direct workload-
VPC connectivity.
