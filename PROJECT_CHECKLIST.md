# Project Checklist — Agentic AWS Network Operations

A living master checklist for the full project lifecycle.

Check items off only after they are completed and validated. Every phase has an explicit completion gate. `PROJECT_CHECKLIST.md` is authoritative for project scope and phase order.

---

## Foundation — Repository & Governance

### F.1 Repository & Development Hygiene

- [x] Create private GitHub repository
- [x] Configure `.gitignore` for Terraform, Python, macOS, secrets, and AWS credential artifacts
- [x] Create and switch development work to the `develop` branch
- [x] Verify `.gitignore` policy explicitly preserves `.terraform.lock.hcl`
  - Policy check only; the actual lock file will be generated during Phase 3 `terraform init`
- [x] Perform initial local Git commit-history and secrets validation
- [x] Confirm no raw secrets, credentials, or sensitive project data are present in initial commit history

### F.2 Governance

- [x] `PROJECT_CHECKLIST.md` created, reviewed, and saved
- [x] `PROJECT_STATUS.md` corrected, reviewed, and saved
- [x] Establish persistent Kiro project governance/steering instructions
  - Repository governance files override conversational recollection
  - Kiro must read governance files from disk before project work
  - Kiro must not reconstruct phase structure from chat history
  - Prefer minimal diffs; never rewrite an entire governance file for a small change
- [x] Review governance changes with `git diff`
- [x] Commit approved governance baseline to Git

- [x] **Foundation COMPLETE**

---

## Phase 1 — Business Requirements & Learning Objectives

- [x] Write a concise real-world network-operations problem statement

- [x] Define intended users and primary use cases

- [x] Define 3–5 measurable learning objectives

- [x] Explain why Agentic AI / Amazon Bedrock AgentCore is appropriate

  - Dynamic tool selection
  - Correlation of evidence across AWS services
  - Explainable diagnosis based on deterministic evidence
  - Human-controlled remediation

- [x] Define success criteria / definition of done

- [x] Define MVP scope

- [x] Define advanced/stretch scope separately from MVP

- [x] Establish cost guardrails

  - Favor short-lived and consumption-based resources
  - Avoid unnecessary persistent services
  - Explicitly evaluate potentially expensive resources before deployment

- [x] Establish security guardrails

  - AI reasoning does not equal authorization
  - Diagnostic/read operations and remediation/write operations remain separated
  - Human approval required for remediation

- [x] Define portfolio audience

  - Hiring managers
  - Cloud/network architects and engineers
  - GenAI/Agentic AI practitioners

- [x] Document Phase 1 requirements in the repository

- [x] Review and approve Phase 1 requirements before architecture design begins

- [x] **Phase 1 COMPLETE**

---

## Phase 2 — Architecture & Technical Design

### 2.1 AWS & Network Architecture

- [x] Confirm target AWS region and required service availability
- [x] Design the minimum useful AWS network lab topology
- [x] Decide VPC count, subnet structure, routing, security groups, NACLs, endpoints, and DNS requirements
- [x] Evaluate whether VPC peering, Transit Gateway, or neither adds sufficient learning/demo value
- [x] Evaluate internet-egress requirements
  - Do not assume NAT Gateway is required
  - Consider no arbitrary internet egress where possible
  - Consider VPC endpoints for supported AWS-service access
  - Evaluate NAT only where the traffic flow genuinely requires it
- [x] Document expected healthy connectivity paths and intentionally blocked paths
- [x] Define where VPC Reachability Analyzer provides deterministic validation
- [x] Decide whether and where VPC Flow Logs are required

### 2.2 AgentCore Architecture

- [x] Finalize Amazon Bedrock AgentCore Runtime approach
- [x] Finalize AgentCore Gateway approach
- [x] Finalize AgentCore Identity/IAM approach
- [x] Finalize AgentCore Observability approach
- [x] Evaluate AgentCore Memory as optional/advanced functionality
- [x] Define agent entry/invocation path
- [x] Evaluate API Gateway + Lambda where they provide a defensible purpose
  - External/demo entry point
  - Authentication/request validation
  - Rate limiting
  - Webhook/non-MCP integration
- [x] Evaluate single-agent MVP vs. multi-agent advanced architecture
  - Use multiple agents only when responsibility separation justifies additional complexity

### 2.3 MCP & Tool Architecture

