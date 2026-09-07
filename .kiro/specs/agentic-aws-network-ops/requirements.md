# Kiro Spec Requirements — Agentic AWS Network Operations

## Authority

This specification derives from `PROJECT_CHECKLIST.md`, `docs/requirements.md`,
`docs/architecture/phase-2-design.md`, and accepted ADRs 001–023. Those sources remain
authoritative. This spec cannot change the 13-phase sequence, authorize deployment, or
mark work complete without implementation and validation. `MUST` denotes MVP scope;
`MAY` denotes post-MVP scope that must not delay or destabilize the MVP.

## System outcomes

- **SYS-001:** The system MUST accept natural-language AWS network troubleshooting
  requests and dynamically select appropriate diagnostic tools.
- **SYS-002:** Responses MUST distinguish observed AWS facts from AI interpretation
  and recommendations and MUST explain symptoms, evidence, supported root cause or
  evidence limitations, affected components, and recommended action.
- **SYS-003:** The complete request, diagnosis, approval/denial, remediation, and
  verification flow MUST be auditable through a correlation identifier.

## Network lab

- **NET-001:** Terraform MUST define dedicated Source `10.10.0.0/16` and Destination
  `10.20.0.0/16` VPCs in `eu-west-1`, each spanning two Availability Zones with the
  approved private `/24` subnets and no public subnets or public workload IPs.
- **NET-002:** The MVP MUST use same-Region VPC peering with explicit bidirectional
  routes and a short-lived private Source-to-Destination TCP/443 test path.
- **NET-003:** The MVP MUST NOT depend on NAT Gateway, Internet Gateway, or VPC
  endpoints, and existing default/non-project AWS resources MUST remain untouched.
- **NET-004:** The lab MUST provide reversible destination-security-group,
  peering-route, and destination-NACL failure scenarios with repeatable reset states.
- **NET-005:** VPC/workload modules MUST remain independent from the interconnect so a
  separate three-VPC TGW configuration/state MAY be added after the peering MVP passes.

## Deterministic diagnostics and MCP

- **DIA-001:** AWS APIs and Reachability Analyzer MUST establish network facts; the
  model MUST NOT assert unsupported reachability conclusions.
- **DIA-002:** The READ boundary MUST expose exactly `describe_vpcs`,
  `describe_subnets`, `describe_route_tables`, `describe_security_groups`,
  `describe_network_acls`, `describe_vpc_endpoints`, `analyze_reachability`,
  `query_flow_logs`, and `get_cloudwatch_metrics`.
- **DIA-003:** Every tool MUST use strict version-controlled schemas and a consistent
  result envelope for success, no finding, unreachable, authorization denied, API
  error, timeout, invalid request, correlation, and evidence completeness.
- **DIA-004:** Authorization failure or incomplete evidence MUST be reported as a
  limitation, not a network root cause. Generic AWS/Boto3/shell execution tools MUST
  NOT exist.
- **DIA-005:** VPC-level Flow Logs MAY run only during controlled sessions, MUST use
  CloudWatch Logs with seven-day retention, and MUST be disableable.

## AgentCore and placement

- **AGT-001:** One AgentCore Runtime outside the workload VPCs MUST host the MVP agent,
  with AgentCore Gateway as the managed tool boundary.
- **AGT-002:** Separate non-VPC diagnostic and remediation Lambdas MUST expose only the
  approved READ and WRITE contracts respectively.
- **AGT-003:** The native MVP client MUST use IAM/SigV4. API Gateway, persistent Memory,
  and multi-agent specialization MAY be reconsidered after the MVP; Memory MUST never
  grant authority.

## Security, identity, and approval

- **SEC-001:** Runtime, diagnostic READ, and remediation WRITE identities MUST remain
  separate and least-privileged; diagnostic IAM MUST have no write permission.
- **SEC-002:** AI reasoning and natural-language confirmation MUST NOT grant authority.
  An authorized human MUST invoke a dedicated non-MCP Approval Lambda via IAM/SigV4;
  Runtime and tool roles MUST NOT invoke it.
