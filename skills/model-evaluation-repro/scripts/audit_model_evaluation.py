#!/usr/bin/env python3
"""Audit a model-evaluation repository and optional collector runs."""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any


REQUIRED_PATHS = (
    "README.md",
    "benchmark/question_bank/manifest.json",
    "benchmark/question_bank/single_turn/dataset/prompts.json",
    "benchmark/question_bank/single_turn/rubrics/rubrics.json",
    "benchmark/question_bank/agent/manifest.json",
    "runners/model-api-collector/config/models.yaml",
    "scripts/smoke-test.sh",
)
SECRET_PATTERNS = (
    re.compile(r"\bsk-[A-Za-z0-9_-]{12,}\b"),
    re.compile(
        r"Authorization\s*:\s*Bearer\s+"
        r"(?!\[?(?:REDACTED|REDACTED_TEST_KEY|YOUR|TOKEN|KEY)\]?)"
        r"[A-Za-z0-9._~+/=-]{16,}",
        re.IGNORECASE,
    ),
    re.compile(
        r'"api_key"\s*:\s*"'
        r"(?!\[?(?:REDACTED|REDACTED_TEST_KEY|YOUR|TOKEN|KEY)\]?)"
        r'[^"]{16,}"',
        re.IGNORECASE,
    ),
)
ENV_SECRET_PATTERN = re.compile(
    r"^\s*([A-Za-z_][A-Za-z0-9_]*(?:KEY|TOKEN|SECRET|PASSWORD)[A-Za-z0-9_]*)"
    r"\s*=\s*(.+?)\s*$",
    re.IGNORECASE,
)
PLACEHOLDER_VALUES = {
    "",
    "changeme",
    "example",
    "placeholder",
    "redacted",
    "redacted_test_key",
    "replace_me",
    "your_key_here",
}
SKIP_DIRS = {".git", ".venv", "node_modules", "__pycache__", ".pytest_cache"}
TEXT_SUFFIXES = {
    ".csv",
    ".css",
    ".example",
    ".html",
    ".json",
    ".jsonl",
    ".md",
    ".sse",
    ".svg",
    ".txt",
    ".yaml",
    ".yml",
}


def load_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            try:
                value = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{line_number}: {exc}") from exc
            if not isinstance(value, dict):
                raise ValueError(f"{path}:{line_number}: record is not an object")
            records.append(value)
    return records


def model_block(text: str, alias: str) -> str | None:
    lines = text.splitlines()
    start = None
    indent = None
    pattern = re.compile(rf"^(\s+){re.escape(alias)}:\s*$")
    for index, line in enumerate(lines):
        match = pattern.match(line)
        if match:
            start = index
            indent = len(match.group(1))
            break
    if start is None or indent is None:
        return None
    end = len(lines)
    for index in range(start + 1, len(lines)):
        line = lines[index]
        if not line.strip():
            continue
        current_indent = len(line) - len(line.lstrip())
        if current_indent <= indent:
            end = index
            break
    return "\n".join(lines[start:end])


def extract_scalar(block: str, key: str) -> str | None:
    match = re.search(rf"^\s+{re.escape(key)}:\s*([^#\n]+)", block, re.MULTILINE)
    return match.group(1).strip().strip("\"'") if match else None


def add(
    issues: list[dict[str, str]], level: str, code: str, message: str
) -> None:
    issues.append({"level": level, "code": code, "message": message})


