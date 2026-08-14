#!/usr/bin/env python3
"""Append one model output record to outputs/results.jsonl."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--item-id", required=True)
    parser.add_argument("--output-file", type=Path)
    parser.add_argument("--output")
    args = parser.parse_args()
    if args.output_file is not None:
        output = args.output_file.read_text(encoding="utf-8")
    elif args.output is not None:
        output = args.output
    else:
        parser.error("provide --output-file or --output")
    record = {
        "run_id": args.run_id,
        "model": args.model,
        "item_id": args.item_id,
        "output": output,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    destination = ROOT / "outputs/results.jsonl"
    with destination.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    print(destination)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
