import json
from pathlib import Path
from typing import Any, Dict, List, Union

from model_api_collector.models import PromptCase


class PromptError(ValueError):
    pass


def _validate_message(message: Any, line_number: int, index: int) -> Dict[str, Any]:
    if not isinstance(message, dict):
        raise PromptError(
            f"Prompt line {line_number} message {index} must be an object"
        )
    role = message.get("role")
    if not isinstance(role, str) or not role:
        raise PromptError(
            f"Prompt line {line_number} message {index} requires role"
        )
    if "content" not in message:
        raise PromptError(
            f"Prompt line {line_number} message {index} requires content"
        )
    return message


def load_prompt_cases(path: Union[str, Path]) -> List[PromptCase]:
    prompt_path = Path(path)
    try:
        lines = prompt_path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise PromptError(f"Cannot read prompt file {prompt_path}: {exc}") from exc

    cases: List[PromptCase] = []
    seen_ids = set()
    for line_number, line in enumerate(lines, start=1):
        if not line.strip():
            continue
        try:
            item = json.loads(line)
        except json.JSONDecodeError as exc:
            raise PromptError(f"Invalid JSON on prompt line {line_number}: {exc}") from exc
        if not isinstance(item, dict):
            raise PromptError(f"Prompt line {line_number} must be an object")

        prompt_id = item.get("id")
        if not isinstance(prompt_id, str) or not prompt_id.strip():
            raise PromptError(f"Prompt line {line_number} requires a non-empty id")
        if prompt_id in seen_ids:
            raise PromptError(f"Prompt line {line_number} has duplicate id {prompt_id!r}")

        messages = item.get("messages")
        if not isinstance(messages, list) or not messages:
            raise PromptError(
                f"Prompt line {line_number} requires a non-empty messages list"
            )
        validated_messages = [
            _validate_message(message, line_number, index)
            for index, message in enumerate(messages, start=1)
        ]

        title = item.get("title", prompt_id)
        tags = item.get("tags", [])
        notes = item.get("notes", "")
        if not isinstance(title, str):
            raise PromptError(f"Prompt line {line_number} title must be a string")
        if not isinstance(tags, list) or not all(isinstance(tag, str) for tag in tags):
            raise PromptError(f"Prompt line {line_number} tags must be strings")
        if not isinstance(notes, str):
            raise PromptError(f"Prompt line {line_number} notes must be a string")

        seen_ids.add(prompt_id)
        cases.append(
            PromptCase(
                id=prompt_id,
                title=title,
                messages=validated_messages,
                tags=list(tags),
                notes=notes,
            )
        )

    if not cases:
        raise PromptError("Prompt file must contain at least one prompt")
    return cases
