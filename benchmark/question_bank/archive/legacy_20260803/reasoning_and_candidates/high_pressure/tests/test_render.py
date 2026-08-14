import json
from pathlib import Path

from benchmark.question_bank.archive.legacy_20260803.reasoning_and_candidates.high_pressure.render import (
    ANSWER_KEY_PATH,
    MARKDOWN_PATH,
    PROMPTS_PATH,
    render_all,
)


def test_render_all_produces_consistent_artifacts(tmp_path, monkeypatch):
    markdown_path = tmp_path / "tasks.md"
    answer_path = tmp_path / "answers.json"
    prompts_path = tmp_path / "prompts.jsonl"
    monkeypatch.setattr(
        "benchmark.question_bank.archive.legacy_20260803.reasoning_and_candidates.high_pressure.render.MARKDOWN_PATH",
        markdown_path,
    )
    monkeypatch.setattr(
        "benchmark.question_bank.archive.legacy_20260803.reasoning_and_candidates.high_pressure.render.ANSWER_KEY_PATH",
        answer_path,
    )
    monkeypatch.setattr(
        "benchmark.question_bank.archive.legacy_20260803.reasoning_and_candidates.high_pressure.render.PROMPTS_PATH",
        prompts_path,
    )

    render_all()

    markdown = markdown_path.read_text(encoding="utf-8")
    answers = json.loads(answer_path.read_text(encoding="utf-8"))
    prompts = [
        json.loads(line)
        for line in prompts_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert len(answers) == 10
    assert len(prompts) == 10
    assert [item["id"] for item in answers] == [item["id"] for item in prompts]
    assert all(f"## {item['id']}" in markdown for item in prompts)
    assert all(item["messages"][0]["content"] in markdown for item in prompts)
    assert all("expected" in item for item in answers)
    assert all("expected" not in item for item in prompts)


def test_default_paths_target_expected_workspaces():
    assert MARKDOWN_PATH.name == "HIGH_PRESSURE_REASONING_TASKS.md"
    assert ANSWER_KEY_PATH.name == "high_pressure_answer_key.json"
    assert PROMPTS_PATH.name == "reasoning_high_pressure_20260805.jsonl"
