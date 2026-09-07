# Development Tooling Risk Record

## Checkov 3.3.15 isolation

As of 2026-08-28, current Checkov 3.3.15 hard-pins `asteval==1.0.6`, which has
published advisories with a fixed version that Checkov cannot yet accept. It also
depends transitively on `ecdsa==0.19.2`, for which the reported advisory has no fixed
release available.

Checkov is therefore excluded from the project/runtime dependency environment and
`uv.lock`. The pre-push hook invokes exact-version Checkov through an isolated `uvx`
environment only for static Terraform scanning. Neither affected library is imported by
project code, packaged for Lambda/AgentCore, or present in the routine test environment.

This is a narrow temporary acceptance for a development-only scanner. Reevaluate the
pin during dependency updates and move Checkov into the locked quality environment when
its dependency constraints permit patched versions. Checkov findings are still reviewed;
this isolation does not suppress or skip the IaC scan.
