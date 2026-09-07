# Local Development and Quality Checks

## Pinned foundation tools

- Python 3.13
- uv 0.12.7
- Terraform 1.5.7 (compatible range declared in `versions.tf`)
- TFLint 0.64.0 with AWS ruleset 0.48.0
- Python tools and transitive dependencies locked in `uv.lock`
- Checkov 3.3.15 isolated through `uvx`; see `docs/security/tooling-risk.md`

The local `uv` and `tflint` commands are installed in `~/bin`, which is already on the
shell PATH. Tool caches, virtual environments, Terraform provider caches, and TFLint
plugins are ignored by Git.

## Set up the local environment

```sh
uv sync --locked
terraform -chdir=terraform/environments/lab init -input=false
tflint --chdir=terraform/environments/lab --init
```

Initialization downloads dependencies but does not provision AWS resources. Never run
plan/apply or AWS-changing commands without the applicable project authorization.

## Fast checks

```sh
uv run ruff check .
uv run ruff format --check .
uv run mypy
uv run pytest
terraform fmt -check -recursive terraform
terraform -chdir=terraform/environments/lab validate
```

## Security and full checks

```sh
uv run bandit -c pyproject.toml -r src -q
uv run pip-audit
tflint --chdir=terraform/environments/lab
uvx --from checkov==3.3.15 checkov -d terraform --framework terraform --compact --quiet
uv run pre-commit run --all-files
```

GitHub Actions runs equivalent non-destructive checks with read-only repository
permissions and no AWS credentials. It never runs Terraform plan/apply or deployment.
