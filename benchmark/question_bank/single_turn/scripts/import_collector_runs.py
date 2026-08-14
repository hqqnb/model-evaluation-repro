#!/usr/bin/env python3
"""Import collector archives and build stable per-answer GitHub links."""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REPOSITORY = "hqqnb/llm-evaluation-question-bank"


def load_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    records = []
    with path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if line.strip():
                record = json.loads(line)
                if not isinstance(record, dict):
                    raise ValueError(f"{path}:{line_number} is not an object")
                records.append(record)
    return records


def parse_collector_run(value: str) -> tuple[str, Path]:
    alias, separator, raw_path = value.partition("=")
    if not separator or not alias or not raw_path:
        raise argparse.ArgumentTypeError("expected MODEL_ALIAS=/path/to/collector/run")
    return alias, Path(raw_path).expanduser().resolve()


def git_revision() -> str | None:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    return result.stdout.strip() if result.returncode == 0 else None


def answer_url(repository: str, campaign_id: str, item_id: str, alias: str) -> str:
    return (
        f"https://github.com/{repository}/blob/main/runs/{campaign_id}/"
        f"responses/{item_id}/{alias}.md"
    )


def validate_run(
    alias: str, run_path: Path, prompt_ids: list[str]
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    run_metadata = load_json(run_path / "run.json")
    results = load_jsonl(run_path / "results.jsonl")
    if run_metadata.get("model_aliases") != [alias]:
        raise ValueError(
            f"{run_path} model aliases are {run_metadata.get('model_aliases')!r}, "
            f"expected [{alias!r}]"
        )
    result_ids = [record.get("prompt_id") for record in results]
    if result_ids != prompt_ids:
        raise ValueError(f"{run_path} result prompt IDs do not match the benchmark")
    if run_metadata.get("repeat") != 1:
        raise ValueError(f"{run_path} was not collected with repeat=1")
    return run_metadata, results


def copy_response(
    source_run: Path,
    source_record: dict[str, Any],
    destination: Path,
) -> str:
    relative = source_record.get("response_text_path")
    if not isinstance(relative, str):
        raise ValueError(f"missing response_text_path in {source_record!r}")
    source = source_run / relative
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, destination)
    return hashlib.sha256(destination.read_bytes()).hexdigest()


def write_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")


