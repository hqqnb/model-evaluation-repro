import json
from pathlib import Path

from benchmark.agent_benchmark.high_pressure.tasks import build_tasks


BENCHMARK_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
MARKDOWN_PATH = BENCHMARK_ROOT / "HIGH_PRESSURE_REASONING_TASKS.md"
ANSWER_KEY_PATH = BENCHMARK_ROOT / "high_pressure_answer_key.json"
PROMPTS_PATH = (
    REPOSITORY_ROOT
    / "runners/model-api-collector/prompts/reasoning_high_pressure_20260805.jsonl"
)


def render_all() -> None:
    tasks = build_tasks()
    markdown_parts = [
        "# 长任务型推理能力测试题",
        "",
        "版本：2026-08-05",
        "",
        "共 10 道，每道 10 分。禁止联网和外部工具。"
        "主分只依据题目要求的客观字段，不因解释长度或表达风格加分。",
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
                    "tags": ["reasoning", "long-form", "high-pressure", "pilot"],
                },
                ensure_ascii=False,
            )
        )

    MARKDOWN_PATH.parent.mkdir(parents=True, exist_ok=True)
    ANSWER_KEY_PATH.parent.mkdir(parents=True, exist_ok=True)
    PROMPTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    MARKDOWN_PATH.write_text("\n".join(markdown_parts).rstrip() + "\n", encoding="utf-8")
    ANSWER_KEY_PATH.write_text(
        json.dumps(answers, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    PROMPTS_PATH.write_text("\n".join(prompt_lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    render_all()
