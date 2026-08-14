import json

from benchmark.agent_benchmark.high_pressure.score_runs import (
    _model_summary,
    _render_report,
    _task_summary,
    score_run_directories,
)


def test_scores_success_and_api_failure(tmp_path):
    task_answer = {
        "STEP": "O",
        "CAPTURE": "J",
        "STAR": "E",
        "WIN": "H",
        "Q_legal_moves": ["b2>a2", "b2>b1", "b2>b4", "b2>d2"],
        "R": {"legal": True, "ended": True, "winner": "红"},
    }
    run_dir = tmp_path / "run"
    request_dir = run_dir / "requests" / "ok"
    request_dir.mkdir(parents=True)
    (request_dir / "response.md").write_text(
        json.dumps(task_answer, ensure_ascii=False), encoding="utf-8"
    )
    records = [
        {
            "request_id": "ok",
            "prompt_id": "T03",
            "model": "Model A",
            "model_alias": "model-a",
            "status": "success",
            "response_text_path": "requests/ok/response.md",
        },
        {
            "request_id": "failed",
            "prompt_id": "T04",
            "model": "Model A",
            "model_alias": "model-a",
            "status": "error",
            "response_text_path": None,
            "error_type": "timeout",
        },
    ]
    (run_dir / "results.jsonl").write_text(
        "\n".join(json.dumps(record) for record in records) + "\n",
        encoding="utf-8",
    )

    rows = score_run_directories([run_dir])

    assert rows[0]["points"] == 10
    assert rows[0]["status"] == "correct"
    assert rows[1]["points"] == 0
    assert rows[1]["status"] == "api_failure"


def test_report_distinguishes_semantic_errors_from_delivery_failures():
    rows = [
        {
            "task_id": "T01",
            "model": "Model A",
            "points": 10,
            "whole_correct": True,
            "status": "correct",
            "format_compliant": True,
            "component_results": {"availability": True},
        },
        {
            "task_id": "T01",
            "model": "Model B",
            "points": 0,
            "whole_correct": False,
            "status": "wrong",
            "format_compliant": True,
            "component_results": {"availability": False},
        },
        {
            "task_id": "T02",
            "model": "Model A",
            "points": 0,
            "whole_correct": False,
            "status": "unfinished",
            "format_compliant": False,
            "component_results": {"facts": False},
        },
        {
            "task_id": "T02",
            "model": "Model B",
            "points": 0,
            "whole_correct": False,
            "status": "api_failure",
            "format_compliant": False,
            "component_results": {},
        },
    ]

    report = _render_report(rows, _model_summary(rows), _task_summary(rows))

    assert "真正产生语义错误的题：T01" in report
    assert "只产生未完成或接口失败的题：T02" in report
    assert "语义推理错误" in report
    assert "长程交付失败" in report