- [x] Define MCP as a first-class integration layer
- [x] Define MCP hosting/deployment approach
- [x] Define local development/testing path
- [x] Define deployed AgentCore Gateway path
- [x] Define read-only diagnostic tool boundary
- [x] Define separately authorized remediation/write tool boundary
- [x] Define MCP input/output schema conventions
- [x] Define MCP authentication and IAM boundaries
- [x] Define explicit human-approval binding, expiration, replay protection, and atomic consumption
- [x] Define exact MVP remediation tools, AWS actions, resource scope, and prohibited operations
- [x] Define MCP tool-call tracing requirements

### 2.4 Deterministic Diagnosis Principle

- [x] Document architectural principle:
  - LLM must not guess network reachability
  - AWS APIs, Reachability Analyzer, Flow Logs, CloudWatch, and other deterministic sources establish facts
  - The agent correlates, explains, and recommends based on that evidence

### 2.5 Terraform & Engineering Decisions

- [x] Select Terraform backend/state strategy
  - Do not assume S3 + DynamoDB until evaluated
- [x] Define `terraform.tfvars.example` strategy
- [x] Define Terraform module structure
- [x] Define branch/PR strategy appropriate for a solo portfolio project
- [x] Define linting, formatting, validation, and test approach
- [x] Define Kiro Spec approach based on approved requirements
- [x] Record significant design decisions and rationale

### 2.6 Architecture Documentation Planning

- [x] Establish professional diagramming approach using official AWS architecture icons where applicable
- [x] Define editable diagram source format/tool
- [x] Plan the five required diagrams
- [x] Identify trust boundaries, IAM boundaries, and data/control-plane flows that diagrams must show
- [x] Review architecture before implementation begins

- [x] **Phase 2 COMPLETE**

---

## Phase 3 — Kiro Spec & Git/Terraform Foundation

- [x] Create structured Kiro Spec from approved Phase 1 and Phase 2 decisions
- [x] Establish repository directory structure
- [x] Initialize Terraform root configuration
- [x] Configure Terraform backend according to Phase 2 decision
- [x] Run `terraform init`
- [x] Verify `.terraform.lock.hcl` is generated
- [x] Verify `.terraform.lock.hcl` is tracked by Git
- [x] Run `terraform validate`
- [x] Establish Terraform modules/variables/outputs/environment conventions
- [x] Create `terraform.tfvars.example` with placeholder values only
- [x] Establish Python project/tooling structure where required
- [x] Configure agreed formatting/linting/testing checks
- [x] Review Git diff before committing foundation code
- [x] Commit validated Phase 3 foundation

- [x] **Phase 3 COMPLETE**

---

## Phase 4 — AWS Network Lab

> Build and validate the healthy network baseline only. Intentional failures belong to Phase 6.

- [x] Provision approved VPC architecture through Terraform
- [x] Provision approved public/private subnets as required by Phase 2 design
- [x] Provision route tables and associations
- [x] Provision security groups
- [x] Provision NACLs
- [x] Provision VPC endpoints where justified
- [x] Provision DNS-related components where required
- [x] Provision VPC peering or Transit Gateway only if approved in Phase 2
- [x] Provision internet/NAT components only if approved and required by the defined traffic flows
- [x] Use only minimal/short-lived test endpoints required to validate connectivity
- [x] Validate expected healthy network paths
- [x] Validate expected intentionally blocked baseline paths
- [x] Validate relevant paths with VPC Reachability Analyzer
- [x] Confirm Terraform state matches deployed architecture
- [x] Confirm `terraform plan` shows no unintended drift
- [x] Record active AWS resources and incremental project cost

- [x] **Phase 4 COMPLETE**

---

## Phase 5 — AgentCore + MCP Diagnostic Tooling

> Phase 5 implements the read-only diagnostic path. Remediation/write tools are implemented separately in Phase 8.

### 5.1 Core MCP Diagnostic Contracts

Implement and document explicit input/output schemas for:

- [x] `describe_vpcs`
- [x] `describe_subnets`
- [x] `describe_route_tables`
- [x] `describe_security_groups`
- [x] `describe_network_acls`
- [x] `describe_vpc_endpoints`
- [x] `analyze_reachability`
- [x] `query_flow_logs`
- [x] `get_cloudwatch_metrics`

Optional enhancements that must not replace the core contracts:

- [ ] Evaluate `describe_enis`
- [ ] Evaluate `detect_cidr_overlap`

