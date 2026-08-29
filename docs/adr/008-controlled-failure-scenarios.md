# ADR 008 — Controlled Failure Scenarios

## Status
Accepted

## Decision
Provide a healthy baseline plus reversible broken-security-group, broken-route, and
broken-NACL scenarios. Endpoint and DNS scenarios remain optional; TGW and peering
failures beyond the required peering-route scenario are outside the MVP.

The primary path is a short-lived private source workload in the Source VPC to a
short-lived private destination workload in the Destination VPC on TCP/443. Both VPCs
must contain the required forward and return peering routes.

- Healthy: routing, NACLs, and the destination security group permit the flow.
- Broken SG: the destination security group does not permit TCP/443 from the approved
  Source VPC/subnet scope.
- Broken route: one required peering route is missing or deliberately incorrect.
- Broken NACL: a destination-subnet NACL rule blocks TCP/443 or required return traffic.

## Consequences
Each scenario needs known evidence, diagnosis, remediation, verification, and reset.
Reachability Analyzer supplies configured-path evidence; VPC Flow Logs provide
complementary ACCEPT/REJECT evidence during controlled tests.
