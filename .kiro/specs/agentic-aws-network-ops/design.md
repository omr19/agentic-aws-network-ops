# Kiro Spec Design — Agentic AWS Network Operations

## Authority

This document organizes the accepted architecture for implementation. It does not
replace ADRs, authorize AWS changes, or permit phase reordering. Conflicts resolve in
favor of `PROJECT_CHECKLIST.md` and the approved requirements/architecture/ADRs.

## Components and boundaries

| Component | Responsibility and trust boundary | Requirements |
|---|---|---|
| IAM/SigV4 client | Submit user requests as the human/operator | SYS-001, AGT-003 |
| AgentCore Runtime | Correlate evidence, explain, propose; never approve | SYS-001–003, AGT-001, SEC-002 |
| AgentCore Gateway | Managed MCP and policy boundary | AGT-001, SEC-004, OBS-001 |
| Diagnostic Lambda | Nine strict READ contracts; no writes | DIA-001–004, AGT-002, SEC-001 |
| Approval Lambda/table | Human approval and one-time atomic state | SEC-002–005 |
| Gateway interceptor | Validate binding without consuming approval | SEC-003–004 |
| Remediation Lambda | Three fixed restorations and verification | REM-001–005, SEC-005–006 |
| VPC modules/interconnect | Private TCP/443 peering lab | NET-001–005 |
| AWS diagnostic services | Establish deterministic evidence | DIA-001, DIA-005 |
| Observability stack | Correlated, sanitized operational evidence | OBS-001–002, SEC-007 |

## Network design

Terraform owns two reusable VPC/workload modules and a separate peering interconnect.
The approved CIDRs, two-AZ private-only layout, bidirectional routes, TCP/443 rules, and
NACL baseline are fixed by ADR 002. No NAT Gateway, public subnet/IP, or endpoint is in
the MVP. Fixtures alter only the approved SG, route, or NACL and provide deterministic
reset. A TGW variant uses separate configuration/state after MVP acceptance.
[NET-001–005, CST-001]

## Diagnosis flow and contracts

1. The IAM/SigV4 client submits a request with correlation/session ID.
2. Runtime selects among the nine Gateway READ contracts.
3. Diagnostic Lambda queries scoped AWS APIs, Reachability Analyzer, and optionally
   controlled-session Flow Logs/CloudWatch data.
4. Versioned JSON Schema envelopes identify facts, limitations, errors, authorization,
   timestamps, evidence references, and completeness; unknown fields are rejected.
5. Runtime separates evidence from interpretation and may emit a canonical proposal.
   No write occurs. Generic execution and model-selected resource IDs are prohibited.

[SYS-001–003, DIA-001–005, AGT-001–003]

## Approval and remediation flow

1. Runtime emits a canonical proposal but cannot approve it.
2. A human invokes Approval Lambda via IAM/SigV4.
3. Approval Lambda canonicalizes the request, calculates SHA-256, and stores a
   five-minute `APPROVED` record bound to every SEC-003 field.
4. Temporal Gateway policy requires the earlier proposal; the interceptor recomputes
   and validates the binding but does not consume it.
5. Remediation Lambda atomically changes `APPROVED` to `EXECUTING`; one caller succeeds.
6. The fixed WRITE adapter checks the broken precondition, uses the Terraform-injected
   manifest, performs the narrow action, and verifies through READ diagnostics and
   Reachability Analyzer.
7. State becomes `COMPLETED` or `FAILED`; the response separately reports execution,
   verification, and Terraform drift/reconciliation.

Missing, expired, altered, denied, failed, or reused approval causes zero new writes.
Policy promotion from `LOG_ONLY` to `ENFORCE` requires adversarial test evidence.
[SEC-001–006, REM-001–005]

## IAM, state, and failure handling

Runtime, Gateway, diagnostic, approval, and remediation roles are independent.
Diagnostic IAM is read-only. Remediation IAM includes only the four approved EC2 actions
and supported Region/resource/tag/condition restrictions. Later implementation must
verify EC2 condition-key support and document compensating manifest/schema/policy/code
controls where AWS cannot scope an action as desired. Verifying exact EC2 condition-key
support is a named Phase 8 prerequisite before remediation IAM is finalized.
[SEC-001–007, REM-001–003]

Terraform is desired-state authority using local ignored state, one `lab` environment,
responsibility modules, placeholder-only examples, and ownership/cost tags. Runtime
never edits Terraform or hides drift. A later apply requires source reconciliation,
plan review, and explicit authorization. [REM-002, REM-005, ENG-001, CST-002]

Invalid schema fails before AWS access. Authorization/incomplete evidence returns a
limitation, never an invented cause. API errors/timeouts are typed. Approval failures
write nothing. Partial WRITE or verification failure preserves audit evidence and never
claims recovery. [DIA-003–004, SEC-004–006, REM-004, TST-002]

## Development, observability, and lifecycle

Shared Python logic uses injected Boto3 clients and thin handlers. Local pytest,
Stubber, schema, fixture, and `agentcore dev` tests require no live credentials. Phase 3
pins uv, Ruff, mypy, pytest-cov, Bandit, pip-audit, Terraform/TFLint/Checkov,
pre-commit, and non-destructive CI versions. [TST-001–002, ENG-001–002]

Sanitized structured events propagate correlation IDs through observable boundaries.
AgentCore Observability, OpenTelemetry, CloudWatch, alarms, SNS, and controlled Flow
Logs provide evidence without hidden reasoning. Budget monitoring, resource inventory,
short-lived workloads, teardown verification, and final documentation enforce portfolio
and cost requirements. [OBS-001–002, DIA-005, CST-001–002, LIF-001]

## Traceability matrix

| Requirements | Design sections | Planned verification tasks |
|---|---|---|
| All requirements (Spec integrity) | All sections | P3-01 |
| SYS-001, SYS-002, SYS-003 | Components; diagnosis flow | P5-04, P8-04, P9-01, P10-01 |
| NET-001, NET-002, NET-003, NET-004, NET-005 | Network design | P4-01, P4-02, P4-03, P6-01, P6-02, P11-01, P12-02 |
| DIA-001, DIA-002, DIA-003, DIA-004, DIA-005 | Diagnosis; failure handling | P5-01, P5-02, P6-02, P7-01, P7-02, P9-02, P10-01 |
| AGT-001, AGT-002, AGT-003 | Components; diagnosis flow | P5-02, P5-04, P10-02 |
| SEC-001, SEC-002, SEC-003, SEC-004, SEC-005, SEC-006, SEC-007 | Approval; IAM/failures | P5-03, P8-01, P8-02, P8-03, P8-05, P10-02 |
| REM-001, REM-002, REM-003, REM-004, REM-005 | Approval; state | P6-01, P8-03, P8-04, P10-01 |
| OBS-001, OBS-002 | Observability/lifecycle | P9-01, P9-02, P10-01 |
| TST-001, TST-002 | Development/failures | P3-02, P3-03, P5-01, P5-02, P7-01, P7-02, P10-01 |
| ENG-001, ENG-002 | State; development | P3-02, P3-03, P3-04, P3-05, P3-06, P3-07, P10-02 |
| CST-001, CST-002 | Network; lifecycle | P3-04, P4-01, P4-03, P9-02, P11-01 |
| LIF-001 | Lifecycle | P11-01, P12-01, P12-02, P13-01 |
