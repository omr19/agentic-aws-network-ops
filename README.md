# Agentic AWS Network Operations

A portfolio project for explainable AWS network diagnosis using deterministic cloud evidence, Amazon Bedrock AgentCore, MCP tooling, and human-controlled remediation boundaries.

## Project Status and Achievements

**Current phase: Phase 12 — Public GitHub Packaging & Documentation (local controlled-sharing preparation; repository intentionally private).** Phase 11 is complete for bounded teardown, immediate cost verification, and delayed billing review. The approved Terraform teardown completed and Terraform state is empty. The nine Network Insights analyses, AgentCore Runtime/Gateway/target, Phase 5 diagnostic Lambda and log group, dedicated IAM roles, Runtime S3 object, and Runtime S3 bucket were deleted and independently verified absent. Delayed Cost Explorer review completed on 2026-08-27 for 2026-08-16 through 2026-08-28 (end exclusive): 12 daily periods, all estimated, account-level and service-grouped, totaling $0.237502973 USD. The data is not project-attributed and includes unrelated account services, so it does not establish project-specific zero billing. The [Phase 11 teardown preflight](docs/architecture/phase-11-teardown-preflight.md) records the evidence and limitations.

README and technical documentation are being prepared for controlled sharing while secret scanning, diagrams, deployment/teardown instructions, and external-reader review remain open. The screenshot strategy is intentionally conservative: raw AWS screenshots remain outside the repository in the private desktop folder, and no raw or sanitized screenshots are copied or committed at this time. Screenshots are optional private/demo evidence rather than required repository deliverables. Reproducibility relies on Terraform source, sanitized JSON evidence, Markdown documentation, tests, and future editable architecture diagrams. Sanitized screenshots may be added later if they provide clear value for an interview, demo, or controlled portfolio review. Public repository publication is deferred and is not required for Phase 12 completion.

Phase 7 also retains a documented limitation: CloudWatch metrics were validated, but live Flow Logs/CloudWatch Logs traffic evidence was not obtained because the project EC2 instances have no IAM instance profiles or SSM readiness. No live Flow Log record or Logs Insights query is claimed.

The delivered architecture and foundation include:

- Two private VPCs with private subnets, controlled routes, security groups, NACLs, and VPC peering.
- Terraform-managed network and lab foundations with deterministic validation evidence.
- An AgentCore Runtime/Gateway design with historical deployed MCP Gateway/Runtime evidence; those separately managed resources were removed during Phase 11 cleanup.
- A diagnostic Lambda behind MCP tools for structured, read-only network observation.
- Deterministic evidence from VPC facts, routes, security groups, NACLs, VPC Reachability Analyzer, CloudWatch metrics, and optional observability inputs.
- Least-privilege IAM with diagnostic/read boundaries separated from future remediation/write authorization.

Both project EC2 instances were terminated during the approved teardown, and no active project EC2 or EBS resources remain. The nine remaining EC2 tag-index entries are stale historical records for terminated/deleted Terraform resources. All temporary Phase 7 Flow Logs, log group, and IAM validation roles were previously cleaned up.

- [Project checklist](PROJECT_CHECKLIST.md) — authoritative phase order and completion gates.
- [Project status](PROJECT_STATUS.md) — current state, governance decisions, and limitations.
- [Phase 2 architecture](docs/architecture/phase-2-design.md) — approved system and security design.
- [Phase 7 deterministic diagnosis](docs/architecture/phase-7-deterministic-diagnosis.md) — diagnosis contract and evidence boundary.
- [Phase 4 validation report](docs/evidence/phase-4-validation.md) — network lab validation.
- [Phase 7 Flow Logs validation evidence](docs/evidence/phase-7/flowlogs-validation.json) — sanitized cleanup and limitation record.
- [Phase 10 requirements-to-evidence matrix](docs/architecture/phase-10-validation-matrix.md) — bounded local coverage, deferred live checks, and unresolved review items.
- [Phase 11 teardown preflight](docs/architecture/phase-11-teardown-preflight.md) — reconciled inventory, cost considerations, executed teardown order, evidence capture, and delayed-billing follow-up.
- [Architecture decision records](docs/adr/README.md) — significant design decisions and rationale.
- [Business case and market positioning](docs/business-case.md) — customer problem, target audiences, differentiation, commercialization path, and production-readiness boundary.
- [ADR 018 — TGW evolution](docs/adr/018-post-mvp-transit-gateway-evolution.md) — future multi-VPC/TGW and optional AWS-to-on-premises design, with complementary Route Analyzer and Reachability Analyzer roles.

