#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
PYTHON_BIN="${PYTHON_BIN:-$ROOT/.venv/bin/python}"

if [[ ! -x "$PYTHON_BIN" ]]; then
  PYTHON_BIN="${PYTHON_BIN_FALLBACK:-python3}"
fi

PYTHONPATH="$ROOT" "$PYTHON_BIN" -m scripts.validate_project
PYTHONPATH="$ROOT" "$PYTHON_BIN" -m benchmark.agent_benchmark.validate_bank
PYTHONPATH="$ROOT" "$PYTHON_BIN" -m benchmark.agent_benchmark.validate_multimodal_bank
"$PYTHON_BIN" "$ROOT/benchmark/curated-bank/scripts/validate_dataset.py"

if [[ "${ALLOW_LIVE_SMOKE_TEST:-0}" == "1" ]]; then
  printf '%s\n' "Live smoke test requested; use scripts/run-evaluation.sh with one model."
else
  printf '%s\n' "Local smoke test passed; no external API request was made."
fi
