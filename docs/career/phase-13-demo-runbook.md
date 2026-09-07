# Phase 13 Demo Runbook

## Purpose

This runbook presents the project as a customer-facing network-operations solution:
observe deterministic facts, diagnose a connectivity issue, propose a bounded change,
obtain human approval, remediate narrowly, and verify the result.

The repository is currently torn down. The steps below are a reproducible future-demo
sequence, while the evidence links identify what has already been validated historically.

## Three-to-five-minute narrative

1. **Frame the customer problem (20–30 seconds).** Network incidents span routes,
   security groups, NACLs, and service telemetry. The operator needs an explainable,
   least-privilege workflow rather than an agent with unrestricted AWS access.
2. **Show the healthy topology (20–30 seconds).** Deploy the reviewed Terraform plan in
   `eu-west-1`, confirm the two private VPCs and peering routes, and verify the TCP/443 path.
3. **Inject one reversible failure (20–30 seconds).** Select one supported scenario:
   `broken_sg`, `broken_route`, or `broken_nacl`. Save the reviewed plan before applying.
4. **Ask the agent to diagnose (30–45 seconds).** Show contract validation, tool selection,
   Reachability Analyzer/configuration evidence, and the distinction between observed facts
   and recommendations.
5. **Show the proposed change (20–30 seconds).** The proposal is canonical, bounded, and
   tied to the exact resource context. Generic AWS execution is not available.
6. **Show human approval (20–30 seconds).** The authenticated approval boundary binds the
   decision to the request, scope, expiry, and replay protection. Rejection or expiry stops.
7. **Remediate and verify (30–45 seconds).** Apply only the approved allowlisted change,
   rerun read-only evidence, confirm the healthy path, and show Terraform drift status.
8. **Close with limitations (15–20 seconds).** Explain that the portfolio validation is
   bounded; trusted live approval, production observability, and full live remediation are
   not claimed unless separately redeployed and evidenced.

## Evidence to show

- [End-to-end architecture](../diagrams/01-end-to-end-solution-architecture.svg)
- [Network topology](../diagrams/02-aws-network-topology.svg)
- [AgentCore/MCP flow](../diagrams/03-agentcore-mcp-tool-flow.svg)
- [Observability flow](../diagrams/04-observability-evidence-flow.svg)
- [Approval/remediation flow](../diagrams/05-observe-diagnose-remediate-approval-flow.svg)
- [Phase 4 validation evidence](../evidence/phase-4-validation.md)
- [Phase 6 scenario evidence](../architecture/phase-6-scenarios.md)
- [Phase 8 bounded-validation status](../../PROJECT_STATUS.md)

## Safe demo rules

- Use a private repository and sanitized screenshots only.
- Tag every temporary resource and keep a written teardown scope.
- Never show account IDs, ARNs, credentials, public IPs, or unrelated resources.
- Do not imply that historical/deleted resources are currently deployed.
- Stop at every AWS, IAM, destructive, approval, commit, and push gate.
