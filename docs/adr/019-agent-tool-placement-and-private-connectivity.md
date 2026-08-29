# ADR 019 — Agent/Tool Placement and Private Connectivity

## Status
Accepted

## Context
The agent needs authoritative AWS control-plane evidence but does not need a direct
TCP path to the private test workloads. VPC-attaching AgentCore Runtime or Lambda would
introduce endpoint, DNS, ENI, and possible NAT requirements without serving an MVP
traffic requirement.

## Decision

- Keep managed AgentCore Runtime outside both project workload VPCs.
- Use managed AgentCore Gateway as the MCP integration and policy boundary.
- Use one non-VPC diagnostic Lambda target exposing the nine READ tools.
- Use one separate non-VPC remediation Lambda target exposing only approved WRITE
  tools.
- Use IAM/SigV4 inbound authorization for the native MVP client.
- Require distinct least-privilege diagnostic and remediation execution roles.
- Create no VPC endpoints in the peering MVP because neither private workload nor
  agent/tool execution has a demonstrated private AWS-service access requirement.

## Consequences
The architecture separates the agentic control plane, network data plane, and evidence
plane. Lambda reaches AWS service APIs without NAT or workload-VPC endpoints. Gateway
tool authorization and AWS IAM remain independent controls.

Reevaluate VPC attachment and PrivateLink only if a later requirement introduces a
private VPC client, private MCP server/API/database, private IdP, or the TGW shared-
services variant. Any such change requires a new architecture, endpoint, IAM, DNS,
cost, and security review.

## References

- [AgentCore VPC connectivity](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/agentcore-vpc.html)
- [AgentCore Gateway core concepts](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/gateway-core-concepts.html)
- [AgentCore interface VPC endpoints](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/vpc-interface-endpoints.html)
