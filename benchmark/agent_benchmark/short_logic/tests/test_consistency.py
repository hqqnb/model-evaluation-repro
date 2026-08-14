import json
import re
from pathlib import Path

from benchmark.agent_benchmark.short_logic.tasks import build_tasks


def test_ids_match_across_all_rendered_artifacts():
    root = Path(__file__).resolve().parents[2]
    repository_root = Path(__file__).resolve().parents[4]
    tasks = build_tasks()
    expected_ids = [task.id for task in tasks]

    answer_key = json.loads((root / "short_logic_answer_key.json").read_text(encoding="utf-8"))
    prompt_rows = [
        json.loads(line)
        for line in (
            repository_root
            / "runners/model-api-collector/prompts/reasoning_short_hard_20260806.jsonl"
        )
        .read_text(encoding="utf-8")
        .splitlines()
        if line.strip()
    ]
    markdown_ids = re.findall(
        r"^## (S\d{2}) ", (root / "SHORT_HARD_LOGIC_TASKS.md").read_text(encoding="utf-8"), re.M
    )

    assert expected_ids == [item["id"] for item in answer_key]
    assert expected_ids == [row["id"] for row in prompt_rows]
    assert expected_ids == markdown_ids
    assert all(len(task.prompt) <= 900 for task in tasks)
