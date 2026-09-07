# Phase 2 Architecture and Technical Design

## Status

**Complete.** This records the Phase 2 decisions approved by the user. The final
independent architecture review passed on 2026-08-28 with no confirmed defects, and
the user approved Phase 2 closure on 2026-08-28.

## Approved principles

- Deterministic AWS evidence establishes network facts; the agent correlates,
  explains, and recommends.
- Natural-language approval communicates intent but never grants AWS authority.
- Diagnostic READ and remediation WRITE capabilities use separate identities and
  authorization domains.
- Terraform remains the authoritative infrastructure definition.
- Costly persistent services require a demonstrated need.
- Observable execution data is traced without secrets or hidden model reasoning.

## Approved target architecture

### Region and network direction

- Use `eu-west-1` (Europe/Ireland).
- Build two dedicated Terraform-managed VPCs connected by same-Region VPC peering.
  Each VPC spans two Availability Zones and contains only private workload subnets:
  - Source VPC `10.10.0.0/16`: `10.10.10.0/24` and `10.10.20.0/24`
  - Destination VPC `10.20.0.0/16`: `10.20.10.0/24` and `10.20.20.0/24`
- Leave the default VPC and all other pre-existing resources untouched.
- Do not use NAT Gateway by default. Prefer selective VPC endpoints for required AWS
  services. Keep DNS support and hostnames enabled in the healthy baseline.
- Use no public subnets or public IP addresses in the MVP.
- Keep the VPC/workload modules independent from the peering interconnect so a separate
  post-MVP TGW variant can reuse them. TGW is not part of the initial deployment.

### Deterministic diagnostics

AWS configuration APIs establish configuration facts. Reachability Analyzer is the
primary configured-path analysis capability. Flow Logs provide complementary observed-
traffic evidence where justified. An authorization or evidence-collection failure is
reported as a limitation—not as a network root cause—including the affected identity
and AWS action where determinable.

Enable VPC-level Flow Logs for both project VPCs only during controlled diagnostic and
demo sessions, deliver them to CloudWatch Logs, and use a seven-day retention period.
The Terraform design must allow Flow Logs to remain disabled outside those sessions.

### AgentCore, invocation, and memory

- Managed AgentCore Runtime hosts one operational agent outside both workload VPCs.
- AgentCore Gateway is the preferred managed integration/authorization boundary.
- MCP defines strict first-class tool contracts; Python/Boto3 performs AWS operations.
- One non-VPC diagnostic Lambda target exposes all nine READ contracts. One separate
  non-VPC remediation Lambda target exposes only approved WRITE contracts.
- Native AgentCore invocation is the MVP entry path. API Gateway plus an adapter
  Lambda is an advanced option for external REST consumers and webhooks.
- The native MVP client uses IAM/SigV4 inbound authorization.
- Use session-scoped context for the MVP. Persistent AgentCore Memory is optional and
  may inform reasoning but can never grant authority.

Runtime and tool execution do not require direct TCP access to the private test
workloads. They gather evidence through AWS service APIs, Reachability Analyzer, Flow
Logs, and CloudWatch. Therefore neither Runtime nor the Lambda targets are attached to
the Source or Destination VPC.

### MCP tools and contracts

Diagnostic capabilities include the checklist's core contracts plus permission
awareness. The nine required diagnostic contracts are:

- `describe_vpcs`
- `describe_subnets`
- `describe_route_tables`
- `describe_security_groups`
- `describe_network_acls`
- `describe_vpc_endpoints`
- `analyze_reachability`
- `query_flow_logs`
- `get_cloudwatch_metrics`

Generic tools such as `execute_boto3` or `run_aws_command` are prohibited.
Strict schemas constrain region, resource, and supported operations. A consistent
result envelope distinguishes success, no finding, unreachable, authorization denied,
API error, timeout, and invalid request and records correlation, evidence, errors,
authorization, and evidence completeness as applicable.

### Identity, approval, and remediation

Use separate least-privilege identities for Agent Runtime, READ diagnostics, and narrow
WRITE remediation. The diagnostic identity has no infrastructure-write permissions.
Gateway uses its execution role to invoke the two Lambda targets; each target uses its
own execution identity for AWS operations.

The preferred enforcement chain is:

`canonical proposal → explicit human approval → AgentCore Policy → interceptor → WRITE MCP tool → atomic consumption → remediation identity → AWS IAM → change → READ verification`

Policy authorizes the MCP tool call; IAM independently authorizes the AWS operation.
Both must permit it. Denial produces zero writes. Approval/denial, authorization,
execution, and verification are auditable events.

Natural-language confirmation does not create approval. The human invokes a dedicated,
non-MCP Approval Lambda using IAM/SigV4. It writes a five-minute, one-time DynamoDB
approval record bound by SHA-256 canonical request hash to the approver, policy session,
correlation ID, tool, region, resource, operation, and exact parameters. Agent Runtime
and tool roles cannot invoke the Approval Lambda.

A temporal Dogwood policy requires a matching earlier proposal in the same policy
session. A Gateway request interceptor validates the approval but does not consume it.
The remediation Lambda conditionally changes `APPROVED` to `EXECUTING`, uses an
execution ID for idempotency, and records `COMPLETED` or `FAILED`. Expired, modified,
failed, or reused requests require a new approval. Policies move from `LOG_ONLY` to
`ENFORCE` only after positive and negative tests pass.

