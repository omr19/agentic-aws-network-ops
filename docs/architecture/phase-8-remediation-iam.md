# Phase 8 Remediation IAM Foundation

`iam/phase8/remediation-write-permissions.json` remains an unattached local fixture for
the write boundary. `iam/phase8/remediation-read-permissions.json` is the offline
representation of the deployed and verified read policy; its sanitized live verification
is recorded in [`docs/evidence/phase-8/remediation-read-iam-verification.json`](../evidence/phase-8/remediation-read-iam-verification.json).
Neither fixture is itself attached or deployed by local validation.

## Allowlist

The fixture allows only:

- `ec2:AuthorizeSecurityGroupIngress` on the exact Terraform-managed destination security group.
- `ec2:CreateRoute` and `ec2:ReplaceRoute` on the exact source and destination project route tables.
- `ec2:ReplaceNetworkAclEntry` on the exact Terraform-managed destination network ACL.

Every statement is constrained to `eu-west-1` and Terraform-managed project tags (`Project`, `Environment`, and `ManagedBy`). VPC conditions further constrain the security-group and NACL resources. The exact TCP/443 ports, `10.10.0.0/16` source CIDR, approved peering target, route destinations, NACL rule number, and DNS behavior are not model-selectable IAM inputs; they are resolved by the immutable remediation manifest and bound into the approved proposal described by [ADR 022](../adr/022-mvp-remediation-write-tools.md) and [ADR 021](../adr/021-human-approval-binding-and-replay-protection.md).

The write policy intentionally contains no delete/revoke, peering-lifecycle, DNS, NACL deletion, IAM, Lambda, Flow Logs, EC2 lifecycle, NAT/IGW, endpoint, TGW, or arbitrary write capability. The separate read fixture allows only `ec2:DescribeSecurityGroups`, `ec2:DescribeRouteTables`, and `ec2:DescribeNetworkAcls` with `Resource = "*"` and `aws:RequestedRegion = eu-west-1`; it contains no write or unrelated actions. IAM is one independent enforcement layer; approval binding, AgentCore policy, manifest validation, preflight READ checks, and post-action verification remain required.

The placeholder resource IDs are expected to be supplied only by a separately approved deployment design. This fixture does not authorize the existing diagnostic or Runtime identities and does not mark Phase 8 complete.
