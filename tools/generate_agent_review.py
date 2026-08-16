#!/usr/bin/env python3
"""Generate a self-contained Agent trajectory review page."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = Path(os.environ.get("MODEL_EVAL_SOURCE_ROOT", PROJECT_ROOT))
FINAL_SCORE_REGISTRY = PROJECT_ROOT / "evaluation" / "agent" / "formal_scores_20260815.json"


TASK_LABELS = {
    1: ("T01", "退款处理"),
    2: ("T02", "Demo 排期"),
    3: ("T03", "迪士尼行程规划"),
    4: ("T04", "OpenRouter 数据分析与制表"),
    5: ("T05", "多文件分析与报告生成"),
    6: ("T06", "项目延期处理"),
    7: ("T07", "银行场景多轮任务"),
    8: ("T08", "发票中断后恢复执行"),
}

MODEL_SOURCES = [
    {
        "key": "opus-4.8",
        "label": "Opus 4.8",
        "path": str(SOURCE_ROOT / "evaluation/agent/raw_runs/agent-suite-v1-20260814/opus-4.8.json"),
        "ranked": True,
    },
    {
        "key": "opus-5",
        "label": "Opus 5",
        "path": str(SOURCE_ROOT / "evaluation/agent/raw_runs/agent-suite-v1-20260814/opus-5.json"),
        "ranked": True,
    },
    {
        "key": "deepseek-v4-pro",
        "label": "DeepSeek V4 Pro",
        "path": str(SOURCE_ROOT / "evaluation/agent/raw_runs/agent-suite-v1-20260814/deepseek-v4-pro.json"),
        "ranked": True,
    },
    {
        "key": "deepseek-v4-flash",
        "label": "DeepSeek V4 Flash",
        "path": str(SOURCE_ROOT / "evaluation/agent/raw_runs/agent-suite-v1-20260814/deepseek-v4-flash.json"),
        "ranked": True,
    },
    {
        "key": "kimi-k3",
        "label": "Kimi K3",
        "path": str(SOURCE_ROOT / "evaluation/agent/raw_runs/agent-suite-v1-20260814/kimi-k3.json"),
        "ranked": True,
    },
    {
        "key": "gpt-5.6-sol",
        "label": "GPT-5.6 Sol",
        "path": str(SOURCE_ROOT / "evaluation/agent/raw_runs/agent-suite-v1-20260814/gpt-5.6-sol.json"),
        "ranked": True,
    },
    {
        "key": "hy3",
        "label": "混元 3",
        "path": str(SOURCE_ROOT / "evaluation/agent/raw_runs/agent-suite-v1-qwen-hy3-rerun-20260814/hy3.json"),
        "ranked": True,
    },
    {
        "key": "qwen3.8-max",
        "label": "Qwen 3.8",
        "path": str(SOURCE_ROOT / "evaluation/agent/raw_runs/agent-suite-v1-qwen-hy3-rerun-20260814/qwen3.8-max.json"),
        "ranked": True,
    },
    {
        "key": "glm-5.2-internal",
        "label": "GLM-5.2-内部",
        "path": str(SOURCE_ROOT / "evaluation/agent/raw_runs/agent-suite-v1-glm52-internal-rerun-20260814/glm-5.2-internal.json"),
        "ranked": True,
    },
    {
        "key": "gpt-5.5",
        "label": "GPT-5.5",
        "path": str(SOURCE_ROOT / "evaluation/agent/raw_runs/agent-suite-v1.1-20260814/gpt-5.5.json"),
        "ranked": True,
    },
]

SCORECARDS = {
    "qwen3.8-max": {
        "task_result": 99.34,
        "trajectory_quality": 95.0,
        "delivery_quality": 96.0,
        "note": "跨工具核验和交付最完整；T08 未完成最终登记，且部分任务存在重复调用。",
    },
    "gpt-5.6-sol": {
        "task_result": 98.75,
        "trajectory_quality": 93.0,
        "delivery_quality": 95.0,
        "note": "执行路径简洁、状态说明准确；T03 已完成计划但未调用最终确认工具。",
    },
    "kimi-k3": {
        "task_result": 100.0,
        "trajectory_quality": 89.0,
        "delivery_quality": 93.0,
        "note": "八题均完成闭环；过程核验和异常解释略少于前两名。",
    },
    "opus-5": {
        "task_result": 100.0,
        "trajectory_quality": 87.0,
        "delivery_quality": 91.0,
        "note": "任务闭环完整；复杂任务中的过程自检和交付拆解不如前三名稳定。",
    },
    "deepseek-v4-pro": {
        "task_result": 100.0,
        "trajectory_quality": 84.0,
        "delivery_quality": 91.0,
        "note": "修正评分器误判后八题均完成；T03 搜索和核验更充分，明显优于 Flash，但存在重复搜索和较长执行路径。",
    },
    "gpt-5.5": {
        "task_result": 98.68,
        "trajectory_quality": 84.0,
        "delivery_quality": 90.0,
        "note": "T01-T07 全部完成；T08 少创建一封供应商邮件草稿，属于真实局部遗漏。",
    },
    "opus-4.8": {
        "task_result": 98.03,
        "trajectory_quality": 85.0,
        "delivery_quality": 89.0,
        "note": "T03/T06 的自动扣分主要来自评分器；T08 仍有真实未完成动作。",
    },
    "hy3": {
        "task_result": 100.0,
        "trajectory_quality": 77.0,
        "delivery_quality": 84.0,
        "note": "任务结果完整，但多数任务的过程核验和风险展开较为简略。",
    },
    "deepseek-v4-flash": {
        "task_result": 100.0,
        "trajectory_quality": 76.0,
        "delivery_quality": 86.0,
        "note": "修正评分器误判后结果层面与 Pro 接近；主要差异是搜索和交叉核验更少，过程证据较薄。",
    },
    "glm-5.2-internal": {
        "task_result": 98.09,
        "trajectory_quality": 68.0,
        "delivery_quality": 82.0,
        "note": "保留 GLM-5.2-内部的有效结果；OpenRouter 任务存在质量检查扣分，T08 未完成最终登记。",
    },
}

CALIBRATED_OVERRIDES = {
    "qwen3.8-max": {
        1: {"score": 100.0, "strict": True, "note": "原始分无须调整。"},
        2: {"score": 100.0, "strict": True, "note": "原始评分通过。"},
        3: {
            "score": 100.0,
            "strict": True,
            "note": "计划约束、风险预案和预算已用中文完整表达；原评分器的 cancelable 关键词判断误伤，且硬失败封顶不成立。",
        },
        4: {"score": 100.0, "strict": True, "note": "原始评分通过。"},
        5: {
            "score": 100.0,
            "strict": True,
            "note": "管理摘要和分析附录已完成事实、推断、不确定事项及异常覆盖；原评分器只接受英文标签，属于格式误判。",
        },
        6: {
            "score": 100.0,
            "strict": True,
            "note": "component、integration、qa 均为真实受影响任务，marketing 和 training 未变更；原评分器错误地要求只更新 integration、qa。",
        },
        7: {"score": 100.0, "strict": True, "note": "原始评分通过。"},
        8: {
            "score": 94.73684210526315,
            "strict": False,
            "note": "内部核对、恢复和供应商邮件草稿均完成，但没有调用 invoice_finalize，最终闭环确实未完成，保留该扣分。",
        },
    },
    "gpt-5.6-sol": {
        1: {"score": 100.0, "strict": True, "note": "原始分无须调整。"},
        2: {"score": 100.0, "strict": True, "note": "原始评分通过。"},
        3: {
            "score": 90.0,
            "strict": False,
            "note": "中文行程已满足慢节奏、风险和预算要求；原评分器的 slow_pace 关键词判断误伤。但检查后未调用最终确认工具，保留 10 分闭环扣分。",
        },
        4: {"score": 100.0, "strict": True, "note": "原始评分通过。"},
        5: {
            "score": 100.0,
            "strict": True,
            "note": "管理摘要和分析附录已完成事实、推断、不确定事项及异常覆盖；原评分器只接受英文标签，属于格式误判。",
        },
        6: {
            "score": 100.0,
            "strict": True,
            "note": "component、integration、qa 均为真实受影响任务，marketing 和 training 未变更；原评分器错误地要求只更新 integration、qa。",
        },
        7: {"score": 100.0, "strict": True, "note": "原始评分通过。"},
        8: {"score": 100.0, "strict": True, "note": "原始评分通过。"},
    },
    "kimi-k3": {
        task_id: {"score": 100.0, "strict": True, "note": "当前证据未发现需要保留的实质性扣分。"}
        for task_id in range(1, 9)
    },
    "opus-5": {
        task_id: {"score": 100.0, "strict": True, "note": "当前证据未发现需要保留的实质性扣分。"}
        for task_id in range(1, 9)
    },
    "opus-4.8": {
        3: {
            "score": 100.0,
            "strict": True,
            "note": "最终状态中的八项旅行约束和 finalized 均为 true；风险与预算已语义覆盖，原评分器只接受固定英文关键词。",
        },
        5: {
            "score": 100.0,
            "strict": True,
            "note": "管理摘要和分析附录已完成事实、推断、不确定事项及异常覆盖；原评分器的英文标签断言属于格式误判。",
        },
        6: {
            "score": 100.0,
            "strict": True,
            "note": "component、integration、qa 均为真实受影响任务，marketing 和 training 未变更；原评分器错误地要求只更新 integration、qa。",
        },
        8: {
            "score": 84.21052631578947,
            "strict": False,
            "note": "保留原始任务中的真实未完成动作，不因其他评分器修正而抹平。",
        },
    },
    "deepseek-v4-pro": {
        3: {
            "score": 100.0,
            "strict": True,
            "note": "八项约束、风险预案和预算拆分均已语义完成，且已 finalized；原评分器的英文关键词匹配误伤。",
        },
        5: {
            "score": 100.0,
            "strict": True,
            "note": "已完成事实、推断、不确定事项、重复和缺失的语义区分，并完成两个交付物；原评分器只接受英文标签。",
        },
        6: {
            "score": 100.0,
            "strict": True,
            "note": "component、integration、qa 均正确顺延，marketing 和 training 保持不变；原评分器的精确集合断言错误。",
        },
        8: {"score": 100.0, "strict": True, "note": "原始评分通过。"},
    },
    "deepseek-v4-flash": {
        3: {
            "score": 100.0,
            "strict": True,
            "note": "八项约束、风险预案和预算拆分均已语义完成，且已 finalized；原评分器的英文关键词匹配误伤。",
        },
        5: {
            "score": 100.0,
            "strict": True,
            "note": "已完成事实、推断、不确定事项、重复和缺失的语义区分，并完成两个交付物；原评分器只接受英文标签。",
        },
        6: {
            "score": 100.0,
            "strict": True,
            "note": "component、integration、qa 均正确顺延，marketing 和 training 保持不变；原评分器的精确集合断言错误。",
        },
        8: {"score": 100.0, "strict": True, "note": "原始评分通过。"},
    },
    "hy3": {
        3: {
            "score": 100.0,
            "strict": True,
            "note": "八项约束、风险预案和预算拆分均已语义完成，且已 finalized；原评分器的英文关键词匹配误伤。",
        },
        5: {
            "score": 100.0,
            "strict": True,
            "note": "已完成事实、推断、不确定事项、重复和缺失的语义区分，并完成两个交付物；原评分器只接受英文标签。",
        },
        6: {
            "score": 100.0,
            "strict": True,
            "note": "component、integration、qa 均正确顺延，marketing 和 training 保持不变；原评分器的精确集合断言错误。",
        },
        8: {"score": 100.0, "strict": True, "note": "原始评分通过。"},
    },
    "glm-5.2-internal": {
        3: {
            "score": 100.0,
            "strict": True,
            "note": "八项约束、风险预案和预算拆分均已语义完成，且已 finalized；原评分器的英文关键词匹配误伤。",
        },
        5: {
            "score": 100.0,
            "strict": True,
            "note": "已完成事实、推断、不确定事项、重复和缺失的语义区分，并完成两个交付物；原评分器只接受英文标签。",
        },
        6: {
            "score": 100.0,
            "strict": True,
            "note": "component、integration、qa 均正确顺延，marketing 和 training 保持不变；原评分器的精确集合断言错误。",
        },
        8: {
            "score": 94.73684210526315,
            "strict": False,
            "note": "没有调用 invoice_finalize，最终闭环确实未完成，保留原始扣分。",
        },
    },
    "gpt-5.5": {
        1: {"score": 100.0, "strict": True, "note": "修正契约后的自动评分通过。"},
        2: {"score": 100.0, "strict": True, "note": "修正契约后的自动评分通过。"},
        3: {"score": 100.0, "strict": True, "note": "修正契约后的自动评分通过。"},
        4: {"score": 100.0, "strict": True, "note": "修正契约后的自动评分通过。"},
        5: {"score": 100.0, "strict": True, "note": "修正契约后的自动评分通过。"},
        6: {"score": 100.0, "strict": True, "note": "修正契约后的自动评分通过。"},
        7: {"score": 100.0, "strict": True, "note": "修正契约后的自动评分通过。"},
        8: {
            "score": 89.47368421052632,
            "strict": False,
            "note": "少创建一封仍需供应商确认的邮件草稿，保留该局部扣分。",
        },
    },
}


def pretty(value: Any) -> str:
    if isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=False, indent=2)


def parse_tool_call(raw: Any) -> dict[str, Any]:
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except json.JSONDecodeError:
            return {"raw": raw}
    if not isinstance(raw, dict):
        return {"raw": pretty(raw)}

    result = {
        "id": raw.get("id"),
        "name": raw.get("name"),
        "arguments": raw.get("arguments", ""),
    }
    arguments = result["arguments"]
    if isinstance(arguments, str):
        try:
            result["arguments_json"] = json.loads(arguments)
        except json.JSONDecodeError:
            result["arguments_json"] = None
    else:
        result["arguments_json"] = arguments
    return result


def sanitize_message(message: dict[str, Any]) -> dict[str, Any]:
    tool_calls = message.get("tool_calls") or []
    return {
        "role": message.get("role", ""),
        "content": pretty(message.get("content", "")),
        "tool_call_id": message.get("tool_call_id"),
        "tool_calls": [parse_tool_call(call) for call in tool_calls],
    }


def normalize_task(task: dict[str, Any]) -> dict[str, Any]:
    task_id, task_label = TASK_LABELS.get(task["id"], (f"T{task['id']:02d}", task["name"]))
    return {
        "id": task["id"],
        "code": task_id,
        "label": task_label,
        "name": task["name"],
        "weighted_score": task.get("weighted_score"),
        "partial_credit": task.get("partial_credit"),
        "strict_pass": task.get("strict_pass"),
        "passed": task.get("passed"),
        "assertions_passed": task.get("assertions_passed"),
        "assertions_total": task.get("assertions_total"),
        "hard_fail_reasons": task.get("hard_fail_reasons") or [],
        "technical_errors": task.get("technical_errors") or [],
        "num_model_calls": task.get("num_model_calls", 0),
        "num_tool_calls": task.get("num_tool_calls", 0),
        "model_time_s": task.get("model_time_s", 0),
        "tool_time_s": task.get("tool_time_s", 0),
        "finish_reasons": task.get("finish_reasons") or [],
        "stop_reasons": task.get("stop_reasons") or [],
        "messages": [sanitize_message(message) for message in task.get("messages", [])],
        "assertions": [
            {
                "type": item.get("type"),
                "passed": item.get("passed"),
                "excluded": item.get("excluded"),
                "points": item.get("points"),
                "params": item.get("params"),
            }
            for item in task.get("assertion_results", [])
        ],
        "end_state": task.get("end_state"),
    }


def load_model(source: dict[str, Any]) -> dict[str, Any]:
    model = {
        "key": source["key"],
        "label": source["label"],
        "ranked": source.get("ranked", False),
        "status_note": source.get("status_note", ""),
        "source_path": source["path"],
        "meta": {},
        "summary": {},
        "tasks": [],
    }
    if not source["path"]:
        model["status"] = "not_run"
        return model

    path = Path(source["path"])
    if not path.exists():
        model["status"] = "missing"
        model["status_note"] = model["status_note"] or "结果文件不存在。"
        return model

    raw = json.loads(path.read_text(encoding="utf-8"))
    model["meta"] = {
        "benchmark_version": raw.get("meta", {}).get("benchmark_version"),
        "batch_id": raw.get("meta", {}).get("formal_runner", {}).get("batch_id"),
        "toolset": raw.get("meta", {}).get("toolset"),
        "reasoning_effort": raw.get("meta", {}).get("reasoning_effort"),
        "total_tasks": raw.get("meta", {}).get("total_tasks"),
        "duration_seconds": raw.get("meta", {}).get("duration_seconds"),
    }
    model["summary"] = raw.get("summary", {})
    model["tasks"] = [normalize_task(task) for task in raw.get("tasks", [])]
    model["status"] = "valid" if source.get("ranked") else "excluded"
    return model


def load_final_score_registry() -> dict[str, Any]:
    """Load the single public total score for every ranked model."""
    registry = json.loads(FINAL_SCORE_REGISTRY.read_text(encoding="utf-8"))
    scores = registry.get("scores")
    expected_keys = {source["key"] for source in MODEL_SOURCES if source.get("ranked")}
    if not isinstance(scores, dict) or set(scores) != expected_keys:
        missing = sorted(expected_keys - set(scores or {}))
        extra = sorted(set(scores or {}) - expected_keys)
        raise ValueError(f"Final score registry keys do not match ranked models: missing={missing}, extra={extra}")
    for model_key, entry in scores.items():
        if not isinstance(entry, dict) or "official_score" not in entry:
            raise ValueError(f"Missing official_score for {model_key}")
        score = entry["official_score"]
        if not isinstance(score, (int, float)) or not 0 <= score <= 100:
            raise ValueError(f"Invalid official_score for {model_key}: {score!r}")
        if entry.get("tier") not in {"T1", "T2", "T3"}:
            raise ValueError(f"Invalid tier for {model_key}: {entry.get('tier')!r}")
    return registry


def js_literal(value: Any) -> str:
    raw = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    return (
        raw.replace("&", "\\u0026")
        .replace("<", "\\u003c")
        .replace(">", "\\u003e")
        .replace("</script", "<\\/script")
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--template",
        default=str(PROJECT_ROOT / "tools/agent-review-template.html"),
    )
    parser.add_argument(
        "--output",
        default=str(PROJECT_ROOT / "evaluation/evidence/agent-interaction-review.html"),
    )
    args = parser.parse_args()

    final_scores = load_final_score_registry()
    models = [load_model(source) for source in MODEL_SOURCES]
    ranked_models = [model for model in models if model["ranked"] and model["status"] == "valid"]
    ranked_models.sort(
        key=lambda model: final_scores["scores"][model["key"]]["official_score"],
        reverse=True,
    )

    report = {
        "generated_at": "2026-08-15",
        "title": "Agent 交互复核预览",
        "task_count": 8,
        "models": models,
        "scorecards": SCORECARDS,
        "final_scores": final_scores,
        "scoring_method": {
            "tiers": {
                "T1": "94 分及以上：任务闭环完整，过程稳定且交付可复核。",
                "T2": "88–93.99 分：基本完成任务，但过程可靠性或交付质量存在明显短板。",
                "T3": "低于 88 分：任务完成度、过程可靠性或交付质量存在较大缺口。",
            },
            "description": "正式总分以人工确认后的正式总分登记为准；预览页不根据题目复核分自动重新汇总模型总分。",
        },
        "initial_overrides": {
            f"{model_key}::T{task_id:02d}": {
                **review,
                "updated_at": "2026-08-14T00:00:00Z",
            }
            for model_key, tasks in CALIBRATED_OVERRIDES.items()
            for task_id, review in tasks.items()
        },
        "ranked_model_keys": [model["key"] for model in ranked_models],
        "default_model_key": "qwen3.8-max",
        "notes": [
            "预览包含系统消息、用户题面、模型可见回复、工具调用、工具返回、断言结果和最终环境状态。",
            "结果文件中的隐藏 reasoning_content 不在预览中展示；人工复核应以模型可见输出、工具轨迹和最终状态为准。",
            "任务级复核分用于查看每道题的执行结果；模型正式总分只读取正式总分登记。",
            "每个模型只保留一个正式总分，题目级分数和过程指标不作为第二个总分展示。",
            "GLM-5.2 与 GLM-5.2-内部为同一模型，本预览仅保留有效的 GLM-5.2-内部结果。",
        ],
    }

    template = Path(args.template).read_text(encoding="utf-8")
    output = template.replace("__REPORT_DATA__", js_literal(report))
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(output, encoding="utf-8")
    print(f"wrote {output_path} ({output_path.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