### Scenarios and Terraform ownership

The primary healthy path is a short-lived private workload in the Source VPC to a
short-lived private workload in the Destination VPC on TCP/443. Both sides contain
explicit peering routes. The workloads have no public IP addresses and require no
arbitrary internet egress.

The MVP has three reversible failures:

- destination security group blocks the approved TCP/443 source
- a required source or return peering route is missing or incorrect
- destination-subnet NACL blocks TCP/443 or required return traffic

Each requires a known symptom, root cause, evidence, remediation, verification, and
reset. Reachability Analyzer is required for configured-path validation; Flow Logs are
complementary traffic evidence during controlled sessions.

The MVP has exactly three WRITE tools: `restore_security_group_ingress`,
`restore_vpc_peering_route`, and `restore_network_acl_entry`. They restore only the
fixed Terraform-defined TCP/443 SG rule, the two approved peering routes, or the fixed
destination-NACL ingress rule. A Terraform-injected non-secret manifest supplies exact
resource IDs and expected state; the model supplies only an approved scenario enum and
approval/correlation/session identifiers. No generic AWS execution tool exists.

The remediation role is limited to `ec2:AuthorizeSecurityGroupIngress`,
`ec2:CreateRoute`, `ec2:ReplaceRoute`, and `ec2:ReplaceNetworkAclEntry`, with exact
resource, tag, Region, and supported condition restrictions wherever AWS permits.
Delete, IAM, role-assumption, public-route, peering-lifecycle, compute, AgentCore,
Lambda-configuration, endpoint, Flow Logs, DNS, and TGW writes are prohibited.

Terraform creates the baseline/scenarios and remains desired-state authority. Approved
runtime remediation must report resulting drift. The agent must not silently edit
Terraform, and broad `ignore_changes` must not conceal drift.

### Terraform, Git, testing, and observability

- Use local state for the single-engineer MVP and one `lab` environment. Keep state,
  real variable files, credentials, and private configuration out of Git. Document
  remote state as a team/production evolution.
- Use responsibility-based modules, a safe `terraform.tfvars.example`, and consistent
  ownership/cost tags. Later apply requires format, validate, plan, human plan review,
  and explicit authorization.
- Use `develop` for integration and `main` for stable state; feature branches are
  optional for substantial/risky work.
- Test static validity, contracts, AWS integration, controlled scenarios,
  authorization/security failures, AI-specific failures, and end-to-end behavior.
- Use correlation IDs, structured JSON events, AgentCore Observability, OpenTelemetry,
  CloudWatch Logs/Metrics/Traces, focused alarms, and SNS email for the MVP. Expected
  lab failures must be distinguishable from unexpected incidents.

### Local development and AWS mocking

Each MCP capability has a version-controlled schema, framework-independent Python logic
with dependency-injected AWS clients, and a thin diagnostic or remediation Lambda
adapter. The local path uses `pytest`, Botocore `Stubber`, JSON Schema validation,
saved Gateway/Lambda event fixtures, and a local handler runner. Routine unit tests use
no live AWS credentials or calls.

Use `agentcore dev` with deterministic stub tool responses for local agent execution,
hot reload, inspection, and traces. Progress to controlled deployed Gateway/Lambda
integration only after schema, tool, adapter, authorization-failure, and local-agent
tests pass. Kiro provides independent review at material schema, IAM/security, coverage,
and final-diff gates rather than repetitive test execution.

### Kiro Spec and quality tooling

Phase 3 creates `.kiro/specs/agentic-aws-network-ops/requirements.md`, `design.md`, and
`tasks.md`, with stable requirement IDs and requirements-to-test traceability. The Spec
derives from authoritative repository requirements, architecture, ADRs, and checklist;
it cannot alter phase order or authorize deployment.

Use `uv`, Ruff, mypy, pytest/pytest-cov, Botocore `Stubber`, JSON Schema validation,
Bandit, and pip-audit for Python/contracts. Use Terraform format/validate/plan, TFLint,
Checkov, and pre-commit for IaC/repository validation. GitHub Actions performs only
non-destructive checks without broad AWS credentials. Pin versions in Phase 3 and
require narrow rationale for suppressions.

## Documentation plan

Significant decisions are recorded under `docs/adr/`. Five diagrams will use official
AWS icons, editable diagrams.net/draw.io sources, and SVG or PNG exports: end-to-end
architecture, network topology, AgentCore/MCP flow, observability flow, and security/
approval/remediation flow. Initial sources begin in Phase 2 and are finalized against
implemented reality in Phase 12.

## Private-connectivity decision

The peering MVP creates no VPC endpoints. The private workloads do not call AgentCore
or AWS service APIs, and non-VPC Lambda tool execution can reach AWS APIs without a
customer-managed NAT Gateway or interface endpoints. That service access uses
AWS-managed Lambda networking and does not create a customer-controlled NAT Gateway
charge. Reevaluate PrivateLink/VPC attachment only for a private VPC-hosted client,
private MCP/API/database/IdP, or the TGW shared-services variant. Such a change requires
a fresh endpoint, DNS, IAM, cost, and security review.

## Phase 2 closure

The final independent architecture review passed with no confirmed defects. No open
Phase 2 architecture decisions remain.

No Terraform/Python implementation, initialization, apply, AWS/IAM change, deployment,
commit, or push is part of this design record.
