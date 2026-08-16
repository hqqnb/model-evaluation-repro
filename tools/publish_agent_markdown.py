#!/usr/bin/env python3
"""Publish one readable Markdown document for every Agent model/task pair."""

from __future__ import annotations

import argparse
import json
import re
from datetime import date
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
MATERIALS_PATH = (
    PROJECT_ROOT
    / "evaluation/agent/reviews/20260815-corrected/materials.json"
)
REVIEW_DIR = (
    PROJECT_ROOT
    / "evaluation/agent/reviews/20260815-corrected"
)
GPT55_PATH = PROJECT_ROOT / "evaluation/agent/raw_runs/agent-suite-v1.1-20260814/gpt-5.5.json"
QUESTION_BANK_ROOT = PROJECT_ROOT / "benchmark/question_bank"
SUMMARY_PATH = PROJECT_ROOT / "evaluation/agent/model_review_summary_20260815.md"
RUN_ID = "20260814-agent"
GITHUB_BASE = (
    "https://github.com/hqqnb/llm-evaluation-question-bank/blob/main/"
    f"runs/{RUN_ID}/responses"
)

TASK_LABELS = {
    "T01": "退款处理",
    "T02": "Demo 排期",
    "T03": "Disney 三日旅行规划",
    "T04": "OpenRouter 数据采集与分析",
    "T05": "多文件分析与报告生成",
    "T06": "项目延期处理",
    "T07": "银行场景多轮任务",
    "T08": "发票中断后恢复执行",
}

MODELS = [
    {"key": "deepseek-v4-pro", "label": "DeepSeek V4 Pro", "materials_key": "deepseek-v4-pro", "review_file": "deepseek-v4-pro.json"},
    {"key": "qwen3.8-max", "label": "Qwen 3.8", "materials_key": "qwen3.8-max", "review_file": "qwen3.8-max.json"},
    {"key": "kimi-k3", "label": "Kimi K3", "materials_key": "kimi-k3", "review_file": "kimi-k3.json"},
    {"key": "deepseek-v4-flash", "label": "DeepSeek V4 Flash", "materials_key": "deepseek-v4-flash", "review_file": "deepseek-v4-flash.json"},
    {"key": "glm-5.2-internal", "label": "GLM-5.2-内部", "materials_key": "glm-5.2", "review_file": "glm-5.2.json"},
    {"key": "gpt-5.6-sol", "label": "GPT-5.6 Sol", "materials_key": "gpt-5.6-sol", "review_file": "gpt-5.6-sol.json"},
    {"key": "opus-5", "label": "Opus 5", "materials_key": "opus-5", "review_file": "opus-5.json"},
    {"key": "hy3", "label": "混元 3", "materials_key": "hy3", "review_file": "hy3.json"},
    {"key": "gpt-5.5", "label": "GPT-5.5", "raw_path": GPT55_PATH, "review_file": None},
    {"key": "opus-4.8", "label": "Opus 4.8", "materials_key": "opus-4.8", "review_file": "opus-4.8.json"},
]

SECRET_PATTERNS = [
    (re.compile(r"(?i)(sk-(?:ws-)?[A-Za-z0-9._-]{12,})"), "[REDACTED_API_KEY]"),
    (re.compile(r"(?i)OR_TEST_KEY_[A-Z0-9_]+"), "[REDACTED_API_KEY]"),
    (re.compile(r"(?i)(Bearer\s+)[A-Za-z0-9._-]{12,}"), r"\1[REDACTED_TOKEN]"),
    (
        re.compile(r'(?i)("api_key"\s*:\s*")([^"]+)(")'),
        r'\1[REDACTED]\3',
    ),
]


def redact(text: str) -> str:
    for pattern, replacement in SECRET_PATTERNS:
        text = pattern.sub(replacement, text)
    return text.replace("\x00", "[NUL]")


def pretty_json(value: Any) -> str:
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except json.JSONDecodeError:
            return value
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def raw_trajectory_to_text(task: dict[str, Any]) -> str:
    chunks: list[str] = []
    for message in task.get("trajectory") or task.get("messages") or []:
        role = message.get("role", "unknown")
        if role == "assistant":
            chunks.append("assistant:")
            content = message.get("content") or ""
            is_tool_annotation = bool(
                re.match(r"(?is)^\s*(?:to|To)=functions\.[^\n]+", content)
            )
            if content and not is_tool_annotation:
                chunks.append(content)
            for call in message.get("tool_calls") or []:
                chunks.append(f"tool_call: {pretty_json(call)}")
        elif role == "tool":
            chunks.append(f"tool_return: {message.get('content', '')}")
        else:
            chunks.append(f"{role}:")
            if message.get("content"):
                chunks.append(message["content"])
        chunks.append("")
    return "\n".join(chunks).strip()


