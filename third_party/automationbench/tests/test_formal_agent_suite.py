"""Safety gates for the formal Agent benchmark batch controller."""

from __future__ import annotations

import copy
import json
from pathlib import Path

from automationbench.scripts.formal_agent_suite import (
    build_eval_command,
    classify_technical_error,
    resume_status_for_verified_result,
    preflight_tool_choice,
    run_model,
    run_batch,
    summarize_results,
    validate_manifest,
    verify_result_file,
)
from automationbench.scripts.eval import (
    EVAL_STATE_COLUMNS,
    _normalize_output_record,
)


MANIFEST = (
    Path(__file__).parents[1]
    / "configs"
    / "agent-suite-v1.1-integrity-20260815.json"
)
HISTORICAL_MANIFEST = (
    Path(__file__).parents[1]
    / "results"
    / "agent_runs"
    / "agent-suite-v1-20260814"
    / "manifest.json"
)
HISTORICAL_RESULT = HISTORICAL_MANIFEST.parent / "opus-5.json"


def test_formal_manifest_matches_the_live_eight_task_dataset():
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))

    assert validate_manifest(manifest) == []


def test_historical_v1_result_remains_bound_to_its_original_manifest():
    manifest = json.loads(HISTORICAL_MANIFEST.read_text(encoding="utf-8"))

    assert verify_result_file(HISTORICAL_RESULT, manifest) == []


def test_manifest_validation_rejects_a_smoke_task_count():
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    tampered = copy.deepcopy(manifest)
    tampered["task_count"] = 2

    errors = validate_manifest(tampered)

    assert any("task_count" in error for error in errors)


def test_manifest_validation_rejects_a_changed_task_contract():
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    tampered = copy.deepcopy(manifest)
    tampered["tasks"][0]["task_contract_sha256"] = "0" * 64

    errors = validate_manifest(tampered)

    assert any("task_contract_sha256" in error for error in errors)


def test_manifest_validation_rejects_out_of_range_client_retry_attempts():
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    manifest["client_retry_attempts"] = 11

    errors = validate_manifest(manifest)

    assert any("client_retry_attempts" in error for error in errors)


def _valid_result(manifest: dict, model: str = "gpt-5.6-sol") -> dict:
    tasks = []
    for index, item in enumerate(manifest["tasks"], start=1):
        tasks.append(
            {
                "id": index,
                "name": item["task_name"],
                "partial_credit": 1.0,
                "weighted_score": 100.0,
                "strict_pass": True,
                "hard_fail_reasons": [],
                "assertion_results": [{"type": "example", "passed": True, "points": 100}],
                "trajectory": [{"role": "assistant", "content": "complete"}],
                "technical_errors": [],
                "task_contract_schema": "automationbench.task-contract.v1",
                "task_contract_sha256": item["task_contract_sha256"],
            }
        )
    return {
        "meta": {
            "model": model,
            "total_tasks": len(tasks),
            "toolset": manifest["toolset"],
            "max_steps": manifest["max_steps"],
            "formal_runner": {"batch_id": manifest["batch_id"]},
        },
        "tasks": tasks,
    }


def test_result_verification_accepts_a_complete_formal_export(tmp_path):
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    result_path = tmp_path / "result.json"
    result_path.write_text(
        json.dumps(_valid_result(manifest), ensure_ascii=False),
        encoding="utf-8",
    )

    assert verify_result_file(result_path, manifest) == []


def test_result_verification_rejects_missing_task_contract_fingerprint(tmp_path):
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    result = _valid_result(manifest)
    for task in result["tasks"]:
        task.pop("task_contract_sha256")
    result_path = tmp_path / "result.json"
    result_path.write_text(json.dumps(result), encoding="utf-8")

    errors = verify_result_file(
        result_path,
        manifest,
        expected_model="gpt-5.6-sol",
        expected_batch_id=manifest["batch_id"],
    )

    assert any("task_contract_sha256" in error for error in errors)


