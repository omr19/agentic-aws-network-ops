# ADR 002 — Network Topology

## Status
Accepted

## Decision
Use two dedicated project VPCs connected by same-Region VPC peering:

- Source VPC: `10.10.0.0/16`
- Destination VPC: `10.20.0.0/16`
- Two private `/24` subnets per VPC across two Availability Zones
- No public subnets, public IP addresses, NAT Gateway, or Internet Gateway dependency
- Short-lived private test workloads for the defined TCP/443 path

The peering connection and explicit routes in both VPCs form the replaceable
interconnect layer. Transit Gateway is excluded from the initial MVP deployment but is
an approved post-MVP architecture evolution described by ADR 018.

## Consequences
Two VPCs provide an authentic removable peering route for the required route-failure
scenario; the immutable local VPC route would not. Separating VPC/workload modules from
the interconnect permits a later TGW variant without rewriting the agentic platform.
