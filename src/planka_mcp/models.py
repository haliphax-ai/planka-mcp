"""Pydantic models for Planka API request/response objects."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class PlankaItem(BaseModel):
    """Generic wrapper: {"item": {...}}."""

    item: dict[str, Any]


class PlankaItems(BaseModel):
    """Generic wrapper: {"items": [...]}."""

    items: list[dict[str, Any]]