def test_result_verification_rejects_wrong_model(tmp_path):
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    result = _valid_result(manifest)
    result["meta"]["model"] = "Opus 5"
    result_path = tmp_path / "result.json"
    result_path.write_text(json.dumps(result), encoding="utf-8")

    errors = verify_result_file(
        result_path,
        manifest,
        expected_model="gpt-5.6-sol",
        expected_batch_id=manifest["batch_id"],
    )

    assert any("result model" in error for error in errors)


def test_result_verification_rejects_a_different_batch(tmp_path):
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    result = _valid_result(manifest)
    result["meta"]["formal_runner"]["batch_id"] = "old-batch"
    result_path = tmp_path / "result.json"
    result_path.write_text(json.dumps(result), encoding="utf-8")

    errors = verify_result_file(
        result_path,
        manifest,
        expected_model="gpt-5.6-sol",
        expected_batch_id=manifest["batch_id"],
    )

    assert any("batch_id" in error for error in errors)


def test_result_verification_rejects_a_two_task_export(tmp_path):
    result_path = tmp_path / "result.json"
    result_path.write_text(
        json.dumps(
            {
                "meta": {"total_tasks": 2},
                "tasks": [
                    {"name": "benchmark.banking_transfer_and_limit_review"},
                    {"name": "benchmark.workspace_artifact_delivery"},
                ],
            }
        ),
        encoding="utf-8",
    )
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))

    errors = verify_result_file(result_path, manifest)

    assert any("expected 8 tasks" in error for error in errors)


def test_result_verification_rejects_a_missing_trajectory(tmp_path):
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    result = _valid_result(manifest)
    result["tasks"][0].pop("trajectory")
    result_path = tmp_path / "result.json"
    result_path.write_text(json.dumps(result), encoding="utf-8")

    errors = verify_result_file(result_path, manifest)

    assert any("trajectory" in error for error in errors)


def test_eval_command_explicitly_lists_all_tasks_without_a_plaintext_key(tmp_path):
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    model = next(item for item in manifest["models"] if item["run_id"] == "gpt-5.6-sol")

    command = build_eval_command(manifest, model, tmp_path / "gpt-5.6-sol.json")

    task_argument = command[command.index("--tasks") + 1]
    assert task_argument.split(",") == [item["task_name"] for item in manifest["tasks"]]
    assert command[command.index("--max-concurrent") + 1] == "2"
    assert "--api-key" not in command
    assert command[command.index("--api-key-var") + 1] == "OPENAI_API_KEY"


def test_run_model_limits_client_retries_from_manifest(tmp_path, monkeypatch):
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    manifest["client_retry_attempts"] = 5
    model = next(item for item in manifest["models"] if item["run_id"] == "gpt-5.6-sol")
    captured = {}

    import automationbench.scripts.formal_agent_suite as suite

    monkeypatch.setattr(
        suite,
        "_runtime_environment",
        lambda _: ({"PATH": "/usr/bin"}, "secret"),
    )

    def fake_run_eval_process(command, *, env, **kwargs):
        captured["env"] = env
        return {"returncode": 1, "timed_out": False}

    monkeypatch.setattr(suite, "_run_eval_process", fake_run_eval_process)

    status = run_model(
        manifest,
        model,
        tmp_path,
        Path(__file__).parents[1],
        technical_retries=0,
        timeout_seconds=1,
    )

    assert status["status"] == "technical_failure"
    assert captured["env"]["AUTO_BENCH_RETRY_MAX_ATTEMPTS"] == "5"


def test_technical_error_classifier_distinguishes_billing_from_capability():
    category = classify_technical_error(
        "Access denied, account in arrears. code=Arrearage"
    )

    assert category == "billing"


def test_technical_error_classifier_detects_arrears_without_provider_code():
    for message in (
        "The account is in arrears and the service has been isolated. Please top up.",
        "API Key 所属账号已欠费，请充值后在控制台重新启用服务。",
    ):
        assert classify_technical_error(message) == "billing"


