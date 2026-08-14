#!/usr/bin/env python3
"""Extract Coding artifacts without modification and build GitHub Pages indexes."""
from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from import_collector_runs import load_json, load_jsonl, write_index, write_jsonl


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PAGES_REPOSITORY = "hqqnb/llm-evaluation-previews"
FENCE_PATTERN = re.compile(r"```([^\n`]*)\n(.*?)```", re.DOTALL)
HTML_DOCUMENT_PATTERN = re.compile(
    r"(?is)(<!doctype\s+html[^>]*>.*?</html\s*>|<html\b.*?</html\s*>)"
)
SVG_DOCUMENT_PATTERN = re.compile(r"(?is)(<svg\b.*?</svg\s*>)")
EXTERNAL_URL_PATTERN = re.compile(r"https?://[^\s\"'<>)\]]+")


def sha256_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def scan_external_urls(text: str) -> list[str]:
    """Return deduplicated external http(s) URLs referenced by an answer."""
    urls = []
    seen = set()
    for match in EXTERNAL_URL_PATTERN.finditer(text):
        url = match.group(0).rstrip(".,;:!?，。；：！？")
        if url in seen:
            continue
        seen.add(url)
        urls.append(url)
    return urls


def fenced_candidates(response: str) -> list[tuple[str, str]]:
    candidates = []
    for match in FENCE_PATTERN.finditer(response):
        info = match.group(1).strip().lower()
        language = re.split(r"[\s,:]", info, maxsplit=1)[0]
        candidates.append((language, match.group(2)))
    # Handle an unclosed trailing fence (model hit the output limit mid-block):
    # when the fence count is odd, treat everything after the last language
    # marker as the block.
    if response.count("```") % 2 == 1:
        last = response.rfind("```")
        rest = response[last + 3 :]
        if rest.startswith("\n"):
            rest = rest[1:]
        info = re.split(r"[\s,:]", rest.splitlines()[0].strip().lower(), maxsplit=1)[0] if rest.splitlines() else ""
        content = "\n".join(rest.splitlines()[1:]) if rest.splitlines() else ""
        if info and content:
            candidates.append((info, content))
    return candidates


def extract_artifact(response: str) -> tuple[str, str] | None:
    candidates = fenced_candidates(response)
    for languages, artifact_type in (
        ({"html", "htm"}, "html"),
        ({"svg"}, "svg"),
        ({"xml"}, "svg"),
    ):
        for language, content in candidates:
            if language in languages:
                if artifact_type == "svg" and "<svg" not in content.lower():
                    continue
                return artifact_type, content

    for _, content in candidates:
        lowered = content.lstrip().lower()
        if lowered.startswith(("<!doctype html", "<html")):
            return "html", content
        if lowered.startswith("<svg"):
            return "svg", content

    html_match = HTML_DOCUMENT_PATTERN.search(response)
    if html_match:
        return "html", html_match.group(1)
    svg_match = SVG_DOCUMENT_PATTERN.search(response)
    if svg_match:
        return "svg", svg_match.group(1)
    return None


def svg_wrapper() -> str:
    return """<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>SVG 模型输出预览</title>
  <style>
    html,body{height:100%;margin:0;background:#111;color:#eee;font-family:system-ui}
    body{display:grid;place-items:center}.frame{width:min(96vw,1200px);height:min(92vh,900px)}
    object{width:100%;height:100%;border:0;background:#fff}
  </style>
</head>
<body><div class="frame"><object data="answer.svg" type="image/svg+xml"></object></div></body>
</html>
"""


def preview_url(repository: str, campaign_id: str, item_id: str, alias: str) -> str:
    owner, name = repository.split("/", maxsplit=1)
    return f"https://{owner}.github.io/{name}/{campaign_id}/{item_id}/{alias}/"


