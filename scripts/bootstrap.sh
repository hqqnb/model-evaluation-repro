#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON_BIN="${PYTHON_BIN:-python3}"
VENV_DIR="${VENV_DIR:-$ROOT/.venv}"

if [[ ! -x "$VENV_DIR/bin/python" ]]; then
  "$PYTHON_BIN" -m venv "$VENV_DIR"
fi

"$VENV_DIR/bin/python" -m pip install --upgrade pip
"$VENV_DIR/bin/python" -m pip install -e "$ROOT[test]"
"$VENV_DIR/bin/python" -m pip install -e "$ROOT/runners/model-api-collector[test]"

if [[ "${INSTALL_AUTOMATIONBENCH:-0}" == "1" ]]; then
  "$VENV_DIR/bin/python" -m pip install -e "$ROOT/third_party/automationbench"
fi

printf '%s\n' "Environment ready at $VENV_DIR"
printf '%s\n' "Next: cp .env.example .env.local"
printf '%s\n' "Then: ./scripts/smoke-test.sh"
