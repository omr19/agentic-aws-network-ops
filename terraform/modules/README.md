# Terraform Module Conventions

Modules are organized by infrastructure responsibility rather than by individual AWS
resource. The initial MVP boundaries are:

- `vpc/` — one reusable private VPC boundary, subnets, route tables, baseline NACLs,
  security groups, and optional controlled-session Flow Logs.
- `vpc_peering/` — the replaceable interconnect boundary containing peering and only
  the routes required between the two VPC modules.
- `test_workload/` — short-lived private TCP/443 endpoints used to verify connectivity.

The peering module must not own VPCs or workloads. This preserves the post-MVP option to
replace only the interconnect with a separate TGW configuration/state.

Each implemented module will use `main.tf`, `variables.tf`, `outputs.tf`, and
`versions.tf`. Inputs must be typed and described, validation must reject unsupported
scope, outputs must be non-sensitive unless explicitly marked, and provider
configuration must remain in the root rather than inside child modules.

Resource implementation belongs to Phase 4. These Phase 3 directories document module
ownership only and intentionally contain no AWS resource blocks.
