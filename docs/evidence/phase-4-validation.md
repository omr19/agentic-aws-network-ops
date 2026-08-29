# Phase 4 Network Validation Evidence

## Evidence status

- Validation date: 2026-08-28 (America/Chicago), 2026-08-29 (UTC)
- AWS Region: `eu-west-1`
- Environment: `lab`
- Evidence classification: sanitized portfolio evidence
- Terraform result: 35 resources added, zero changed, zero destroyed
- Post-apply drift result: no changes

This report records reproducible outcomes without account IDs, ARNs, credentials,
temporary session data, or environment-specific resource IDs. Terraform state remains
local and ignored.

Machine-readable sanitized results are available in
[`phase-4-results.json`](phase-4-results.json).

## Tool versions

| Tool | Validated version |
|---|---|
| Terraform | 1.5.7 (`darwin_arm64`) |
| HashiCorp AWS provider | 6.62.0 |
| TFLint | 0.64.0 |
| TFLint AWS ruleset | 0.48.0 |
| Checkov | 3.3.15, isolated from project dependencies |
| Python | 3.13.15 |
| uv | 0.12.7 |
| Ruff | 0.16.5 |
| mypy | 2.3.1 |
| pytest | 9.1.1 |

## Validation command and result matrix

Commands are shown in reproducible form; environment-specific profile and resource
identifiers are intentionally omitted.

| Validation | Reproducible command or API | Recorded result |
|---|---|---|
| Terraform formatting | `terraform fmt -check -recursive terraform` | Passed |
| Terraform configuration | `terraform -chdir=terraform/environments/lab validate` | Passed |
| Terraform lint | `tflint --chdir=terraform/environments/lab` | Passed |
| IaC security | `checkov -d terraform --framework terraform` | 73 passed, zero failed, four documented skips |
| Python tests | `uv run pytest` | Seven passed |
| Python lint | `uv run ruff check .` | Passed |
| Python typing | `uv run mypy` | Passed for eight source/test files |
| Plan review | `terraform plan -out=<ignored-plan>` | 35 add, zero change, zero destroy |
| Deployment | `terraform apply <reviewed-plan>` | 35 added, zero changed, zero destroyed |
| Drift review | `terraform plan -detailed-exitcode` | Exit 0; no changes |
| EC2 health | `ec2:DescribeInstanceStatus` | Both system and instance checks `ok` |
| Live application path | Sanitized Source console output | `network-lab healthy tcp/443` |
| Healthy deterministic path | `ec2:StartNetworkInsightsAnalysis` | Succeeded; path found |
| Blocked deterministic path | Temporary tagged TCP/80 analysis | Succeeded; path not found |
| IAM authorization | `iam:SimulatePrincipalPolicy` | Five Tiros actions allowed after approved correction |
| Evidence hygiene | Link, diff, secret, account-ID, ARN, and resource-ID scans | Passed |

The four Checkov skips apply to the two short-lived endpoints: detailed EC2 monitoring
is intentionally disabled to avoid unnecessary cost, and no IAM instance role is
attached because the workloads call no AWS API. Encryption, IMDSv2, private addressing,
restricted security groups, and explicit tags remain enforced.

## Deployed baseline

The healthy baseline contains:

- Source VPC `10.10.0.0/16`
- Destination VPC `10.20.0.0/16`
- Two private subnets per VPC across two Availability Zones
- Same-Region VPC peering and explicit bidirectional routes
- Restricted workload security groups and stateless NACL rules
- One private Source and one private Destination `t3.nano` endpoint
- No public IP, Internet Gateway, NAT Gateway, endpoint, TGW, or load balancer
- VPC Flow Logs disabled for this validation window

### Reviewed Terraform resource inventory

| Resource type | Count |
|---|---:|
| VPC | 2 |
| Private subnet | 4 |
| Private route table | 4 |
| Route-table association | 4 |
| VPC peering connection and options | 2 |
| Bidirectional peering route | 4 |
| Custom NACL | 2 |
| NACL rule | 4 |
| Restricted default security group | 2 |
| Workload security group | 2 |
| Workload security-group rule | 2 |
| Private EC2 endpoint | 2 |
| Managed TCP/443 Network Insights Path | 1 |
| **Total Terraform-managed resources** | **35** |

The AMI lookup is a Terraform data source and is not included in the managed-resource
count. EBS root volumes are created as part of the two EC2 resources and are explicitly
encrypted, tagged, and deleted with their instances.

All taggable resources use at least:

```text
Project     = agentic-aws-network-ops
Environment = lab
ManagedBy   = terraform | validation
```

## Healthy TCP/443 result

Two independent methods confirmed the approved path:

1. The Source endpoint's console evidence recorded `network-lab healthy tcp/443` after
   reaching the private Destination HTTPS service.
