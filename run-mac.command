#!/bin/bash
# One-command local startup for macOS. Run from an extracted ZIP folder.
set -euo pipefail
cd "$(dirname "$0")"
if ! command -v python3 >/dev/null; then echo 'Install Python 3.11+ first.'; exit 1; fi
if ! command -v npm >/dev/null; then echo 'Install Node.js 22 first: https://nodejs.org/'; exit 1; fi
if ! python3 -c 'import sys; assert sys.version_info >= (3, 11)' 2>/dev/null; then
  echo 'Python 3.11 or newer is required. Check python3 --version and install a newer version.'
  exit 1
fi
if ! node -e 'process.exit(Number(process.versions.node.split(".")[0])>=20?0:1)' 2>/dev/null; then
  echo 'Node.js 20 or newer is required (22 recommended). Check node --version.'
  exit 1
fi
if [ ! -f .env ]; then cp .env.example .env; echo 'Created .env. Edit it to enable live OpenAI.'; fi
if [ ! -d .venv ]; then python3 -m venv .venv; fi
source .venv/bin/activate
pip install -r backend/requirements.txt
(
  cd frontend
  if [ ! -d node_modules ]; then npm install --no-audit --no-fund; fi
)
export PYTHONPATH="$PWD/backend"
uvicorn app.main:app --host 127.0.0.1 --port 8000 &
BACKEND_PID=$!
cleanup(){ kill "$BACKEND_PID" 2>/dev/null || true; }
trap cleanup EXIT INT TERM
sleep 1
printf '\n===========================================\n'
printf 'Asset Integrity Copilot: http://localhost:5173\n'
printf 'Press Ctrl+C in this terminal to stop.\n'
printf '===========================================\n\n'
cd frontend
npm run dev
