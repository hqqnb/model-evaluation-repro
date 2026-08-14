import json
import os
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List

from benchmark.agent_benchmark.high_pressure.grade import grade_response
from benchmark.agent_benchmark.high_pressure.tasks import build_tasks


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
COLLECTOR_RUNS = Path(
    os.environ.get(
        "COLLECTOR_RUNS_DIR",
        REPOSITORY_ROOT / "runners/model-api-collector/runs",
    )
)
SCORES_PATH = Path(__file__).resolve().parent / "scores.json"
MANIFEST_PATH = Path(__file__).resolve().parent / "run_manifest.json"
REPORT_PATH = Path(__file__).resolve().parents[1] / (
    "HIGH_PRESSURE_DISCRIMINATION_REPORT_20260805.md"
)


def discover_run_directories() -> List[Path]:
    return sorted(
        path.parent
        for path in COLLECTOR_RUNS.glob("high-pressure-20260805-*/*/results.jsonl")
    )


def _load_records(run_dir: Path) -> Iterable[Dict[str, Any]]:
    result_path = run_dir / "results.jsonl"
    for line in result_path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            yield json.loads(line)


def score_run_directories(run_directories: Iterable[Path]) -> List[Dict[str, Any]]:
    tasks = {task.id: task for task in build_tasks()}
    rows = []
    for run_dir in run_directories:
        for record in _load_records(run_dir):
            base = {
                "run_dir": str(run_dir),
                "request_id": record.get("request_id"),
                "task_id": record.get("prompt_id"),
                "model": record.get("model"),
                "model_alias": record.get("model_alias"),
                "http_status": record.get("http_status"),
                "total_time_ms": record.get("total_time_ms"),
                "total_tokens": record.get("total_tokens"),
                "format_compliant": False,
                "component_results": {},
            }
            if record.get("status") != "success":
                rows.append(
                    {
                        **base,
                        "points": 0,
                        "whole_correct": False,
                        "status": "api_failure",
                        "error": record.get("error_type") or "request failed",
                    }
                )
                continue

            task_id = record["prompt_id"]
            response_path_value = record.get("response_text_path")
            if task_id not in tasks or not response_path_value:
                rows.append(
                    {
                        **base,
                        "points": 0,
                        "whole_correct": False,
                        "status": "unfinished",
                        "error": "missing task or response path",
                    }
                )
                continue
            response_path = run_dir / response_path_value
            response = response_path.read_text(encoding="utf-8") if response_path.exists() else ""
            result = grade_response(tasks[task_id], response)
            rows.append(
                {
                    **base,
                    "points": result.points,
                    "whole_correct": result.whole_correct,
                    "status": result.status,
                    "format_compliant": result.format_compliant,
                    "component_results": result.component_results,
                    "parsed_answer": result.parsed_answer,
                    "error": result.error,
                    "response_path": str(response_path),
                }
            )
    return rows