### 5.2 Tool Implementation & Security

- [x] Implement diagnostic tools using Python/Boto3 and Lambda or other approved execution environment where appropriate
- [x] Enforce read-only least-privilege IAM
- [x] Confirm diagnostic role contains no remediation/write permissions
- [x] Return structured agent-consumable results
- [x] Return actionable structured errors rather than raw stack traces
- [x] Add structured tool-call logging/tracing
- [x] Unit test tools with mocked AWS responses where appropriate

### 5.3 AgentCore Integration

- [x] Deploy/host agent using AgentCore Runtime according to Phase 2 design
- [x] Integrate MCP diagnostic tooling through AgentCore Gateway
- [x] Configure AgentCore Identity/IAM boundaries
- [ ] Version-control agent system prompts/configuration
- [x] Validate local MCP development/testing path
- [x] Validate deployed AgentCore Gateway path
- [x] Validate agent can select and invoke required diagnostic tools
- [x] Validate end-to-end read-only happy path

- [x] **Phase 5 COMPLETE**

---

## Phase 6 — Network Failure Scenarios

- [x] Define selectable intentionally broken scenarios
- [x] Implement Terraform `scenario` variable or equivalent controlled mechanism where practical

Required candidates:

- [x] Broken security-group rule
- [x] Broken route-table entry
- [x] Broken NACL
- [x] Broken VPC endpoint configuration — N/A (no project VPC endpoints deployed)
- [x] DNS-related failure where applicable (local deterministic fixture; no AWS DNS resource)
- [x] VPC peering failure (TGW remains out of scope)

For each implemented scenario:

- [x] Document expected symptom
- [x] Document deterministic root cause
- [x] Document expected diagnostic evidence
- [x] Document correct remediation
- [x] Verify scenario can be injected cleanly
- [x] Verify scenario produces expected failure
- [x] Verify scenario can be reversed cleanly
- [x] Confirm healthy baseline can be restored

- [x] **Phase 6 COMPLETE**

---

## Phase 7 — Intelligent Deterministic Diagnosis

- [ ] Define diagnostic workflow for each implemented failure class
- [ ] Use deterministic AWS evidence as the factual basis of diagnosis
- [ ] Use VPC Reachability Analyzer where applicable
- [ ] Use AWS configuration/API evidence where applicable
- [ ] Use VPC Flow Logs where applicable
- [ ] Use CloudWatch metrics/logs where applicable
- [ ] Correlate evidence across multiple tools/services where useful
- [ ] Require the agent to distinguish observed evidence from recommendation
- [ ] Prevent unsupported/hallucinated root-cause claims
- [ ] Test healthy infrastructure for false-positive diagnoses
- [ ] Test each defined failure scenario against expected root cause
- [ ] Repeat representative scenarios to assess consistency
- [ ] Document limitations and ambiguous cases

- [ ] **Phase 7 COMPLETE**

---

## Phase 8 — Human-Controlled Remediation

> Full control flow: Observe → Diagnose → Propose → Human Approves/Denies → Execute → Verify.

### 8.1 Separate Write/Remediation Tools

- [ ] Define remediation/write MCP contracts separately from diagnostic contracts
- [ ] Define explicit input/output schemas
- [ ] Create separate least-privilege write IAM role/policy
- [ ] Restrict write permissions to specific approved corrective actions
- [ ] Document authorization boundary and blast radius for every write tool

### 8.2 Human Approval

- [ ] Agent proposes remediation without executing it
- [ ] Present proposed action and expected impact to human operator
- [ ] Implement explicit approval/denial mechanism
- [ ] Prevent agent from self-approving
- [ ] Prevent execution without recorded approval
- [ ] Record approval/denial with correlation/session ID and timestamp
- [ ] Verify denied requests produce no write side effects

### 8.3 Execute & Verify

- [ ] Execute only the explicitly approved remediation
- [ ] Record remediation result
- [ ] Re-run relevant diagnostic tools
- [ ] Re-run Reachability Analyzer where applicable
- [ ] Confirm expected connectivity/state is restored
- [ ] Surface verification result with remediation record
- [ ] Detect and report configuration drift when runtime remediation changes a Terraform-managed resource
- [ ] Require explicit Terraform source reconciliation before a later apply can restore the broken state

- [ ] **Phase 8 COMPLETE**

---

