# Copyright 2026 Zapier, Inc.
# SPDX-License-Identifier: MIT

"""API adapters for the bounded virtual workspace service."""

from __future__ import annotations

from typing import Any

from automationbench.schema.world import WorldState
from automationbench.tools.zapier.agentic_workspace import (
    agentic_workspace_finalize,
    agentic_workspace_inspect_artifacts,
    agentic_workspace_list_files,
    agentic_workspace_read_file,
    agentic_workspace_record_artifact,
    agentic_workspace_run_python,
    agentic_workspace_write_file,
)


def workspace_files_list(world: WorldState, **_: Any) -> str:
    return agentic_workspace_list_files(world)


def workspace_file_get(world: WorldState, path: str, **_: Any) -> str:
    return agentic_workspace_read_file(world, path=path)


def workspace_file_create(world: WorldState, body: dict[str, Any]) -> str:
    return agentic_workspace_write_file(
        world,
        path=str(body.get("path", "")),
        content=str(body.get("content", "")),
        overwrite=bool(body.get("overwrite", False)),
    )


def workspace_code_run(world: WorldState, body: dict[str, Any]) -> str:
    return agentic_workspace_run_python(world, source=str(body.get("source", "")))


def workspace_artifacts_create(world: WorldState, body: dict[str, Any]) -> str:
    return agentic_workspace_record_artifact(
        world,
        path=str(body.get("path", "")),
        kind=str(body.get("kind", "")),
        size_bytes=int(body.get("sizeBytes", 0)),
        checks=list(body.get("checks", [])),
    )


def workspace_artifacts_list(world: WorldState, **_: Any) -> str:
    return agentic_workspace_inspect_artifacts(world)


def workspace_finalize_create(world: WorldState, body: dict[str, Any]) -> str:
    return agentic_workspace_finalize(
        world,
        deliverables=list(body.get("deliverables", [])),
        summary=str(body.get("summary", "")),
    )
