# Phase 8 Remediation IAM Foundation

`iam/phase8/remediation-write-permissions.json` is an unattached local policy fixture for the narrow Phase 8 remediation role. It is not created, attached, simulated, or used against AWS.

## Allowlist

The fixture allows only:

- `ec2:AuthorizeSecurityGroupIngress` on the exact Terraform-managed destination security group.
- `ec2:CreateRoute` and `ec2:ReplaceRoute` on the exact source and destination project route tables.
- `ec2:ReplaceNetworkAclEntry` on the exact Terraform-managed destination network ACL.

Every statement is constrained to `eu-west-1` and Terraform-managed project tags (`Project`, `Environment`, and `ManagedBy`). VPC conditions further constrain the security-group and NACL resources. The exact TCP/443 ports, `10.10.0.0/16` source CIDR, approved peering target, route destinations, NACL rule number, and DNS behavior are not model-selectable IAM inputs; they are resolved by the immutable remediation manifest and bound into the approved proposal described by [ADR 022](../adr/022-mvp-remediation-write-tools.md) and [ADR 021](../adr/021-human-approval-binding-and-replay-protection.md).

The policy intentionally contains no delete/revoke, peering-lifecycle, DNS, NACL deletion, IAM, Lambda, Flow Logs, EC2 lifecycle, NAT/IGW, endpoint, TGW, or arbitrary write capability. IAM is one independent enforcement layer; approval binding, AgentCore policy, manifest validation, preflight READ checks, and post-action verification remain required.

The placeholder resource IDs are expected to be supplied only by a separately approved deployment design. This fixture does not authorize the existing diagnostic or Runtime identities and does not mark Phase 8 complete.
