# Agentic AWS Network Operations — Business Requirements & Learning Objectives

## 1. Purpose

The Agentic AWS Network Operations project demonstrates how generative and agentic AI can assist cloud and network engineers with AWS network operations while preserving deterministic diagnostics, least-privilege security, human control, observability, and cost awareness.

The project combines advanced AWS networking capabilities with Amazon Bedrock AgentCore, Model Context Protocol (MCP), Terraform, Python/Boto3, and AWS-native diagnostic and observability services.

The objective is not to replace network engineers or allow an LLM to make unsupported infrastructure decisions. The objective is to demonstrate a controlled operational assistant that gathers authoritative AWS evidence, correlates that evidence, explains likely root causes, recommends corrective action, and performs narrowly authorized remediation only after explicit human approval.

---

## 2. Business Problem

AWS network connectivity incidents can require engineers to manually inspect multiple services and configuration layers, including:

- VPCs and subnets
- Route tables
- Security groups
- Network ACLs
- Elastic network interfaces
- VPC endpoints
- DNS configuration
- VPC Flow Logs
- CloudWatch telemetry
- VPC Reachability Analyzer

Troubleshooting becomes more difficult as environments grow across accounts, VPCs, regions, and security boundaries.

The project will demonstrate how an agentic system can reduce this diagnostic burden by dynamically selecting appropriate diagnostic tools, collecting deterministic evidence from AWS, correlating the results, and presenting an understandable diagnosis and remediation recommendation.

---

## 3. Intended Users

Primary users:

- AWS Network Engineers
- Cloud Engineers
- Cloud Infrastructure Engineers
- Site Reliability Engineers
- DevOps / Platform Engineers
- Cloud and Solutions Architects

Secondary audiences:

- Security engineers reviewing network-related changes
- Technical leaders evaluating controlled AI-assisted operations
- Hiring managers evaluating practical AWS, networking, automation, and Agentic AI engineering skills

---

## 4. Primary Use Cases

### UC-1 — Observe Network State

An engineer asks the assistant to inspect relevant AWS network configuration and operational telemetry.

The assistant selects appropriate read-only MCP tools that expose controlled AWS network inspection capabilities backed by AWS APIs and Python/Boto3, and returns structured evidence without changing infrastructure.

### UC-2 — Diagnose Connectivity Failure

An engineer provides a connectivity problem such as a source that cannot reach a destination.

The assistant uses deterministic AWS evidence such as configuration APIs, VPC Reachability Analyzer, Flow Logs, and CloudWatch telemetry to determine the likely root cause.

The LLM must not invent or guess network reachability facts.

### UC-3 — Explain Root Cause

The assistant translates deterministic technical evidence into an understandable explanation showing:

- observed symptom
- relevant AWS evidence
- identified or likely root cause
- affected network component
- recommended corrective action

Observed facts must remain distinguishable from AI-generated interpretation or recommendation.

### UC-4 — Propose Controlled Remediation

When an approved remediation exists, the assistant proposes the specific infrastructure change and expected impact.

No write operation occurs automatically.

### UC-5 — Human-Approved Remediation

An authorized human explicitly approves or denies the proposed remediation.

Only an approved action may invoke separately authorized WRITE tooling.

After execution, the system reruns appropriate diagnostics to verify that the expected network state or connectivity has been restored.

### UC-6 — Audit Operational Activity

Operators can trace a representative interaction from:

user request → agent → MCP/tool invocation → AWS evidence → diagnosis → recommendation → approval/denial → remediation → verification.

Observable execution data must be captured without claiming access to hidden model chain-of-thought.

---

## 5. Learning Objectives

By completing this project, demonstrate the ability to:

### LO-1 — Build an Agentic AWS Operations Workflow

Implement an operational agent using Amazon Bedrock AgentCore that can dynamically select and invoke appropriate tools rather than relying on a fixed troubleshooting script.

### LO-2 — Integrate MCP with AWS Network Operations

