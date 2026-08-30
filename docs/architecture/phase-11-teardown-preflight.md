# Phase 11 Read-Only Teardown and Cost-Verification Preflight

**Status:** Read-only preflight complete; Phase 11 teardown and cost-verification gates remain unchecked.

**Scope:** This document reconciles the local Terraform state, repository evidence, and the read-only inventory captured for the approved `eu-west-1` lab. It authorizes no Terraform, AWS, IAM, Lambda, AgentCore, deletion, lifecycle, or billing mutation. It does not claim that teardown has started or that Phase 11 is complete.

## Reconciled inventory

### Terraform-managed state

The local state contains **49 entries**: one AMI data source and **48 managed state entries**. The 48 managed entries comprise:

- **35 Phase 4 baseline resources:** two VPCs, four private subnets, four route tables, four route associations, four peering routes, one VPC peering connection plus its options, two custom NACLs, four NACL rules, two restricted default security groups, two workload security groups, two workload security-group rules, two stopped `t3.nano` instances, and one Terraform-managed TCP/443 Network Insights Path. The EC2 root volumes are part of the instance resources and are separately verified as encrypted 8-GiB gp3 volumes.
- **13 Phase 8 readiness resources:** two Lambda functions, two seven-day CloudWatch log groups, one on-demand DynamoDB approval table, two Lambda execution roles, and six inline IAM role policies.

The current state addresses are authoritative for the planned Terraform teardown scope. The AMI lookup is a data source and is not deleted.

### Separately managed Phase 5 resources

The following resources are outside the Terraform state and require a separate cleanup decision and sequence:

- Diagnostic Lambda: `agentic-aws-network-ops-phase5-diagnostic`.
- Diagnostic Lambda log group: `/aws/lambda/agentic-aws-network-ops-phase5-diagnostic`.
- Diagnostic IAM role: `agentic-aws-network-ops-lab-diagnostic`.
- AgentCore Gateway IAM role: `agentic-aws-network-ops-lab-gateway`.
- AgentCore Gateway and its diagnostic target, tagged with `Project=agentic-aws-network-ops`.
- AgentCore Runtime: `agentic_aws_network_ops_p5_runtime`, retained in historical deployment evidence.
- Runtime IAM role and the manually managed runtime artifact bucket:
  `agentic-aws-network-ops-runtime-<account-id>-euw1`.
- Runtime object: `phase5/runtime.zip`.

The installed AWS CLI lacks the AgentCore control-plane service used by the historical deployment. Gateway and Runtime deletion therefore require a supported AgentCore console/API inspection before any cleanup approval.

### Manually retained Network Insights analyses

The current read-only inventory reports **nine tagged Network Insights analyses** attached to the managed TCP/443 path:

- `nia-047eca8b3d26e8c95` — historical healthy path.
- `nia-005a1a2272b6a2e7f` — healthy verification.
- `nia-0cc05f549fcde9b4b` — broken security group.
- `nia-0afa1ed55ee3d3e48` — broken route.
- `nia-094eade4bb9570b79` — healthy verification.
- `nia-05f2614fb24465d89` — broken NACL.
- `nia-0b7d2658a0871259b` — healthy verification / broken NACL.
- `nia-0b5e03873a017a35b` — broken peering.
- `nia-0fb430275079c0202` — healthy verification / broken peering.

These records are not Terraform-managed. They are retained validation artifacts and must be explicitly included or excluded from cleanup. Analysis records must be handled before the managed Network Insights Path is deleted.

### Temporary resources and intentional retention

Phase 7 evidence records the temporary Flow Logs, delivery/provisioner roles, temporary log group, and observability role as deleted. The current tag inventory did not find those resources. The two stopped EC2 instances, their encrypted root volumes, the Terraform baseline, the Phase 5 resources, and the Phase 8 resources were retained for subsequent project phases or the separately gated demonstration workflow.

The nine current analyses are not covered by the historical “temporary path deleted” statement; their current presence is now explicitly recorded as a Phase 11 cleanup decision.

## Documentation reconciliation

The following repository inconsistencies are resolved by this preflight without rewriting historical evidence:

| Previous statement | Reconciled interpretation |
|---|---|
| “35 Terraform-managed resources” | 35 refers to the Phase 4 baseline. Current state is 48 managed entries: 35 Phase 4 plus 13 Phase 8. |
| “One retained healthy-path analysis” | Current inventory contains nine tagged analyses. All nine are listed above and require an explicit cleanup decision. |
| “No AgentCore Runtime/Gateway deployed” | Superseded for current inventory purposes by later deployment evidence and tagged Gateway evidence. Gateway, diagnostic Lambda, Runtime evidence, IAM roles, and the S3 artifact are separately managed; current Runtime/Gateway status still needs a supported control-plane read. |
| Historical temporary-analysis cleanup record | It remains valid for the specific temporary path then deleted, but does not establish absence of the nine analyses currently returned by read-only inventory. |
| Phase 11 status | Phase 11 is a read-only preflight only. No checklist item or Phase 11 completion gate is checked. |

RDS and CloudFormation inventory remains unverified where the current operator role lacks the required read permissions. This preflight makes no account-wide absence claim for those services.

## Cost and retention considerations

