import json

from benchmark.question_bank.archive.legacy_20260803.reasoning_and_candidates.short_logic.score_runs import (
    _model_summary,
    _render_report,
    merge_delivery_retries,
    score_run_directories,
)
from benchmark.question_bank.archive.legacy_20260803.reasoning_and_candidates.short_logic.tasks import build_tasks


def _row(model, task_id, status, points):
    return {
        "model": model,
        "model_alias": model,
        "task_id": task_id,
        "status": status,
        "points": points,
        "whole_correct": status == "correct",
        "format_compliant": status not in {"api_failure", "unfinished"},
    }


def test_retry_only_replaces_delivery_failures():
    primary = [
        _row("model-a", "S01", "wrong", 0),
        _row("model-a", "S02", "api_failure", 0),
        _row("model-a", "S03", "unfinished", 0),
    ]
    retries = [
        _row("model-a", "S01", "correct", 10),
        _row("model-a", "S02", "correct", 10),
        _row("model-a", "S03", "correct", 10),
    ]

    merged = merge_delivery_retries(primary, retries)

    assert [row["points"] for row in merged] == [0, 10, 10]
    assert merged[0].get("replaced_by_retry") is None
    assert merged[1]["replaced_by_retry"] is True
    assert merged[2]["replaced_by_retry"] is True


def test_failed_retry_does_not_replace_primary_delivery_failure():
    primary = [_row("model-a", "S03", "api_failure", 0)]
    retries = [_row("model-a", "S03", "unfinished", 0)]

    assert merge_delivery_retries(primary, retries) == primary


def test_delivery_failures_are_not_counted_as_format_failures():
    primary = [_row("model-a", "S03", "unfinished", 0)]

    summary = _model_summary(primary, primary)

    assert summary[0]["initial_delivery_anomalies"] == 1
    assert summary[0]["format_noncompliant"] == 0


def test_score_run_distinguishes_correct_empty_and_api_failure(tmp_path):
    run_dir = tmp_path / "run"
    request_dir = run_dir / "requests"
    request_dir.mkdir(parents=True)
    task = next(task for task in build_tasks() if task.id == "S01")

    correct_dir = request_dir / "correct"
    correct_dir.mkdir()
    (correct_dir / "response.md").write_text(
        json.dumps(task.expected, ensure_ascii=False), encoding="utf-8"
    )
    empty_dir = request_dir / "empty"
    empty_dir.mkdir()
    (empty_dir / "response.md").write_text("", encoding="utf-8")

    records = [
        {
            "request_id": "correct",
            "prompt_id": "S01",
            "model": "Model A",
            "model_alias": "model-a",
            "status": "success",
            "response_text_path": "requests/correct/response.md",
        },
        {
            "request_id": "empty",
            "prompt_id": "S01",
            "model": "Model B",
            "model_alias": "model-b",
            "status": "success",
            "response_text_path": "requests/empty/response.md",
        },
        {
            "request_id": "failed",
            "prompt_id": "S01",
            "model": "Model C",
            "model_alias": "model-c",
            "status": "failed",
            "error_type": "incomplete_stream",
        },
    ]
    (run_dir / "results.jsonl").write_text(
        "\n".join(json.dumps(record) for record in records) + "\n",
        encoding="utf-8",
    )

    rows = score_run_directories([run_dir])

    assert [row["status"] for row in rows] == [
        "correct",
        "unfinished",
        "api_failure",
    ]


def test_report_separates_semantic_difference_from_delivery_recovery():
    primary = [
        _row("model-a", "S01", "correct", 10),
        _row("model-b", "S01", "wrong", 0),
        _row("model-a", "S03", "api_failure", 0),
        _row("model-b", "S03", "correct", 10),
    ]
    retries = [_row("model-a", "S03", "correct", 10)]
    merged = merge_delivery_retries(primary, retries)

    report = _render_report(
        primary,
        retries,
        merged,
        _model_summary(merged, primary),
    )

    assert "真正产生语义差异的题：S01" in report
    assert "首次交付异常：1 次" in report
    assert "补跑恢复：1 次" in report
    assert "未达到入库门槛" in report