def write_public_indexes(
    preview_root: Path,
    repository: str,
    campaign_id: str,
    records: list[dict[str, Any]],
) -> None:
    owner, name = repository.split("/", maxsplit=1)
    coding_records = [record for record in records if record["category"] == "coding"]
    campaign_lines = [
        "<!doctype html>",
        '<html lang="zh-CN"><head><meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width,initial-scale=1">',
        f"<title>{html.escape(campaign_id)} Coding 预览</title>",
        "<style>body{font:16px/1.6 system-ui;max-width:1100px;margin:40px auto;padding:0 20px}"
        "table{border-collapse:collapse;width:100%}th,td{border:1px solid #ddd;padding:8px;text-align:left}"
        "th{background:#f5f5f5}code{background:#f3f3f3;padding:2px 4px}</style></head><body>",
        f"<h1>{html.escape(campaign_id)} Coding 预览</h1>",
        "<p>页面仅包含从模型原始回答中机械提取的可运行代码；未修复模型代码。</p>",
        "<table><thead><tr><th>题目</th><th>模型</th><th>状态</th><th>预览</th></tr></thead><tbody>",
    ]
    for record in coding_records:
        url = record.get("preview_url")
        link = f'<a href="{html.escape(url)}">打开</a>' if url else "—"
        campaign_lines.append(
            "<tr>"
            f"<td><code>{html.escape(record['item_id'])}</code></td>"
            f"<td><code>{html.escape(record['model_alias'])}</code></td>"
            f"<td>{html.escape(record.get('preview_status') or '')}</td>"
            f"<td>{link}</td></tr>"
        )
    campaign_lines.extend(["</tbody></table></body></html>", ""])
    campaign_path = preview_root / campaign_id
    campaign_path.mkdir(parents=True, exist_ok=True)
    (campaign_path / "index.html").write_text(
        "\n".join(campaign_lines), encoding="utf-8"
    )

    root_index = f"""<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>LLM Evaluation Previews</title></head><body>
<h1>LLM Evaluation Previews</h1>
<p><a href="./{html.escape(campaign_id)}/">{html.escape(campaign_id)}</a></p>
<p>Repository: <a href="https://github.com/{owner}/{name}">{owner}/{name}</a></p>
</body></html>
"""
    (preview_root / "index.html").write_text(root_index, encoding="utf-8")
    (preview_root / ".nojekyll").touch()


def publish(
    campaign_id: str,
    preview_root: Path,
    repository: str,
) -> dict[str, int]:
    campaign_path = ROOT / "runs" / campaign_id
    results_path = campaign_path / "results.jsonl"
    records = load_jsonl(results_path)
    prompts = load_json(ROOT / "dataset/prompts.json")["items"]
    target_campaign = preview_root / campaign_id
    if target_campaign.exists():
        shutil.rmtree(target_campaign)

    counts = {"published": 0, "not_extracted": 0, "not_successful": 0}
    for record in records:
        if record["category"] != "coding":
            continue
        if record["status"] != "success":
            record["preview_status"] = "model-request-failed"
            counts["not_successful"] += 1
            continue
        answer_path = ROOT / record["answer_path"]
        answer_text = answer_path.read_text(encoding="utf-8")
        record["external_urls"] = scan_external_urls(answer_text)
        artifact = extract_artifact(answer_text)
        if artifact is None:
            record["preview_status"] = "no-runnable-artifact-extracted"
            counts["not_extracted"] += 1
            continue

        artifact_type, content = artifact
        destination = target_campaign / record["item_id"] / record["model_alias"]
        destination.mkdir(parents=True, exist_ok=True)
        artifact_bytes = content.encode("utf-8")
        if artifact_type == "html":
            (destination / "index.html").write_bytes(artifact_bytes)
            artifact_name = "index.html"
        else:
            (destination / "answer.svg").write_bytes(artifact_bytes)
            (destination / "index.html").write_text(svg_wrapper(), encoding="utf-8")
            artifact_name = "answer.svg"
        metadata = {
            "campaign_id": campaign_id,
            "item_id": record["item_id"],
            "model_alias": record["model_alias"],
            "artifact_type": artifact_type,
            "artifact_file": artifact_name,
            "artifact_sha256": sha256_bytes(artifact_bytes),
            "source_answer_sha256": record["answer_sha256"],
            "external_urls": record["external_urls"],
            "extraction_policy": "mechanical-only-no-code-repair",
        }
        (destination / "metadata.json").write_text(
            json.dumps(metadata, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        record["preview_status"] = "published"
        record["preview_url"] = preview_url(
            repository, campaign_id, record["item_id"], record["model_alias"]
        )
        counts["published"] += 1

    write_jsonl(results_path, records)
    write_index(campaign_path / "index.md", campaign_id, prompts, records)
    write_public_indexes(preview_root, repository, campaign_id, records)
    public_manifest = {
        "campaign_id": campaign_id,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_repository": "hqqnb/llm-evaluation-question-bank",
        "extraction_policy": "mechanical-only-no-code-repair",
        "counts": counts,
    }
    (target_campaign / "manifest.json").write_text(
        json.dumps(public_manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return counts


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--campaign-id", required=True)
    parser.add_argument("--preview-repo", type=Path, required=True)
    parser.add_argument("--github-repository", default=DEFAULT_PAGES_REPOSITORY)
    args = parser.parse_args()
    counts = publish(
        args.campaign_id, args.preview_repo.resolve(), args.github_repository
    )
    print(json.dumps(counts, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