- The two stopped `t3.nano` instances avoid active compute charges but their two encrypted 8-GiB gp3 root volumes continue to incur storage charges.
- Network Insights analyses have one-time charges; the older `$0.20` record must not be treated as a current billing total now that nine retained analyses are identified. Exact billing requires Cost Explorer or billing evidence and may lag resource activity.
- Phase 8 Lambda functions, seven-day log groups, and the on-demand DynamoDB table can incur invocation, log-storage, table/storage, or request charges.
- The Phase 5 diagnostic Lambda and its seven-day log group remain separately managed; the log group currently contains retained bytes.
- The Runtime S3 bucket retains a Standard-storage `phase5/runtime.zip` artifact of approximately 14.8 MB.
- AgentCore Runtime/Gateway usage and retained control-plane resources require service-specific billing verification.
- VPCs, subnets, route tables, security groups, NACLs, and the peering connection are not expected to create standing hourly charges under the documented MVP design, but their deletion must still be verified.
- No project Budget/cost-alert configuration was verified.
- Billing data may arrive after resource deletion. Capture immediate Cost Explorer/billing signals, record the account’s billing lag, and perform a later follow-up check before considering cost verification complete.

Keep local Terraform state and its backup private until post-teardown verification and billing review finish. They contain infrastructure identifiers and are ignored by Git; they must not be committed.

## Pre-deletion evidence to capture

Capture and sanitize the following before any destructive approval:

1. Account, Region, timestamp, selected project/environment scope, and operator identity.
2. Terraform state address list, managed-entry count, outputs, and the exact approved destroy scope.
3. EC2 instance state showing both instances stopped; volume encryption, size, attachment, and tags.
4. VPCs, subnets, route tables, routes, NACLs, security groups, and active peering.
5. Managed TCP/443 Network Insights Path plus all nine analysis IDs, tags, statuses, and results.
6. Phase 8 Lambda configuration, log retention, DynamoDB billing/TTL settings, and dedicated IAM roles/policies.
7. Phase 5 diagnostic Lambda, log group, IAM roles, AgentCore Gateway/target status, Runtime status, and Runtime IAM role.
8. Runtime S3 bucket and object metadata.
9. Current Cost Explorer/billing signals and any retained-resource charges.

Do not store credentials, secrets, raw logs, unrelated resources, or unsanitized account data in tracked evidence.

## Exact proposed teardown order

This is a plan only. It was not executed during the preflight.

1. Freeze the environment and obtain explicit approval for the exact account, Region, resource list, and whether Phase 5 AgentCore/S3 resources are included.
2. Preserve the pre-deletion evidence above and confirm no further demonstration or validation run is required.
3. Delete the nine manually retained Network Insights analyses first, then verify each analysis is absent. Do not delete the managed path while dependent analyses remain.
4. Review the exact Terraform destroy plan in the approved environment and execute the destructive Terraform teardown only after separate approval. The intended scope is the 48 managed entries, not the AMI data source or unrelated resources.
5. Verify Terraform-managed EC2, EBS, VPC, network, Network Insights Path, Phase 8 Lambda, log, DynamoDB, IAM-role, and IAM-policy resources are absent.
6. Using the supported AgentCore control plane, delete the Runtime first, then the Gateway target, then the Gateway; verify each dependency is absent before deleting its dedicated IAM role.
7. Delete the separately managed Phase 5 diagnostic Lambda and log group, then delete its IAM role after confirming no other function uses it.
8. Confirm the Runtime artifact is no longer needed, delete the S3 object, empty the bucket, and delete the bucket. Verify both object and bucket absence.
9. Run independent service-specific and tag-based inventory checks for EC2, EBS, VPC/networking, Network Insights, Lambda, Logs, DynamoDB, IAM, S3, AgentCore, RDS, CloudFormation, and other approved service categories.
10. Capture immediate Cost Explorer/billing signals, document expected billing lag, and schedule the delayed billing follow-up.
11. Keep local state/backup private until resource and billing verification are complete; document any intentionally retained local backend/state artifacts.

## Independent post-teardown verification checklist

- [ ] Resource Groups Tagging API returns no project-tagged resources, except explicitly documented retained resources.
- [ ] No project EC2 instances or EBS volumes remain.
- [ ] Both project VPCs, subnets, route tables, routes, NACLs, security groups, and peering are absent.
- [ ] The managed Network Insights Path and all nine analyses are absent.
- [ ] Phase 8 Lambda functions, log groups, DynamoDB table, IAM roles, and inline policies are absent.
- [ ] Phase 5 diagnostic Lambda, log group, IAM roles, Gateway, Gateway target, and Runtime are absent or intentionally retained and documented.
- [ ] Runtime S3 object and bucket are absent or intentionally retained and documented.
- [ ] No unintended project-tagged billable resources remain.
- [ ] Immediate and delayed billing/Cost Explorer checks are recorded, including billing lag.
- [ ] Local Terraform state/backend retention is documented and remains private.
- [ ] Phase 11 checklist items are checked only after the corresponding destructive action and independent verification are actually complete.

## Current preflight decision

Phase 11 remains **not complete**. Destructive teardown is blocked pending explicit approval of the reconciled resource scope, resolution of AgentCore control-plane access, and a decision about the nine retained analyses and separately managed Phase 5 resources.
