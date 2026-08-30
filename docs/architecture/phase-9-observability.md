# Phase 9 — Local Observability Foundation

## Scope

This foundation records observable execution metadata for the existing local Runtime,
Gateway/MCP, diagnostic, approval, remediation, and verification boundaries. It does not
claim AgentCore Observability, OpenTelemetry exporters, CloudWatch resources, VPC Flow Logs,
alarms, dashboards, budgets, or live end-to-end AWS telemetry.

## Event contract

The versioned contract is `schemas/observability/observability-event.schema.json`, currently
`1.0.0`. Events use the shared helper in
`src/agentic_aws_network_ops/shared/observability.py` and contain the following metadata
where applicable:

- `event_name`, `schema_version`, `status`, and `redaction_policy`
- correlation, session, request, tool-call, approval, execution, and verification IDs
- region, environment, duration in milliseconds, and error class
- safe tool, action, decision, evidence-completeness, and write-performed fields

The helper uses `allowlist-v1`. It rejects fields outside the schema and never serializes
prompts, tool arguments, request payloads, credentials, principals, exception messages,
tracebacks, or hidden model chain-of-thought. Failure logging records only an exception
class.

## Instrumented local boundaries

- Runtime request start, selected MCP tool, MCP result, and Runtime outcome
- Native Runtime entry-point MCP request/result and configured-endpoint failures
- Diagnostic Lambda success and failure with tool, correlation, region, and evidence metadata
- Phase 8 approval acceptance/rejection and explicit approval decision
- Phase 8 remediation acceptance/rejection and execution outcome
- Separate READ verification start, result, failure, and verification ID

Correlation/session binding and READ/WRITE authorization are unchanged. Observability is
side-effect-free metadata emission and cannot authorize a write or bypass fail-closed
validation.

## Offline evidence

Contract, unit, and security tests validate schema conformance, required version/redaction
fields, identifier consistency across a representative Runtime-to-MCP sequence, success and
failure events, denied approval events, exception-message redaction, and rejection of
unallowlisted fields.

## Deferred operational work

The remaining Phase 9 work requires a separately authorized AWS implementation and evidence
gate: AgentCore/OpenTelemetry integration, deployed CloudWatch Logs/Metrics/Traces,
MCP trace export, dashboards, focused alarms, model/token usage, live Flow Logs, safe alarm
validation, and Budget/cost alerting.
