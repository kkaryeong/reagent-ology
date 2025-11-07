#!/usr/bin/env bash
set -euo pipefail

# One-click launcher for macOS (double-clickable .command file)
# - Creates/uses a local virtualenv (.venv)
# - Installs Python dependencies
# - Starts FastAPI server with Uvicorn
# - Opens the app in the default browser

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

PYTHON_BIN="${PYTHON_BIN:-python3}"

if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  echo "[ERROR] python3 가 필요합니다. Homebrew 로 설치: brew install python"
  exit 1
fi

VENV_DIR="$SCRIPT_DIR/.venv"
if [ ! -d "$VENV_DIR" ]; then
  echo "[INFO] 가상환경 생성 (.venv)"
  "$PYTHON_BIN" -m venv "$VENV_DIR"
fi

# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"

python -m pip install --upgrade pip
pip install -r requirements.txt

# Open browser shortly after the server starts
( sleep 2; open "http://127.0.0.1:8000/index.html" ) >/dev/null 2>&1 &

# Start server (foreground)
exec python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
