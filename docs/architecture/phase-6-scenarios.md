# Phase 6 Controlled Failure Scenarios

Phase 6 adds a single Terraform `scenario` variable that injects exactly one
deterministic failure into the existing Phase 4/5 network lab. It uses conditional
attributes/counts on the existing resources rather than duplicate modules. Switching
scenarios changes AWS configuration on apply (including creating a deny NACL rule and
deleting/recreating Terraform-managed peering route resources), so every non-healthy
scenario is an AWS mutation gated behind a later, separately authorized `terraform
apply`. IAM is not modified.

This document describes the local framework. Injecting a scenario against AWS still
requires a separately authorized `terraform plan`/`apply` during a controlled session.

## Scenario variable

- Variable: `scenario` in `terraform/environments/lab/variables.tf`.
- Default: `healthy` (the approved baseline).
- Validated allowed values: `healthy`, `broken_sg`, `broken_route`, `broken_nacl`,
  `broken_dns`, `broken_peering`.

The `scenario_effects` map in `terraform/environments/lab/locals.tf` translates the
selected value into deterministic toggles, exposed by the `active_scenario` output.

## Scenario matrix

| Scenario | Injection (how) | AWS mutation on apply | Deterministic root cause | Restore |
|---|---|---|---|---|
| `healthy` | Baseline: SG allows source CIDR, peering routes present, no deny NACL, cross-VPC DNS on | none (baseline) | none | n/a (default) |
| `broken_sg` | Destination TCP/443 ingress CIDR set to unroutable `192.0.2.0/32` | SG rule change (ingress CIDR mutated; rule not deleted) | Destination SG ingress does not match the approved source | Set `scenario=healthy` |
| `broken_route` | `enable_source_route=false` (return route kept) sets the source `aws_route` count to 0 | Deletes only the source->destination peering route resources | Missing source->destination peering route (one direction) | Set `scenario=healthy` (source routes recreated) |
| `broken_nacl` | Deny rule (number 90) added before allow rule (100) | Creates a new deny NACL rule (allow rule retained) | Destination NACL denies TCP/443 ingress | Set `scenario=healthy` (deny rule removed) |
| `broken_dns` | Local-only fixture flag `dns_fixture_broken=true` | none (no Route 53 / AWS resource) | Local DNS fixture unresolved | Set `scenario=healthy` |
| `broken_peering` | `enable_source_route=false`, `enable_destination_route=false`, and `enable_dns_resolution=false` | Deletes both route directions AND changes peering DNS-resolution options; peering connection retained | Peering path disabled (both route directions deleted + DNS off) | Set `scenario=healthy` (routes recreated, DNS re-enabled) |

Notes:

- `broken_route` disables only the source->destination direction (return route retained),
  giving a single-direction failure. `broken_peering` disables both directions and also
  disables `allow_remote_vpc_dns_resolution`, giving a distinct broader signature.
- Every non-healthy scenario is an AWS mutation and MUST pass a separately authorized
  apply gate before it is applied. This document and the local harness do not apply it.
- VPC endpoint failure testing is **not applicable**: no project VPC endpoints are
  deployed.
- Transit Gateway is **out of scope** for the peering MVP.

## Injection and restoration model

Each scenario is a pure function of the `scenario` input:

1. **Inject:** select `scenario=<value>`; `scenario_effects` sets the toggles; the
   modules render the single deterministic deviation.
2. **Diagnose:** deterministic AWS evidence (READ diagnostics / Reachability Analyzer)
   identifies the single injected root cause. Expected root causes are enumerated in the
   scenario matrix and in `scripts/phase6_scenario_harness.py`.
3. **Restore:** set `scenario=healthy`; every toggle returns to the approved baseline.
4. **Verify:** confirm the healthy signature and (during an authorized session) a healthy
   Reachability Analyzer result.

Because scenarios are attribute toggles on existing resources, switching between them is
reversible and creates/deletes no infrastructure.

## Local, offline harness

`scripts/phase6_scenario_harness.py` models the contract above without Terraform apply or
AWS access. It prints or emits JSON evidence for the `scenario -> diagnose -> restore ->
verify` lifecycle:

```text
uv run python scripts/phase6_scenario_harness.py           # human-readable, all scenarios
uv run python scripts/phase6_scenario_harness.py --json     # machine-readable evidence
uv run python scripts/phase6_scenario_harness.py --scenario broken_nacl
```

`tests/integration/test_phase6_scenarios.py` runs the same model under pytest and asserts
that each scenario has exactly one deterministic deviation (two for `broken_peering`),
maps to a root cause, and restores to the exact healthy baseline.

## Boundaries preserved

- No `terraform apply`, no AWS calls, and no IAM changes are performed by this framework
  or its harness. Applying any non-healthy scenario is an AWS-mutating action requiring a
  separate approval gate.
- The healthy configuration and all existing Phase 5 behavior are unchanged when
  `scenario=healthy` (the default).
- Scenario switching never deletes VPCs, subnets, the peering connection, workloads, or
  the Network Insights Path. It does delete/recreate the Terraform-managed peering
  **route** resources for `broken_route` and `broken_peering`, and create/remove the
  deny NACL rule for `broken_nacl`. Restoring `scenario=healthy` recreates the baseline.
