import json
import re
from typing import Any, Dict, Tuple

from benchmark.agent_benchmark.high_pressure.models import GradeResult, TaskCase


_FENCED_JSON = re.compile(r"```(?:json)?\s*(\{.*?\})\s*```", re.DOTALL)


def _extract_json(text: str) -> Tuple[Dict[str, Any], bool]:
    stripped = text.strip()
    try:
        parsed = json.loads(stripped)
        if isinstance(parsed, dict):
            return parsed, True
    except json.JSONDecodeError:
        pass

    fenced = _FENCED_JSON.search(text)
    if fenced:
        parsed = json.loads(fenced.group(1))
        if isinstance(parsed, dict):
            return parsed, False

    decoder = json.JSONDecoder()
    for index, char in enumerate(text):
        if char != "{":
            continue
        try:
            parsed, _ = decoder.raw_decode(text[index:])
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            return parsed, False
    raise ValueError("no JSON object found")


def _normalize(value: Any, mode: str) -> Any:
    if mode == "set":
        if not isinstance(value, list):
            return value
        return sorted((_normalize(item, "exact") for item in value), key=str)
    if mode == "number":
        return float(value)
    if isinstance(value, dict):
        return {
            str(key): _normalize(item, "exact")
            for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))
        }
    if isinstance(value, list):
        return [_normalize(item, "exact") for item in value]
    if isinstance(value, str):
        return " ".join(value.strip().split())
    return value


def grade_response(task: TaskCase, response: str) -> GradeResult:
    try:
        parsed, format_compliant = _extract_json(response)
    except (ValueError, json.JSONDecodeError) as exc:
        return GradeResult(
            task_id=task.id,
            points=0,
            whole_correct=False,
            status="unfinished",
            format_compliant=False,
            component_results={component.field: False for component in task.components},
            error=str(exc),
        )

    component_results = {}
    points = 0
    for component in task.components:
        actual = parsed.get(component.field)
        expected = task.expected.get(component.field)
        try:
            correct = _normalize(actual, component.mode) == _normalize(
                expected, component.mode
            )
        except (TypeError, ValueError):
            correct = False
        component_results[component.field] = correct
        if correct:
            points += component.points

    whole_correct = all(component_results.values())
    if whole_correct:
        status = "correct"
    elif points:
        status = "partial"
    else:
        status = "wrong"
    return GradeResult(
        task_id=task.id,
        points=points,
        whole_correct=whole_correct,
        status=status,
        format_compliant=format_compliant,
        component_results=component_results,
        parsed_answer=parsed,
    )