## Phase-by-Phase Progress

The table preserves the 13 authoritative phases in `PROJECT_CHECKLIST.md`.

| Phase | Status | Verified scope |
|---|---|---|
| 1 — Business Requirements & Learning Objectives | Complete | Requirements, audience, objectives, MVP scope, cost and security guardrails documented and approved. |
| 2 — Architecture & Technical Design | Complete | AWS network, AgentCore, MCP, IAM boundaries, deterministic diagnosis principles, and Terraform decisions documented. |
| 3 — Kiro Spec & Git/Terraform Foundation | Complete | Repository, Kiro Spec, Terraform foundation, Python tooling, validation, and Git foundation established. |
| 4 — AWS Network Lab | Complete | Approved private network lab, peering, controls, healthy/blocked paths, Reachability Analyzer evidence, and Terraform validation completed. |
| 5 — AgentCore + MCP Diagnostic Tooling | Complete | Read-only diagnostic contracts, Lambda/MCP tooling, least-privilege IAM, AgentCore integration path, and local/deployed validation completed. |
| 6 — Network Failure Scenarios | Complete | Controlled security-group, route, NACL, DNS fixture, and peering failure scenarios documented and validated. |
| 7 — Intelligent Deterministic Diagnosis | Complete with limitation | Deterministic diagnosis foundation and CloudWatch metrics validated; live Flow Logs/CloudWatch Logs traffic evidence is limited by missing EC2 IAM instance profiles and SSM readiness. |
| 8 — Human-Controlled Remediation | Complete — bounded validation scope | Local approval-to-remediation-to-verification workflow, IAM evidence, Lambda deployment boundary, and fail-closed smoke are validated. Trusted authenticated approval, live approved remediation, and live post-remediation verification are deferred by approved scope. |
| 9 — Monitoring, Alerting & Observability | Complete — bounded local-validation scope | Versioned observability contract, sanitized instrumentation, correlation/session metadata, redaction, and offline validation are complete. Live CloudWatch/AgentCore telemetry, dashboards, alarms, budgets, Flow Logs delivery, and deployed end-to-end correlation are deferred. |
| 10 — Testing, Architecture Review, Security Review & Cost Review | Complete — bounded validation scope | Repository-only offline functional/repeatability tests, deterministic diagnosis, local approval/denial/verification contracts, architecture/security review, exact-account IAM correction, local quality validation, and cost-control documentation. Live and unresolved capabilities are deferred by approved bounded scope; this is not a production-readiness or full live-remediation claim. |
| 11 — Destroy & Cost Verification | Complete — bounded teardown, immediate cost verification, and delayed billing review | Terraform state is empty; all nine analyses, AgentCore Runtime/Gateway/target, Phase 5 Lambda/log group, dedicated IAM roles, Runtime S3 object/bucket are deleted and independently verified absent. No active EC2/EBS resources remain; nine EC2 tag-index entries are stale historical records. Delayed Cost Explorer review on 2026-08-27 covered 2026-08-16 through 2026-08-28 (end exclusive), with all 12 daily periods estimated and an account-level, non-project-attributed total of $0.237502973 USD; it does not establish project-specific zero billing. |
| 12 — Public GitHub Packaging & Documentation | In progress — local controlled-sharing preparation | The GitHub repository intentionally remains private. README and technical documentation, sanitization, secret scanning, diagrams, deployment/teardown instructions, and external-reader review are being prepared for controlled sharing. Public publication is deferred and not required for Phase 12 completion; sanitized screenshots, a demo video, LinkedIn, and a portfolio case study remain viable showcase paths. |
| 13 — Career & Demo Packaging | Pending / future authorization | Demo, interview, resume, and portfolio packaging remain future work. |