def write_index(
    path: Path,
    campaign_id: str,
    items: list[dict[str, Any]],
    records: list[dict[str, Any]],
) -> None:
    by_key = {(record["item_id"], record["model_alias"]): record for record in records}
    aliases = []
    for record in records:
        if record["model_alias"] not in aliases:
            aliases.append(record["model_alias"])
    lines = [
        f"# 模型回答：{campaign_id}",
        "",
        "每道题每个模型调用一次。所有“原始回答”文件均为 API 返回文本的原样副本；",
        "Coding 题的运行预览链接在提取并发布后写入本页。",
        "",
    ]
    category_names = {
        "reasoning": "推理",
        "coding": "Coding & Agent",
        "multimodal": "多模态",
    }
    for category in ("reasoning", "coding", "multimodal"):
        lines.extend(
            [
                f"## {category_names[category]}",
                "",
                "| 题目 | 模型 | 状态 | 原始回答 | 运行预览 | 外部依赖 |",
                "| --- | --- | --- | --- | --- | --- |",
            ]
        )
        for item in items:
            if item["category"] != category:
                continue
            for alias in aliases:
                record = by_key[(item["id"], alias)]
                relative_answer = Path(record["answer_path"]).relative_to(
                    f"runs/{campaign_id}"
                )
                answer_link = f"[查看](./{relative_answer.as_posix()})"
                preview_url = record.get("preview_url")
                preview_link = f"[打开]({preview_url})" if preview_url else "—"
                external = record.get("external_urls") or []
                external_note = (
                    f"有（{len(external)} 个 URL）" if external else "无"
                )
                lines.append(
                    f"| `{item['id']}` | `{alias}` | {record['status']} | "
                    f"{answer_link} | {preview_link} | {external_note} |"
                )
        lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def import_runs(
    campaign_id: str,
    collector_runs: list[tuple[str, Path]],
    repository: str,
) -> Path:
    prompts_path = ROOT / "dataset/prompts.json"
    items = load_json(prompts_path)["items"]
    prompt_ids = [item["id"] for item in items]
    categories = {item["id"]: item["category"] for item in items}
    campaign_path = ROOT / "runs" / campaign_id
    if campaign_path.exists():
        raise FileExistsError(f"campaign already exists: {campaign_path}")
    temporary_path = ROOT / "runs" / f".{campaign_id}.tmp"
    if temporary_path.exists():
        shutil.rmtree(temporary_path)
    temporary_path.mkdir(parents=True)

    all_records: list[dict[str, Any]] = []
    imported_runs: list[dict[str, Any]] = []
    try:
        for alias, source_run in collector_runs:
            run_metadata, results = validate_run(alias, source_run, prompt_ids)
            archive_destination = temporary_path / "collector" / alias
            shutil.copytree(
                source_run,
                archive_destination,
                ignore=shutil.ignore_patterns("*.sse"),
            )
            imported_runs.append(
                {
                    "model_alias": alias,
                    "collector_run_id": run_metadata["run_id"],
                    "oneapi_base_url": run_metadata["oneapi_base_url"],
                    "archive_path": f"runs/{campaign_id}/collector/{alias}",
                }
            )
            for source_record in results:
                item_id = source_record["prompt_id"]
                relative_answer = Path("responses") / item_id / f"{alias}.md"
                digest = copy_response(
                    source_run,
                    source_record,
                    temporary_path / relative_answer,
                )
                request_id = source_record["request_id"]
                record = {
                    "campaign_id": campaign_id,
                    "item_id": item_id,
                    "category": categories[item_id],
                    "model_alias": alias,
                    "model": source_record.get("model"),
                    "status": source_record.get("status"),
                    "http_status": source_record.get("http_status"),
                    "answer_sha256": digest,
                    "answer_path": f"runs/{campaign_id}/{relative_answer.as_posix()}",
                    "answer_url": answer_url(repository, campaign_id, item_id, alias),
                    "collector_metadata_path": (
                        f"runs/{campaign_id}/collector/{alias}/requests/"
                        f"{request_id}/metadata.json"
                    ),
                    "collector_raw_response_path": (
                        f"runs/{campaign_id}/collector/{alias}/"
                        f"{source_record.get('raw_response_path')}"
                    ),
                    "preview_url": None,
                    "preview_status": None,
                }
                for key in (
                    "time_to_first_event_ms",
                    "time_to_first_reasoning_ms",
                    "time_to_first_text_ms",
                    "total_time_ms",
                    "prompt_tokens",
                    "completion_tokens",
                    "total_tokens",
                    "error_type",
                ):
                    record[key] = source_record.get(key)
                for key in ("notes", "variant"):
                    if source_record.get(key) is not None:
                        record[key] = source_record[key]
                all_records.append(record)

        expected = len(items) * len(collector_runs)
        if len(all_records) != expected:
            raise ValueError(f"imported {len(all_records)} results, expected {expected}")

        manifest = {
            "schema_version": "1.0",
            "campaign_id": campaign_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "question_bank_revision": git_revision(),
            "prompts_sha256": hashlib.sha256(prompts_path.read_bytes()).hexdigest(),
            "repeat": 1,
            "item_count": len(items),
            "model_count": len(collector_runs),
            "request_count": len(all_records),
            "repository": repository,
            "collector_runs": imported_runs,
        }
        (temporary_path / "run.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        write_jsonl(temporary_path / "results.jsonl", all_records)
        write_index(
            temporary_path / "index.md", campaign_id, items, all_records
        )
        temporary_path.rename(campaign_path)
    except Exception:
        shutil.rmtree(temporary_path, ignore_errors=True)
        raise
    return campaign_path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--campaign-id", required=True)
    parser.add_argument(
        "--collector-run",
        action="append",
        type=parse_collector_run,
        required=True,
        metavar="MODEL_ALIAS=PATH",
    )
    parser.add_argument("--github-repository", default=DEFAULT_REPOSITORY)
    args = parser.parse_args()
    campaign_path = import_runs(
        args.campaign_id, args.collector_run, args.github_repository
    )
    print(campaign_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
