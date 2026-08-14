#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

MODEL_NAME="${1:-qwen3.8-max}"
PROMPTS="${2:-runners/model-api-collector/prompts/example.jsonl}"
ENV_FILE="${ENV_FILE:-$ROOT/.env.local}"
CONFIG="${CONFIG:-$ROOT/runners/model-api-collector/config/qwen.yaml}"
PYTHON_BIN="${PYTHON_BIN:-$ROOT/.venv/bin/python}"

if [[ ! -x "$PYTHON_BIN" ]]; then
  printf '%s\n' "Missing $PYTHON_BIN. Run ./scripts/bootstrap.sh first." >&2
  exit 1
fi
if [[ ! -f "$ENV_FILE" ]]; then
  printf '%s\n' "Missing $ENV_FILE. Copy .env.example and set the selected provider key." >&2
  exit 1
fi

exec "$PYTHON_BIN" -m model_api_collector.cli run \
  --env-file "$ENV_FILE" \
  --config "$CONFIG" \
  --prompts "$PROMPTS" \
  --models "$MODEL_NAME" \
  --repeat 1
