# Copyright 2026 Zapier, Inc.
# SPDX-License-Identifier: MIT

"""Run and audit the pinned eight-task formal Agent benchmark suite."""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import os
import signal
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import openai
from dotenv import dotenv_values

from automationbench.domains.benchmark.tasks import get_benchmark_dataset
from automationbench.rubric import AssertionRegistry
from automationbench.task_contract import TASK_CONTRACT_SCHEMA, task_contract_sha256
from automationbench.tools import ALL_TOOLS


MANIFEST_SCHEMA = "automationbench.formal-agent-suite.v1"
FORMAL_TASK_COUNT = 8
REQUIRED_SCORE_FIELDS = {
    "partial_credit",
    "weighted_score",
    "strict_pass",
    "hard_fail_reasons",
    "assertion_results",
    "trajectory",
    "technical_errors",
}
SUPPORTED_APIS = {"chat_completions", "responses"}
TECHNICAL_RETRY_CATEGORIES = {
    "authentication",
    "billing",
    "model_not_found",
    "network",
    "provider",
    "rate_limit",
    "timeout",
    "tool_protocol",
}


def _now() -> str:
    return datetime.now().isoformat()


def _load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise TypeError(f"{path} must contain a JSON object")
    return value


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def _task_info(row: dict[str, Any]) -> dict[str, Any]:
    info = row.get("info") or {}
    if isinstance(info, str):
        info = json.loads(info)
    if not isinstance(info, dict):
        raise TypeError("task info must be an object")
    return info


def _registered_tool_names() -> set[str]:
    names = set()
    for tool in ALL_TOOLS:
        name = getattr(tool, "__name__", None) or getattr(tool, "name", None)
        if name:
            names.add(str(name))
    return names


def validate_manifest(manifest: dict[str, Any]) -> list[str]:
    """Validate the manifest against the live formal task dataset."""
    errors: list[str] = []
    if manifest.get("manifest_schema") != MANIFEST_SCHEMA:
        errors.append(
            f"manifest_schema must be {MANIFEST_SCHEMA!r}, got "
            f"{manifest.get('manifest_schema')!r}"
        )
    if manifest.get("domain") != "benchmark":
        errors.append("domain must be 'benchmark'")
    if manifest.get("toolset") != "limited_zapier":
        errors.append("toolset must be 'limited_zapier'")
    if manifest.get("task_count") != FORMAL_TASK_COUNT:
        errors.append(
            f"task_count must be {FORMAL_TASK_COUNT}, got {manifest.get('task_count')!r}"
        )
    if not isinstance(manifest.get("max_steps"), int) or manifest["max_steps"] <= 0:
        errors.append("max_steps must be a positive integer")
    if not isinstance(manifest.get("max_concurrent_tasks_per_model"), int):
        errors.append("max_concurrent_tasks_per_model must be an integer")
    elif not 1 <= manifest["max_concurrent_tasks_per_model"] <= 2:
        errors.append("max_concurrent_tasks_per_model must be between 1 and 2")
    if not isinstance(manifest.get("max_concurrent_models"), int):
        errors.append("max_concurrent_models must be an integer")
    elif not 1 <= manifest["max_concurrent_models"] <= 2:
        errors.append("max_concurrent_models must be between 1 and 2")
    if not isinstance(manifest.get("client_retry_attempts"), int):
        errors.append("client_retry_attempts must be an integer")
    elif not 1 <= manifest["client_retry_attempts"] <= 10:
        errors.append("client_retry_attempts must be between 1 and 10")
    if "output_dir" in manifest and not isinstance(manifest["output_dir"], str):
        errors.append("output_dir must be a string when provided")

    manifest_tasks = manifest.get("tasks")
    if not isinstance(manifest_tasks, list):
        errors.append("tasks must be a list")
        manifest_tasks = []
    if len(manifest_tasks) != FORMAL_TASK_COUNT:
        errors.append(f"tasks must contain exactly {FORMAL_TASK_COUNT} entries")

    try:
        dataset = list(get_benchmark_dataset())
    except Exception as exc:
        errors.append(f"failed to load live benchmark dataset: {type(exc).__name__}: {exc}")
        dataset = []
    if len(dataset) != FORMAL_TASK_COUNT:
        errors.append(
            f"live benchmark dataset must contain exactly {FORMAL_TASK_COUNT} tasks, "
            f"got {len(dataset)}"
        )

    tool_names = _registered_tool_names()
    assertion_names = set(AssertionRegistry._handlers)
    for index, (row, pinned) in enumerate(zip(dataset, manifest_tasks, strict=False), start=1):
        if not isinstance(pinned, dict):
            errors.append(f"tasks[{index - 1}] must be an object")
            continue
        try:
            info = _task_info(row)
        except Exception as exc:
            errors.append(f"T{index:02d}: invalid live task info: {exc}")
            continue
        expected_id = f"T{index:02d}"
        live_id = info.get("task_id")
        live_name = info.get("task_name")
        if live_id != expected_id:
            errors.append(f"T{index:02d}: live task_id must be {expected_id}, got {live_id!r}")
        if pinned.get("task_id") != live_id:
            errors.append(
                f"T{index:02d}: manifest task_id {pinned.get('task_id')!r} "
                f"does not match live {live_id!r}"
            )
        if pinned.get("task_name") != live_name:
            errors.append(
                f"{expected_id}: manifest task_name {pinned.get('task_name')!r} "
                f"does not match live {live_name!r}"
            )

        assertions = info.get("assertions")
        tools = info.get("zapier_tools")
        initial_state = info.get("initial_state")
        if not isinstance(initial_state, dict):
            errors.append(f"{expected_id}: initial_state must be an object")
        if not isinstance(assertions, list) or not assertions:
            errors.append(f"{expected_id}: assertions must be a non-empty list")
            assertions = []
        if not isinstance(tools, list) or not tools:
            errors.append(f"{expected_id}: zapier_tools must be a non-empty list")
            tools = []

        points = 0
        for assertion in assertions:
            if not isinstance(assertion, dict):
                errors.append(f"{expected_id}: every assertion must be an object")
                continue
            assertion_type = assertion.get("type")
            if assertion_type not in assertion_names:
                errors.append(f"{expected_id}: assertion {assertion_type!r} is not registered")
            point_value = assertion.get("points")
            if not isinstance(point_value, int) or point_value <= 0:
                errors.append(f"{expected_id}: assertion points must be positive integers")
            else:
                points += point_value
        if points != 100:
            errors.append(f"{expected_id}: assertion points must sum to 100, got {points}")

        unknown_tools = sorted(set(tools) - tool_names)
        if unknown_tools:
            errors.append(f"{expected_id}: unregistered tools: {unknown_tools}")

        try:
            live_hash = task_contract_sha256(
                example_id=row["example_id"],
                prompt=row["prompt"],
                info=info,
            )
        except Exception as exc:
            errors.append(f"{expected_id}: failed to hash live task contract: {exc}")
        else:
            if pinned.get("task_contract_sha256") != live_hash:
                errors.append(
                    f"{expected_id}: task_contract_sha256 mismatch: "
                    f"manifest={pinned.get('task_contract_sha256')!r}, live={live_hash!r}"
                )

    score_outputs = manifest.get("score_outputs")
    if not isinstance(score_outputs, list):
        errors.append("score_outputs must be a list")
    else:
        missing_outputs = sorted(REQUIRED_SCORE_FIELDS - set(score_outputs))
        if missing_outputs:
            errors.append(f"score_outputs missing required fields: {missing_outputs}")

    models = manifest.get("models")
    if not isinstance(models, list) or not models:
        errors.append("models must be a non-empty list")
        models = []
    run_ids: list[str] = []
    required_model_fields = {
        "run_id",
        "model",
        "api",
        "base_url",
        "env_file",
        "source_key_var",
        "runtime_key_var",
        "reasoning_effort",
    }
    for index, model in enumerate(models):
        if not isinstance(model, dict):
            errors.append(f"models[{index}] must be an object")
            continue
        missing = sorted(required_model_fields - set(model))
        if missing:
            errors.append(f"models[{index}] missing fields: {missing}")
            continue
        run_ids.append(str(model["run_id"]))
        if model["api"] not in SUPPORTED_APIS:
            errors.append(f"{model['run_id']}: unsupported api {model['api']!r}")
        env_file = Path(str(model["env_file"])).expanduser()
        if not env_file.is_file():
            errors.append(f"{model['run_id']}: env_file does not exist: {env_file}")
            continue
        values = dotenv_values(env_file)
        source_var = str(model["source_key_var"])
        if not values.get(source_var):
            errors.append(f"{model['run_id']}: {source_var} is missing or empty in env_file")
    if len(run_ids) != len(set(run_ids)):
        errors.append("model run_id values must be unique")
    return errors


