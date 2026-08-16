# Copyright 2026 Zapier, Inc.
# SPDX-License-Identifier: MIT

"""REST-style routes for the bounded benchmark workspace service."""

from automationbench.tools.api.impl.benchmark_workspace import (
    workspace_artifacts_create,
    workspace_artifacts_list,
    workspace_code_run,
    workspace_file_create,
    workspace_file_get,
    workspace_files_list,
    workspace_finalize_create,
)
from automationbench.utils.routing import make_router


_ROUTES = [
    ("GET", r"workspace/v1/files$", "files_list"),
    ("GET", r"workspace/v1/files/(.+)$", "file_get"),
    ("POST", r"workspace/v1/files$", "file_create"),
    ("POST", r"workspace/v1/code$", "code_run"),
    ("GET", r"workspace/v1/artifacts$", "artifacts_list"),
    ("POST", r"workspace/v1/artifacts$", "artifacts_create"),
    ("POST", r"workspace/v1/finalize$", "finalize_create"),
]

_HANDLERS = {
    "files_list": lambda w, ids, p, b: workspace_files_list(w),
    "file_get": lambda w, ids, p, b: workspace_file_get(w, ids[0]),
    "file_create": lambda w, ids, p, b: workspace_file_create(w, b),
    "code_run": lambda w, ids, p, b: workspace_code_run(w, b),
    "artifacts_list": lambda w, ids, p, b: workspace_artifacts_list(w),
    "artifacts_create": lambda w, ids, p, b: workspace_artifacts_create(w, b),
    "finalize_create": lambda w, ids, p, b: workspace_finalize_create(w, b),
}

route_agentic_workspace = make_router(_ROUTES, _HANDLERS)

# Keep the exported name aligned with the WorldState field for service gating.
route_benchmark_workspace = route_agentic_workspace