Design and implement standardized MCP tool contracts that allow the agent to securely invoke controlled AWS network inspection, deterministic diagnostic, telemetry, and remediation capabilities, using AgentCore Gateway as the managed integration boundary where appropriate.

### LO-3 — Combine Deterministic Networking Evidence with Generative AI

Use AWS-native deterministic evidence—including VPC Reachability Analyzer, AWS configuration APIs, Flow Logs, and CloudWatch telemetry—to establish network facts while using the LLM for correlation, explanation, and recommendation.

### LO-4 — Implement Secure Human-Controlled Automation

Demonstrate separation between READ diagnostic tools and WRITE remediation tools, least-privilege IAM, explicit human approval, controlled blast radius, and post-remediation verification.

### LO-5 — Demonstrate Production-Oriented Engineering Practices

Apply Terraform, structured logging, tracing, observability, testing, security review, cost controls, documentation, repeatable teardown, and professional architecture documentation to create a portfolio-quality reference implementation.

---

## 5a. Agentic AI / AgentCore Justification

An agent-based architecture is chosen over a scripted or workflow-orchestrated approach
for the following specific reasons:

- **Dynamic tool selection.** Network failures do not follow a single linear diagnostic
  path. An agent can reason about which diagnostic tools to invoke in what order based
  on intermediate evidence, rather than executing a predetermined script that may waste
  time or miss relevant signals.

- **Cross-service evidence correlation.** A diagnosis often requires combining outputs
  from multiple independent AWS services (e.g., Reachability Analyzer path result,
  security group rule set, route table entries, NACL rules). An agent can hold and
  reason across these evidence fragments within a session in a way that a simple tool
  chain cannot do adaptively.

- **Explainable diagnosis based on deterministic evidence.** The LLM is used to
  interpret and explain facts established by deterministic AWS APIs and services.
  The diagnosis is grounded in authoritative evidence; the agent's role is
  correlation and explanation, not invention. Observed facts remain distinguishable
  from AI-generated interpretation.

- **Human-controlled remediation.** The agent architecture enforces a hard separation
  between READ diagnostic tooling and WRITE remediation tooling. No remediation
  action can occur without an explicit, auditable human approval signal. This is a
  structural property of the design, not a runtime policy that can be bypassed by
  a prompt.

---

## 6. Success Criteria

The project is successful when it can demonstrate an end-to-end workflow in which:

1. Terraform creates a small, controlled AWS network lab.
2. A known network failure can be introduced intentionally.
3. The agent receives a natural-language troubleshooting request.
4. The agent selects appropriate diagnostic MCP tools.
5. Deterministic AWS evidence identifies or supports the actual root cause.
6. The assistant explains the evidence and recommends an appropriate corrective action.
7. Infrastructure is not modified without explicit human approval.
8. An approved remediation uses separately authorized WRITE tooling.
9. The system reruns diagnostics and verifies the expected recovery.
10. The complete observable workflow can be traced through AgentCore/CloudWatch
    telemetry using a consistent correlation or session ID that is present in all
    relevant log records for a single interaction (request → tool calls → diagnosis
    → approval/denial → remediation → verification).
11. The environment can be cleanly destroyed and independently checked for unintended billable resources.
12. The repository contains sufficient documentation, tests, security controls, and architecture diagrams to explain and reproduce the project.

---

## 7. MVP Scope

The MVP will include:

- Small Terraform-managed AWS network lab
- Healthy baseline connectivity
- Three required MVP failure classes:
  - Security group misconfiguration blocking expected traffic
  - Route table misconfiguration preventing reachability
  - Network ACL rule blocking expected traffic
- VPC endpoint and DNS failure scenarios are conditional/advanced, subject to
  Phase 2 architecture decisions
- Transit Gateway and VPC peering failure scenarios are conditional on those
  components being selected in Phase 2
- Read-only AWS network diagnostic tools
- Core MCP contracts defined in the project checklist
- Amazon Bedrock AgentCore Runtime
- AgentCore Gateway
- AgentCore Identity/IAM
- AgentCore Observability
- VPC Reachability Analyzer
- VPC Flow Logs where a defined diagnostic scenario benefits from traffic-level
  evidence not sufficiently established by configuration APIs or Reachability
  Analyzer alone, subject to Phase 2 cost and design review