def _verify_task_result(
    task: Any,
    expected: dict[str, Any],
    index: int,
) -> list[str]:
    errors: list[str] = []
    label = expected["task_name"]
    if not isinstance(task, dict):
        return [f"task {index} ({label}) must be an object"]
    if task.get("name") != label:
        errors.append(f"task {index}: expected name {label!r}, got {task.get('name')!r}")
    missing = sorted(REQUIRED_SCORE_FIELDS - set(task))
    if missing:
        errors.append(f"{label}: missing required result fields: {missing}")
    partial_credit = task.get("partial_credit")
    if not isinstance(partial_credit, (int, float)) or not 0 <= partial_credit <= 1:
        errors.append(f"{label}: partial_credit must be between 0 and 1")
    weighted_score = task.get("weighted_score")
    if not isinstance(weighted_score, (int, float)) or not 0 <= weighted_score <= 100:
        errors.append(f"{label}: weighted_score must be between 0 and 100")
    if not isinstance(task.get("strict_pass"), bool):
        errors.append(f"{label}: strict_pass must be boolean")
    for field in ("hard_fail_reasons", "assertion_results", "trajectory", "technical_errors"):
        if field in task and not isinstance(task[field], list):
            errors.append(f"{label}: {field} must be a list")
    if task.get("task_contract_schema") != TASK_CONTRACT_SCHEMA:
        errors.append(f"{label}: task_contract_schema does not match the formal contract schema")
    if task.get("task_contract_sha256") != expected["task_contract_sha256"]:
        errors.append(
            f"{label}: task_contract_sha256 does not match the pinned manifest contract"
        )
    return errors


def verify_result_file(
    result_path: Path | str,
    manifest: dict[str, Any],
    *,
    expected_model: str | None = None,
    expected_batch_id: str | None = None,
) -> list[str]:
    """Verify that an export is exactly the pinned eight-task formal run."""
    path = Path(result_path)
    if not path.is_file():
        return [f"result file does not exist: {path}"]
    try:
        result = _load_json(path)
    except Exception as exc:
        return [f"result file is not valid JSON: {type(exc).__name__}: {exc}"]

    errors: list[str] = []
    tasks = result.get("tasks")
    if not isinstance(tasks, list):
        return ["result tasks must be a list"]
    expected_count = int(manifest.get("task_count", FORMAL_TASK_COUNT))
    meta = result.get("meta")
    if not isinstance(meta, dict):
        errors.append("result meta must be an object")
        meta = {}
    if meta.get("total_tasks") != expected_count:
        errors.append(
            f"result meta expected {expected_count} tasks, got {meta.get('total_tasks')!r}"
        )
    if len(tasks) != expected_count:
        errors.append(f"result expected {expected_count} tasks, got {len(tasks)}")
    if meta.get("toolset") != manifest.get("toolset"):
        errors.append(
            f"result toolset must be {manifest.get('toolset')!r}, got {meta.get('toolset')!r}"
        )
    if meta.get("max_steps") != manifest.get("max_steps"):
        errors.append(
            f"result max_steps must be {manifest.get('max_steps')!r}, "
            f"got {meta.get('max_steps')!r}"
        )
    if expected_model is not None and meta.get("model") != expected_model:
        errors.append(
            f"result model must be {expected_model!r}, got {meta.get('model')!r}"
        )
    if expected_batch_id is not None:
        formal_runner = meta.get("formal_runner")
        actual_batch_id = (
            formal_runner.get("batch_id") if isinstance(formal_runner, dict) else None
        )
        if actual_batch_id != expected_batch_id:
            errors.append(
                f"result formal_runner batch_id must be {expected_batch_id!r}, "
                f"got {actual_batch_id!r}"
            )

    expected_tasks = manifest.get("tasks") or []
    for index, (task, expected) in enumerate(zip(tasks, expected_tasks, strict=False), start=1):
        errors.extend(_verify_task_result(task, expected, index))
    actual_names = [task.get("name") for task in tasks if isinstance(task, dict)]
    expected_names = [item["task_name"] for item in expected_tasks]
    if actual_names != expected_names:
        errors.append("result task names/order do not match the pinned eight-task manifest")
    return errors