def audit_repo(
    repo: Path,
    model: str | None,
    expected_effort: str | None,
    issues: list[dict[str, str]],
) -> dict[str, Any]:
    for relative in REQUIRED_PATHS:
        if not (repo / relative).exists():
            add(issues, "error", "missing_path", relative)

    summary: dict[str, Any] = {"repo": str(repo)}
    manifest_path = repo / "benchmark/question_bank/manifest.json"
    if manifest_path.exists():
        try:
            manifest = load_json(manifest_path)
            summary["bank_id"] = manifest.get("bank_id")
            summary["task_count"] = manifest.get("task_count")
            categories = manifest.get("categories", {})
            counts = {
                name: value.get("count")
                for name, value in categories.items()
                if isinstance(value, dict)
            }
            summary["category_counts"] = counts
            if manifest.get("status") != "active":
                add(issues, "error", "inactive_manifest", "manifest status is not active")
            if manifest.get("task_count") != 28:
                add(
                    issues,
                    "error",
                    "task_count",
                    f"expected 28 active tasks, got {manifest.get('task_count')}",
                )
            expected_counts = {
                "reasoning": 8,
                "coding": 8,
                "multimodal": 4,
                "agent": 8,
            }
            if counts != expected_counts:
                add(
                    issues,
                    "error",
                    "category_counts",
                    f"expected {expected_counts}, got {counts}",
                )
        except (OSError, json.JSONDecodeError) as exc:
            add(issues, "error", "manifest_json", str(exc))

    if model:
        config_path = repo / "runners/model-api-collector/config/models.yaml"
        if config_path.exists():
            text = config_path.read_text(encoding="utf-8")
            block = model_block(text, model)
            if block is None:
                add(issues, "error", "model_alias", f"{model!r} not found in {config_path}")
            else:
                effort = extract_scalar(block, "reasoning_effort")
                summary["model"] = {
                    "alias": model,
                    "model_id": extract_scalar(block, "model"),
                    "endpoint": extract_scalar(block, "endpoint"),
                    "stream": extract_scalar(block, "stream"),
                    "reasoning_effort": effort,
                }
                if not effort:
                    add(
                        issues,
                        "warning",
                        "reasoning_effort_missing",
                        f"{model} does not declare reasoning_effort",
                    )
                if expected_effort and effort != expected_effort:
                    add(
                        issues,
                        "error",
                        "reasoning_effort_mismatch",
                        f"expected {expected_effort!r}, got {effort!r}",
                    )
    elif expected_effort:
        add(
            issues,
            "error",
            "expected_effort_without_model",
            "--expected-reasoning-effort requires --model",
        )
    for relative in (
        ".env.example",
        "configs",
        "runners/model-api-collector/config",
        "third_party/automationbench/configs",
    ):
        candidate = repo / relative
        if candidate.exists():
            scan_tree(candidate, issues)
    return summary


def resolve_run_dir(path: Path) -> Path:
    if (path / "run.json").is_file() and (path / "results.jsonl").is_file():
        return path
    candidates = sorted(path.glob("*/run.json"))
    if len(candidates) == 1:
        candidate = candidates[0].parent
        if (candidate / "results.jsonl").is_file():
            return candidate
    raise ValueError(f"{path} is not a collector run directory")


def scan_secret_text(path: Path, issues: list[dict[str, str]]) -> None:
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except OSError as exc:
        add(issues, "error", "read_error", f"{path}: {exc}")
        return
    for pattern in SECRET_PATTERNS:
        if pattern.search(text):
            add(issues, "error", "possible_secret", str(path))
            return
    for line in text.splitlines():
        match = ENV_SECRET_PATTERN.match(line)
        if not match:
            continue
        value = match.group(2).strip().strip("\"'")
        normalized = value.strip("[]{}<>").lower()
        if len(value) >= 12 and normalized not in PLACEHOLDER_VALUES:
            add(issues, "error", "possible_env_secret", str(path))
            return


def scan_tree(path: Path, issues: list[dict[str, str]]) -> None:
    """Scan text artifacts without descending into dependency/cache directories."""
    candidates = [path] if path.is_file() else path.rglob("*")
    for candidate in candidates:
        if not candidate.is_file():
            continue
        relative_root = path if path.is_dir() else candidate.parent
        if any(
            part in SKIP_DIRS
            for part in candidate.relative_to(relative_root).parts
        ):
            continue
        if candidate.suffix.lower() in TEXT_SUFFIXES:
            scan_secret_text(candidate, issues)


