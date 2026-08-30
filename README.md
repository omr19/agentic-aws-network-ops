# Agentic AWS Network Operations

A portfolio project for explainable AWS network diagnosis using deterministic cloud evidence, Amazon Bedrock AgentCore, MCP tooling, and human-controlled remediation boundaries.

## Project Status and Achievements

**Current phase: Phase 9 — Monitoring, Alerting & Observability (complete under bounded local-validation scope).** Phases 1–8 are complete within their documented scopes. Phase 9’s versioned observability schema, sanitized instrumentation, identifier propagation, redaction controls, and offline tests are complete. Live CloudWatch/AgentCore telemetry, dashboards, alarms, budgets, Flow Logs delivery, and deployed end-to-end correlation are explicitly deferred; this project does not claim production monitoring validation. The next governed phase is Phase 10 — Testing, Architecture Review, Security Review & Cost Review.

Phase 7 also retains a documented limitation: CloudWatch metrics were validated, but live Flow Logs/CloudWatch Logs traffic evidence was not obtained because the project EC2 instances have no IAM instance profiles or SSM readiness. No live Flow Log record or Logs Insights query is claimed.

The delivered architecture and foundation include:

- Two private VPCs with private subnets, controlled routes, security groups, NACLs, and VPC peering.
- Terraform-managed network and lab foundations with deterministic validation evidence.
- An AgentCore Runtime/Gateway direction with a deployed, ready MCP Gateway path.
- A diagnostic Lambda behind MCP tools for structured, read-only network observation.
- Deterministic evidence from VPC facts, routes, security groups, NACLs, VPC Reachability Analyzer, CloudWatch metrics, and optional observability inputs.
- Least-privilege IAM with diagnostic/read boundaries separated from future remediation/write authorization.

Both project EC2 instances are currently stopped, and all temporary Phase 7 Flow Logs, log group, and IAM validation roles were cleaned up. The authoritative project records and detailed evidence are:

- [Project checklist](PROJECT_CHECKLIST.md) — authoritative phase order and completion gates.
- [Project status](PROJECT_STATUS.md) — current state, governance decisions, and limitations.
- [Phase 2 architecture](docs/architecture/phase-2-design.md) — approved system and security design.
- [Phase 7 deterministic diagnosis](docs/architecture/phase-7-deterministic-diagnosis.md) — diagnosis contract and evidence boundary.
- [Phase 4 validation report](docs/evidence/phase-4-validation.md) — network lab validation.
- [Phase 7 Flow Logs validation evidence](docs/evidence/phase-7/flowlogs-validation.json) — sanitized cleanup and limitation record.
- [Phase 10 requirements-to-evidence matrix](docs/architecture/phase-10-validation-matrix.md) — bounded local coverage, deferred live checks, and unresolved review items.
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
| 10 — Testing, Architecture Review, Security Review & Cost Review | Pending / future authorization | Formal cross-cutting reviews and final cost/security validation remain future work. |
| 11 — Destroy & Cost Verification | Pending / future authorization | Governed teardown and independent cost/resource verification remain future work. |
| 12 — Public GitHub Packaging & Documentation | Pending / future authorization | Public-readiness review, polished documentation, diagrams, sanitization, and packaging remain future work. |
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
      -> P10–P13 Future enhancements
```

## Reproducibility and Cost Controls

- **Redeployment:** Terraform defines the network lab and environment composition. Review the [lab Terraform configuration](terraform/environments/lab/main.tf), [Terraform modules](terraform/modules/), and [`terraform.tfvars.example`](terraform/environments/lab/terraform.tfvars.example) before any authorized deployment.
- **Validation and evidence:** Local tests and diagnosis contracts live under [`tests/`](tests/); architecture and sanitized validation records are collected under [`docs/architecture/`](docs/architecture/) and [`docs/evidence/`](docs/evidence/).
- **Temporary resources:** Validation resources are explicitly tagged, scoped to the test, and cleaned up after use. The Phase 7 record documents cleanup of temporary Flow Logs, the log group, and IAM roles.
- **EC2 operating model:** Keep the two lab instances stopped when not testing. Stopping them reduces compute charges while retaining EBS storage charges; restarting, termination, and Terraform destroy belong to the governed operational path.
- **Observability boundary:** CloudWatch metrics are validated. Live Flow Logs/CloudWatch Logs traffic evidence remains unavailable because the instances lack IAM instance profiles and SSM readiness; no profile, endpoint, or additional IAM permission was added to bypass that boundary.
- **Teardown and validation guidance:** Start with the [Phase 4 validation report](docs/evidence/phase-4-validation.md), [Phase 7 evidence](docs/evidence/phase-7/flowlogs-validation.json), [project status](PROJECT_STATUS.md), and the [authoritative checklist](PROJECT_CHECKLIST.md). Follow the documented approval gates before any AWS-changing action.

## Repository Guide

- [`docs/requirements.md`](docs/requirements.md) — business requirements and learning objectives.
- [`src/`](src/) — local diagnostic implementation.
- [`iam/`](iam/) — reviewed policy fixtures and IAM boundaries.
- [`terraform/`](terraform/) — infrastructure definitions and environment composition.
- [`tests/`](tests/) — unit, contract, and security validation.
