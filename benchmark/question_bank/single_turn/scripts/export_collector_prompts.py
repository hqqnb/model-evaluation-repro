#!/usr/bin/env python3
"""Export benchmark items to model-api-collector JSONL files."""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import mimetypes
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]


def load_items(source: Path) -> list[dict[str, Any]]:
    with source.open(encoding="utf-8") as handle:
        payload = json.load(handle)
    items = payload.get("items")
    if not isinstance(items, list) or not items:
        raise ValueError(f"{source} does not contain a non-empty items list")
    return items


def data_url(path: Path) -> str:
    media_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{media_type};base64,{encoded}"


def prompt_text(item: dict[str, Any]) -> str:
    prompt = item["prompt"].strip()
    response_format = item.get("response_format", "").strip()
    if response_format:
        return f"{prompt}\n\n输出要求：\n{response_format}"
    return prompt


def message_content(
    item: dict[str, Any], protocol: str, root: Path
) -> str | list[dict[str, Any]]:
    text = prompt_text(item)
    attachments = item.get("attachments", [])
    if not attachments:
        return text

    if protocol == "chat":
        content: list[dict[str, Any]] = [{"type": "text", "text": text}]
        for attachment in attachments:
            content.append(
                {
                    "type": "image_url",
                    "image_url": {
                        "url": data_url(root / attachment),
                        "detail": "auto",
                    },
                }
            )
        return content

    content = [{"type": "input_text", "text": text}]
    for attachment in attachments:
        content.append(
            {
                "type": "input_image",
                "image_url": data_url(root / attachment),
                "detail": "auto",
            }
        )
    return content


def collector_record(
    item: dict[str, Any], protocol: str, root: Path
) -> dict[str, Any]:
    return {
        "id": item["id"],
        "title": f"{item['category']} #{item['number']}",
        "messages": [
            {
                "role": "user",
                "content": message_content(item, protocol, root),
            }
        ],
        "tags": [item["category"], "benchmark-20260806"],
        "notes": "由题库原文自动导出；未添加系统提示词。",
    }


def write_jsonl(path: Path, records: list[dict[str, Any]]) -> str:
    digest = hashlib.sha256()
    with path.open("wb") as handle:
        for record in records:
            line = (
                json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n"
            ).encode("utf-8")
            handle.write(line)
            digest.update(line)
    return digest.hexdigest()


def export(source: Path, output_dir: Path) -> dict[str, Any]:
    items = load_items(source)
    output_dir.mkdir(parents=True, exist_ok=True)
    files: dict[str, Any] = {}
    for protocol in ("chat", "responses"):
        destination = output_dir / f"prompts-{protocol}.jsonl"
        records = [collector_record(item, protocol, ROOT) for item in items]
        files[protocol] = {
            "path": destination.name,
            "sha256": write_jsonl(destination, records),
        }

    manifest = {
        "source": str(source.resolve()),
        "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "item_count": len(items),
        "files": files,
    }
    (output_dir / "export.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--source", type=Path, default=ROOT / "dataset/prompts.json"
    )
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    manifest = export(args.source, args.output_dir)
    print(f"exported {manifest['item_count']} items to {args.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