def file_sha256(path: Path) -> str:
    import hashlib

    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def audit_run(
    run_path: Path,
    model: str | None,
    expected_effort: str | None,
    issues: list[dict[str, str]],
) -> dict[str, Any]:
    run_dir = resolve_run_dir(run_path)
    run = load_json(run_dir / "run.json")
    records = load_jsonl(run_dir / "results.jsonl")
    status_counts = Counter(str(record.get("status")) for record in records)
    prompt_ids: list[str] = []

    if model and model not in run.get("model_aliases", []):
        add(
            issues,
            "error",
            "run_model_mismatch",
            f"{run_dir} does not include model alias {model}",
        )

    for record in records:
        prompt_id = str(record.get("prompt_id", ""))
        prompt_ids.append(prompt_id)
        request_id = record.get("request_id")
        response_relative = record.get("response_text_path")
        if record.get("status") == "success":
            if not isinstance(response_relative, str):
                add(
                    issues,
                    "error",
                    "missing_response_path",
                    f"{run_dir}: {prompt_id}",
                )
            else:
                response_path = run_dir / response_relative
                if not response_path.is_file() or response_path.stat().st_size == 0:
                    add(
                        issues,
                        "error",
                        "empty_response",
                        f"{run_dir}: {prompt_id}: {response_path}",
                    )

        metadata_path = run_dir / "requests" / str(request_id) / "metadata.json"
        request_path = run_dir / "requests" / str(request_id) / "request.json"
        if not metadata_path.is_file():
            add(
                issues,
                "error",
                "missing_metadata",
                f"{run_dir}: {prompt_id}: {metadata_path}",
            )
        else:
            metadata = load_json(metadata_path)
            requested_parameters = metadata.get("requested_parameters") or {}
            effective_parameters = metadata.get("effective_parameters") or {}
            effort = requested_parameters.get("reasoning_effort")
            effective_effort = effective_parameters.get("reasoning_effort")
            if expected_effort and effort != expected_effort:
                add(
                    issues,
                    "error",
                    "run_effort_mismatch",
                    f"{prompt_id}: expected {expected_effort!r}, got {effort!r}",
                )
            if expected_effort and effective_effort is None:
                add(
                    issues,
                    "warning",
                    "effective_reasoning_unconfirmed",
                    f"{prompt_id}: upstream did not echo effective reasoning_effort",
                )
            elif (
                expected_effort
                and effective_effort is not None
                and effective_effort != expected_effort
            ):
                add(
                    issues,
                    "warning",
                    "effective_reasoning_mismatch",
                    f"{prompt_id}: requested {expected_effort!r}, "
                    f"upstream echoed {effective_effort!r}",
                )

        if request_path.is_file():
            scan_secret_text(request_path, issues)
            if prompt_id.startswith("multimodal-"):
                request_text = request_path.read_text(encoding="utf-8", errors="ignore")
                if "image_url" not in request_text and "input_image" not in request_text:
                    add(
                        issues,
                        "error",
                        "multimodal_image_missing",
                        f"{run_dir}: {prompt_id}",
                    )

        if prompt_id.startswith("coding-") and record.get("status") == "success":
            add(
                issues,
                "warning",
                "coding_review_required",
                f"{prompt_id}: API success still requires deliverable and browser review",
            )

    scan_tree(run_dir, issues)
    return {
        "run_dir": str(run_dir),
        "run_id": run.get("run_id"),
        "created_at": run.get("created_at"),
        "delivery_mode": run.get("delivery_mode"),
        "repeat": run.get("repeat"),
        "models": run.get("model_aliases"),
        "prompt_ids": prompt_ids,
        "status_counts": dict(status_counts),
    }


