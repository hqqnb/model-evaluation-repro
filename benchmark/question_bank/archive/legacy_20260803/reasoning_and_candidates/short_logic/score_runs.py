import json
import os
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

from benchmark.question_bank.archive.legacy_20260803.reasoning_and_candidates.short_logic.grade import grade_response
from benchmark.question_bank.archive.legacy_20260803.reasoning_and_candidates.short_logic.tasks import build_tasks


DELIVERY_FAILURE_STATUSES = {"api_failure", "unfinished"}
SEMANTIC_ERROR_STATUSES = {"wrong", "partial"}

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
COLLECTOR_RUNS = Path(
    os.environ.get(
        "COLLECTOR_RUNS_DIR",
        REPOSITORY_ROOT / "runners/model-api-collector/runs",
    )
)
PRIMARY_RUN = Path(
    os.environ.get(
        "SHORT_LOGIC_PRIMARY_RUN",
        COLLECTOR_RUNS / "20260806T061903262278Z-a6d720b2",
    )
)
RETRY_RUN = Path(
    os.environ.get(
        "SHORT_LOGIC_RETRY_RUN",
        COLLECTOR_RUNS / "20260806T062716371088Z-90b951b9",
    )
)
OUTPUT_ROOT = Path(__file__).resolve().parents[1]
SCORES_PATH = OUTPUT_ROOT / "short_logic_scores_20260806.json"
MANIFEST_PATH = OUTPUT_ROOT / "short_logic_run_manifest_20260806.json"
REPORT_PATH = OUTPUT_ROOT / "SHORT_HARD_LOGIC_DISCRIMINATION_REPORT_20260806.md"


def _load_records(run_dir: Path) -> Iterable[Dict[str, Any]]:
    result_path = run_dir / "results.jsonl"
    for line in result_path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            yield json.loads(line)