2. A tagged Reachability Analyzer run completed with:

```json
{
  "destination_port": 443,
  "protocol": "tcp",
  "status": "succeeded",
  "path_found": true
}
```

Both endpoints subsequently passed EC2 system and instance health checks. A refreshed
Terraform plan reported no drift.

## Intentionally blocked TCP/80 result

A separate temporary tagged Network Insights Path tested an unapproved destination
port without changing the healthy infrastructure. Its single analysis completed with:

```json
{
  "destination_port": 80,
  "protocol": "tcp",
  "status": "succeeded",
  "path_found": false
}
```

AWS returned these deterministic explanation classes:

| Direction | Evidence code | Meaning |
|---|---|---|
| Source egress | `ENI_SG_RULES_MISMATCH` | The Source security group permits only the approved TCP/443 egress path. |
| Source egress | `SUBNET_ACL_RESTRICTION` | The Source NACL default-denies unapproved TCP/80 egress. |
| Destination ingress | `ENI_SG_RULES_MISMATCH` | The Destination security group permits only approved TCP/443 ingress. |
| Destination ingress | `SUBNET_ACL_RESTRICTION` | The Destination NACL default-denies unapproved TCP/80 ingress. |

This demonstrates the project's deterministic-diagnosis principle: AWS evidence—not an
LLM inference—established both the reachable and blocked results.

### Healthy-versus-blocked comparison

| Test | TCP/443 approved path | TCP/80 unapproved path |
|---|---|---|
| Analysis status | `succeeded` | `succeeded` |
| Path found | `true` | `false` |
| Live workload evidence | HTTPS probe succeeded | Not required; configured-path analysis used |
| Security-group result | Approved rules match | Source egress and Destination ingress mismatch |
| NACL result | Approved forward/return rules match | Source egress and Destination ingress default-deny |
| Infrastructure mutation | None during analysis | None during analysis |

## IAM validation note

The first healthy-path analysis exposed a missing Reachability Analyzer caller
permission. Read-only policy inspection and simulation showed that the existing role
allowed `ec2:StartNetworkInsightsAnalysis` but implicitly denied AWS's Tiros query
actions. With explicit approval, only the following actions were added to the existing
inline role policy:

```text
tiros:CreateQuery
tiros:ExtendQuery
tiros:GetQueryAnswer
tiros:GetQueryExplanation
tiros:GetQueryExtensionAccounts
```

IAM simulation confirmed those five actions before the analysis was retried. No
service-linked role or additional managed policy was created.

| IAM check | Before correction | After correction |
|---|---|---|
| `ec2:StartNetworkInsightsAnalysis` | Allowed | Allowed |
| Five Tiros query actions | `implicitDeny` | Allowed |
| Permissions boundary | None | None |
| Reachability Analyzer service-linked role | Absent; not required for this same-account path | Not created |

## Cost evidence

- Two `t3.nano` instances and two encrypted 8-GiB gp3 volumes accrue usage while active.
- Two Reachability Analyzer runs add an expected total one-time charge of `$0.20`.
- The VPC peering connection has no hourly attachment charge.
- No NAT Gateway, TGW, public IPv4 address, Flow Logs, or load balancer cost was added.
- Exact compute and storage charges will be recorded when billing data becomes available.

## Resource and tagging verification

- Exactly four project subnets were independently returned by the project tag filter.
- Both EC2 endpoints were running with private addresses and no public IP addresses.
- Both root volumes were encrypted, in use, 8 GiB, and explicitly project-tagged.
- VPCs, subnets, route tables, NACLs, security groups, instances, volumes, peering, the
  managed path, and both analyses were discoverable using project tags where supported.
- Individual routes, route-table associations, NACL rules, and peering options do not
  support independent tags; Terraform state and their tagged parents establish ownership.

## Cleanup status

- The Terraform-managed healthy environment remains active for Phase 4 completion and
  subsequent project phases.
- The successful TCP/443 analysis remains as tagged evidence.
- After evidence capture and explicit authorization, the temporary TCP/80 analysis was
  deleted first and its dependent temporary path was then deleted successfully.
- Independent lookups confirmed both temporary identifiers no longer exist.
- A post-cleanup Terraform plan reported no changes, both endpoints remained healthy,
  and the managed TCP/443 path and successful analysis remained present.
- Deleting an analysis record does not reverse its one-time charge.

## Evidence limitations

- Console output and Reachability Analyzer establish the tested paths at the recorded
  time; they are not a substitute for continuous monitoring.
- Flow Logs were intentionally disabled, so no observed packet-log evidence was
  collected during this run.
- Resource IDs are intentionally omitted from this Git-tracked report. Authoritative
  IDs remain in ignored Terraform state and live AWS inventory.
- Failure-scenario injection belongs to Phase 6 and was not performed here.
