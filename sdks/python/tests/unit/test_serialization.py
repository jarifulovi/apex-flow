import dataclasses
import datetime
import decimal
import enum
import json
import pathlib
import uuid
import pytest
from pydantic import BaseModel, Field

from apex_flow_sdk.core.serialization import (
    json_dump_bytes,
    json_dumps,
    to_jsonable,
)
from apex_flow_sdk.adapters.storage import StorageResolver


class PriorityEnum(enum.Enum):
    LOW = "low"
    HIGH = "high"


@dataclasses.dataclass
class Address:
    street: str
    city: str


@dataclasses.dataclass
class UserProfile:
    name: str
    address: Address
    tags: set


class OrderItem(BaseModel):
    item_id: str
    quantity: int
    price: float


class OrderPayload(BaseModel):
    order_id: uuid.UUID
    created_at: datetime.datetime
    items: list[OrderItem]
    priority: PriorityEnum
    total: decimal.Decimal


def test_serialization_pydantic_model():
    order = OrderPayload(
        order_id=uuid.UUID("12345678-1234-5678-1234-567812345678"),
        created_at=datetime.datetime(2026, 10, 11, 12, 0, 0, tzinfo=datetime.timezone.utc),
        items=[OrderItem(item_id="item-A", quantity=2, price=49.99)],
        priority=PriorityEnum.HIGH,
        total=decimal.Decimal("99.98"),
    )

    data = to_jsonable(order)
    assert data["order_id"] == "12345678-1234-5678-1234-567812345678"
    assert "2026-10-11T12:00:00" in data["created_at"]
    assert data["priority"] == "high"
    assert float(data["total"]) == 99.98
    assert len(data["items"]) == 1
    assert data["items"][0]["item_id"] == "item-A"

    # Verify standard json.dumps works without any custom default
    json_str = json.dumps(data)
    assert "99.98" in json_str


def test_serialization_dataclass_with_nested_and_sets():
    profile = UserProfile(
        name="Alice",
        address=Address(street="123 Tech Blvd", city="San Francisco"),
        tags={"ai", "workflows", "developer"},
    )

    data = to_jsonable(profile)
    assert data["name"] == "Alice"
    assert data["address"]["city"] == "San Francisco"
    assert isinstance(data["tags"], list)
    assert set(data["tags"]) == {"ai", "workflows", "developer"}

    json_bytes = json_dump_bytes(profile)
    assert b"San Francisco" in json_bytes


def test_serialization_primitives_and_decimals():
    now = datetime.datetime.now(datetime.timezone.utc)
    today = datetime.date.today()
    sample_uuid = uuid.uuid4()
    path = pathlib.Path("/tmp/apexflow/data.json")

    obj = {
        "uuid": sample_uuid,
        "now": now,
        "today": today,
        "path": path,
        "int_dec": decimal.Decimal("100"),
        "float_dec": decimal.Decimal("100.55"),
        "tuple_items": (1, 2, 3),
    }

    normalized = to_jsonable(obj)
    assert normalized["uuid"] == str(sample_uuid)
    assert normalized["now"] == now.isoformat()
    assert normalized["today"] == today.isoformat()
    assert normalized["path"] == str(path)
    assert normalized["int_dec"] == 100
    assert normalized["float_dec"] == 100.55
    assert normalized["tuple_items"] == [1, 2, 3]


@pytest.mark.asyncio
async def test_storage_resolver_with_pydantic_payload():
    """Verify StorageResolver handles Pydantic models cleanly without serialization crashes."""
    from unittest.mock import AsyncMock
    import httpx

    order = OrderPayload(
        order_id=uuid.uuid4(),
        created_at=datetime.datetime.now(datetime.timezone.utc),
        items=[OrderItem(item_id="X1", quantity=1, price=10.0)],
        priority=PriorityEnum.LOW,
        total=decimal.Decimal("10.00"),
    )

    client = AsyncMock(spec=httpx.AsyncClient)
    client.base_url = "http://test"

    # Offload check for small inline payload (<= 250KB)
    result_payload, is_offloaded = await StorageResolver.offload_if_needed(
        http_client=client,
        base_url="http://test",
        payload=order,
    )

    assert not is_offloaded
    assert isinstance(result_payload, dict)
    assert result_payload["priority"] == "low"
    assert result_payload["items"][0]["item_id"] == "X1"
