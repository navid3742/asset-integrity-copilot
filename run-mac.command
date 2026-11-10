#!/bin/bash
# Local dev on macOS: installs dependencies, then starts FastAPI (:8000) and Vite (:5173).
set -euo pipefail
cd "$(dirname "$0")"

if ! python3 -c 'import sys; assert sys.version_info >= (3, 11)' 2>/dev/null; then
  echo "Python 3.11+ is required (found: $(python3 --version 2>&1))."
  exit 1
fi
if ! node -e 'process.exit(Number(process.versions.node.split(".")[0]) >= 20 ? 0 : 1)' 2>/dev/null; then
  echo "Node.js 20+ is required: https://nodejs.org/"
  exit 1
fi

[ -f .env ] || { cp .env.example .env; echo "Created .env from .env.example"; }
[ -d .venv ] || python3 -m venv .venv
source .venv/bin/activate
pip install -q -r backend/requirements-dev.txt
(cd frontend && [ -d node_modules ] || npm ci --no-audit --no-fund)

export PYTHONPATH="$PWD/backend"
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000 &
BACKEND_PID=$!
trap 'kill "$BACKEND_PID" 2>/dev/null || true' EXIT INT TERM

echo "Open http://localhost:5173 (Ctrl+C to stop)"
cd frontend && npm run dev
