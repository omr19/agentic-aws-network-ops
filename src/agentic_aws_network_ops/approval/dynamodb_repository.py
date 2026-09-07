"""Mockable DynamoDB implementation of the Phase 8 approval repository."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any, cast

from boto3.dynamodb.types import TypeDeserializer, TypeSerializer  # type: ignore[import-untyped]
from botocore.exceptions import BotoCoreError, ClientError  # type: ignore[import-untyped]

from .repository import ApprovalRepository, ConsumeResult


class DynamoDBApprovalError(ValueError):
    """Fail-closed persistence error with a safe category for callers/tests."""

    def __init__(self, message: str, *, code: str, retryable: bool) -> None:
        super().__init__(message)
        self.code = code
        self.retryable = retryable


class DynamoDBApprovalRepository(ApprovalRepository):
    """Persist approval state with conditional, single-owner transitions.

    The client is deliberately injected as a boto3-style low-level DynamoDB
    client. This class never creates a session or client and is therefore fully
    mockable with a fake client or botocore Stubber.
    """

    _RETRYABLE_CODES = frozenset(
        {
            "InternalServerError",
            "ProvisionedThroughputExceededException",
            "RequestLimitExceeded",
            "ServiceUnavailable",
            "ThrottlingException",
            "TransactionInProgressException",
        }
    )

    def __init__(self, client: Any, *, table_name: str) -> None:
        if not table_name:
            raise ValueError("table_name is required")
        self._client = client
        self._table_name = table_name
        self._serializer = TypeSerializer()
        self._deserializer = TypeDeserializer()

    def save(self, record: Mapping[str, Any]) -> None:
        self._required_id(record, "approval_id")
        item = self._to_item(record)
        self._client_call(
            "put_item",
            TableName=self._table_name,
            Item=item,
            ConditionExpression="attribute_not_exists(approval_id)",
        )

    def get(self, approval_id: str) -> Mapping[str, Any] | None:
        approval_id = self._validate_id(approval_id, "approval_id")
        response = self._client_call(
            "get_item",
            TableName=self._table_name,
            Key={"approval_id": self._serializer.serialize(approval_id)},
            ConsistentRead=True,
        )
        item = response.get("Item")
        if not item:
            return None
        return self._from_item(item)

    def consume(self, approval_id: str, execution_id: str, now: datetime) -> ConsumeResult:
        approval_id = self._validate_id(approval_id, "approval_id")
        execution_id = self._validate_id(execution_id, "execution_id")
        if now.tzinfo is None:
            raise ValueError("now must be timezone-aware")

        current = self.get(approval_id)
        outcome = self._classify(current, execution_id, now)
        if outcome is not None:
            return outcome

        key = {"approval_id": self._serializer.serialize(approval_id)}
        values = {
            ":execution_id": self._serializer.serialize(execution_id),
            ":executing": self._serializer.serialize("EXECUTING"),
            ":true": self._serializer.serialize(True),
            ":approved": self._serializer.serialize("APPROVED"),
            ":false": self._serializer.serialize(False),
            ":now": self._serializer.serialize(self._timestamp(now)),
        }
        try:
            response = self._client.update_item(
                TableName=self._table_name,
                Key=key,
                UpdateExpression=(
                    "SET execution_id = :execution_id, "
                    "execution_status = :executing, consumed = :true"
                ),
                ConditionExpression=(
                    "decision = :approved AND consumed = :false "
                    "AND attribute_not_exists(execution_id) AND expires_at > :now"
                ),
                ExpressionAttributeValues=values,
                ReturnValues="ALL_NEW",
            )
        except ClientError as error:
            if self._error_code(error) == "ConditionalCheckFailedException":
                winner = self.get(approval_id)
                classified = self._classify(winner, execution_id, now)
                if classified is not None:
                    return classified
                return ConsumeResult("NOT_FOUND")
            self._raise_client_error("UpdateItem", error)
        except BotoCoreError as error:
            raise DynamoDBApprovalError(
                "DynamoDB UpdateItem failed", code="BOTOCORE_ERROR", retryable=True
            ) from error

        item = response.get("Attributes")
        if not item:
            raise DynamoDBApprovalError(
                "DynamoDB claim returned no state", code="INVALID_RESPONSE", retryable=False
            )
        return ConsumeResult("CLAIMED", self._from_item(item))

    def record_execution_result(
        self, approval_id: str, execution_id: str, result: Mapping[str, Any]
    ) -> None:
        approval_id = self._validate_id(approval_id, "approval_id")
        execution_id = self._validate_id(execution_id, "execution_id")
        current = self.get(approval_id)
        if current is None:
            raise ValueError("approval does not exist")
        if current.get("execution_id") != execution_id:
            raise ValueError("execution does not own approval")
        existing = current.get("execution_result")
        supplied = dict(result)
        if existing is not None:
            if dict(existing) == supplied:
                return
            raise ValueError("execution result already recorded differently")

        status = str(supplied.get("status", "FAILED")).upper()
        try:
            self._client.update_item(
                TableName=self._table_name,
                Key={"approval_id": self._serializer.serialize(approval_id)},
                UpdateExpression="SET execution_status = :status, execution_result = :result",
                ConditionExpression="execution_id = :execution_id",
                ExpressionAttributeValues={
                    ":status": self._serializer.serialize(status),
                    ":result": self._serializer.serialize(supplied),
                    ":execution_id": self._serializer.serialize(execution_id),
                },
            )
        except ClientError as error:
            if self._error_code(error) == "ConditionalCheckFailedException":
                raise ValueError("execution does not own approval") from error
            self._raise_client_error("UpdateItem", error)
        except BotoCoreError as error:
            raise DynamoDBApprovalError(
                "DynamoDB UpdateItem failed", code="BOTOCORE_ERROR", retryable=True
            ) from error

    def _client_call(self, operation: str, **kwargs: Any) -> dict[str, Any]:
        try:
            response = getattr(self._client, operation)(**kwargs)
        except ClientError as error:
            if (
                operation == "put_item"
                and self._error_code(error) == "ConditionalCheckFailedException"
            ):
                raise ValueError("approval_id already exists") from error
            self._raise_client_error(operation, error)
        except BotoCoreError as error:
            raise DynamoDBApprovalError(
                f"DynamoDB {operation} failed", code="BOTOCORE_ERROR", retryable=True
            ) from error
        return cast(dict[str, Any], response)

    def _to_item(self, record: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
        item: dict[str, dict[str, Any]] = {}
        for key, value in record.items():
            if key == "execution_id" and value is None:
                continue
            item[str(key)] = self._serializer.serialize(value)
        if "consumed" not in item:
            item["consumed"] = self._serializer.serialize(False)
        if "execution_status" not in item:
            item["execution_status"] = self._serializer.serialize("PENDING")
        expires_at = record.get("expires_at")
        if not isinstance(expires_at, str):
            raise ValueError("expires_at is required")
        expiry = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
        if expiry.tzinfo is None:
            raise ValueError("expires_at must be timezone-aware")
        item["ttl_epoch"] = self._serializer.serialize(int(expiry.timestamp()))
        return item

    def _from_item(self, item: Mapping[str, Any]) -> dict[str, Any]:
        record = {str(key): self._deserializer.deserialize(value) for key, value in item.items()}
        record.setdefault("execution_id", None)
        record.setdefault("execution_result", None)
        return record

    @staticmethod
    def _classify(
        record: Mapping[str, Any] | None, execution_id: str, now: datetime
    ) -> ConsumeResult | None:
        if record is None:
            return ConsumeResult("NOT_FOUND")
        owner = record.get("execution_id")
        if owner == execution_id:
            return ConsumeResult("REPLAY_SAME_EXECUTION", record)
        if owner is not None:
            return ConsumeResult("REPLAY_DIFFERENT_EXECUTION", record)
        if record.get("decision") != "APPROVED":
            return ConsumeResult("NOT_APPROVED", record)
        expires_at = datetime.fromisoformat(str(record["expires_at"]).replace("Z", "+00:00"))
        if now >= expires_at:
            return ConsumeResult("EXPIRED", record)
        return None

    @staticmethod
    def _required_id(record: Mapping[str, Any], field: str) -> str:
        return DynamoDBApprovalRepository._validate_id(record.get(field), field)

    @staticmethod
    def _validate_id(value: object, field: str) -> str:
        if not isinstance(value, str) or not value:
            raise ValueError(f"{field} is required")
        return value

    @staticmethod
    def _timestamp(value: datetime) -> str:
        return value.astimezone(UTC).isoformat().replace("+00:00", "Z")

    @staticmethod
    def _error_code(error: ClientError) -> str:
        return str(error.response.get("Error", {}).get("Code", "AWS_ERROR"))

    def _raise_client_error(self, operation: str, error: ClientError) -> None:
        code = self._error_code(error)
        raise DynamoDBApprovalError(
            f"DynamoDB {operation} failed",
            code=code,
            retryable=code in self._RETRYABLE_CODES,
        ) from error