- **SEC-003:** Approval MUST be explicit, auditable, one-time, expire after five
  minutes, and bind approver, policy session, correlation ID, tool, region, resource,
  operation, exact parameters, and canonical SHA-256 request hash.
- **SEC-004:** Gateway policy/interceptor and AWS IAM MUST independently authorize a
  WRITE request. Any denial or validation failure MUST cause zero writes.
- **SEC-005:** Remediation MUST atomically transition `APPROVED` to `EXECUTING`, enforce
  idempotency, and record `COMPLETED` or `FAILED`. Expired, altered, failed, or reused
  approvals MUST require a new approval.
- **SEC-006:** Policy MUST begin in `LOG_ONLY` and enter `ENFORCE` only after positive
  and negative authorization tests pass.
- **SEC-007:** Secrets, credentials, account IDs, sensitive variables, Terraform state,
  and hidden model reasoning MUST NOT enter Git, logs, or public artifacts.

## Remediation and verification

- **REM-001:** The WRITE boundary MUST expose exactly `restore_security_group_ingress`,
  `restore_vpc_peering_route`, and `restore_network_acl_entry`.
- **REM-002:** Terraform MUST inject an immutable non-secret manifest containing exact
  resource IDs and expected state. Model inputs MUST be limited to an approved scenario
  enum and approval/correlation/session identifiers.
- **REM-003:** Remediation IAM MUST be limited to the approved EC2 actions with exact
  Region/resource/tag/condition restrictions wherever supported. Delete, IAM, role
  assumption, public route, peering lifecycle, compute, AgentCore, Lambda configuration,
  endpoint, Flow Logs, DNS, and TGW writes MUST be prohibited.
- **REM-004:** Each WRITE tool MUST inspect its precondition, perform only the fixed
  restoration, rerun relevant READ diagnostics and Reachability Analyzer, and report
  verification separately from execution.
- **REM-005:** Runtime changes to Terraform-managed resources MUST return an explicit
  drift/reconciliation warning; Terraform remains desired-state authority.

## Observability, testing, engineering, and lifecycle

- **OBS-001:** Sanitized structured events MUST carry correlation/session identifiers
  across Runtime, Gateway, tools, AWS evidence, approval, remediation, and verification.
- **OBS-002:** AgentCore Observability, OpenTelemetry, CloudWatch logs/metrics/traces,
  focused alarms, and SNS MUST provide operational visibility without hidden reasoning.
- **TST-001:** Framework-independent Python logic MUST use dependency-injected AWS
  clients and thin Lambda adapters.
- **TST-002:** Routine tests MUST use pytest, Stubber, JSON Schema, and saved fixtures
  without live AWS credentials/calls and cover healthy/failure paths, authorization and
  evidence failures, denial, expiry/replay/tampering, idempotency, drift, and verification.
  Representative diagnostic scenarios MUST be repeated to assess consistency, reject
  false positives on healthy infrastructure, and document ambiguous/conflicting evidence.
- **ENG-001:** Terraform MUST pass fmt, validate, lint/security checks, and reviewed plan
  before separately authorized apply; Python/contracts MUST use ADR 023's pinned tools.
- **ENG-002:** GitHub Actions MUST be non-destructive and carry no broad AWS deployment
  credentials; suppressions MUST be narrow and justified.
- **CST-001:** The MVP MUST favor short-lived/consumption resources and MUST NOT default
  to NAT Gateway, TGW, persistent compute, unnecessary load balancers, or OpenSearch.
- **CST-002:** Budget/cost monitoring, project-resource inventory, repeatable teardown,
  and independent verification of no unintended billable resources MUST be implemented.
- **LIF-001:** The repository MUST provide reproducible setup, use, tests, cleanup,
  security, cost, ADR, and architecture-diagram documentation.

## Traceability rule

Every implementation task in `tasks.md` MUST cite requirement IDs. Every requirement
MUST map to `design.md` and at least one planned verification, and the design
traceability matrix MUST resolve back to the applicable task IDs in `tasks.md`.
Deployment authorization remains a separate human decision even after prerequisites pass.
