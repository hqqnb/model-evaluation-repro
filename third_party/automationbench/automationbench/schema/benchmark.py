# Copyright 2026 Zapier, Inc.
# SPDX-License-Identifier: MIT

"""Shared mutable state for the formal eight-task Agent benchmark."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class BenchmarkState(BaseModel):
    """Task-local records, events, and audit data for benchmark scenarios."""

    model_config = ConfigDict(validate_assignment=True, extra="forbid")

    task_id: str = ""
    data: dict[str, Any] = Field(default_factory=dict)
    actions: list[dict[str, Any]] = Field(default_factory=list)
    events: list[dict[str, Any]] = Field(default_factory=list)
    tool_log: list[dict[str, Any]] = Field(default_factory=list)