def test_resume_status_marks_a_verified_result_as_valid(tmp_path):
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    result = _valid_result(manifest)
    result_path = tmp_path / "gpt-5.6-sol.json"

    status = resume_status_for_verified_result(
        run_id="gpt-5.6-sol",
        output_path=result_path,
        result=result,
        manifest=manifest,
        previous_status={
            "status": "invalid_result",
            "process": {"returncode": 0},
        },
    )

    assert status["status"] == "valid"
    assert status["verification_errors"] == []
    assert status["remaining_technical_failures"] == {}
    assert status["process"] == {"returncode": 0}
    assert status["output_path"] == str(result_path)


def test_resume_keeps_a_verified_result_when_preflight_temporarily_fails(
    tmp_path,
    monkeypatch,
):
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    manifest["models"] = [
        next(item for item in manifest["models"] if item["run_id"] == "opus-5")
    ]
    manifest.pop("output_dir", None)
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    result_path = tmp_path / "opus-5.json"
    result_path.write_text(
        json.dumps(_valid_result(manifest, model="Opus 5"), ensure_ascii=False),
        encoding="utf-8",
    )

    import automationbench.scripts.formal_agent_suite as suite

    monkeypatch.setattr(suite, "validate_manifest", lambda _: [])
    monkeypatch.setattr(
        suite,
        "preflight_model",
        lambda model: {
            "run_id": model["run_id"],
            "status": "technical_failure",
            "category": "provider",
        },
    )

    assert run_batch(manifest_path, resume=True) == 0

    summary = json.loads((tmp_path / "summary.json").read_text(encoding="utf-8"))
    assert summary["models"]["opus-5"]["status"] == "complete"


def test_resume_does_not_preflight_a_verified_result(tmp_path, monkeypatch):
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    manifest["models"] = [
        next(item for item in manifest["models"] if item["run_id"] == "opus-5")
    ]
    manifest.pop("output_dir", None)
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    result_path = tmp_path / "opus-5.json"
    result_path.write_text(
        json.dumps(_valid_result(manifest, model="Opus 5"), ensure_ascii=False),
        encoding="utf-8",
    )

    import automationbench.scripts.formal_agent_suite as suite

    calls = []
    monkeypatch.setattr(suite, "validate_manifest", lambda _: [])
    monkeypatch.setattr(
        suite,
        "preflight_model",
        lambda model: calls.append(model["run_id"]) or {
            "run_id": model["run_id"],
            "status": "passed",
        },
    )

    assert run_batch(manifest_path, resume=True) == 0
    assert calls == []


def test_chat_preflight_uses_auto_tool_choice_for_thinking_models():
    assert preflight_tool_choice(responses_api=False) == "auto"
    assert preflight_tool_choice(responses_api=True) == {
        "type": "function",
        "name": "formal_preflight_echo",
    }


def test_summary_excludes_technical_failures_from_capability_denominator():
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    result = _valid_result(manifest)
    result["tasks"][0]["technical_errors"] = ["provider timeout"]
    result["tasks"][0]["partial_credit"] = 0.0
    result["tasks"][0]["weighted_score"] = 0.0
    result["tasks"][0]["strict_pass"] = False

    summary = summarize_results({"gpt-5.6-sol": result}, manifest)
    model_summary = summary["models"]["gpt-5.6-sol"]

    assert model_summary["technical_failure_count"] == 1
    assert model_summary["capability_task_count"] == 7
    assert model_summary["strict_pass_rate"] == 1.0
    assert model_summary["avg_weighted_score"] == 100.0


def test_eval_preserves_task_contract_fingerprint_through_state_export():
    assert "_task_contract_schema" in EVAL_STATE_COLUMNS
    assert "_task_contract_sha256" in EVAL_STATE_COLUMNS

    normalized = _normalize_output_record(
        {
            "task": "benchmark.t01_refund_processing",
            "reward": 1.0,
            "info": {},
            "_task_contract_schema": "automationbench.task-contract.v1",
            "_task_contract_sha256": "a" * 64,
        }
    )

    assert normalized["_task_contract_schema"] == "automationbench.task-contract.v1"
    assert normalized["_task_contract_sha256"] == "a" * 64
