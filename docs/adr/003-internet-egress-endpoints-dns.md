# ADR 003 — Internet Egress, Endpoints, and DNS

## Status
Accepted with open details

## Decision
Do not deploy NAT Gateway by default. Prefer selective VPC endpoints for required AWS
services. Keep DNS support and hostnames enabled. Add arbitrary internet egress only
for a demonstrated requirement.

## Consequences
This lowers standing cost and exposure. Exact endpoint requirements depend on final
Agent/tool component placement. The initial private test workloads require no arbitrary
internet egress; any endpoint must be justified by an actual AWS-service access path.
