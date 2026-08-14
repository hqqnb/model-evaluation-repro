import hashlib
import json
from pathlib import Path
from typing import Dict

from benchmark.question_bank.archive.legacy_20260803.reasoning_and_candidates.short_logic.tasks import build_tasks


BENCHMARK_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
MARKDOWN_PATH = BENCHMARK_ROOT / "SHORT_HARD_LOGIC_TASKS.md"
ANSWER_KEY_PATH = BENCHMARK_ROOT / "short_logic_answer_key.json"
PROMPTS_PATH = (
    REPOSITORY_ROOT
    / "runners/model-api-collector/prompts/reasoning_short_hard_20260806.jsonl"
)


def render_all() -> Dict[str, str]:
    tasks = build_tasks()
    markdown_parts = [
        "# 短题型高难逻辑测试",
        "",
        "版本：2026-08-06",
        "",
        "共 6 道，每道 10 分。禁止联网和外部工具。"
        "题目不要求展示思维链，只按固定 JSON 字段判分。",
        "",
    ]
    answers = []
    prompt_lines = []
    for task in tasks:
        markdown_parts.extend(
            [
                f"## {task.id} {task.title}",
                "",
                task.prompt,
                "",
            ]
        )
        answers.append(
            {
                "id": task.id,
                "title": task.title,
                "expected": task.expected,
                "near_miss": task.near_miss,
                "components": [
                    {
                        "field": component.field,
                        "points": component.points,
                        "mode": component.mode,
                    }
                    for component in task.components
                ],
            }
        )
        prompt_lines.append(
            json.dumps(
                {
                    "id": task.id,
                    "title": task.title,
                    "messages": [{"role": "user", "content": task.prompt}],
                    "tags": ["reasoning", "short", "hard-logic", "pilot"],
                },
                ensure_ascii=False,
            )
        )

    MARKDOWN_PATH.parent.mkdir(parents=True, exist_ok=True)
    ANSWER_KEY_PATH.parent.mkdir(parents=True, exist_ok=True)
    PROMPTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    MARKDOWN_PATH.write_text(
        "\n".join(markdown_parts).rstrip() + "\n", encoding="utf-8"
    )
    ANSWER_KEY_PATH.write_text(
        json.dumps(answers, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    PROMPTS_PATH.write_text("\n".join(prompt_lines) + "\n", encoding="utf-8")
    prompt_hash = hashlib.sha256(PROMPTS_PATH.read_bytes()).hexdigest()
    print(f"Prompt SHA-256: {prompt_hash}")
    return {
        "markdown": str(MARKDOWN_PATH),
        "answer_key": str(ANSWER_KEY_PATH),
        "prompts": str(PROMPTS_PATH),
    }


if __name__ == "__main__":
    for name, path in render_all().items():
        print(f"{name}: {path}")
