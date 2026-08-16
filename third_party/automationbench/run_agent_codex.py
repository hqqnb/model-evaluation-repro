#!/usr/bin/env python3
"""Run one AutomationBench task through the Codex agent (via MCP) and score it."""
from __future__ import annotations

import json
import subprocess
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


TASK_GETTERS = {
    "support.gorgias_refund_processing": get_support_gorgias_refund_processing_task,
    "support.intercom_demo_scheduling": get_support_intercom_demo_scheduling_task,
    "operations.asana_fire_drill": get_ops_asana_fire_drill_task,
    "sales.negative_selection": get_negative_selection_task,
    "finance.expense_anomaly_detection": get_fin_expense_anomaly_task,
}

STATE_FILE = "/tmp/agent_world.json"
TASK_FILE = "/tmp/agent_task.txt"
ANSWER_FILE = "/tmp/agent_answer.md"


def strip_none(value):
    if isinstance(value, dict):
        return {k: strip_none(v) for k, v in value.items() if v is not None}
    if isinstance(value, list):
        return [strip_none(v) for v in value]
    return value


def build_prompt(task) -> str:
    parts = []
    for message in task["prompt"]:
        role = message.get("role")
        content = message.get("content") or ""
        if role == "system":
            parts.append(content)
        else:
            parts.append(content)
    return "\n\n".join(parts)


def run_task(name: str, reasoning_effort: str = "max") -> dict:
    task = TASK_GETTERS[name]()
    prompt = build_prompt(task)
    Path(TASK_FILE).write_text(name, encoding="utf-8")
    if Path(STATE_FILE).exists():
        Path(STATE_FILE).unlink()

    cmd = [
        "codex", "exec",
        "-m", "deepseek-v4-pro",
        "-c", f"model_reasoning_effort={reasoning_effort}",
        "-s", "danger-full-access",
        "--skip-git-repo-check",
        "-o", ANSWER_FILE,
        "-",
    ]
    proc = subprocess.run(cmd, input=prompt, text=True, capture_output=True, timeout=3600)

    if not Path(STATE_FILE).exists():
        return {
            "task": name,
            "error": "no state file",
            "stdout_tail": proc.stdout[-500:],
            "stderr_tail": proc.stderr[-500:],
        }

    dumped = json.loads(Path(STATE_FILE).read_text(encoding="utf-8"))
    final_world = WorldState(**dumped["world"])
    state = {
        "info": dumped["info"],
        "world": final_world,
        "initial_state": dumped["initial_state"],
    }
    score = partial_credit(state)
    return {
        "task": name,
        "partial_credit": score,
        "passed": score == 1.0,
        "assertion_results": state.get("_assertion_results", []),
        "answer_tail": (Path(ANSWER_FILE).read_text(encoding="utf-8") if Path(ANSWER_FILE).exists() else "")[-500:],
    }


if __name__ == "__main__":
    name = sys.argv[1]
    effort = sys.argv[2] if len(sys.argv) > 2 else "max"
    result = run_task(name, effort)
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