### Future enterprise enhancement: TGW and on-premises connectivity

The current MVP intentionally uses two-VPC peering. A future, separately authorized
variant can replace the interconnect with a Transit Gateway and optionally add a
Site-to-Site VPN or Direct Connect attachment to represent on-premises connectivity.
Route Analyzer would inspect TGW route-table decisions; Reachability Analyzer would
remain useful for supported static path and security-control analysis; Flow Logs and
CloudWatch would provide observed traffic evidence. This enhancement would use separate
Terraform state and a controlled demo window because TGW and VPN/Direct Connect add cost.

## Architecture Diagram

```text
[User]
   |
   v
[AgentCore Runtime]
   |
   v
[MCP Gateway]
   |
   v
[Diagnostic Lambda]
   |
   v
[Deterministic AWS evidence]
   |-- VPC facts, routes, security groups, NACLs
   |-- VPC Reachability Analyzer
   |-- CloudWatch metrics
   `-- Flow Logs / CloudWatch Logs: live traffic evidence limitation
   |
   v
[Diagnosis / recommendation]
   |
   v
[Human approval]
   |
   v
[Phase 8 remediation tools — locally validated; live execution deferred]
```

The agent correlates observed facts and produces bounded recommendations; it does not treat reasoning as authorization or silently infer network reachability.

## Phase Lifecycle Diagram

```text
P1 Requirements
      -> P2 Architecture
      -> P3 Repository
      -> P4 Terraform/AWS
      -> P5 AgentCore/MCP
      -> P6 Failure scenarios
      -> P7 Diagnosis
      -> P8 Remediation (bounded validation complete)
      -> P9 Monitoring/observability
      -> P10 Testing/architecture/security/cost review (bounded validation complete)
      -> P11 Destroy/cost verification
      -> P12 Public packaging/documentation
      -> P13 Career/demo packaging
```

## Reproducibility and Cost Controls

- **Redeployment:** Terraform defines the network lab and environment composition. Review the [lab Terraform configuration](terraform/environments/lab/main.tf), [Terraform modules](terraform/modules/), and [`terraform.tfvars.example`](terraform/environments/lab/terraform.tfvars.example) before any authorized deployment.
- **Validation and evidence:** Local tests and diagnosis contracts live under [`tests/`](tests/); architecture and sanitized validation records are collected under [`docs/architecture/`](docs/architecture/) and [`docs/evidence/`](docs/evidence/).
- **Temporary resources:** Validation resources are explicitly tagged, scoped to the test, and cleaned up after use. The Phase 7 record documents cleanup of temporary Flow Logs, the log group, and IAM roles.
- **EC2 operating model:** Historical validation kept the lab instances stopped when not testing; Phase 11 teardown subsequently terminated/deleted the project EC2 and EBS resources, so no active project compute or storage remains.
- **Observability boundary:** CloudWatch metrics are validated. Live Flow Logs/CloudWatch Logs traffic evidence remains unavailable because the instances lack IAM instance profiles and SSM readiness; no profile, endpoint, or additional IAM permission was added to bypass that boundary.
- **Teardown and validation guidance:** Start with the [Phase 4 validation report](docs/evidence/phase-4-validation.md), [Phase 7 evidence](docs/evidence/phase-7/flowlogs-validation.json), [project status](PROJECT_STATUS.md), and the [authoritative checklist](PROJECT_CHECKLIST.md). Follow the documented approval gates before any AWS-changing action.

## Repository Guide

- [`docs/requirements.md`](docs/requirements.md) — business requirements and learning objectives.
- [`src/`](src/) — local diagnostic implementation.
- [`iam/`](iam/) — reviewed policy fixtures and IAM boundaries.
- [`terraform/`](terraform/) — infrastructure definitions and environment composition.
- [`tests/`](tests/) — unit, contract, and security validation.
