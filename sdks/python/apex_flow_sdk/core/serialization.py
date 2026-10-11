"""
ApexFlow Serialization Engine
=============================
Provides serialization helpers to transparently normalize arbitrary Python objects
(Pydantic models, dataclasses, datetimes, UUIDs, decimals, enums) into JSON-compliant
data structures for control plane communication and storage offloading.
"""

from __future__ import annotations

import dataclasses
import datetime
import decimal
import enum
import json
import pathlib
import uuid
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union


def to_jsonable(obj: Any) -> Any:
    """
    Recursively normalize an arbitrary Python object into JSON-compliant primitives
    (dict, list, str, int, float, bool, None).
    """
    if obj is None or isinstance(obj, (str, int, float, bool)):
        return obj

    # Pydantic v2 & v1 support
    if hasattr(obj, "model_dump") and callable(getattr(obj, "model_dump")):
        try:
            return to_jsonable(obj.model_dump(mode="json"))
        except TypeError:
            return to_jsonable(obj.model_dump())
    elif hasattr(obj, "dict") and callable(getattr(obj, "dict")) and not isinstance(obj, type):
        try:
            return to_jsonable(obj.dict())
        except Exception:
            pass

    # Dataclasses
    if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
        return to_jsonable(dataclasses.asdict(obj))

    # Temporal types (datetime, date, time)
    if isinstance(obj, (datetime.datetime, datetime.date, datetime.time)):
        return obj.isoformat()

    # UUID
    if isinstance(obj, uuid.UUID):
        return str(obj)

    # Decimal
    if isinstance(obj, decimal.Decimal):
        if obj % 1 == 0:
            return int(obj)
        return float(obj)

    # Enums
    if isinstance(obj, enum.Enum):
        return to_jsonable(obj.value)

    # Path objects
    if isinstance(obj, (pathlib.Path, pathlib.PurePath)):
        return str(obj)

    # Dictionaries
    if isinstance(obj, dict):
        return {str(k): to_jsonable(v) for k, v in obj.items()}

    # Sequences (list, tuple, set, frozenset)
    if isinstance(obj, (list, tuple, set, frozenset)):
        return [to_jsonable(item) for item in obj]

    # Custom object hook: to_dict() or __json__()
    if hasattr(obj, "to_dict") and callable(getattr(obj, "to_dict")):
        try:
            return to_jsonable(obj.to_dict())
        except Exception:
            pass

    if hasattr(obj, "__json__") and callable(getattr(obj, "__json__")):
        try:
            return to_jsonable(obj.__json__())
        except Exception:
            pass

    # Fallback for standard Python objects with __dict__
    if hasattr(obj, "__dict__") and not isinstance(obj, type):
        try:
            return to_jsonable(vars(obj))
        except Exception:
            pass

    return str(obj)


def default_json_serializer(obj: Any) -> Any:
    """JSON serializer fallback for objects not handled by default json.dumps."""
    return to_jsonable(obj)


def json_dumps(obj: Any, **kwargs: Any) -> str:
    """Serialize object to JSON string with transparent rich object normalization."""
    normalized = to_jsonable(obj)
    kwargs.setdefault("ensure_ascii", False)
    kwargs.setdefault("default", default_json_serializer)
    return json.dumps(normalized, **kwargs)


def json_dump_bytes(obj: Any, **kwargs: Any) -> bytes:
    """Serialize object directly to UTF-8 encoded bytes."""
    return json_dumps(obj, **kwargs).encode("utf-8")
