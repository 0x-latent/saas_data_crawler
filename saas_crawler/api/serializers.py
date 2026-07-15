"""Small SQLAlchemy serialization helpers."""

from __future__ import annotations

from datetime import datetime
from typing import Any


def value_to_json(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    return value


def model_to_dict(model: Any, fields: list[str] | None = None) -> dict[str, Any]:
    columns = fields or [column.name for column in model.__table__.columns]
    return {field: value_to_json(getattr(model, field)) for field in columns}
