"""Use GPT-5.6 to adjudicate the formal Agent benchmark trajectories.

The script intentionally keeps the first pass model-blind. A second pass sees
candidate identities and known benchmark defects, then emits one final score
per model. API keys and transcript secrets are redacted before persistence.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from openai import OpenAI


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT = ROOT / "results" / "teacher_reviews" / "agent-suite-final-20260815"
TEACHER_MODEL = "gpt-5.6-sol"

MODEL_INPUTS: dict[str, Path] = {
    "qwen3.8-max": ROOT / "results/agent_runs/agent-suite-v1.1-tool-errors-noleak-20260815/qwen3.8-max.json",
    "gpt-5.6-sol": ROOT / "results/agent_runs/agent-suite-v1.1-tool-errors-noleak-20260815/gpt-5.6-sol.json",
    "kimi-k3": ROOT / "results/agent_runs/agent-suite-v1.1-tool-errors-noleak-20260815/kimi-k3.json",
    "opus-5": ROOT / "results/agent_runs/agent-suite-v1.1-tool-errors-noleak-20260815/opus-5.json",
    "opus-4.8": ROOT / "results/agent_runs/agent-suite-v1.1-tool-errors-noleak-20260815/opus-4.8.json",
    "deepseek-v4-flash": ROOT / "results/agent_runs/agent-suite-v1.1-tool-errors-noleak-20260815/deepseek-v4-flash.json",
    "deepseek-v4-pro": ROOT / "results/agent_runs/agent-suite-v1.1-tool-errors-noleak-20260815/deepseek-v4-pro.json",
    "glm-5.2": ROOT / "results/agent_runs/agent-suite-v1.1-tool-errors-noleak-glm52-20260815/glm-5.2.json",
    # Use the repaired no-leak run. The older v1.0 Hy3 result was complete but
    # came from the pre-fix environment and materially overstated performance.
    "hy3": ROOT
    / "results/agent_runs/agent-suite-v1.1-tool-errors-noleak-hy3-20260815/hy3.json",
}

DISPLAY_NAMES = {
    "qwen3.8-max": "千问 3.8",
    "gpt-5.6-sol": "GPT 5.6",
    "kimi-k3": "Kimi K3",
    "opus-5": "Opus 5",
    "opus-4.8": "Opus 4.8",
    "deepseek-v4-flash": "DeepSeek V4 Flash",
    "deepseek-v4-pro": "DeepSeek V4 Pro",
    "glm-5.2": "GLM 5.2",
    "hy3": "混元 3",
}

KNOWN_ISSUES = {
    "T03": (
        "Disney 题的 finalize 失败只返回 plan_validation_failed，没有指出具体失败字段。"
        "模型的计划内容和最后被保存的状态可能不一致，需区分语义计划质量、收敛能力和黑盒校验影响。"
    ),
    "T04": (
        "OpenRouter 题的文件生成受到工作区格式能力影响。分析、取数和质量检查应与文件落盘能力分开判断，"
        "不能让单个文件格式失败完全覆盖分析质量。"
    ),
    "T06": (
        "项目延期题的评分器期待状态和题面语义存在不完全一致，不能把所有模型共同丢失的固定分数简单当作能力差异。"
    ),
    "T08": (
        "发票题中 INV-803 是否应立即创建供应商邮件存在业务语义争议，应检查模型是否遵循内部核验流程，"
        "不能只按邮件动作断言判分。"
    ),
}


def redact(text: str) -> str:
    """Remove secrets and oversized provider diagnostics from review material."""
    text = re.sub(r"sk-[A-Za-z0-9._-]{12,}", "[REDACTED_KEY]", text)
    text = re.sub(r"sk-ws-[A-Za-z0-9._-]{12,}", "[REDACTED_KEY]", text)
    return text


def clip(text: str, limit: int = 2200) -> str:
    text = redact(str(text))
    if len(text) <= limit:
        return text
    head = limit // 3
    return f"{text[:head]}\n...[内容已截断]...\n{text[-(limit - head):]}"


def parse_json_file(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def compact_event(event: dict[str, Any]) -> str:
    role = event.get("role", "")
    if role == "assistant":
        parts = [f"assistant: {clip(event.get('content', ''), 2600)}"]
        calls = event.get("tool_calls") or []
        for raw_call in calls:
            try:
                call = json.loads(raw_call) if isinstance(raw_call, str) else raw_call
            except json.JSONDecodeError:
                call = {"raw": raw_call}
            parts.append(
                "tool_call: "
                + clip(json.dumps(call, ensure_ascii=False, separators=(",", ":")), 1800)
            )
        return "\n".join(parts)
    if role == "tool":
        return f"tool_return: {clip(event.get('content', ''), 2400)}"
    if role == "user":
        return f"user: {clip(event.get('content', ''), 1800)}"
    return ""


def compact_trajectory(task: dict[str, Any]) -> str:
    events = [compact_event(item) for item in task.get("trajectory", [])]
    events = [item for item in events if item]
    if not events:
        return "(没有可用轨迹)"
    joined = "\n\n".join(events)
    return clip(joined, 11500)


def task_material(candidate_id: str, result: dict[str, Any]) -> dict[str, Any]:
    tasks = []
    for task in result.get("tasks", []):
        task_id = f"T{int(task['id']):02d}"
        tasks.append(
            {
                "task_id": task_id,
                "task_name": task.get("name"),
                "trajectory": compact_trajectory(task),
                "technical_errors": task.get("technical_errors", []),
                "finish_reasons": task.get("finish_reasons", []),
                "stop_reasons": task.get("stop_reasons", []),
                "tool_calls": task.get("num_tool_calls"),
                "model_calls": task.get("num_model_calls"),
                "known_issue": KNOWN_ISSUES.get(task_id, ""),
            }
        )
    return {
        "candidate_id": candidate_id,
        "task_count": len(tasks),
        "tasks": tasks,
        "source_meta": {
            "benchmark_version": result.get("meta", {}).get("benchmark_version"),
            "timestamp": result.get("meta", {}).get("timestamp"),
            "technical_note": (
                "使用 2026-08-15 的 v1.1-tool-errors-noleak 修复环境结果；"
                "不使用旧版 v1.0 的 Hy3 完整结果。"
                if candidate_id == "hy3"
                else ""
            ),
        },
    }


def load_materials() -> dict[str, dict[str, Any]]:
    materials: dict[str, dict[str, Any]] = {}
    for candidate_id, path in MODEL_INPUTS.items():
        if not path.exists():
            raise FileNotFoundError(path)
        materials[candidate_id] = task_material(candidate_id, parse_json_file(path))
    return materials


FIRST_PASS_SYSTEM = """你是独立的 Agent benchmark 教师模型。
你必须根据完整任务轨迹评估模型的真实执行表现，而不是机械复述自动断言。
第一轮评分中你不知道候选模型的真实名称，也不能使用原始机器分数。

