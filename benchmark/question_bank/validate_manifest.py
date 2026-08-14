"""Validate the active unified question-bank manifest without API calls."""

from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parent
MANIFEST_PATH = ROOT / "manifest.json"
PROMPTS_PATH = ROOT / "single_turn/dataset/prompts.json"
RUBRICS_PATH = ROOT / "single_turn/rubrics/rubrics.json"
AGENT_MANIFEST_PATH = ROOT / "agent/manifest.json"
AGENT_TASKS_PATH = ROOT / "agent/tasks.md"


def load_json(path: Path) -> dict:
    with path.open(encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def validate() -> str:
    manifest = load_json(MANIFEST_PATH)
    prompts = load_json(PROMPTS_PATH)
    rubrics = load_json(RUBRICS_PATH)
    agent_manifest = load_json(AGENT_MANIFEST_PATH)
    agent_tasks = AGENT_TASKS_PATH.read_text(encoding="utf-8")

    prompt_items = prompts["items"]
    rubric_items = rubrics["items"]
    prompt_ids = [item["id"] for item in prompt_items]
    rubric_ids = [item["id"] for item in rubric_items]
    assert prompt_ids == rubric_ids, "single-turn prompt and rubric IDs differ"

    expected_counts = {
        category: details["count"]
        for category, details in manifest["categories"].items()
        if category != "agent"
    }
    actual_counts = Counter(item["category"] for item in prompt_items)
    assert dict(actual_counts) == expected_counts, (
        f"single-turn counts differ: expected {expected_counts}, got {dict(actual_counts)}"
    )

    agent_ids = [task["id"] for task in agent_manifest["tasks"]]
    expected_agent_ids = manifest["categories"]["agent"]["ids"]
    assert agent_ids == expected_agent_ids, "agent manifest IDs differ from bank manifest"
    headings = re.findall(r"^## (T\d{2}) ", agent_tasks, re.MULTILINE)
    assert headings == expected_agent_ids, (
        f"agent task headings differ: expected {expected_agent_ids}, got {headings}"
    )

    expected_total = sum(expected_counts.values()) + len(agent_ids)
    assert manifest["task_count"] == expected_total, (
        f"bank task count is {manifest['task_count']}, expected {expected_total}"
    )

    return (
        f"Validated unified bank {manifest['bank_id']}: "
        f"{manifest['task_count']} tasks "
        f"({', '.join(f'{key}={value}' for key, value in expected_counts.items())}, "
        f"agent={len(agent_ids)})"
    )


if __name__ == "__main__":
    print(validate())
