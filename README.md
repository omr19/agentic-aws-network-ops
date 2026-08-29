# agentic-aws-network-ops
Agentic AI for intelligent AWS network operations, diagnostics, and remediation.

Phase 2 architecture and Phase 3 foundation are complete. **Phase 4 — AWS Network Lab**
is deployed and has deterministic healthy TCP/443 and blocked TCP/80 evidence. See the
[Phase 4 validation report](docs/evidence/phase-4-validation.md),
[Phase 2 design](docs/architecture/phase-2-design.md), [ADRs](docs/adr/README.md),
[project checklist](PROJECT_CHECKLIST.md), and [current status](PROJECT_STATUS.md).

## Review the deployed AWS lab

The Phase 4 environment remains deployed in `eu-west-1` for the next project phases.
To understand it before continuing, review these files in order:

1. [`docs/architecture/phase-2-design.md`](docs/architecture/phase-2-design.md) — approved architecture and security boundaries.
2. [`terraform/environments/lab/main.tf`](terraform/environments/lab/main.tf) — composition of the deployed lab.
3. [`terraform/modules/vpc/main.tf`](terraform/modules/vpc/main.tf) — private VPCs, subnets, routes, and NACLs.
4. [`terraform/modules/vpc_peering/main.tf`](terraform/modules/vpc_peering/main.tf) — VPC peering and bidirectional routes.
5. [`terraform/modules/test_workload/main.tf`](terraform/modules/test_workload/main.tf) — two private `t3.nano` test endpoints and TCP/443 security groups.
6. [`docs/evidence/phase-4-validation.md`](docs/evidence/phase-4-validation.md) — deployment inventory, healthy/blocked results, tagging, IAM diagnostic, costs, and cleanup.
7. [`docs/evidence/phase-4-results.json`](docs/evidence/phase-4-results.json) — sanitized machine-readable results.

The active baseline consists of two VPCs, four private subnets, VPC peering, supporting
routes/security controls, two running private `t3.nano` instances with encrypted 8-GiB
gp3 root volumes, and one retained TCP/443 Network Insights Path/analysis. It has no
public IPs, Internet Gateway, NAT Gateway, VPC endpoint, Transit Gateway, load balancer,
or enabled Flow Logs.

Stopping the two EC2 instances pauses compute charges but prevents the live TCP/443 lab
from operating; EBS storage charges continue while the volumes exist. Termination and
Terraform destroy require explicit approval and belong to the governed cleanup path.
