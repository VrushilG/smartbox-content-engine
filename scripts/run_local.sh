#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$SCRIPT_DIR/../backend"

echo "==> Installing backend dependencies..."
cd "$BACKEND_DIR"
pip install -r requirements.txt

echo ""
echo "==> Starting Smartbox Content Engine..."
echo "    Open http://localhost:8000 in your browser"
echo ""

uvicorn app.main:app --reload --port 8000 --host 0.0.0.0
