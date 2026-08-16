# Copyright 2026 Zapier, Inc.
# SPDX-License-Identifier: MIT

"""Bounded in-memory workspace state for artifact-oriented agent tasks."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class WorkspaceFile(BaseModel):
    model_config = ConfigDict(validate_assignment=True, extra="forbid")

    path: str
    content: str = ""
    mime_type: str | None = None


class WorkspaceArtifact(BaseModel):
    model_config = ConfigDict(validate_assignment=True, extra="forbid")

    path: str
    kind: str
    size_bytes: int = Field(ge=0)
    checks: list[str] = Field(default_factory=list)


class AgenticWorkspaceState(BaseModel):
    """A virtual workspace; tools never touch the host filesystem."""

    model_config = ConfigDict(validate_assignment=True, extra="forbid")

    files: list[WorkspaceFile] = Field(default_factory=list)
    artifacts: list[WorkspaceArtifact] = Field(default_factory=list)
    tool_log: list[dict[str, Any]] = Field(default_factory=list)
    finalized: bool = False
    finalize_summary: str = ""
