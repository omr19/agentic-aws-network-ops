# ADR 022 — MVP Remediation WRITE Tools

## Status
Accepted

## Decision
The MVP exposes exactly three remediation MCP tools:

1. `restore_security_group_ingress`
2. `restore_vpc_peering_route`
3. `restore_network_acl_entry`

Failure injection and complete scenario reset remain Terraform responsibilities. No
generic AWS command or arbitrary configuration tool is permitted.

## Tool boundaries

### `restore_security_group_ingress`

May call only `ec2:AuthorizeSecurityGroupIngress` to restore TCP/443 from
`10.10.0.0/16` on the exact Terraform-managed destination security group. It cannot
change egress, delete/revoke rules, use another port/CIDR/group, or modify a default
security group. An already-present rule returns `already_healthy` without a write.

### `restore_vpc_peering_route`

May call only `ec2:CreateRoute` or `ec2:ReplaceRoute` for these mappings:

- Source project route table: `10.20.0.0/16` to the exact project peering connection
- Destination project route table: `10.10.0.0/16` to the exact project peering connection

It cannot delete routes, change associations, use default/public routes or another
target, create route tables, or change the peering lifecycle.

### `restore_network_acl_entry`

May call only `ec2:ReplaceNetworkAclEntry` to restore the fixed Terraform-defined
ingress rule on the exact destination project NACL: TCP/443 from `10.10.0.0/16` with
action `ALLOW`. It cannot choose arbitrary rule numbers, directions, ports, CIDRs, or
NACLs; delete entries; change associations; or modify a default NACL.

## Remediation manifest and input

Terraform injects an immutable, non-secret remediation manifest into the remediation
Lambda configuration. It maps each scenario to exact project resource IDs, expected
CIDRs, ports/protocols, peering target, NACL rule, and required tags.

The model-controlled input is limited to:

```json
{
  "scenario_id": "approved-enum",
  "approval_id": "uuid",
  "request_hash": "sha256",
  "correlation_id": "uuid",
  "policy_session_id": "uuid"
}
```

The Lambda resolves and validates the complete change against the manifest. The human
proposal displays that complete resolved change before approval.

## IAM and prohibitions

The remediation role's separate WRITE policy receives only:

- `ec2:AuthorizeSecurityGroupIngress`
- `ec2:CreateRoute`
- `ec2:ReplaceRoute`
- `ec2:ReplaceNetworkAclEntry`

A separate READ policy is required for preflight and verification: `ec2:DescribeSecurityGroups`,
`ec2:DescribeRouteTables`, and `ec2:DescribeNetworkAcls`. It does not broaden the WRITE
boundary and is scoped to `Resource = "*"` with `aws:RequestedRegion = eu-west-1`.

Use exact resource ARNs, project tags, `eu-west-1`, and supported EC2 condition keys
where AWS supports them. Where an EC2 action lacks resource-level permissions, combine
the minimum action with applicable conditions, Policy default-deny, approval binding,
interceptor validation, and manifest validation.

The role receives no IAM, role assumption, delete, peering-lifecycle, public-route,
NAT/IGW, EC2-instance, AgentCore, Lambda-configuration, Flow Logs, endpoint, DNS, TGW,
or out-of-project WRITE capability.

## Execution and verification

Each tool performs a READ preflight, confirms ownership/manifest match, validates and
atomically consumes approval, executes at most one correction, reruns relevant READ
diagnostics and Reachability Analyzer where applicable, reports verification, and
emits an explicit Terraform-drift/reconciliation warning.

## References

- [EC2 actions, resources, and condition keys](https://docs.aws.amazon.com/service-authorization/latest/reference/list_ec2.html)
- [VPC peering route configuration](https://docs.aws.amazon.com/vpc/latest/peering/vpc-peering-routing.html)
- [ReplaceNetworkAclEntry API](https://docs.aws.amazon.com/AWSEC2/latest/APIReference/API_ReplaceNetworkAclEntry.html)
