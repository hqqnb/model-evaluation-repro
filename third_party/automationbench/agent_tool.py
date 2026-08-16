#!/usr/bin/env python3
"""Subcommand CLI used by the in-session Codex agent to drive one AutomationBench task."""
from __future__ import annotations

import json
import sys
from pathlib import Path

from automationbench.domains.finance.tasks import get_fin_expense_anomaly_task
from automationbench.domains.operations.tasks import get_ops_asana_fire_drill_task
from automationbench.domains.sales.tasks import get_negative_selection_task
from automationbench.domains.support.tasks import (
    get_support_gorgias_refund_processing_task,
    get_support_intercom_demo_scheduling_task,
)
from automationbench.rubric import partial_credit
from automationbench.schema.world import WorldState
from automationbench.tools.api import api_fetch, api_search


TASK_GETTERS = {
    "support.gorgias_refund_processing": get_support_gorgias_refund_processing_task,
    "support.intercom_demo_scheduling": get_support_intercom_demo_scheduling_task,
    "operations.asana_fire_drill": get_ops_asana_fire_drill_task,
    "sales.negative_selection": get_negative_selection_task,
    "finance.expense_anomaly_detection": get_fin_expense_anomaly_task,
}

STATE_DIR = Path("/tmp/agent_live")


def strip_none(value):
    if isinstance(value, dict):
        return {k: strip_none(v) for k, v in value.items() if v is not None}
    if isinstance(value, list):
        return [strip_none(v) for v in value]
    return value


def load_state() -> dict:
    return json.loads((STATE_DIR / "state.json").read_text(encoding="utf-8"))


def save_state(state: dict) -> None:
    STATE_DIR.mkdir(exist_ok=True)
    (STATE_DIR / "state.json").write_text(json.dumps(state, ensure_ascii=False), encoding="utf-8")


def cmd_init(task_name: str) -> None:
    task = TASK_GETTERS[task_name]()
    info = strip_none(json.loads(json.dumps(task["info"], default=str)))
    info["assertions"] = [strip_none(a) for a in info.get("assertions", [])]
    initial_state = strip_none(info.get("initial_state", {}))
    world = WorldState(**initial_state)
    state = {
        "task": task_name,
        "info": info,
        "initial_state": initial_state,
        "world": world.model_dump(mode="json"),
    }
    save_state(state)
    prompt = "\n\n".join(m.get("content") or "" for m in task["prompt"])
    print(prompt)


def cmd_search(query: str) -> None:
    print(api_search(query))


def cmd_call(method: str, url: str, params: str | None, body: str | None) -> None:
    state = load_state()
    world = WorldState(**state["world"])
    result = api_fetch(world, method, url, params, body)
    state["world"] = world.model_dump(mode="json")
    save_state(state)
    print(result)


def cmd_score() -> None:
    state = load_state()
    world = WorldState(**state["world"])
    st = {
        "info": state["info"],
        "world": world,
        "initial_state": state["initial_state"],
    }
    score = partial_credit(st)
    passed = sum(1 for a in st.get("_assertion_results", []) if a.get("passed") and not a.get("excluded"))
    total = sum(1 for a in st.get("_assertion_results", []) if not a.get("excluded"))
    print(json.dumps({"score": score, "passed": passed, "total": total, "results": st.get("_assertion_results", [])}, ensure_ascii=False, default=str))


if __name__ == "__main__":
    args = sys.argv[1:]
    if args[0] == "init":
        cmd_init(args[1])
    elif args[0] == "search":
        cmd_search(" ".join(args[1:]))
    elif args[0] == "call":
        # call <method> <url> [params_json] [body_json]
        cmd_call(args[1], args[2], args[3] if len(args) > 3 else None, args[4] if len(args) > 4 else None)
    elif args[0] == "score":
        cmd_score()
    else:
        print("unknown command", file=sys.stderr)
