#!/usr/bin/env bash
# Cross-platform (macOS/Linux) launcher for Reagent-ology
# - Creates venv if missing
# - Installs dependencies
# - Starts unified Python launcher (run_app.py)
set -euo pipefail

# Move to script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Python detection
PY=${PYTHON:-python3}
if ! command -v "$PY" >/dev/null 2>&1; then
  if command -v python >/dev/null 2>&1; then
    PY=python
  else
    echo "Python not found. Please install Python 3.9+" >&2
    exit 1
  fi
fi

# Create venv if missing
if [ ! -d ".venv" ]; then
  echo "Creating virtual environment (.venv)"
  "$PY" -m venv .venv
fi

# Activate venv
# shellcheck disable=SC1091
source .venv/bin/activate

# Upgrade pip and install requirements
python -m pip install --upgrade pip
if [ -f requirements.txt ]; then
  pip install -r requirements.txt
else
  # Minimum deps fallback
  pip install fastapi uvicorn pyserial python-multipart httpx
fi

# Run launcher
exec python run_app.py
