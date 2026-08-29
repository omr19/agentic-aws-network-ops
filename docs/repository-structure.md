# Repository Structure

This Phase 3 scaffold separates infrastructure, application logic, contracts, tests,
fixtures, automation, and documentation without implementing later-phase behavior.

```text
.
├── .kiro/
│   ├── specs/agentic-aws-network-ops/   # Approved Kiro Spec
│   └── steering/                        # Persistent repository governance
├── docs/
│   ├── adr/                             # Architecture decision records
│   ├── architecture/                    # Architecture design documentation
│   └── diagrams/                        # Editable diagram sources and exports
├── schemas/
│   ├── common/                          # Shared result-envelope schemas
│   ├── diagnostic/                      # Nine READ contract schemas
│   └── remediation/                     # Three narrow WRITE contract schemas
├── scripts/                             # Non-destructive development/validation helpers
├── src/agentic_aws_network_ops/
│   ├── adapters/                        # Thin Lambda/Gateway adapters
│   ├── agent/                           # Agent orchestration and prompts
│   ├── approval/                        # Human-approval domain logic
│   ├── diagnostics/                     # Framework-independent READ logic
│   ├── remediation/                     # Framework-independent narrow WRITE logic
│   └── shared/                          # Typed shared models/utilities
├── terraform/
│   ├── environments/lab/                # Single-engineer MVP root configuration
│   └── modules/                         # Responsibility-based reusable modules
└── tests/
    ├── contract/                        # Schema and boundary tests
    ├── fixtures/events/                 # Saved Gateway/Lambda events
    ├── integration/                     # Controlled integration tests
    └── unit/                            # Stubber-based tests without live AWS calls
```

Empty scaffold directories contain `.gitkeep` files until their authorized phase adds
implementation. Terraform state, real variable files, credentials, secrets, generated
plans, caches, and runtime artifacts remain excluded from Git.

## Boundary rules

- `src/` contains shared logic and thin adapters; it does not contain Terraform.
- `schemas/` is the version-controlled source for strict MCP inputs and outputs.
- Routine `tests/unit/` and `tests/contract/` require no live AWS credentials or calls.
- `tests/integration/` may contact AWS only in an explicitly authorized phase/session.
- `terraform/environments/lab/` is the only MVP root; local state is never committed.
- `terraform/modules/` module boundaries and interfaces are finalized in the dedicated
  Phase 3 Terraform foundation task.
- `scripts/` must default to non-destructive behavior and must not embed credentials.
- `docs/diagrams/` will contain editable diagrams.net sources and reviewed SVG/PNG exports.
