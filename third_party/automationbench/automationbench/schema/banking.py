# Copyright 2026 Zapier, Inc.
# SPDX-License-Identifier: MIT

"""Deterministic banking state used by benchmark-inspired tasks."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class BankingState(BaseModel):
    """Small, local banking environment with explicit mutable collections."""

    model_config = ConfigDict(validate_assignment=True, extra="forbid")

    customers: list[dict[str, Any]] = Field(default_factory=list)
    accounts: list[dict[str, Any]] = Field(default_factory=list)
    transactions: list[dict[str, Any]] = Field(default_factory=list)
    policies: list[dict[str, Any]] = Field(default_factory=list)
    verifications: list[dict[str, Any]] = Field(default_factory=list)
    transfer_requests: list[dict[str, Any]] = Field(default_factory=list)
    limit_requests: list[dict[str, Any]] = Field(default_factory=list)
    handoffs: list[dict[str, Any]] = Field(default_factory=list)
    security_events: list[dict[str, Any]] = Field(default_factory=list)
    tool_log: list[dict[str, Any]] = Field(default_factory=list)