def audit_agent_summary(
    summary_path: Path,
    model: str | None,
    expected_effort: str | None,
    issues: list[dict[str, str]],
) -> dict[str, Any]:
    summary = load_json(summary_path)
    if summary.get("task_count") != 8:
        add(
            issues,
            "error",
            "agent_task_count",
            f"{summary_path}: expected 8 tasks, got {summary.get('task_count')}",
        )
    models = summary.get("models")
    if not isinstance(models, dict) or not models:
        add(issues, "error", "agent_models_missing", str(summary_path))
        return {"summary": str(summary_path), "models": {}}

    selected = {model: models[model]} if model and model in models else models
    if model and model not in models:
        add(
            issues,
            "error",
            "agent_model_missing",
            f"{summary_path}: {model} is not present",
        )

    for alias, details in selected.items():
        if not isinstance(details, dict):
            add(issues, "error", "agent_model_record", f"{alias}: not an object")
            continue
        preflight = details.get("provider_preflight") or {}
        if preflight.get("status") not in {"passed", "technical_failure"}:
            add(
                issues,
                "error",
                "agent_preflight_status",
                f"{alias}: invalid preflight status {preflight.get('status')!r}",
            )
        effort = preflight.get("reasoning_effort")
        if expected_effort and effort and effort != expected_effort:
            add(
                issues,
                "error",
                "agent_reasoning_effort",
                f"{alias}: expected {expected_effort!r}, got {effort!r}",
            )
        status = details.get("status")
        if status == "complete":
            if details.get("raw_task_count") != 8:
                add(
                    issues,
                    "error",
                    "agent_raw_task_count",
                    f"{alias}: complete run has {details.get('raw_task_count')} raw tasks",
                )
            if details.get("capability_task_count") != 8:
                add(
                    issues,
                    "error",
                    "agent_capability_task_count",
                    f"{alias}: complete run has {details.get('capability_task_count')} capability tasks",
                )
            if details.get("technical_failure_count") != 0:
                add(
                    issues,
                    "error",
                    "agent_technical_failures",
                    f"{alias}: complete run has technical failures",
                )
        elif status == "technical_failure":
            add(
                issues,
                "warning",
                "agent_technical_failure",
                f"{alias}: excluded from capability score",
            )

    ranking = summary.get("ranking") or []
    seen_ranks: set[Any] = set()
    scores: list[float] = []
    for row in ranking:
        if not isinstance(row, dict):
            add(issues, "error", "agent_ranking_row", "ranking row is not an object")
            continue
        rank = row.get("rank")
        if rank in seen_ranks:
            add(issues, "error", "agent_duplicate_rank", str(rank))
        seen_ranks.add(rank)
        if row.get("run_id") not in models:
            add(
                issues,
                "error",
                "agent_ranking_model",
                f"unknown run_id {row.get('run_id')!r}",
            )
        score = row.get("avg_weighted_score")
        if isinstance(score, (int, float)):
            scores.append(float(score))
    if any(left < right for left, right in zip(scores, scores[1:])):
        add(
            issues,
            "warning",
            "agent_ranking_order",
            "ranking scores are not monotonically descending; verify ranking rule",
        )

    scan_tree(summary_path, issues)
    return {
        "summary": str(summary_path),
        "batch_id": summary.get("batch_id"),
        "task_count": summary.get("task_count"),
        "model_count": len(models),
        "selected_models": list(selected),
        "ranking_count": len(ranking),
    }