def build_eval_command(
    manifest: dict[str, Any],
    model: dict[str, Any],
    output_path: Path | str,
    *,
    task_names: list[str] | None = None,
    max_concurrent: int | None = None,
    reasoning_effort: str | None = None,
    max_steps: int | None = None,
) -> list[str]:
    """Build a key-free AutomationBench command for one model."""
    names = task_names or [item["task_name"] for item in manifest["tasks"]]
    concurrency = (
        max_concurrent
        if max_concurrent is not None
        else manifest["max_concurrent_tasks_per_model"]
    )
    command = [
        sys.executable,
        "-m",
        "automationbench.scripts.eval",
        "--model",
        str(model["model"]),
        "--domains",
        str(manifest["domain"]),
        "--toolset",
        str(manifest["toolset"]),
        "--base-url",
        str(model["base_url"]),
        "--api",
        str(model["api"]),
        "--api-key-var",
        str(model["runtime_key_var"]),
        "--max-steps",
        str(max_steps if max_steps is not None else manifest["max_steps"]),
        "--max-concurrent",
        str(concurrency),
        "--tasks",
        ",".join(names),
        "--save-every",
        "1",
        "--export-json",
        str(output_path),
        "--no-ensure-complete",
    ]
    effort = reasoning_effort if reasoning_effort is not None else model.get("reasoning_effort")
    if effort:
        command.extend(["--reasoning-effort", str(effort)])
    return command


def classify_technical_error(message: str) -> str:
    """Map provider/runtime failures to a stable technical category."""
    text = message.lower()
    if any(
        word in text
        for word in (
            "arrearage",
            "arrears",
            "overdue payment",
            "insufficient balance",
            "top up",
            "欠费",
            "充值",
        )
    ):
        return "billing"
    if any(
        word in text
        for word in (
            "authentication",
            "unauthorized",
            "invalid api key",
            "incorrect api key",
            "permission denied",
            "forbidden",
        )
    ):
        return "authentication"
    if any(word in text for word in ("model_not_found", "model not found", "unknown model")):
        return "model_not_found"
    if any(word in text for word in ("rate limit", "rate_limit", "too many requests", "429")):
        return "rate_limit"
    if any(word in text for word in ("timeout", "timed out", "deadline exceeded")):
        return "timeout"
    if any(
        word in text
        for word in (
            "connection error",
            "connection reset",
            "connection refused",
            "dns",
            "network",
        )
    ):
        return "network"
    if any(
        word in text
        for word in (
            "bad request",
            "unsupported",
            "invalid_request",
            "tool call",
            "function call",
        )
    ):
        return "tool_protocol"
    if any(word in text for word in ("internal error", "upstream", "service unavailable", "5xx")):
        return "provider"
    return "unknown"


def _runtime_environment(model: dict[str, Any]) -> tuple[dict[str, str], str]:
    env_file = Path(str(model["env_file"])).expanduser()
    values = dotenv_values(env_file)
    source_var = str(model["source_key_var"])
    key = values.get(source_var)
    if not key:
        raise RuntimeError(f"{source_var} is missing or empty in {env_file}")
    runtime_var = str(model["runtime_key_var"])
    env = os.environ.copy()
    for name, value in values.items():
        if value is not None:
            env[str(name)] = str(value)
    env[runtime_var] = str(key)
    return env, str(key)


def _preflight_tool_schema(*, responses_api: bool) -> dict[str, Any]:
    parameters = {
        "type": "object",
        "properties": {"value": {"type": "string"}},
        "required": ["value"],
        "additionalProperties": False,
    }
    if responses_api:
        return {
            "type": "function",
            "name": "formal_preflight_echo",
            "description": "Return the requested preflight value.",
            "parameters": parameters,
        }
    return {
        "type": "function",
        "function": {
            "name": "formal_preflight_echo",
            "description": "Return the requested preflight value.",
            "parameters": parameters,
        },
    }


def preflight_tool_choice(*, responses_api: bool) -> Any:
    """Return a tool-choice form accepted by ordinary and thinking APIs."""
    if responses_api:
        return {"type": "function", "name": "formal_preflight_echo"}
    # DeepSeek and Kimi thinking modes reject a forced function choice. The
    # live evaluator also leaves tool selection automatic, so this mirrors it.
    return "auto"


def preflight_model(model: dict[str, Any], attempts: int = 2) -> dict[str, Any]:
    """Verify endpoint, auth, model ID, protocol, and function-tool support."""
    started = time.monotonic()
    record: dict[str, Any] = {
        "run_id": model["run_id"],
        "model": model["model"],
        "api": model["api"],
        "base_url": model["base_url"],
        "started_at": _now(),
        "status": "technical_failure",
        "tool_call_verified": False,
    }
    try:
        _, key = _runtime_environment(model)
    except Exception as exc:
        record.update(
            {
                "category": "authentication",
                "error_type": type(exc).__name__,
                "error": str(exc),
                "duration_seconds": round(time.monotonic() - started, 3),
            }
        )
        return record

    last_error: Exception | None = None
    for attempt in range(1, max(1, attempts) + 1):
        client = openai.OpenAI(
            api_key=key,
            base_url=str(model["base_url"]),
            timeout=120.0,
            max_retries=0,
        )
        try:
            effort = model.get("reasoning_effort")
            if model["api"] == "responses":
                kwargs: dict[str, Any] = {
                    "model": model["model"],
                    "input": (
                        "Call formal_preflight_echo exactly once with value "
                        "'FORMAL_AGENT_SUITE_OK'. Do not answer in plain text."
                    ),
                    "tools": [_preflight_tool_schema(responses_api=True)],
                    "tool_choice": preflight_tool_choice(responses_api=True),
                    "max_output_tokens": 512,
                }
                if effort:
                    kwargs["reasoning"] = {"effort": effort}
                response = client.responses.create(**kwargs)
                tool_called = any(
                    getattr(item, "type", None) == "function_call"
                    and getattr(item, "name", None) == "formal_preflight_echo"
                    for item in getattr(response, "output", [])
                )
            else:
                kwargs = {
                    "model": model["model"],
                    "messages": [
                        {
                            "role": "user",
                            "content": (
                                "Call formal_preflight_echo exactly once with value "
                                "'FORMAL_AGENT_SUITE_OK'. Do not answer in plain text."
                            ),
                        }
                    ],
                    "tools": [_preflight_tool_schema(responses_api=False)],
                    "tool_choice": preflight_tool_choice(responses_api=False),
                }
                if effort:
                    kwargs["reasoning_effort"] = effort
                response = client.chat.completions.create(**kwargs)
                message = response.choices[0].message
                tool_called = any(
                    call.function.name == "formal_preflight_echo"
                    for call in (message.tool_calls or [])
                )
            if not tool_called:
                raise RuntimeError("provider returned no formal_preflight_echo tool call")
            record.update(
                {
                    "status": "passed",
                    "tool_call_verified": True,
                    "attempts": attempt,
                    "duration_seconds": round(time.monotonic() - started, 3),
                    "completed_at": _now(),
                }
            )
            return record
        except Exception as exc:
            last_error = exc
            category = classify_technical_error(str(exc))
            if category in {"authentication", "billing", "model_not_found", "tool_protocol"}:
                break
            if attempt < attempts:
                time.sleep(min(4.0, 2.0**attempt))
        finally:
            client.close()

    error_text = str(last_error) if last_error else "unknown preflight failure"
    record.update(
        {
            "category": classify_technical_error(error_text),
            "error_type": type(last_error).__name__ if last_error else "RuntimeError",
            "error": error_text,
            "attempts": max(1, attempts),
            "duration_seconds": round(time.monotonic() - started, 3),
            "completed_at": _now(),
        }
    )
    return record


