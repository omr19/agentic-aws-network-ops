# ADR 018 — Post-MVP Transit Gateway Evolution

## Status
Accepted as a post-MVP enhancement

## Context
The two-VPC peering MVP is the lowest-cost path to proving the full AgentCore/MCP
diagnosis and remediation workflow. Transit Gateway provides stronger enterprise
networking learning only when the design exercises multi-VPC hub routing,
segmentation, associations, propagation, and transitive connectivity.

## Decision
Complete, test, document, and tear down the two-VPC peering MVP before authorizing a
separate three-VPC Transit Gateway variant. The TGW variant will reuse VPC, workload,
agent, MCP, observability, approval, and test modules while replacing the interconnect.

The planned variant contains application, shared-services/operations, and isolated/test
VPCs with multiple TGW route tables. It will demonstrate route-table association,
propagation, segmentation, missing-route, and blackhole-route scenarios.

The enterprise extension may also include a Site-to-Site VPN or Direct Connect
attachment representing an on-premises network. This would support AWS-to-on-premises
route diagnosis while keeping the customer network outside Terraform's control boundary.

The analyzer strategy is complementary: Route Analyzer evaluates Transit Gateway
route-table decisions between VPC, VPN, Direct Connect, and other TGW attachments; it
does not inspect VPC route tables, security groups, NACLs, or customer-gateway settings.
Reachability Analyzer remains useful for supported static, hop-by-hop path analysis but
does not send packets or prove data-plane health. VPC Flow Logs and CloudWatch provide
observed traffic evidence when live delivery is available.

TGW diagnostic contracts will be evaluated for gateway, attachment, route-table,
association, propagation, VPN/Direct Connect attachment, and route inspection. Exact
schemas, IAM permissions, on-premises test ranges, and evidence requirements must be
approved before implementation.

## Cost and deployment consequences
TGW is not continuously deployed. Use a separate deployable configuration and separate
Terraform state from the peering lab. Deploy it for a controlled learning/demo window,
capture sanitized evidence, destroy it, and independently verify attachment removal.
Stopping test compute does not stop TGW attachment-hour charges.

The TGW enhancement must not delay completion of the peering MVP and requires a fresh
architecture, cost, IAM, and implementation authorization gate.