def _model_summary(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    grouped = defaultdict(list)
    for row in rows:
        grouped[row["model"]].append(row)
    summaries = []
    for model, model_rows in grouped.items():
        statuses = Counter(row["status"] for row in model_rows)
        summaries.append(
            {
                "model": model,
                "score": sum(row["points"] for row in model_rows),
                "whole_correct": sum(row["whole_correct"] for row in model_rows),
                "partial": statuses["partial"],
                "unfinished": statuses["unfinished"],
                "api_failure": statuses["api_failure"],
                "format_noncompliant": sum(
                    row["status"] != "api_failure" and not row["format_compliant"]
                    for row in model_rows
                ),
            }
        )
    return sorted(
        summaries,
        key=lambda item: (-item["score"], -item["whole_correct"], item["model"]),
    )


def _task_summary(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    grouped = defaultdict(list)
    for row in rows:
        grouped[row["task_id"]].append(row)
    summaries = []
    for task_id, task_rows in grouped.items():
        summaries.append(
            {
                "task_id": task_id,
                "pass_count": sum(row["whole_correct"] for row in task_rows),
                "average_points": round(
                    sum(row["points"] for row in task_rows) / len(task_rows), 2
                ),
                "statuses": dict(Counter(row["status"] for row in task_rows)),
            }
        )
    return sorted(summaries, key=lambda item: item["task_id"])


def _render_report(
    rows: List[Dict[str, Any]],
    model_summary: List[Dict[str, Any]],
    task_summary: List[Dict[str, Any]],
) -> str:
    tasks = {task.id: task for task in build_tasks()}
    task_rows = defaultdict(list)
    model_rows = defaultdict(list)
    for row in rows:
        task_rows[row["task_id"]].append(row)
        model_rows[row["model"]].append(row)

    semantic_error_tasks = sorted(
        task_id
        for task_id, grouped_rows in task_rows.items()
        if any(row["status"] in {"wrong", "partial"} for row in grouped_rows)
    )
    delivery_only_tasks = sorted(
        task_id
        for task_id, grouped_rows in task_rows.items()
        if not any(row["status"] in {"wrong", "partial"} for row in grouped_rows)
        and any(row["status"] in {"unfinished", "api_failure"} for row in grouped_rows)
    )
    semantic_clean_models = sorted(
        model
        for model, grouped_rows in model_rows.items()
        if any(row["status"] == "correct" for row in grouped_rows)
        and all(row["status"] in {"correct", "api_failure"} for row in grouped_rows)
    )
    semantic_error_count = sum(
        row["status"] in {"wrong", "partial"} for row in rows
    )
    delivery_failure_count = sum(
        row["status"] in {"unfinished", "api_failure"} for row in rows
    )
    medium_tasks = sum(2 <= item["pass_count"] <= 5 for item in task_summary)
    all_pass_tasks = sum(item["pass_count"] == 7 for item in task_summary)
    score_tiers = len({item["score"] for item in model_summary})
    criteria = {
        "最多3道全员通过": all_pass_tasks <= 3,
        "至少6道通过率为2/7至5/7": medium_tasks >= 6,
        "至少3个分数梯队": score_tiers >= 3,
        "结果完整覆盖70次调用": len(rows) == 70,
    }
    lines = [
        "# 长任务型推理题区分度 Pilot",
        "",
        "日期：2026-08-05",
        "",
        "## 1. 总览",
        "",
        f"- 结果记录：{len(rows)} 条；",
        f"- 全员通过题：{all_pass_tasks} 道；",
        f"- 通过率处于 2/7 至 5/7 的题：{medium_tasks} 道；",
        f"- 模型分数梯队：{score_tiers} 个。",
        "",
        "### 核心判断",
        "",
        f"- 语义推理错误：{semantic_error_count} 次；"
        f"长程交付失败：{delivery_failure_count} 次。",
        "- 真正产生语义错误的题："
        f"{'、'.join(semantic_error_tasks) if semantic_error_tasks else '无'}。",
        "- 只产生未完成或接口失败的题："
        f"{'、'.join(delivery_only_tasks) if delivery_only_tasks else '无'}。",
        "- 在成功返回的请求中没有语义失分的模型："
        f"{'、'.join(semantic_clean_models) if semantic_clean_models else '无'}。",
        "",
        "| 模型 | 总分 | 整题正确 | 部分正确 | 未完成 | 接口失败 | 格式不合规 |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for item in model_summary:
        lines.append(
            f"| {item['model']} | {item['score']} | {item['whole_correct']}/10 | "
            f"{item['partial']} | {item['unfinished']} | {item['api_failure']} | "
            f"{item['format_noncompliant']} |"
        )
    lines.extend(
        [
            "",
            "## 2. 逐题结果",
            "",
            "| 题目 | 名称 | 整题通过 | 平均得分 | 状态分布 |",
            "|---|---|---:|---:|---|",
        ]
    )
    for item in task_summary:
        status_text = "、".join(
            f"{status}={count}" for status, count in sorted(item["statuses"].items())
        )
        lines.append(
            f"| {item['task_id']} | {tasks[item['task_id']].title} | "
            f"{item['pass_count']}/7 | {item['average_points']}/10 | {status_text} |"
        )
    lines.extend(["", "## 3. 验收标准", ""])
    for label, passed in criteria.items():
        lines.append(f"- {'通过' if passed else '未通过'}：{label}。")
    lines.extend(
        [
            "",
            "## 4. 题目处理建议",
            "",
            "- 保留为核心推理诊断："
            f"{'、'.join(semantic_error_tasks) if semantic_error_tasks else '无'}。"
            "这些题至少让一个模型给出了可解析但语义错误的答案。",
            "- 仅作为长程交付压力测试："
            f"{'、'.join(delivery_only_tasks) if delivery_only_tasks else '无'}。"
            "这些题没有制造语义差异，不能据此给完成作答的旗舰模型排序。",
            "- 本轮可以区分中低表现模型，但旗舰模型上限已明显饱和；"
            "下一轮应提高推理结构难度，而不是继续增加输入长度或机械步骤。",
            "",
            "## 5. 失败明细",
            "",
        ]
    )
    for row in sorted(rows, key=lambda item: (item["task_id"], item["model"])):
        if row["whole_correct"]:
            continue
        failed_components = [
            field
            for field, correct in row.get("component_results", {}).items()
            if not correct
        ]
        lines.append(
            f"- {row['task_id']} / {row['model']}：{row['status']}，"
            f"得分 {row['points']}/10，错误字段 "
            f"{'、'.join(failed_components) if failed_components else '无可提取字段'}。"
        )
    return "\n".join(lines).rstrip() + "\n"


def generate_outputs(run_directories: Iterable[Path] = ()) -> List[Dict[str, Any]]:
    directories = list(run_directories) or discover_run_directories()
    rows = score_run_directories(directories)
    model_summary = _model_summary(rows)
    task_summary = _task_summary(rows)
    payload = {
        "rows": rows,
        "model_summary": model_summary,
        "task_summary": task_summary,
    }
    SCORES_PATH.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    manifest = [
        {
            "run_dir": str(run_dir),
            "record_count": sum(1 for _ in _load_records(run_dir)),
        }
        for run_dir in directories
    ]
    MANIFEST_PATH.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    REPORT_PATH.write_text(
        _render_report(rows, model_summary, task_summary),
        encoding="utf-8",
    )
    return rows


if __name__ == "__main__":
    result_rows = generate_outputs()
    print(f"Scored {len(result_rows)} results")
    print(REPORT_PATH)