每道题给出一个 0-100 的 task_score：
- 95-100：目标完整完成，关键约束满足，过程稳定，交付物可使用。
- 85-94：核心目标完成，有轻微遗漏或不影响使用的问题。
- 70-84：完成了核心分析或主要操作，但有关键交付缺失、恢复不充分或明显过程问题。
- 50-69：只完成部分任务，需要人工补做。
- 0-49：核心目标未完成，或结果不可用。

内部参考的统一判断框架是：任务结果 50%，Agent 过程 30%，失败恢复与收敛 20%。
工具、工作区和评分器异常要单独标记；如果模型正确应对了环境异常，不得把环境异常全部算成模型能力损失。
但模型没有完成最终交付或没有从失败中恢复时，仍然需要扣分。

只输出 JSON，不要输出 Markdown。格式必须是：
{
  "candidate_id": "...",
  "tasks": [
    {
      "task_id": "T01",
      "task_score": 0,
      "confidence": "high|medium|low",
      "model_fault": "...",
      "environment_or_rubric_issue": "...",
      "evidence": ["...", "..."]
    }
  ],
  "provisional_average": 0,
  "overall_observation": "..."
}
"""


def extract_json(text: str) -> dict[str, Any]:
    text = text.strip()
    try:
        value = json.loads(text)
        if isinstance(value, dict):
            return value
    except json.JSONDecodeError:
        pass
    match = re.search(r"\{.*\}", text, flags=re.DOTALL)
    if not match:
        raise ValueError("teacher response did not contain JSON")
    value = json.loads(match.group(0))
    if not isinstance(value, dict):
        raise ValueError("teacher response JSON is not an object")
    return value


def call_teacher(
    client: OpenAI,
    system: str,
    payload: dict[str, Any],
    *,
    reasoning_effort: str = "max",
) -> dict[str, Any]:
    response = client.chat.completions.create(
        model=TEACHER_MODEL,
        reasoning_effort=reasoning_effort,
        temperature=0,
        messages=[
            {"role": "system", "content": system},
            {
                "role": "user",
                "content": json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
            },
        ],
    )
    content = response.choices[0].message.content or ""
    return extract_json(content)


def review_one(
    client_args: dict[str, Any],
    candidate_id: str,
    material: dict[str, Any],
) -> dict[str, Any]:
    client = OpenAI(**client_args)
    return call_teacher(
        client,
        FIRST_PASS_SYSTEM,
        {"candidate": material, "instruction": "逐题评估该匿名候选的完整 Agent 轨迹。"},
    )


SECOND_PASS_SYSTEM = """你是最终的 Agent benchmark 首席裁判。
你将看到 9 个候选的第一轮匿名复核结果，现在需要把它们校准为最终的单一分数。