def final_response_from_text(trajectory: str) -> str:
    parts = re.split(r"\n\nassistant:\s*", trajectory)
    if len(parts) > 1:
        candidate = parts[-1].strip()
        if candidate:
            return candidate
    return "未形成可单独提取的最终文本回复，完整过程见下方交互记录。"


def final_response_from_raw(task: dict[str, Any]) -> str:
    for message in reversed(task.get("trajectory") or task.get("messages") or []):
        content = str(message.get("content") or "").strip()
        if message.get("role") != "assistant" or not content:
            continue
        if message.get("tool_calls"):
            continue
        if re.match(r"(?is)^\s*(?:to|To)=functions\.[^\n]+", content):
            continue
        if re.fullmatch(r"(?is)<thinking>.*?</thinking>", content):
            continue
        return content
    return "该轨迹在最后一次工具调用后未形成可单独提取的最终文本回复，完整过程见下方交互记录。"


def review_map() -> dict[str, dict[str, Any]]:
    output: dict[str, dict[str, Any]] = {}
    for model in MODELS:
        review_file = model.get("review_file")
        if not review_file:
            continue
        path = REVIEW_DIR / review_file
        if not path.is_file():
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        output[model["key"]] = {item["task_id"]: item for item in data.get("tasks", [])}
    return output


def compact_meta(model: dict[str, Any], task: dict[str, Any]) -> list[str]:
    lines = [
        f"- 模型：{model['label']}",
        f"- 题目：{task['task_id']} {TASK_LABELS.get(task['task_id'], task.get('task_name', ''))}",
        f"- 运行批次：`{RUN_ID}`",
    ]
    for key, label in (
        ("tool_calls", "工具调用次数"),
        ("model_calls", "模型调用轮数"),
        ("technical_errors", "技术错误"),
    ):
        value = task.get(key)
        if value is None:
            continue
        if isinstance(value, list):
            value = len(value)
        lines.append(f"- {label}：{value}")
    return lines


def render_document(
    model: dict[str, Any],
    task: dict[str, Any],
    review: dict[str, Any] | None,
    trajectory: str,
    final_response: str,
) -> str:
    trajectory = redact(trajectory)
    final_response = redact(final_response)
    safe_trajectory = trajectory.replace("~~~~", r"\~\~\~\~")
    lines = [
        f"# {task['task_id']} {TASK_LABELS.get(task['task_id'], task.get('task_name', 'Agent 任务'))}｜{model['label']}",
        "",
        "本文记录该模型在本题中的最终回复和完整工具交互过程，供人工复核使用。",
        "",
        *compact_meta(model, task),
        "",
        "## 最终回复",
        "",
        final_response,
        "",
    ]
    if review:
        lines.extend(
            [
                "## 复核要点",
                "",
                f"- 复核置信度：{review.get('confidence', '未记录')}",
                f"- 模型表现：{review.get('model_fault', '未记录')}",
                f"- 环境或评分说明：{review.get('environment_or_rubric_issue', '未记录')}",
                "",
                "证据：",
                "",
            ]
        )
        for evidence in review.get("evidence", []):
            lines.append(f"- {evidence}")
        lines.append("")
    lines.extend(
        [
            "## 完整交互过程",
            "",
            "~~~~text",
            safe_trajectory,
            "~~~~",
            "",
        ]
    )
    # Strip whitespace from embedded trajectory lines as well as outer Markdown lines.
    rendered = "\n".join(
        subline.rstrip() for subline in "\n".join(lines).splitlines()
    ).rstrip() + "\n"
    return redact(rendered)


def load_tasks(materials: dict[str, Any], model: dict[str, Any]) -> dict[str, dict[str, Any]]:
    if model.get("materials_key"):
        items = materials[model["materials_key"]]["tasks"]
        return {item["task_id"]: item for item in items}
    raw = json.loads(model["raw_path"].read_text(encoding="utf-8"))
    return {
        f"T{item['id']:02d}": {
            "task_id": f"T{item['id']:02d}",
            "task_name": item["name"],
            "trajectory": raw_trajectory_to_text(item),
            "tool_calls": item.get("num_tool_calls"),
            "model_calls": item.get("num_model_calls"),
            "technical_errors": item.get("technical_errors", []),
            "_final_response": final_response_from_raw(item),
        }
        for item in raw.get("tasks", [])
    }


