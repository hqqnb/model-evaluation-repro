#!/usr/bin/env python3
"""Check that the current directory looks like the canonical evaluation repo."""

from pathlib import Path
import sys


REQUIRED = (
    "README.md",
    "configs/providers.example.yaml",
    "configs/models.example.yaml",
    "scripts/smoke-test.sh",
    "benchmark",
    "runners",
)


def main() -> int:
    root = Path.cwd()
    missing = [path for path in REQUIRED if not (root / path).exists()]
    if missing:
        for path in missing:
            print(f"missing: {path}", file=sys.stderr)
        return 1
    print(f"evaluation repository context: {root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
