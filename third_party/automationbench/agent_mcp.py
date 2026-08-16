#!/usr/bin/env python3
"""Minimal MCP server exposing AutomationBench API tools to a Codex agent."""
from __future__ import annotations

import atexit
import json
import os

from mcp.server.fastmcp import FastMCP

from automationbench.domains.finance.tasks import get_fin_expense_anomaly_task
from automationbench.domains.operations.tasks import get_ops_asana_fire_drill_task
from automationbench.domains.sales.tasks import get_negative_selection_task
from automationbench.domains.support.tasks import (
    get_support_gorgias_refund_processing_task,
    get_support_intercom_demo_scheduling_task,
)
from automationbench.schema.world import WorldState
from automationbench.tools.api import (
    base64_encode as _base64_encode,
    api_fetch as _api_fetch,
    api_search as _api_search,
)


TASK_GETTERS = {
    "support.gorgias_refund_processing": get_support_gorgias_refund_processing_task,
    "support.intercom_demo_scheduling": get_support_intercom_demo_scheduling_task,
    "operations.asana_fire_drill": get_ops_asana_fire_drill_task,
    "sales.negative_selection": get_negative_selection_task,
    "finance.expense_anomaly_detection": get_fin_expense_anomaly_task,
}


def strip_none(value):
    if isinstance(value, dict):
        return {k: strip_none(v) for k, v in value.items() if v is not None}
    if isinstance(value, list):
        return [strip_none(v) for v in value]
    return value


def load_task(name: str):
    getter = TASK_GETTERS.get(name)
    if getter is None:
        raise SystemExit(f"unknown task: {name}")
    task = getter()
    info = json.loads(json.dumps(task["info"], default=str))
    info = strip_none(info)
    initial_state = strip_none(info.get("initial_state", {}))
    info["assertions"] = [strip_none(a) for a in info.get("assertions", [])]
    world = WorldState(**initial_state)
    return task, info, initial_state, world


TASK_NAME = os.environ.get("AGENT_TASK", "")
TASK_FILE = os.environ.get("AGENT_TASK_FILE", "/tmp/agent_task.txt")
if not TASK_NAME and os.path.exists(TASK_FILE):
    TASK_NAME = open(TASK_FILE, encoding="utf-8").read().strip()
STATE_FILE = os.environ.get("AGENT_STATE_FILE", "/tmp/agent_world.json")

_task, INFO, INITIAL_STATE, WORLD = load_task(TASK_NAME)


def _dump() -> None:
    payload = {
        "task": TASK_NAME,
        "info": INFO,
        "initial_state": INITIAL_STATE,
        "world": WORLD.model_dump(mode="json"),
    }
    with open(STATE_FILE, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False)


atexit.register(_dump)


mcp = FastMCP("automationbench-agent")


@mcp.tool()
def api_search(query: str, top_k: int = 5) -> str:
    """Search available API endpoints by keyword to discover which endpoint to call."""
    return _api_search(query, top_k)


@mcp.tool()
def api_fetch(method: str, url: str, params: str | None = None, body: str | None = None) -> str:
    """Call an API endpoint by full URL, routing to the world state mutation."""
    return _api_fetch(WORLD, method, url, params, body)


@mcp.tool()
def base64_encode(text: str) -> str:
    """Encode text to base64url, the format Gmail body fields require."""
    return _base64_encode(text)


if __name__ == "__main__":
    mcp.run()