def update_summary(summary_path: Path, link_map: dict[tuple[int, str], str]) -> int:
    text = summary_path.read_text(encoding="utf-8")
    lines = text.splitlines()
    header_index = next(
        index for index, line in enumerate(lines) if line.startswith("| 序号") and "deepseek-v4-pro0813" in line
    )
    headers = [part.strip() for part in lines[header_index].split("|")]
    model_indexes = {
        header: index
        for index, header in enumerate(headers)
        if header in {
            "deepseek-v4-pro0813",
            "qwen3.8-max",
            "kimi-k3",
            "deepseek-v4-flash-0731",
            "glm-5.2",
            "gpt-5.6-sol",
            "opus-5",
            "hy3",
            "gpt-5.5",
            "opus-4.8",
        }
    }
    alias_by_header = {
        "deepseek-v4-pro0813": "deepseek-v4-pro",
        "qwen3.8-max": "qwen3.8-max",
        "kimi-k3": "kimi-k3",
        "deepseek-v4-flash-0731": "deepseek-v4-flash",
        "glm-5.2": "glm-5.2-internal",
        "gpt-5.6-sol": "gpt-5.6-sol",
        "opus-5": "opus-5",
        "hy3": "hy3",
        "gpt-5.5": "gpt-5.5",
        "opus-4.8": "opus-4.8",
    }
    changed = 0
    link_pattern = re.compile(r"\[(?:完整交互预览|完整交互回答)\]\([^)]*\)")
    for index, line in enumerate(lines):
        match = re.match(r"^\|\s*([1-8])\s*\|", line)
        if not match:
            continue
        task_id = int(match.group(1))
        parts = line.split("|")
        for header, cell_index in model_indexes.items():
            alias = alias_by_header[header]
            url = f"{GITHUB_BASE}/agent-t{task_id:02d}/{alias}.md"
            replacement = f"[完整交互回答]({url})"
            old_cell = parts[cell_index]
            if replacement in old_cell:
                continue
            new_cell, count = link_pattern.subn(replacement, old_cell)
            if count != 1:
                raise ValueError(f"Expected one existing preview link in T{task_id:02d}/{alias}, got {count}")
            parts[cell_index] = new_cell
            changed += count
        lines[index] = "|".join(parts)
    summary_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return changed


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--question-bank-root", type=Path, default=QUESTION_BANK_ROOT)
    parser.add_argument("--summary-path", type=Path, default=SUMMARY_PATH)
    args = parser.parse_args()

    materials = json.loads(MATERIALS_PATH.read_text(encoding="utf-8"))
    reviews = review_map()
    output_root = args.question_bank_root / "runs" / RUN_ID / "responses"
    output_root.mkdir(parents=True, exist_ok=True)
    manifest: dict[str, Any] = {
        "run_id": RUN_ID,
        "generated_at": date.today().isoformat(),
        "source": "agent-suite-final-20260815",
        "documents": [],
    }

    generated = 0
    for model in MODELS:
        tasks = load_tasks(materials, model)
        if set(tasks) != set(TASK_LABELS):
            raise ValueError(f"{model['key']} task set mismatch: {sorted(tasks)}")
        for task_id in sorted(TASK_LABELS):
            task = tasks[task_id]
            trajectory = task.get("trajectory", "")
            final_response = task.get("_final_response") or final_response_from_text(trajectory)
            path = output_root / f"agent-{task_id.lower()}" / f"{model['key']}.md"
            path.parent.mkdir(parents=True, exist_ok=True)
            review = reviews.get(model["key"], {}).get(task_id)
            path.write_text(
                render_document(model, task, review, trajectory, final_response),
                encoding="utf-8",
            )
            manifest["documents"].append(
                {
                    "task_id": task_id,
                    "model": model["key"],
                    "path": str(path.relative_to(args.question_bank_root)),
                    "url": f"{GITHUB_BASE}/agent-{task_id.lower()}/{model['key']}.md",
                }
            )
            generated += 1

    run_root = args.question_bank_root / "runs" / RUN_ID
    readme = [
        f"# Agent 交互回答（{RUN_ID}）",
        "",
        "本目录保存 8 道 Agent 题目与 10 个模型的单题单模型交互记录。",
        "每个 Markdown 文件包含最终回复、工具调用过程和人工复核要点（如已有复核记录）。",
        "",
        "## 目录",
        "",
        "- `responses/agent-t01` 至 `responses/agent-t08`：按题目组织的模型回答。",
        "- `manifest.json`：全部 80 个文档的路径与链接清单。",
        "",
        "轨迹中的 API Key、Bearer Token 和其他密钥均已脱敏。",
        "",
    ]
    (run_root / "README.md").write_text("\n".join(readme), encoding="utf-8")
    (run_root / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    changed_links = update_summary(args.summary_path, {
        (int(item["task_id"][1:]), item["model"]): item["url"]
        for item in manifest["documents"]
    })
    print(f"generated {generated} Agent Markdown documents")
    print(f"updated {changed_links} summary-table links")
    print(f"output: {run_root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
