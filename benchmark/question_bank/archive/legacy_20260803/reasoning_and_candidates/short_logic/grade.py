import json
from dataclasses import replace
from typing import Any, Dict

from benchmark.question_bank.archive.legacy_20260803.reasoning_and_candidates.high_pressure.grade import (
    _extract_json,
    grade_response as _strict_grade_response,
)
from benchmark.question_bank.archive.legacy_20260803.reasoning_and_candidates.short_logic.models import GradeResult, TaskCase


def _sentence_id(value: Any) -> Any:
    if isinstance(value, int):
        return f"S{value}"
    if isinstance(value, str) and value.isdigit():
        return f"S{value}"
    return value


def _normalize_short_logic_answer(
    task: TaskCase, answer: Dict[str, Any]
) -> Dict[str, Any]:
    normalized = dict(answer)
    if task.id == "S04":
        for field in ("always_true", "always_false"):
            value = normalized.get(field)
            if isinstance(value, list):
                normalized[field] = [_sentence_id(item) for item in value]

    if task.id == "S05":
        counterexample = normalized.get("fast_action_counterexample")
        if isinstance(counterexample, dict):
            state = counterexample.get(
                "state",
                counterexample.get("n", counterexample.get("failing_state")),
            )
            if state is not None:
                normalized["fast_action_counterexample"] = {
                    "action": counterexample.get("action"),
                    "state": str(state),
                }
    return normalized


def grade_response(task: TaskCase, response: str) -> GradeResult:
    try:
        parsed, format_compliant = _extract_json(response)
    except (ValueError, json.JSONDecodeError):
        return _strict_grade_response(task, response)

    normalized = _normalize_short_logic_answer(task, parsed)
    result = _strict_grade_response(
        task, json.dumps(normalized, ensure_ascii=False)
    )
    return replace(
        result,
        format_compliant=format_compliant,
        parsed_answer=parsed,
    )
