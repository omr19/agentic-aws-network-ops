"""Contract test that manifest-resolved proposals validate as closed-world JSON."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from jsonschema import Draft202012Validator, FormatChecker  # type: ignore[import-untyped]

from agentic_aws_network_ops.remediation.workflow import create_proposal, request_hash

ROOT = Path(__file__).parents[2]
SCHEMA = json.loads((ROOT / "schemas/remediation/proposal.schema.json").read_text())


def test_manifest_resolved_proposal_matches_contract() -> None:
    request = {
        "schema_version": "1.0.0",
        "scenario_id": "route_table_entry",
        "approval_id": str(uuid4()),
        "request_hash": "",
        "correlation_id": str(uuid4()),
        "policy_session_id": str(uuid4()),
    }
    request["request_hash"] = request_hash(request)
    proposal = create_proposal(
        request=request,
        action="restore_vpc_peering_route",
        evidence=[{"fact": "Approved routes are absent."}],
        proposed_at=datetime(2026, 9, 4, tzinfo=UTC),
    )
    Draft202012Validator(SCHEMA, format_checker=FormatChecker()).validate(proposal)
