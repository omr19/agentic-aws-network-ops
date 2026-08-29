# Phase 7 Deterministic Diagnosis Foundation

This local-only foundation correlates normalized READ evidence; it does not call AWS, Terraform, IAM, deployment, or remediation/write tooling. The workflow is implemented in `src/agentic_aws_network_ops/diagnostics/deterministic.py` and deliberately does not duplicate the Phase 6 scenario model.

## Workflow

1. Accept a normalized evidence object using `schemas/diagnostic/normalized-evidence.schema.json`.
2. Validate the common correlation, region, timestamp, completeness, and Reachability Analyzer fields.
3. Preserve Reachability Analyzer and configuration/API observations as facts.
4. Correlate a completed reachability result with configuration facts using a closed set of deterministic signatures.
5. Return a diagnosis result using the existing result-envelope shape, with diagnosis data separated into `observed_facts`, `root_cause`, and advisory `recommendations`.
6. Return no-finding/healthy when a completed Reachability Analyzer result finds a path and no blocker is observed.
7. Return no root-cause claim for incomplete, unsupported, or conflicting evidence.

The result contract is defined in `schemas/diagnostic/diagnosis-result.schema.json`. Recommendations are descriptive only; this module has no AWS client, Terraform, IAM, or write-tool dependency.

## Supported failure classes

| Classification | Required deterministic evidence | Stable root-cause identifier | Human-readable explanation |
|---|---|---|---|
| `security_group_mismatch` | Unreachable result plus observed SG source CIDR differs from the approved expected CIDR | `destination_security_group_ingress_does_not_match_source` | Destination SG ingress does not match the approved source |
| `missing_route` | Unreachable result plus source-to-destination route absent and return route present | `missing_source_to_destination_peering_route` | A required peering route is missing |
| `nacl_restriction` | Unreachable result plus observed destination TCP/443 deny rule | `destination_nacl_denies_tcp_443_ingress` | Destination NACL denies the tested traffic |
| `peering_path_dns_failure` | Unreachable result plus both peering route directions absent and both DNS options false | `peering_path_disabled_both_route_directions_and_dns` | The peering path is disabled by routes and DNS options |

The local DNS fixture remains a Phase 6 concern and is not silently inferred as an AWS DNS failure by this workflow. It can be represented as a future normalized evidence extension only when its local-only provenance is explicit.

## Healthy, incomplete, and conflicting evidence

Healthy evidence is `status=succeeded`, `path_found=true`, and no contradictory blocker. It returns `status=no_finding`, classification `healthy`, a null root cause, observed facts, and no recommendation.

Pending, failed, partial, or missing configuration evidence returns `status=no_finding` with classification `indeterminate`, an `INCOMPLETE_EVIDENCE` error, and no root-cause claim. A completed healthy reachability result combined with a blocking configuration fact returns `invalid_request` with `CONFLICTING_EVIDENCE`. Multiple independent blockers also return `invalid_request`; the workflow never silently chooses one.

## Evidence and recommendation boundary

`observed_facts` are direct normalized observations, such as `path_found=false`, a route absence, an NACL rule number, or DNS options. `recommendations` are bounded advisory text, such as restoring the approved route or SG CIDR. Recommendations are not evidence and are never executable actions.

## Tests and limitations

`tests/unit/test_deterministic_diagnosis.py` covers healthy no-finding, all four implemented AWS failure classes, tracked Phase 6 SG/route/NACL/peering fixtures, incomplete evidence, conflicting evidence, unsupported claims, and repeatability. Schema tests cover closed-world normalized input.

Limitations:

- The workflow diagnoses only the four implemented AWS failure classes; it does not query AWS or infer facts absent from normalized input.
- Reachability Analyzer is correlated but not treated as sufficient by itself for a root-cause claim when configuration evidence is incomplete.
- Multiple blockers are reported as conflicting rather than ranked.
- Flow Logs and CloudWatch metrics are not yet required inputs for this foundation and remain separate Phase 7 checklist work.
- A future adapter may expose this as a read-only contract, but adding it to the MCP/Gateway allowlist is outside this local foundation task.