def _redact(text: str, secret: str) -> str:
    if not secret:
        return text
    return text.replace(secret, "[REDACTED]")


def _run_eval_process(
    command: list[str],
    *,
    env: dict[str, str],
    secret: str,
    log_path: Path,
    cwd: Path,
    timeout_seconds: int,
) -> dict[str, Any]:
    started = time.monotonic()
    process: subprocess.Popen[str] | None = None
    try:
        # Keep each isolated task in its own process group. A timed-out
        # provider request can otherwise leave child processes alive and hold
        # the runner's pipes open, making the next task appear hung.
        process = subprocess.Popen(
            command,
            cwd=cwd,
            env=env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
        try:
            output, _ = process.communicate(timeout=timeout_seconds)
        except subprocess.TimeoutExpired as exc:
            output = (exc.stdout or "") if isinstance(exc.stdout, str) else ""
            output += "\nFORMAL_RUNNER_TIMEOUT\n"
            if process.poll() is None:
                try:
                    os.killpg(process.pid, signal.SIGTERM)
                except ProcessLookupError:
                    pass
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    try:
                        os.killpg(process.pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                    process.wait()
            returncode = 124
            timed_out = True
        else:
            returncode = process.returncode
            timed_out = False
    except Exception as exc:
        output = f"FORMAL_RUNNER_EXCEPTION: {type(exc).__name__}: {exc}\n"
        returncode = 1
        timed_out = False
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.write_text(_redact(output, secret), encoding="utf-8")
    return {
        "returncode": returncode,
        "timed_out": timed_out,
        "duration_seconds": round(time.monotonic() - started, 3),
        "log_path": str(log_path),
    }


def _task_technical_issues(task: dict[str, Any], max_steps: int) -> list[dict[str, str]]:
    issues: list[dict[str, str]] = []
    for message in task.get("technical_errors") or []:
        issues.append({"category": classify_technical_error(str(message)), "message": str(message)})
    trajectory = task.get("trajectory") or []
    if trajectory:
        last = trajectory[-1]
        if (
            isinstance(last, dict)
            and last.get("role") == "assistant"
            and last.get("tool_calls")
            and int(task.get("steps", 0) or 0) < max_steps - 2
        ):
            issues.append(
                {
                    "category": "provider",
                    "message": "trajectory ended on unexecuted tool calls before the step cap",
                }
            )
    return issues


def resume_status_for_verified_result(
    *,
    run_id: str,
    output_path: Path,
    result: dict[str, Any],
    manifest: dict[str, Any],
    previous_status: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the status record for a result reused by ``--resume``."""
    max_steps = int(manifest["max_steps"])
    remaining_technical = {
        task["name"]: _task_technical_issues(task, max_steps)
        for task in result.get("tasks") or []
        if _task_technical_issues(task, max_steps)
    }
    previous_status = previous_status or {}
    return {
        "run_id": run_id,
        "status": "valid_with_technical_failures" if remaining_technical else "valid",
        "completed_at": _now(),
        "process": previous_status.get("process", {"reused": True}),
        "verification_errors": [],
        "remaining_technical_failures": remaining_technical,
        "output_path": str(output_path),
    }


def _recompute_result_summary(result: dict[str, Any]) -> None:
    tasks = result.get("tasks") or []
    summary = result.setdefault("summary", {})
    summary.update(
        {
            "avg_score": (
                sum(float(task.get("partial_credit", 0.0)) for task in tasks) / len(tasks)
                if tasks
                else 0.0
            ),
            "avg_weighted_score": (
                sum(float(task.get("weighted_score", 0.0)) for task in tasks) / len(tasks)
                if tasks
                else 0.0
            ),
            "pass_rate": (
                sum(1 for task in tasks if task.get("strict_pass") is True) / len(tasks)
                if tasks
                else 0.0
            ),
            "passed_count": sum(1 for task in tasks if task.get("strict_pass") is True),
            "failed_count": sum(1 for task in tasks if task.get("strict_pass") is not True),
            "total_input_tokens": sum(int(task.get("input_tokens", 0) or 0) for task in tasks),
            "total_output_tokens": sum(int(task.get("output_tokens", 0) or 0) for task in tasks),
            "total_cached_input_tokens": sum(
                int(task.get("cached_input_tokens", 0) or 0) for task in tasks
            ),
            "total_reasoning_tokens": sum(
                int(task.get("reasoning_tokens", 0) or 0) for task in tasks
            ),
            "total_tool_calls": sum(int(task.get("num_tool_calls", 0) or 0) for task in tasks),
            "total_model_time_s": round(
                sum(float(task.get("model_time_s", 0.0) or 0.0) for task in tasks), 3
            ),
            "total_tool_time_s": round(
                sum(float(task.get("tool_time_s", 0.0) or 0.0) for task in tasks), 3
            ),
            "total_cost": sum(float(task.get("cost", 0.0) or 0.0) for task in tasks),
            "tasks_with_errors": sum(1 for task in tasks if task.get("technical_errors")),
        }
    )
    result.setdefault("meta", {})["total_tasks"] = len(tasks)


def _merge_retry(
    main_result: dict[str, Any],
    retry_result: dict[str, Any],
    task_name: str,
) -> bool:
    retry_tasks = retry_result.get("tasks") or []
    if len(retry_tasks) != 1 or retry_tasks[0].get("name") != task_name:
        return False
    replacement = retry_tasks[0]
    for index, task in enumerate(main_result.get("tasks") or []):
        if task.get("name") == task_name:
            replacement["id"] = task.get("id", index + 1)
            main_result["tasks"][index] = replacement
            _recompute_result_summary(main_result)
            return True
    return False


def _result_from_tasks(
    manifest: dict[str, Any],
    model: dict[str, Any],
    tasks: list[dict[str, Any]],
    *,
    duration_seconds: float,
    formal_runner: dict[str, Any],
    reasoning_effort: str | None,
    max_steps: int | None,
) -> dict[str, Any]:
    """Build a formal-shaped result from independently completed task exports."""
    by_name = {str(task.get("name")): task for task in tasks}
    ordered_tasks: list[dict[str, Any]] = []
    for index, item in enumerate(manifest["tasks"], start=1):
        task = by_name.get(str(item["task_name"]))
        if task is None:
            continue
        task["id"] = index
        ordered_tasks.append(task)

    result: dict[str, Any] = {
        "meta": {
            "timestamp": _now(),
            "model": model["model"],
            "toolset": manifest["toolset"],
            "domains": [manifest["domain"]],
            "total_tasks": len(ordered_tasks),
            "duration_seconds": round(duration_seconds, 3),
            "reasoning_effort": reasoning_effort or model.get("reasoning_effort"),
            "max_steps": max_steps if max_steps is not None else manifest["max_steps"],
            "formal_runner": formal_runner,
        },
        "tasks": ordered_tasks,
        "usage_by_task": [
            {
                "task_id": task.get("id"),
                "task_name": task.get("name"),
                "input_tokens": task.get("input_tokens", 0),
                "output_tokens": task.get("output_tokens", 0),
                "total_tokens": int(task.get("input_tokens", 0) or 0)
                + int(task.get("output_tokens", 0) or 0),
                "cost": task.get("cost"),
            }
            for task in ordered_tasks
        ],
    }
    _recompute_result_summary(result)
    return result


def _run_model_isolated(
    manifest: dict[str, Any],
    model: dict[str, Any],
    batch_dir: Path,
    repo_root: Path,
    *,
    env: dict[str, str],
    secret: str,
    status_path: Path,
    output_path: Path,
    technical_retries: int,
    timeout_seconds: int,
    reasoning_effort: str | None,
    max_steps: int | None,
) -> dict[str, Any]:
    """Run each task in its own process and checkpoint after every task."""
    started = time.monotonic()
    run_id = str(model["run_id"])
    effective_max_steps = max_steps if max_steps is not None else manifest["max_steps"]
    task_dir = batch_dir / "isolated" / run_id
    task_dir.mkdir(parents=True, exist_ok=True)
    partial_path = output_path.with_suffix(".partial.json")
    completed: list[dict[str, Any]] = []
    process_records: list[dict[str, Any]] = []
    failures: dict[str, str] = {}
    expected_by_name = {item["task_name"]: item for item in manifest["tasks"]}

    for item in manifest["tasks"]:
        task_name = str(item["task_name"])
        task_id = str(item["task_id"]).lower()
        task_path = task_dir / f"{task_id}.json"
        task_log = task_dir / f"{task_id}.log"
        task_result: dict[str, Any] | None = None
        last_process: dict[str, Any] | None = None

        # A previous isolated run may already have a verified task export.
        # Reuse it so a fallback run only spends tokens on unfinished tasks.
        if task_path.is_file():
            try:
                existing = _load_json(task_path)
                candidates = existing.get("tasks") or []
                if len(candidates) == 1 and candidates[0].get("name") == task_name:
                    verification_errors = _verify_task_result(
                        candidates[0],
                        expected_by_name[task_name],
                        1,
                    )
                    if not verification_errors and not _task_technical_issues(
                        candidates[0],
                        effective_max_steps,
                    ):
                        task_result = candidates[0]
                        completed.append(task_result)
                        print(
                            f"[isolated] {run_id} {task_name}: reused verified result",
                            flush=True,
                        )
            except Exception:
                task_result = None

        if task_result is not None:
            partial = _result_from_tasks(
                manifest,
                model,
                completed,
                duration_seconds=time.monotonic() - started,
                formal_runner={
                    "batch_id": manifest["batch_id"],
                    "status": "partial",
                    "completed_at": _now(),
                    "client_retry_attempts": manifest["client_retry_attempts"],
                    "processes": process_records,
                    "failures": failures,
                },
                reasoning_effort=reasoning_effort,
                max_steps=max_steps,
            )
            _write_json(partial_path, partial)
            continue

        for attempt in range(technical_retries + 1):
            if task_path.exists():
                task_path.unlink()
            last_process = _run_eval_process(
                build_eval_command(
                    manifest,
                    model,
                    task_path,
                    task_names=[task_name],
                    max_concurrent=1,
                    reasoning_effort=reasoning_effort,
                    max_steps=max_steps,
                ),
                env=env,
                secret=secret,
                log_path=task_log,
                cwd=repo_root,
                timeout_seconds=timeout_seconds,
            )
            process_records.append(
                {
                    "task_name": task_name,
                    "attempt": attempt + 1,
                    **last_process,
                }
            )
            if not task_path.is_file():
                continue
            try:
                candidate = _load_json(task_path)
                candidates = candidate.get("tasks") or []
                if len(candidates) != 1 or candidates[0].get("name") != task_name:
                    continue
                verification_errors = _verify_task_result(
                    candidates[0],
                    expected_by_name[task_name],
                    1,
                )
                if verification_errors or _task_technical_issues(
                    candidates[0],
                    effective_max_steps,
                ):
                    continue
                task_result = candidates[0]
                break
            except Exception:
                continue

        if task_result is None:
            failures[task_name] = (
                "isolated task produced no verified result"
                if last_process is None
                else (
                    "isolated task timed out"
                    if last_process.get("timed_out")
                    else "isolated task failed after retries"
                )
            )
        else:
            completed.append(task_result)

        partial = _result_from_tasks(
            manifest,
            model,
            completed,
            duration_seconds=time.monotonic() - started,
            formal_runner={
                "batch_id": manifest["batch_id"],
                "status": "partial",
                "completed_at": _now(),
                "client_retry_attempts": manifest["client_retry_attempts"],
                "processes": process_records,
                "failures": failures,
            },
            reasoning_effort=reasoning_effort,
            max_steps=max_steps,
        )
        _write_json(partial_path, partial)
        print(
            f"[isolated] {run_id} {task_name}: "
            + ("verified" if task_result is not None else failures[task_name]),
            flush=True,
        )

    if failures:
        status = {
            "run_id": run_id,
            "status": "technical_failure",
            "completed_at": _now(),
            "category": "timeout" if any(
                "timed out" in message for message in failures.values()
            ) else "runner",
            "error": "one or more isolated tasks did not produce verified results",
            "failures": failures,
            "partial_output_path": str(partial_path),
            "processes": process_records,
        }
        _write_json(status_path, status)
        return status

    result = _result_from_tasks(
        manifest,
        model,
        completed,
        duration_seconds=time.monotonic() - started,
        formal_runner={
            "batch_id": manifest["batch_id"],
            "completed_at": _now(),
            "client_retry_attempts": manifest["client_retry_attempts"],
            "processes": process_records,
            "isolated_tasks": True,
        },
        reasoning_effort=reasoning_effort,
        max_steps=max_steps,
    )
    _write_json(output_path, result)
    validation_manifest = {**manifest, "max_steps": effective_max_steps}
    verification_errors = verify_result_file(
        output_path,
        validation_manifest,
        expected_model=str(model["model"]),
        expected_batch_id=str(manifest["batch_id"]),
    )
    status = {
        "run_id": run_id,
        "status": "valid" if not verification_errors else "invalid_result",
        "completed_at": _now(),
        "verification_errors": verification_errors,
        "output_path": str(output_path),
        "partial_output_path": str(partial_path),
        "processes": process_records,
    }
    _write_json(status_path, status)
    return status


def run_model(
    manifest: dict[str, Any],
    model: dict[str, Any],
    batch_dir: Path,
    repo_root: Path,
    *,
    technical_retries: int,
    timeout_seconds: int,
    reasoning_effort: str | None = None,
    task_concurrency: int | None = None,
    isolate_tasks: bool = False,
    max_steps: int | None = None,
) -> dict[str, Any]:
    """Run one model over all eight tasks and retry only technical task failures."""
    run_id = str(model["run_id"])
    effective_max_steps = max_steps if max_steps is not None else manifest["max_steps"]
    output_path = batch_dir / f"{run_id}.json"
    status_path = batch_dir / "status" / f"{run_id}.json"
    _write_json(
        status_path,
        {
            "run_id": run_id,
            "status": "running",
            "started_at": _now(),
            "output_path": str(output_path),
        },
    )
    env, secret = _runtime_environment(model)
    env["AUTO_BENCH_RETRY_MAX_ATTEMPTS"] = str(manifest["client_retry_attempts"])
    if isolate_tasks:
        return _run_model_isolated(
            manifest,
            model,
            batch_dir,
            repo_root,
            env=env,
            secret=secret,
            status_path=status_path,
            output_path=output_path,
            technical_retries=technical_retries,
            timeout_seconds=timeout_seconds,
            reasoning_effort=reasoning_effort,
            max_steps=max_steps,
        )
    process = _run_eval_process(
        build_eval_command(
            manifest,
            model,
            output_path,
            max_concurrent=task_concurrency,
            reasoning_effort=reasoning_effort,
            max_steps=max_steps,
        ),
        env=env,
        secret=secret,
        log_path=batch_dir / "logs" / f"{run_id}.log",
        cwd=repo_root,
        timeout_seconds=timeout_seconds,
    )

    if not output_path.is_file():
        status = {
            "run_id": run_id,
            "status": "technical_failure",
            "completed_at": _now(),
            "process": process,
            "category": "timeout" if process["timed_out"] else "runner",
            "error": "evaluation process produced no result file",
        }
        _write_json(status_path, status)
        return status

    try:
        result = _load_json(output_path)
    except Exception as exc:
        status = {
            "run_id": run_id,
            "status": "invalid_result",
            "completed_at": _now(),
            "process": process,
            "error": f"{type(exc).__name__}: {exc}",
        }
        _write_json(status_path, status)
        return status

    retry_history: list[dict[str, Any]] = []
    expected_by_name = {item["task_name"]: item for item in manifest["tasks"]}
    for attempt in range(1, technical_retries + 1):
        affected = [
            task["name"]
            for task in result.get("tasks") or []
            if _task_technical_issues(task, effective_max_steps)
        ]
        if not affected:
            break
        for task_name in affected:
            retry_path = (
                batch_dir
                / "retries"
                / run_id
                / f"attempt-{attempt}-{task_name.rsplit('.', 1)[-1]}.json"
            )
            retry_process = _run_eval_process(
                build_eval_command(
                    manifest,
                    model,
                    retry_path,
                    task_names=[task_name],
                    max_concurrent=1,
                    reasoning_effort=reasoning_effort,
                    max_steps=max_steps,
                ),
                env=env,
                secret=secret,
                log_path=retry_path.with_suffix(".log"),
                cwd=repo_root,
                timeout_seconds=timeout_seconds,
            )
            retry_record: dict[str, Any] = {
                "attempt": attempt,
                "task_name": task_name,
                "process": retry_process,
                "merged": False,
            }
            if retry_path.is_file():
                try:
                    retry_result = _load_json(retry_path)
                    retry_tasks = retry_result.get("tasks") or []
                    task_errors = (
                        _verify_task_result(retry_tasks[0], expected_by_name[task_name], 1)
                        if len(retry_tasks) == 1
                        else ["retry result must contain exactly one task"]
                    )
                    retry_record["verification_errors"] = task_errors
                    if (
                        not task_errors
                        and not _task_technical_issues(
                            retry_tasks[0],
                            effective_max_steps,
                        )
                    ):
                        retry_record["merged"] = _merge_retry(result, retry_result, task_name)
                except Exception as exc:
                    retry_record["verification_errors"] = [
                        f"{type(exc).__name__}: {exc}"
                    ]
            retry_history.append(retry_record)

    result.setdefault("meta", {})["formal_runner"] = {
        "batch_id": manifest["batch_id"],
        "completed_at": _now(),
        "process": process,
        "client_retry_attempts": manifest["client_retry_attempts"],
        "technical_retry_history": retry_history,
    }
    _recompute_result_summary(result)
    _write_json(output_path, result)
    validation_manifest = {**manifest, "max_steps": effective_max_steps}
    verification_errors = verify_result_file(
        output_path,
        validation_manifest,
        expected_model=str(model["model"]),
        expected_batch_id=str(manifest["batch_id"]),
    )
    remaining_technical = {
        task["name"]: _task_technical_issues(task, effective_max_steps)
        for task in result.get("tasks") or []
        if _task_technical_issues(task, effective_max_steps)
    }
    status = {
        "run_id": run_id,
        "status": "valid_with_technical_failures" if remaining_technical else "valid",
        "completed_at": _now(),
        "process": process,
        "verification_errors": verification_errors,
        "remaining_technical_failures": remaining_technical,
        "output_path": str(output_path),
    }
    if verification_errors:
        status["status"] = "invalid_result"
    _write_json(status_path, status)
    return status


def summarize_results(
    results: dict[str, dict[str, Any]],
    manifest: dict[str, Any],
    preflights: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Compute capability metrics without counting technical failures as model failures."""
    preflights = preflights or {}
    model_summaries: dict[str, Any] = {}
    for model in manifest.get("models") or []:
        run_id = str(model["run_id"])
        if run_id not in results and run_id not in preflights:
            continue
        result = results.get(run_id)
        if result is None:
            model_summaries[run_id] = {
                "model": model["model"],
                "provider_preflight": preflights.get(run_id),
                "raw_task_count": 0,
                "capability_task_count": 0,
                "technical_failure_count": FORMAL_TASK_COUNT,
                "avg_weighted_score": None,
                "strict_pass_rate": None,
                "strict_pass_count": 0,
                "status": "technical_failure",
            }
            continue

        technical_failures: list[dict[str, Any]] = []
        capability_tasks: list[dict[str, Any]] = []
        for task in result.get("tasks") or []:
            issues = _task_technical_issues(task, manifest["max_steps"])
            if issues:
                technical_failures.append({"task_name": task.get("name"), "issues": issues})
            else:
                capability_tasks.append(task)
        capability_count = len(capability_tasks)
        avg_weighted = (
            sum(float(task["weighted_score"]) for task in capability_tasks) / capability_count
            if capability_count
            else None
        )
        strict_count = sum(1 for task in capability_tasks if task.get("strict_pass") is True)
        strict_rate = strict_count / capability_count if capability_count else None
        model_summaries[run_id] = {
            "model": model["model"],
            "provider_preflight": preflights.get(run_id),
            "raw_task_count": len(result.get("tasks") or []),
            "capability_task_count": capability_count,
            "technical_failure_count": len(technical_failures),
            "technical_failures": technical_failures,
            "avg_weighted_score": avg_weighted,
            "strict_pass_rate": strict_rate,
            "strict_pass_count": strict_count,
            "status": "complete" if not technical_failures else "partial_technical",
        }

    ranking = [
        {
            "run_id": run_id,
            "model": item["model"],
            "avg_weighted_score": item["avg_weighted_score"],
            "strict_pass_rate": item["strict_pass_rate"],
            "capability_task_count": item["capability_task_count"],
            "technical_failure_count": item["technical_failure_count"],
        }
        for run_id, item in model_summaries.items()
        if item["avg_weighted_score"] is not None
    ]
    ranking.sort(
        key=lambda item: (
            float(item["strict_pass_rate"]),
            float(item["avg_weighted_score"]),
            item["capability_task_count"],
        ),
        reverse=True,
    )
    for index, item in enumerate(ranking, start=1):
        item["rank"] = index
    return {
        "manifest_schema": manifest.get("manifest_schema"),
        "batch_id": manifest.get("batch_id"),
        "generated_at": _now(),
        "task_count": manifest.get("task_count"),
        "models": model_summaries,
        "ranking": ranking,
    }


def _summary_markdown(summary: dict[str, Any]) -> str:
    lines = [
        f"# Formal Agent Suite: {summary.get('batch_id')}",
        "",
        "| Rank | Model | Valid capability tasks | Technical failures | "
        "Avg weighted score | Strict pass rate |",
        "|---:|---|---:|---:|---:|---:|",
    ]
    for item in summary.get("ranking") or []:
        lines.append(
            f"| {item['rank']} | {item['model']} | {item['capability_task_count']} | "
            f"{item['technical_failure_count']} | {item['avg_weighted_score']:.2f} | "
            f"{item['strict_pass_rate']:.2%} |"
        )
    failed = [
        (run_id, item)
        for run_id, item in (summary.get("models") or {}).items()
        if item.get("avg_weighted_score") is None
    ]
    if failed:
        lines.extend(["", "## Technical preflight failures", ""])
        for run_id, item in failed:
            preflight = item.get("provider_preflight") or {}
            lines.append(
                f"- `{run_id}`: {preflight.get('category', 'unknown')} "
                f"({preflight.get('error_type', 'unknown')})"
            )
    return "\n".join(lines) + "\n"


def _selected_models(
    manifest: dict[str, Any],
    selected_run_ids: list[str] | None,
) -> list[dict[str, Any]]:
    models = manifest["models"]
    if not selected_run_ids:
        return list(models)
    by_id = {str(model["run_id"]): model for model in models}
    unknown = sorted(set(selected_run_ids) - set(by_id))
    if unknown:
        raise ValueError(f"unknown model run_ids: {unknown}")
    return [by_id[run_id] for run_id in selected_run_ids]


def run_batch(
    manifest_path: Path,
    *,
    selected_run_ids: list[str] | None = None,
    preflight_only: bool = False,
    resume: bool = False,
    force: bool = False,
    technical_retries: int = 2,
    timeout_seconds: int = 14400,
    reasoning_effort: str | None = None,
    task_concurrency: int | None = None,
    isolate_tasks: bool = False,
    max_steps: int | None = None,
) -> int:
    manifest = _load_json(manifest_path)
    errors = validate_manifest(manifest)
    if errors:
        for error in errors:
            print(f"[manifest-error] {error}", file=sys.stderr)
        return 2

    output_dir = manifest.get("output_dir")
    if output_dir:
        output_path = Path(str(output_dir)).expanduser()
        batch_dir = (
            output_path
            if output_path.is_absolute()
            else manifest_path.parent / output_path
        )
    else:
        batch_dir = manifest_path.parent
    repo_root = Path(__file__).resolve().parents[2]
    models = _selected_models(manifest, selected_run_ids)
    print(
        f"[formal-suite] manifest valid: {manifest['task_count']} tasks, "
        f"{len(models)} selected models"
    )

    preflights: dict[str, dict[str, Any]] = {}
    results: dict[str, dict[str, Any]] = {}
    reused_run_ids: set[str] = set()
    preflight_models: list[dict[str, Any]] = []

    # A verified result is already bound to this manifest and does not need a
    # live provider check.  This keeps resume runs offline for completed models.
    if resume and not force and not preflight_only:
        for model in models:
            run_id = str(model["run_id"])
            output_path = batch_dir / f"{run_id}.json"
            if not output_path.is_file():
                preflight_models.append(model)
                continue
            existing = _load_json(output_path)
            existing_errors = verify_result_file(
                output_path,
                manifest,
                expected_model=str(model["model"]),
                expected_batch_id=str(manifest["batch_id"]),
            )
            if existing_errors:
                preflight_models.append(model)
                continue
            results[run_id] = existing
            reused_run_ids.add(run_id)
            status_path = batch_dir / "status" / f"{run_id}.json"
            previous_status = _load_json(status_path) if status_path.is_file() else None
            _write_json(
                status_path,
                resume_status_for_verified_result(
                    run_id=run_id,
                    output_path=output_path,
                    result=existing,
                    manifest=manifest,
                    previous_status=previous_status,
                ),
            )
            preflights[run_id] = {
                "run_id": run_id,
                "model": model["model"],
                "status": "reused",
                "source": "verified_result",
                "output_path": str(output_path),
                "completed_at": _now(),
            }
            print(f"[resume] {run_id}: using existing verified eight-task result")
    else:
        preflight_models = list(models)

    max_preflight_models = min(manifest["max_concurrent_models"], len(preflight_models))
    with concurrent.futures.ThreadPoolExecutor(
        max_workers=max(1, max_preflight_models)
    ) as executor:
        future_map = {
            executor.submit(preflight_model, model): model
            for model in preflight_models
        }
        for future in concurrent.futures.as_completed(future_map):
            model = future_map[future]
            run_id = str(model["run_id"])
            try:
                record = future.result()
            except Exception as exc:
                record = {
                    "run_id": run_id,
                    "model": model["model"],
                    "status": "technical_failure",
                    "category": classify_technical_error(str(exc)),
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                    "completed_at": _now(),
                }
            preflights[run_id] = record
            print(
                f"[preflight] {run_id}: {record['status']}"
                + (f" ({record.get('category')})" if record["status"] != "passed" else "")
            )
    _write_json(batch_dir / "preflight.json", preflights)
    if preflight_only:
        return 0 if all(item["status"] == "passed" for item in preflights.values()) else 3

    runnable: list[dict[str, Any]] = []
    for model in models:
        run_id = str(model["run_id"])
        if run_id in reused_run_ids:
            continue
        output_path = batch_dir / f"{run_id}.json"
        if output_path.exists() and not force:
            existing_errors = verify_result_file(
                output_path,
                manifest,
                expected_model=str(model["model"]),
                expected_batch_id=str(manifest["batch_id"]),
            )
            if preflights[run_id]["status"] != "passed":
                continue
            if resume and existing_errors:
                runnable.append(model)
                continue
            raise FileExistsError(
                f"{output_path} already exists; use --resume to reuse or --force to replace"
            )
        if preflights[run_id]["status"] != "passed":
            continue
        runnable.append(model)

    statuses: dict[str, Any] = {}
    max_workers = max(1, min(manifest["max_concurrent_models"], len(runnable)))
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_map = {
            executor.submit(
                run_model,
                manifest,
                model,
                batch_dir,
                repo_root,
                technical_retries=technical_retries,
                timeout_seconds=timeout_seconds,
                reasoning_effort=reasoning_effort,
                task_concurrency=task_concurrency,
                isolate_tasks=isolate_tasks,
                max_steps=max_steps,
            ): model
            for model in runnable
        }
        for future in concurrent.futures.as_completed(future_map):
            model = future_map[future]
            run_id = str(model["run_id"])
            try:
                status = future.result()
            except Exception as exc:
                status = {
                    "run_id": run_id,
                    "status": "technical_failure",
                    "category": classify_technical_error(str(exc)),
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                    "completed_at": _now(),
                }
            statuses[run_id] = status
            output_path = batch_dir / f"{run_id}.json"
            if output_path.is_file() and not verify_result_file(
                output_path,
                manifest,
                expected_model=str(model["model"]),
                expected_batch_id=str(manifest["batch_id"]),
            ):
                results[run_id] = _load_json(output_path)
            print(f"[run] {run_id}: {status['status']}")

    state = {
        "batch_id": manifest["batch_id"],
        "updated_at": _now(),
        "selected_models": [model["run_id"] for model in models],
        "preflight": preflights,
        "runs": statuses,
    }
    _write_json(batch_dir / "batch_state.json", state)
    summary = summarize_results(results, manifest, preflights)
    _write_json(batch_dir / "summary.json", summary)
    (batch_dir / "summary.md").write_text(_summary_markdown(summary), encoding="utf-8")

    expected_results = {
        str(model["run_id"])
        for model in models
        if preflights[str(model["run_id"])]["status"] == "passed"
    }
    return 0 if expected_results <= set(results) else 4


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run the pinned eight-task formal Agent benchmark suite."
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        required=True,
        help="Path to the formal suite manifest.json",
    )
    parser.add_argument(
        "--models",
        default=None,
        help="Comma-separated manifest run_ids. Defaults to all models.",
    )
    parser.add_argument("--preflight-only", action="store_true")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--technical-retries", type=int, default=2)
    parser.add_argument("--timeout-seconds", type=int, default=14400)
    parser.add_argument(
        "--reasoning-effort",
        choices=("low", "medium", "high", "xhigh", "max"),
        default=None,
        help="Override the effort in the manifest for this run.",
    )
    parser.add_argument(
        "--task-concurrency",
        type=int,
        default=None,
        help="Override per-model task concurrency for this run.",
    )
    parser.add_argument(
        "--isolate-tasks",
        action="store_true",
        help="Run and checkpoint each task independently.",
    )
    parser.add_argument(
        "--max-steps",
        type=int,
        default=None,
        help="Override the manifest step cap for this run.",
    )
    args = parser.parse_args()
    selected = (
        [item.strip() for item in args.models.split(",") if item.strip()]
        if args.models
        else None
    )
    raise SystemExit(
        run_batch(
            args.manifest,
            selected_run_ids=selected,
            preflight_only=args.preflight_only,
            resume=args.resume,
            force=args.force,
            technical_retries=max(0, args.technical_retries),
            timeout_seconds=max(1, args.timeout_seconds),
            reasoning_effort=args.reasoning_effort,
            task_concurrency=(
                max(1, args.task_concurrency) if args.task_concurrency is not None else None
            ),
            isolate_tasks=args.isolate_tasks,
            max_steps=max(1, args.max_steps) if args.max_steps is not None else None,
        )
    )


if __name__ == "__main__":
    main()
