"""Approval persistence seam for local Phase 8 tests and a future DynamoDB adapter."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from threading import Lock
from typing import Any, Protocol


@dataclass(frozen=True)
class ConsumeResult:
    """Atomic approval-claim outcome."""

    status: str
    record: Mapping[str, Any] | None = None


class ApprovalRepository(Protocol):
    """Persistence contract intentionally independent from AWS or remediation execution."""

    def save(self, record: Mapping[str, Any]) -> None: ...

    def get(self, approval_id: str) -> Mapping[str, Any] | None: ...

    def consume(self, approval_id: str, execution_id: str, now: datetime) -> ConsumeResult: ...

    def record_execution_result(
        self, approval_id: str, execution_id: str, result: Mapping[str, Any]
    ) -> None: ...


class InMemoryApprovalRepository:
    """Thread-safe test fake; no durability or production authorization is implied."""

    def __init__(self) -> None:
        self.records: dict[str, dict[str, Any]] = {}
        self._lock = Lock()

    def save(self, record: Mapping[str, Any]) -> None:
        with self._lock:
            approval_id = str(record["approval_id"])
            if approval_id in self.records:
                raise ValueError("approval_id already exists")
            self.records[approval_id] = dict(record)

    def get(self, approval_id: str) -> Mapping[str, Any] | None:
        with self._lock:
            record = self.records.get(approval_id)
            return dict(record) if record else None

    def consume(self, approval_id: str, execution_id: str, now: datetime) -> ConsumeResult:
        with self._lock:
            record = self.records.get(approval_id)
            if record is None:
                return ConsumeResult("NOT_FOUND")
            if record.get("execution_id") == execution_id:
                return ConsumeResult("REPLAY_SAME_EXECUTION", dict(record))
            if record.get("execution_id") is not None:
                return ConsumeResult("REPLAY_DIFFERENT_EXECUTION", dict(record))
            if record.get("decision") != "APPROVED":
                return ConsumeResult("NOT_APPROVED", dict(record))
            expires_at = datetime.fromisoformat(str(record["expires_at"]).replace("Z", "+00:00"))
            if now >= expires_at:
                return ConsumeResult("EXPIRED", dict(record))
            record["execution_id"] = execution_id
            record["execution_status"] = "EXECUTING"
            record["consumed"] = True
            return ConsumeResult("CLAIMED", dict(record))

    def record_execution_result(
        self, approval_id: str, execution_id: str, result: Mapping[str, Any]
    ) -> None:
        with self._lock:
            record = self.records.get(approval_id)
            if record is None or record.get("execution_id") != execution_id:
                raise ValueError("execution does not own approval")
            record["execution_status"] = str(result.get("status", "FAILED")).upper()
            record["execution_result"] = dict(result)