def audit_publication(
    question_bank: Path | None,
    preview_repo: Path | None,
    campaign_id: str | None,
    model: str | None,
    issues: list[dict[str, str]],
) -> dict[str, Any] | None:
    provided = [question_bank is not None, preview_repo is not None, campaign_id is not None]
    if any(provided) and not all(provided):
        add(
            issues,
            "error",
            "publication_args",
            "--question-bank, --preview-repo, and --campaign-id must be used together",
        )
        return None
    if not all(provided):
        return None

    assert question_bank is not None
    assert preview_repo is not None
    assert campaign_id is not None
    campaign_dir = question_bank / "runs" / campaign_id
    results_path = campaign_dir / "results.jsonl"
    preview_campaign = preview_repo / campaign_id
    manifest_path = preview_campaign / "manifest.json"
    if not results_path.is_file():
        add(issues, "error", "campaign_results_missing", str(results_path))
        return {
            "campaign_id": campaign_id,
            "question_bank": str(question_bank),
            "preview_repo": str(preview_repo),
        }
    if not manifest_path.is_file():
        add(issues, "error", "preview_manifest_missing", str(manifest_path))

    records = load_jsonl(results_path)
    selected = [
        record
        for record in records
        if model is None or record.get("model_alias") == model
    ]
    if model and not selected:
        add(
            issues,
            "error",
            "published_model_missing",
            f"{model!r} is not present in {results_path}",
        )

    statuses = Counter(str(record.get("status")) for record in selected)
    categories = Counter(str(record.get("category")) for record in selected)
    published_previews = 0
    checked_answers = 0
    for record in selected:
        answer_relative = record.get("answer_path")
        answer_path = question_bank / str(answer_relative)
        if not answer_path.is_file():
            add(
                issues,
                "error",
                "published_answer_missing",
                f"{record.get('item_id')}: {answer_path}",
            )
            continue
        checked_answers += 1
        expected_answer_hash = record.get("answer_sha256")
        if expected_answer_hash and file_sha256(answer_path) != expected_answer_hash:
            add(
                issues,
                "error",
                "published_answer_hash",
                f"{record.get('item_id')}: answer hash mismatch",
            )

        if (
            record.get("category") == "coding"
            and record.get("preview_status") == "published"
        ):
            metadata_path = (
                preview_campaign
                / str(record.get("item_id"))
                / str(record.get("model_alias"))
                / "metadata.json"
            )
            if not metadata_path.is_file():
                add(
                    issues,
                    "error",
                    "preview_metadata_missing",
                    str(metadata_path),
                )
                continue
            metadata = load_json(metadata_path)
            artifact_path = metadata_path.parent / str(metadata.get("artifact_file"))
            if not artifact_path.is_file():
                add(
                    issues,
                    "error",
                    "preview_artifact_missing",
                    str(artifact_path),
                )
                continue
            if metadata.get("source_answer_sha256") != expected_answer_hash:
                add(
                    issues,
                    "error",
                    "preview_source_hash",
                    f"{record.get('item_id')}: preview source hash mismatch",
                )
            expected_artifact_hash = metadata.get("artifact_sha256")
            if (
                expected_artifact_hash
                and file_sha256(artifact_path) != expected_artifact_hash
            ):
                add(
                    issues,
                    "error",
                    "preview_artifact_hash",
                    f"{record.get('item_id')}: preview artifact hash mismatch",
                )
            published_previews += 1

    scan_tree(campaign_dir, issues)
    scan_tree(preview_campaign, issues)
    return {
        "campaign_id": campaign_id,
        "question_bank": str(question_bank),
        "preview_repo": str(preview_repo),
        "selected_model": model,
        "record_count": len(selected),
        "checked_answers": checked_answers,
        "status_counts": dict(statuses),
        "category_counts": dict(categories),
        "verified_coding_previews": published_previews,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    parser.add_argument("--model")
    parser.add_argument("--expected-reasoning-effort")
    parser.add_argument("--run-dir", type=Path, action="append", default=[])
    parser.add_argument("--agent-summary", type=Path, action="append", default=[])
    parser.add_argument("--scan-root", type=Path, action="append", default=[])
    parser.add_argument("--question-bank", type=Path)
    parser.add_argument("--preview-repo", type=Path)
    parser.add_argument("--campaign-id")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    repo = args.repo.resolve()
    issues: list[dict[str, str]] = []
    try:
        report = {
            "repository": audit_repo(
                repo, args.model, args.expected_reasoning_effort, issues
            ),
            "runs": [
                audit_run(
                    path.resolve(),
                    args.model,
                    args.expected_reasoning_effort,
                    issues,
                )
                for path in args.run_dir
            ],
            "agent_summaries": [
                audit_agent_summary(
                    path.resolve(),
                    args.model,
                    args.expected_reasoning_effort,
                    issues,
                )
                for path in args.agent_summary
            ],
            "publication": audit_publication(
                args.question_bank.resolve() if args.question_bank else None,
                args.preview_repo.resolve() if args.preview_repo else None,
                args.campaign_id,
                args.model,
                issues,
            ),
        }
        for path in args.scan_root:
            scan_tree(path.resolve(), issues)
        report["scan_roots"] = [str(path.resolve()) for path in args.scan_root]
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        add(issues, "error", "audit_exception", str(exc))
        report = {"repository": {"repo": str(repo)}, "runs": []}

    report["issues"] = issues
    report["ok"] = not any(issue["level"] == "error" for issue in issues)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        repository = report["repository"]
        print(f"Repository: {repository.get('repo')}")
        if repository.get("bank_id"):
            print(
                f"Question bank: {repository['bank_id']} "
                f"({repository.get('task_count')} tasks)"
            )
        if repository.get("model"):
            print(f"Model config: {json.dumps(repository['model'], ensure_ascii=False)}")
        for run in report["runs"]:
            print(
                f"Run: {run['run_id']} | {run['delivery_mode']} | "
                f"{run['status_counts']}"
            )
        publication = report.get("publication")
        if publication:
            print(
                f"Publication: {publication['campaign_id']} | "
                f"{publication.get('record_count', 0)} records | "
                f"{publication.get('verified_coding_previews', 0)} previews"
            )
        for issue in issues:
            print(
                f"{issue['level'].upper()}: {issue['code']}: {issue['message']}",
                file=sys.stderr if issue["level"] == "error" else sys.stdout,
            )
        print("Audit passed" if report["ok"] else "Audit failed")
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