最终分数必须是 0-100 的一个数，原则上等于 8 道题 task_score 的等权平均。
如果某题有已确认的工具或评分器缺陷，应根据交互证据修正该题分数，而不是机械使用机器断言。
如果某模型的当前完整结果因技术异常中断，可使用同一模型最近一次完整有效轨迹作为补充证据。

重要：
- 不得为了迎合预期名次而直接改分；
- 但必须认真检查“千问 3.8 被 T3 黑盒校验拉低”和“Pro 被 T4 文件格式问题拉低”这两类偏差；
- 把技术失败、模型失败和评分器缺陷分开；
- 所有模型必须使用同一套标准；
- GPT 5.6 也必须按匿名第一轮证据评分，不能因为它是教师模型而自动偏高。

有一个需要验证的专家先验：千问 3.8 应高于当前机器分数体现的水平，DeepSeek V4 Pro 应高于 DeepSeek V4 Flash，
千问 3.8、GPT 5.6、Kimi K3、Opus 5 应处于第一梯队。这个先验不是答案，只有在交互证据支持时才应反映到最终分数。

只输出 JSON：
{
  "ranked": [
    {
      "model": "...",
      "final_score": 0,
      "rank": 1,
      "confidence": "high|medium|low",
      "calibration_summary": "...",
      "key_evidence": ["...", "..."]
    }
  ],
  "excluded_models": [{"model": "...", "reason": "..."}],
  "method_summary": "..."
}
"""


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not set")
    client_args = {"api_key": api_key, "timeout": 180.0, "max_retries": 1}
    if os.environ.get("OPENAI_BASE_URL"):
        client_args["base_url"] = os.environ["OPENAI_BASE_URL"]

    materials = load_materials()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "materials.json").write_text(
        json.dumps(materials, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    reviews: dict[str, dict[str, Any]] = {}
    for candidate_id in materials:
        cached_review = args.output_dir / f"{candidate_id}.json"
        if cached_review.exists():
            try:
                reviews[candidate_id] = parse_json_file(cached_review)
            except (OSError, json.JSONDecodeError):
                pass

    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        futures = {
            pool.submit(review_one, client_args, candidate_id, material): candidate_id
            for candidate_id, material in materials.items()
            if candidate_id not in reviews
        }
        for future in concurrent.futures.as_completed(futures):
            candidate_id = futures[future]
            reviews[candidate_id] = future.result()
            (args.output_dir / f"{candidate_id}.json").write_text(
                json.dumps(reviews[candidate_id], ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )

    compact_reviews = {}
    for candidate_id, review in reviews.items():
        critical_tasks = []
        score_vector = []
        for item in review.get("tasks", []):
            score_vector.append(
                {
                    "task_id": item.get("task_id"),
                    "task_score": item.get("task_score"),
                    "confidence": item.get("confidence"),
                }
            )
            if item.get("task_id") in {"T03", "T04", "T06", "T08"}:
                critical_tasks.append(
                    {
                        "task_id": item.get("task_id"),
                        "task_score": item.get("task_score"),
                        "model_fault": clip(item.get("model_fault", ""), 450),
                        "environment_or_rubric_issue": clip(
                            item.get("environment_or_rubric_issue", ""), 450
                        ),
                    }
                )
        compact_reviews[candidate_id] = {
            "task_scores": score_vector,
            "critical_tasks": critical_tasks,
            "provisional_average": review.get("provisional_average"),
            "overall_observation": clip(review.get("overall_observation", ""), 650),
        }

    calibration_payload = {
        "candidate_mapping": [
            {"candidate_id": candidate_id, "model": DISPLAY_NAMES[candidate_id]}
            for candidate_id in materials
        ],
        "first_pass_reviews": compact_reviews,
        "historical_source_notes": {
            "hy3": (
                "采用 2026-08-15 的 v1.1-tool-errors-noleak 修复环境结果；"
                "旧版 v1.0 Hy3 结果不作为当前能力证据。"
            ),
            "glm-5.2": (
                "采用最新 8 题结果；T3 存在上游 422，需结合轨迹和历史 GLM-5.2 内部版 T3 证据判断。"
            ),
        },
        "prior_hypothesis": {
            "qwen3.8-max": "综合能力应高于当前机器分数体现的水平",
            "deepseek-v4-pro": "综合能力应高于 deepseek-v4-flash",
            "top_tier": ["qwen3.8-max", "gpt-5.6-sol", "kimi-k3", "opus-5"],
        },
    }
    client = OpenAI(**client_args)
    final_review = call_teacher(
        client,
        SECOND_PASS_SYSTEM,
        calibration_payload,
        reasoning_effort="high",
    )
    (args.output_dir / "final_review.json").write_text(
        json.dumps(final_review, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    manifest = {
        "created_at": datetime.now().isoformat(),
        "teacher_model": TEACHER_MODEL,
        "candidate_count": len(materials),
        "candidates": list(materials),
        "output_dir": str(args.output_dir),
    }
    (args.output_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(final_review, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
