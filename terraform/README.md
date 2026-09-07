# Terraform

`environments/lab/` is the single-engineer MVP root configuration. It owns provider and
backend configuration, fixed approved topology values, environment-level inputs, module
composition, and root outputs. Real `.tfvars`, state, plans, and `.terraform/` data stay
local and untracked; `.terraform.lock.hcl` is tracked.

`modules/` contains responsibility-based reusable infrastructure boundaries. Child
modules declare requirements but do not configure providers or backends. Environment
roots may call modules; modules must not call environment roots.

Naming uses `snake_case` for Terraform identifiers and stable lowercase-hyphenated AWS
names derived from project, environment, and responsibility. Every project resource
must inherit ownership/cost tags. Outputs expose only values needed by composition,
verification, or later approved tooling.

No Terraform plan/apply or AWS resource implementation is part of these conventions.