def score_run_directories(
    run_directories: Iterable[Path],
) -> List[Dict[str, Any]]:
    tasks = {task.id: task for task in build_tasks()}
    rows = []
    for run_dir in run_directories:
        for record in _load_records(run_dir):
            task_id = record.get("prompt_id")
            base = {
                "run_dir": str(run_dir),
                "request_id": record.get("request_id"),
                "task_id": task_id,
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
            response = (
                response_path.read_text(encoding="utf-8")
                if response_path.exists()
                else ""
            )
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


def merge_delivery_retries(
    primary_rows: Iterable[Dict[str, Any]],
    retry_rows: Iterable[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    retries: Dict[Tuple[Any, Any], Dict[str, Any]] = {
        (row.get("model_alias"), row.get("task_id")): row for row in retry_rows
    }
    merged = []
    for row in primary_rows:
        retry = retries.get((row.get("model_alias"), row.get("task_id")))
        if (
            row.get("status") in DELIVERY_FAILURE_STATUSES
            and retry is not None
            and retry.get("status") not in DELIVERY_FAILURE_STATUSES
        ):
            replacement = dict(retry)
            replacement["replaced_by_retry"] = True
            replacement["primary_status"] = row.get("status")
            replacement["primary_request_id"] = row.get("request_id")
            merged.append(replacement)
        else:
            merged.append(dict(row))
    return merged


def _model_summary(
    merged_rows: List[Dict[str, Any]],
    primary_rows: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    merged_grouped = defaultdict(list)
    primary_grouped = defaultdict(list)
    for row in merged_rows:
        merged_grouped[row["model_alias"]].append(row)
    for row in primary_rows:
        primary_grouped[row["model_alias"]].append(row)

    summaries = []
    for model_alias, model_rows in merged_grouped.items():
        initial_rows = primary_grouped[model_alias]
        initial_statuses = Counter(row["status"] for row in initial_rows)
        summaries.append(
            {
                "model": model_rows[0]["model"],
                "model_alias": model_alias,
                "score": sum(row["points"] for row in model_rows),
                "whole_correct": sum(row["whole_correct"] for row in model_rows),
                "semantic_errors": sum(
                    row["status"] in SEMANTIC_ERROR_STATUSES for row in model_rows
                ),
                "initial_api_failure": initial_statuses["api_failure"],
                "initial_unfinished": initial_statuses["unfinished"],
                "initial_delivery_anomalies": sum(
                    initial_statuses[status]
                    for status in DELIVERY_FAILURE_STATUSES
                ),
                "retries_recovered": sum(
                    bool(row.get("replaced_by_retry")) for row in model_rows
                ),
                "format_noncompliant": sum(
                    row["status"] not in DELIVERY_FAILURE_STATUSES
                    and not row["format_compliant"]
                    for row in model_rows
                ),
            }
        )
    return sorted(
        summaries,
        key=lambda item: (-item["score"], -item["whole_correct"], item["model"]),
    )


def _task_summary(
    primary_rows: List[Dict[str, Any]],
    merged_rows: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    primary_grouped = defaultdict(list)
    merged_grouped = defaultdict(list)
    for row in primary_rows:
        primary_grouped[row["task_id"]].append(row)
    for row in merged_rows:
        merged_grouped[row["task_id"]].append(row)

    summaries = []
    for task_id, task_rows in merged_grouped.items():
        initial_rows = primary_grouped[task_id]
        summaries.append(
            {
                "task_id": task_id,
                "pass_count": sum(row["whole_correct"] for row in task_rows),
                "average_points": round(
                    sum(row["points"] for row in task_rows) / len(task_rows), 2
                ),
                "statuses": dict(Counter(row["status"] for row in task_rows)),
                "semantic_error_count": sum(
                    row["status"] in SEMANTIC_ERROR_STATUSES for row in task_rows
                ),
                "initial_delivery_anomalies": sum(
                    row["status"] in DELIVERY_FAILURE_STATUSES
                    for row in initial_rows
                ),
                "retries_recovered": sum(
                    bool(row.get("replaced_by_retry")) for row in task_rows
                ),
            }
        )
    return sorted(summaries, key=lambda item: item["task_id"])


def _semantic_failure_note(row: Dict[str, Any]) -> str:
    parsed = row.get("parsed_answer")
    if row["task_id"] == "S01" and isinstance(parsed, dict):
        if "AC" in parsed.get("worlds", []):
            return "错误加入 AC；选择 A 必须同时选 B，因此 AC 不是合法世界"
    if row["task_id"] == "S04" and isinstance(parsed, dict):
        solutions = parsed.get("solutions")
        if isinstance(solutions, list):
            return (
                f"输出 {len(solutions)} 个自洽解；穷举校验后实际只有 "
                "FFTFTF 这 1 个"
            )
    failed_components = [
        field
        for field, correct in row.get("component_results", {}).items()
        if not correct
    ]
    return (
        "错误字段："
        f"{'、'.join(failed_components) if failed_components else '无可提取字段'}"
    )


def _render_report(
    primary_rows: List[Dict[str, Any]],
    retry_rows: List[Dict[str, Any]],
    merged_rows: List[Dict[str, Any]],
    model_summary: List[Dict[str, Any]],
) -> str:
    tasks = {task.id: task for task in build_tasks()}
    task_summary = _task_summary(primary_rows, merged_rows)
    semantic_tasks = [
        item["task_id"] for item in task_summary if item["semantic_error_count"]
    ]
    non_semantic_tasks = [
        item["task_id"] for item in task_summary if not item["semantic_error_count"]
    ]
    delivery_anomalies = sum(
        row["status"] in DELIVERY_FAILURE_STATUSES for row in primary_rows
    )
    retries_recovered = sum(
        bool(row.get("replaced_by_retry")) for row in merged_rows
    )
    format_noncompliant = sum(
        row["status"] not in DELIVERY_FAILURE_STATUSES
        and not row["format_compliant"]
        for row in merged_rows
    )
    threshold_passed = len(semantic_tasks) >= 4
    denominator = max(Counter(row["model_alias"] for row in merged_rows).values())

    lines = [
        "# 短题型高难逻辑题区分度实测",
        "",
        "日期：2026-08-06",
        "",
        "## 结论",
        "",
        f"- 实测 3 个模型、6 道题，首次调用 {len(primary_rows)} 次；"
        f"另对交付异常补跑 {len(retry_rows)} 次。",
        "- 真正产生语义差异的题："
        f"{'、'.join(semantic_tasks) if semantic_tasks else '无'}，"
        f"共 {len(semantic_tasks)}/6 道。",
        f"- 首次交付异常：{delivery_anomalies} 次；"
        f"补跑恢复：{retries_recovered} 次。",
        f"- 格式不合规：{format_noncompliant} 次，单独记录，不计为推理错误。",
        "- "
        f"{'达到' if threshold_passed else '未达到'}入库门槛："
        "原定要求至少 4/6 道在强模型间产生语义差异。",
        "",
        "这组题有有限区分度，但不足以作为旗舰模型的稳定排序题组。"
        "当前不建议继续扩展更多模型；应保留 S01、S04，增强或替换其余题目后再预跑。",
        "",
        "## 模型结果",
        "",
        "| 模型 | 语义分 | 正确题 | 语义错误 | 首次交付异常 | 补跑恢复 | 格式不合规 |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for item in model_summary:
        lines.append(
            f"| {item['model']} | {item['score']}/60 | "
            f"{item['whole_correct']}/{denominator} | "
            f"{item['semantic_errors']} | {item['initial_delivery_anomalies']} | "
            f"{item['retries_recovered']} | {item['format_noncompliant']} |"
        )

    lines.extend(
        [
            "",
            "语义分使用补跑恢复交付异常后的结果；补跑只替换接口失败或空回答，"
            "不会覆盖首次已经返回的错误答案。",
            "",
            "## 逐题结果",
            "",
            "| 题目 | 测试重点 | 语义正确 | 首次交付异常 | 判断 |",
            "|---|---|---:|---:|---|",
        ]
    )
    for item in task_summary:
        judgment = (
            "产生语义差异"
            if item["semantic_error_count"]
            else (
                "仅测到交付稳定性"
                if item["initial_delivery_anomalies"]
                else "3 个模型全部通过"
            )
        )
        lines.append(
            f"| {item['task_id']} | {tasks[item['task_id']].title} | "
            f"{item['pass_count']}/3 | {item['initial_delivery_anomalies']} | "
            f"{judgment} |"
        )

    lines.extend(["", "## 关键差异", ""])
    semantic_failures = [
        row
        for row in merged_rows
        if row["status"] in SEMANTIC_ERROR_STATUSES
    ]
    for row in sorted(
        semantic_failures, key=lambda item: (item["task_id"], item["model"])
    ):
        lines.append(
            f"- {row['task_id']} / {row['model']}："
            f"{_semantic_failure_note(row)}。"
        )
    primary_delivery_failures = [
        row
        for row in primary_rows
        if row["status"] in DELIVERY_FAILURE_STATUSES
    ]
    for row in sorted(
        primary_delivery_failures,
        key=lambda item: (item["task_id"], item["model"]),
    ):
        recovered = any(
            item.get("replaced_by_retry")
            and item["model_alias"] == row["model_alias"]
            and item["task_id"] == row["task_id"]
            for item in merged_rows
        )
        lines.append(
            f"- {row['task_id']} / {row['model']}：首次为 {row['status']}，"
            f"{'补跑后答对' if recovered else '补跑未恢复'}；"
            "该项记为交付稳定性，不记为语义错误。"
        )

    lines.extend(
        [
            "",
            "## 评分边界",
            "",
            "- S04 中 `[3,5]` 与 `[\"S3\",\"S5\"]` 语义等价。",
            "- S05 中 `state`、`n`、`failing_state` 表示同一个状态编号，"
            "数值相同即视为语义等价。",
            "- 使用 Markdown 代码块包裹 JSON 记为格式不合规，但语义答案仍正常评分。",
            "- 补跑只恢复 `api_failure` 或 `unfinished`；"
            "`wrong` 和 `partial` 不允许被补跑覆盖。",
            "",
            "## 题目处理",
            "",
            "- 保留：S01、S04。两题让至少一个强模型给出了完整但错误的答案。",
            "- 降为稳定性诊断：S03。成功返回后 3 个模型均答对，"
            "区分来自首次交付异常而非推理能力。",
            "- 增强或替换："
            f"{'、'.join(task for task in non_semantic_tasks if task != 'S03')}。"
            "这些题在本轮没有形成语义差异。",
        ]
    )
    return "\n".join(lines).rstrip() + "\n"


def _run_manifest(run_dir: Path, role: str) -> Dict[str, Any]:
    metadata = json.loads((run_dir / "run.json").read_text(encoding="utf-8"))
    return {
        "role": role,
        "run_dir": str(run_dir),
        "run_id": metadata.get("run_id"),
        "created_at": metadata.get("created_at"),
        "model_aliases": metadata.get("model_aliases"),
        "prompt_ids": metadata.get("prompt_ids"),
        "record_count": sum(1 for _ in _load_records(run_dir)),
        "prompts_sha256": metadata.get("prompts_sha256"),
        "config_sha256": metadata.get("config_sha256"),
        "oneapi_base_url": metadata.get("oneapi_base_url"),
    }


def generate_outputs(
    primary_run: Path = PRIMARY_RUN,
    retry_run: Path = RETRY_RUN,
) -> List[Dict[str, Any]]:
    primary_rows = score_run_directories([primary_run])
    retry_rows = score_run_directories([retry_run])
    merged_rows = merge_delivery_retries(primary_rows, retry_rows)
    model_summary = _model_summary(merged_rows, primary_rows)
    task_summary = _task_summary(primary_rows, merged_rows)

    payload = {
        "scoring_policy": {
            "primary_result_is_authoritative_for_semantic_answers": True,
            "retry_replaces_statuses": sorted(DELIVERY_FAILURE_STATUSES),
            "semantic_error_statuses": sorted(SEMANTIC_ERROR_STATUSES),
        },
        "primary_rows": primary_rows,
        "retry_rows": retry_rows,
        "merged_rows": merged_rows,
        "model_summary": model_summary,
        "task_summary": task_summary,
    }
    SCORES_PATH.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    MANIFEST_PATH.write_text(
        json.dumps(
            [
                _run_manifest(primary_run, "primary"),
                _run_manifest(retry_run, "delivery_retry"),
            ],
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    REPORT_PATH.write_text(
        _render_report(primary_rows, retry_rows, merged_rows, model_summary),
        encoding="utf-8",
    )
    return merged_rows


if __name__ == "__main__":
    result_rows = generate_outputs()
    print(f"Scored {len(result_rows)} merged results")
    print(REPORT_PATH)
