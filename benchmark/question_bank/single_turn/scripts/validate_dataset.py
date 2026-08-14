#!/usr/bin/env python3
"""Validate benchmark prompts, rubrics, and referenced assets."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load(path: Path):
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def main() -> int:
    prompts = load(ROOT / "dataset/prompts.json")
    rubrics = load(ROOT / "rubrics/rubrics.json")
    prompt_items = prompts["items"]
    rubric_items = rubrics["items"]
    prompt_ids = [item["id"] for item in prompt_items]
    rubric_ids = [item["id"] for item in rubric_items]
    assert len(prompt_ids) == len(set(prompt_ids)), "duplicate prompt id"
    assert prompt_ids == rubric_ids, "prompt/rubric ids are not aligned"
    for item in prompt_items:
        assert item["prompt"].strip(), f"empty prompt: {item['id']}"
        for attachment in item.get("attachments", []):
            assert (ROOT / attachment).is_file(), f"missing asset: {attachment}"
    categories = {item["category"] for item in prompt_items}
    assert categories == {"reasoning", "coding", "multimodal"}, categories
    print(f"validated {len(prompt_items)} items")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