## Phase 9 — Monitoring, Alerting & Observability

> Trace observable execution data only. Do not claim to expose or log hidden model chain-of-thought.

- [ ] Implement structured JSON logging
- [ ] Establish end-to-end session/correlation IDs
- [ ] Trace user request → agent invocation → selected tool → MCP request/result → Lambda/AWS API where applicable → deterministic evidence → diagnosis/recommendation → approval/denial → remediation result → verification
- [ ] Enable/configure AgentCore Observability
- [ ] Implement OpenTelemetry tracing where appropriate
- [ ] Implement MCP tool-call tracing
- [ ] Configure CloudWatch Logs
- [ ] Configure useful CloudWatch Metrics
- [ ] Build CloudWatch dashboard
- [ ] Monitor Lambda/tool errors, duration, and throttling where applicable
- [ ] Monitor agent/tool invocation failures and latency
- [ ] Monitor model/token usage where available
- [ ] Monitor suspicious or denied remediation attempts
- [ ] Enable VPC Flow Logs according to Phase 2 design
- [ ] Configure a focused set of meaningful alarms
- [ ] Configure AWS Budget/cost alert
- [ ] Validate correlation IDs can trace representative sessions end-to-end
- [ ] Validate at least one safe test alarm/alert path where practical
- [ ] Document observability architecture and operational workflow

- [ ] **Phase 9 COMPLETE**

---

## Phase 10 — Testing, Architecture Review, Security Review & Cost Review

### 10.1 Functional & End-to-End Testing

- [ ] Test healthy baseline
- [ ] Test each implemented failure scenario
- [ ] Test deterministic diagnosis
- [ ] Test incorrect/irrelevant tool-selection handling
- [ ] Test agent/tool failure handling
- [ ] Test remediation approval
- [ ] Test remediation denial
- [ ] Test post-remediation verification
- [ ] Test representative repeated runs for consistency
- [ ] Document test matrix and results

### 10.2 Architecture Review

- [ ] Review implementation against approved Phase 2 architecture
- [ ] Document intentional deviations
- [ ] Reassess single-agent vs. multi-agent decision
- [ ] Reassess API Gateway/Lambda entry-path decision
- [ ] Reassess MCP hosting/integration decision
- [ ] Reassess network topology choices
- [ ] Review scalability, resilience, and operational limitations
- [ ] Perform senior-architect-style design review

### 10.3 IAM & Security Review

- [ ] Verify least-privilege IAM
- [ ] Verify read and write roles remain separated
- [ ] Verify no unintended sensitive-action wildcards
- [ ] Verify human approval cannot be bypassed
- [ ] Verify no raw credentials/secrets are committed or logged
- [ ] Verify managed secret/config references are used appropriately where needed
- [ ] Review project resources for unintended public/cross-account exposure
- [ ] Run agreed IaC/security scanning
- [ ] Document accepted findings with rationale

### 10.4 Cost Review

- [ ] Review actual project-created resource usage
- [ ] Estimate representative lab cost
- [ ] Identify primary cost drivers
- [ ] Verify unnecessary persistent resources were avoided
- [ ] Verify Budget/cost alert configuration
- [ ] Document cost controls and expected operating model

- [ ] **Phase 10 COMPLETE**

---

## Phase 11 — Destroy & Cost Verification

- [ ] Run planned Terraform teardown
- [ ] Confirm `terraform destroy` completes successfully
- [ ] Independently verify project-created resources in AWS
- [ ] Verify AgentCore resources are removed or intentionally retained/documented
- [ ] Verify Lambda resources are removed where applicable
- [ ] Verify API Gateway resources are removed if selected
- [ ] Verify EC2/network resources are removed
- [ ] Verify CloudWatch/logging resources according to retention plan
- [ ] Verify S3/resources according to retention plan
- [ ] Verify no unintended project-created billable resources remain
- [ ] Document any intentionally retained Terraform state/backend resources if applicable
- [ ] Review immediate Cost Explorer/billing signals where available
- [ ] Document teardown and independent verification procedure

- [ ] **Phase 11 COMPLETE**

---

## Phase 12 — Public GitHub Packaging & Documentation

### 12.1 README & Technical Documentation

