#!/usr/bin/env python3
"""Compatibility entry point for validating a clean evaluation checkout."""

from __future__ import annotations

from pathlib import Path
import sys


def main() -> int:
    root = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path.cwd()
    required = (
        "README.md",
        "configs/providers.example.yaml",
        "configs/models.example.yaml",
        "scripts/smoke-test.sh",
        "benchmark",
        "runners",
    )
    missing = [path for path in required if not (root / path).exists()]
    if missing:
        for path in missing:
            print(f"missing: {path}", file=sys.stderr)
        return 1
    print(f"evaluation repository context: {root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
