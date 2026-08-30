# Architecture Diagrams

This directory will contain editable diagrams.net (`.drawio`) sources and reviewed
SVG or PNG exports for the five diagrams approved in Phase 2. Diagram implementation
and finalization remain governed by their later checklist phases.

## Phase 12 diagram set

Each diagram has an editable diagrams.net source and a same-named SVG export:

1. `01-end-to-end-solution-architecture` — high-level AgentCore, MCP, evidence, approval, and remediation boundaries.
2. `02-aws-network-topology` — the approved private two-VPC topology, peering routes, healthy TCP/443 path, and reversible failure scenarios.
3. `03-agentcore-mcp-tool-flow` — native invocation, Gateway/MCP READ flow, approval gates, bounded WRITE flow, and fail-closed branches.
4. `04-observability-evidence-flow` — sanitized observable events and deterministic evidence inputs, with deferred production telemetry marked explicitly.
5. `05-observe-diagnose-remediate-approval-flow` — evidence, recommendation, human authorization, policy/IAM gates, bounded remediation, and verification.

Blue nodes/rows represent approved architecture or validated local contracts. Amber nodes/rows represent historical/deleted resources or deferred/bounded capabilities. The diagrams intentionally use logical names and CIDRs only; they contain no account IDs, ARNs, credentials, tokens, raw screenshots, or unrelated identifiers.

The diagrams describe the approved/reproducible MVP while noting that AWS resources are currently torn down after Phase 11. They do not claim current deployment, live AgentCore Policy/interceptor enforcement, live remediation, production observability, or project-specific zero billing. The repository remains private and controlled sharing is the intended Phase 12 model.

## How to read the end-to-end flow

The primary journey begins with the **Operator** in diagram 01 and follows the arrows:

1. The operator submits a bounded network-diagnostics request.
2. AgentCore Runtime validates the request and selects an approved READ operation.
3. AgentCore Gateway applies the MCP boundary and forwards the call to the diagnostic Lambda.
4. The Lambda gathers deterministic AWS evidence: configuration, routes, security controls,
   Reachability Analyzer results, metrics, or controlled Flow Logs.
5. The agent correlates evidence and reports observed facts, likely cause, confidence, and limitations.
6. If a WRITE action is appropriate, a human decision and independent policy/IAM gates are required.
7. The narrowly scoped change is verified and the sanitized result is recorded for review.

## Diagram-specific flow summaries

### 01 — End-to-end solution architecture

Operator → AgentCore Runtime → AgentCore Gateway → diagnostic Lambda → AWS evidence APIs
→ evidence correlation. A separate approval branch reaches remediation only after explicit authorization.

### 02 — AWS network topology

Source EC2/subnet → source route table → VPC peering → destination route table → destination
subnet/security controls → destination EC2. Scenario toggles remove one control at a time and restore it.

The hierarchy is **AWS Region `eu-west-1` → two VPCs → Availability Zones `eu-west-1a` and
`eu-west-1b` → private subnets → route tables and security controls → EC2 workloads**. The
two VPCs use non-overlapping CIDRs (`10.10.0.0/16` and `10.20.0.0/16`) and communicate only
through the approved peering routes.

### 03 — AgentCore and MCP tool flow

User request → contract validation → Gateway/MCP selection → approved READ tool → diagnostic
result envelope. Invalid or unauthorized requests terminate in the fail-closed branch.

### 04 — Observability and evidence flow

Network event/request → deterministic service evidence → sanitized structured event → correlation
and explanation → retained evidence artifact. Deferred production telemetry remains labeled as such.

### 05 — Observe, diagnose, remediate, approval flow

Observe → diagnose → propose → human approve/reject → policy/IAM gates → narrow remediation
→ post-change verification → recorded result. Rejection, expiry, replay, or failed gates stop the write.

These summaries explain the arrows without claiming deferred live remediation or production telemetry.