- [ ] Write polished README
- [ ] Document business use case
- [ ] Document intended audience
- [ ] Document learning objectives
- [ ] Add "Why Agentic AI?" explanation
- [ ] Document architecture
- [ ] Document AgentCore components and responsibilities
- [ ] Document MCP contracts and integration
- [ ] Document deterministic diagnosis approach
- [ ] Document Observe/Diagnose/Remediate workflow
- [ ] Document security/IAM design
- [ ] Document observability
- [ ] Document failure scenarios
- [ ] Document testing
- [ ] Document cost
- [ ] Document deployment
- [ ] Document demo workflow
- [ ] Document teardown
- [ ] Document limitations
- [ ] Document important design decisions and lessons learned
- [ ] Include `terraform.tfvars.example`
- [ ] Include sanitized sample outputs where useful
- [ ] Add appropriate license

### 12.2 Professional Architecture Diagrams

Each diagram requires an editable source file plus PNG/SVG export. Use professional diagramming and official AWS architecture icons where applicable. Diagrams must show appropriate trust/security boundaries and remain synchronized with the implemented architecture.

- [ ] **Diagram 1 — High-level end-to-end solution architecture**
- [ ] **Diagram 2 — AWS network topology / VPC view**
- [ ] **Diagram 3 — AgentCore + MCP tool-call sequence / flow**
- [ ] **Diagram 4 — Observability / monitoring data-flow**
- [ ] **Diagram 5 — Observe → Diagnose → Remediate security / approval flow**
- [ ] Store editable diagram sources in `docs/diagrams/`
- [ ] Store PNG/SVG exports in `docs/diagrams/`
- [ ] Review diagrams against deployed Terraform and final implementation

### 12.3 Repository Sanitization & Public Readiness

- [ ] Scan full Git history for secrets
- [ ] Confirm no raw credentials/secrets in repository history
- [ ] Confirm example variable files contain placeholders only
- [ ] Sanitize account IDs and environment-specific identifiers from public-facing artifacts where appropriate
- [ ] Verify no Terraform state is committed
- [ ] Verify documentation links
- [ ] Verify setup/teardown instructions
- [ ] Review repository as an external reader
- [ ] Make repository public only after sanitization/readiness review passes

- [ ] **Phase 12 COMPLETE**

---

## Phase 13 — Career & Demo Packaging

### 13.1 Portfolio Demo

- [ ] Prepare 3–5 minute demonstration:
  - deploy/use intentionally broken environment
  - ask agent to diagnose
  - show tool selection
  - show deterministic AWS evidence
  - show diagnosis
  - show proposed remediation
  - show human approval
  - execute remediation
  - verify restored connectivity
  - show AgentCore/CloudWatch trace
- [ ] Prepare concise architecture explanation
- [ ] Prepare interview-ready project story

### 13.2 Career Materials

- [ ] Create 2–3 resume bullets focused on architecture, scope, security, automation, and measurable outcomes
- [ ] Prepare LinkedIn project summary/post
- [ ] Prepare GitHub project description
- [ ] Document Career Demonstration Matrix mapping project components to demonstrated skills
- [ ] Public demo video optional; prepare if it adds portfolio value

### 13.3 Existing GitHub Portfolio Audit

- [ ] Review existing GitHub repositories
- [ ] Classify each relevant repository:
  - Keep
  - Improve
  - Archive
  - Private
  - Delete
- [ ] Check secrets and external dependencies/links before archive/delete decisions
- [ ] Select strongest 4–6 repositories for pinned portfolio
- [ ] Position Agentic AWS Network Operations as a primary portfolio project
- [ ] Evaluate whether a GitHub profile README improves career positioning

- [ ] **Phase 13 COMPLETE**

---

## Final Project Completion Gate

- [ ] Foundation COMPLETE
- [ ] Phases 1–13 COMPLETE
- [ ] Functional/end-to-end testing completed
- [ ] Architecture review completed
- [ ] IAM/security review completed
- [ ] Cost and Budget controls validated
- [ ] Teardown independently verified
- [ ] No unintended project-created billable AWS resources remain
- [ ] Full secret/sanitization review passed
- [ ] All five professional diagrams completed and synchronized
- [ ] README and supporting documentation completed
- [ ] Public portfolio readiness review passed
- [ ] Existing GitHub portfolio audit completed
- [ ] Resume/LinkedIn/demo career materials prepared
- [ ] Important lessons learned and design decisions documented
- [ ] Final demo successfully completed

- [ ] **PROJECT COMPLETE**

---

*Last updated: 2026-08-28*
