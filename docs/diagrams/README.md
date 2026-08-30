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
