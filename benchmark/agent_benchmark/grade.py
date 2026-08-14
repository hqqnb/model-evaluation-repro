from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any, Dict, List


ROOT = Path(__file__).resolve().parent


@dataclass(frozen=True)
class GradeResult:
    correct: bool
    points: int
    normalized_answer: Any = None
    expected_answer: Any = None
    error: str = None


def load_questions() -> List[Dict[str, Any]]:
    with (ROOT / "questions.json").open(encoding="utf-8") as handle:
        return json.load(handle)


def load_answer_key() -> Dict[str, Dict[str, Any]]:
    with (ROOT / "answer_key.json").open(encoding="utf-8") as handle:
        records = json.load(handle)
    return {record["id"]: record for record in records}


def _parse_response(response: Any) -> Any:
    if not isinstance(response, str):
        return response

    text = response.strip()
    if not text:
        return ""

    if text[0] in "[{":
        parsed = json.loads(text)
        if isinstance(parsed, dict) and "answer" in parsed:
            return parsed["answer"]
        return parsed

    return text


def _normalize_scalar(value: Any) -> Any:
    if isinstance(value, str):
        return " ".join(value.strip().split())
    return value


def _normalize(value: Any, answer_type: str) -> Any:
    if answer_type == "choice":
        return str(value).strip().upper()
    if answer_type == "integer":
        return int(value)
    if answer_type == "number":
        return float(value)
    if answer_type in {"sequence", "set"}:
        if isinstance(value, str):
            separator = ">" if ">" in value else ","
            value = [part for part in value.split(separator) if part.strip()]
        if not isinstance(value, (list, tuple)):
            raise ValueError(f"{answer_type} answer must be a list")
        normalized = [_normalize_scalar(item) for item in value]
        return sorted(normalized, key=str) if answer_type == "set" else normalized
    if answer_type == "mapping":
        if not isinstance(value, dict):
            raise ValueError("mapping answer must be an object")
        return {
            str(key).strip(): _normalize_scalar(item)
            for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))
        }
    return _normalize_scalar(value)


def grade_answer(question_id: str, response: Any) -> GradeResult:
    questions = {item["id"]: item for item in load_questions()}
    answer_key = load_answer_key()
    if question_id not in questions or question_id not in answer_key:
        raise KeyError(question_id)

    question = questions[question_id]
    record = answer_key[question_id]
    try:
        parsed = _parse_response(response)
        normalized = _normalize(parsed, question["answer_type"])
        expected = _normalize(record["expected"], question["answer_type"])
        if question["answer_type"] == "number":
            tolerance = question["scoring"].get("tolerance", 0.0)
            correct = abs(normalized - expected) <= tolerance
        else:
            correct = normalized == expected
        return GradeResult(
            correct=correct,
            points=question["scoring"]["points"] if correct else 0,
            normalized_answer=normalized,
            expected_answer=expected,
        )
    except (TypeError, ValueError, json.JSONDecodeError) as exc:
        return GradeResult(correct=False, points=0, error=str(exc))