- Natural-language diagnosis based on deterministic evidence
- Separate READ and WRITE authorization paths
- Explicit, auditable human approval or denial interaction before any remediation
  write operation; the implementation mechanism (CLI, API, UI, webhook, or other)
  is deferred to Phase 2
- Post-remediation verification
- Structured logging and correlation IDs
- CloudWatch operational visibility
- Cost controls and teardown verification
- Minimum MVP test coverage:
  - Healthy baseline: agent correctly reports no failure on unmodified infrastructure
  - Each implemented failure scenario: agent diagnosis matches the known root cause
  - Approval path: an approved remediation executes and post-remediation verification
    confirms recovery
  - Denial path: a denied remediation produces no infrastructure write side effects
- Detailed testing strategy and additional test coverage remain Phase 10 scope

---

## 8. Advanced / Stretch Scope

The following capabilities may be added only after the MVP works end-to-end:

- Multi-agent specialization
- AgentCore Memory
- API Gateway external/demo entry point
- Additional network failure scenarios
- Transit Gateway troubleshooting
- VPC peering troubleshooting
- Cross-account diagnostics
- Multi-region diagnostics
- Additional security/policy analysis
- Additional MCP tools
- More advanced automated testing
- Expanded dashboards and operational analytics

Stretch capabilities must not delay or destabilize the MVP.

---

## 9. Security Guardrails

The project must follow these principles:

- AI reasoning does not equal authorization.
- Diagnostic READ permissions and remediation WRITE permissions must remain separated.
- Least-privilege IAM must be used.
- Remediation requires an explicit, auditable human approval or denial interaction.
  The implementation mechanism is deferred to Phase 2.
- The agent must not self-approve remediation.
- Denied remediation must produce no infrastructure write side effects.
- Secrets and raw credentials must not be committed or exposed in logs.
- Terraform state and sensitive variable files must not be committed.
- Public-facing repository artifacts must be sanitized before publication.
- Remediation tools must have defined scope and blast-radius limitations.

---

## 10. Cost Guardrails

The project is designed as a short-lived learning and portfolio environment.

Requirements:

- Prefer consumption-based/serverless services where practical.
- Avoid NAT Gateway by default unless architecture requires and justifies it.
- Avoid OpenSearch Serverless unless a later requirement clearly justifies it.
- Avoid unnecessary load balancers and persistent compute.
- Use minimal test endpoints.
- Evaluate Transit Gateway and other hourly-cost resources before deployment.
- Configure budget/cost monitoring.
- Record project-created resources during implementation.
- Destroy temporary infrastructure after testing.
- Independently verify that no unintended billable project resources remain.

---

## 11. Portfolio Objective

The completed project should demonstrate the intersection of:

- Advanced AWS networking
- Infrastructure as Code
- Python/Boto3 automation
- Amazon Bedrock AgentCore
- Model Context Protocol
- Agentic AI architecture
- Deterministic network diagnostics
- IAM and responsible automation
- Human-in-the-loop remediation
- Cloud observability
- Testing and engineering discipline
- FinOps awareness
- Architecture documentation and technical communication

The project should be presented as a production-oriented reference architecture and portfolio implementation rather than claiming enterprise production readiness without corresponding scale and operational testing.

---

## 12. Phase 1 Definition of Done

Phase 1 is complete when:

- Business problem is documented.
- Intended users are identified.
- Primary use cases are documented.
- Five measurable learning objectives are defined.
- Agentic AI / AgentCore justification is documented, covering dynamic tool
  selection, cross-service evidence correlation, explainable diagnosis based on
  deterministic evidence, and human-controlled remediation.
- Success criteria are defined.
- MVP and stretch scope are separated.
- Security guardrails are documented.
- Cost guardrails are documented.
- Portfolio audience and objective are documented.
- Requirements are independently reviewed for material omissions or contradictions.
- Requirements are approved before Phase 2 architecture design begins.