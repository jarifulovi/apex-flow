#!/usr/bin/env bash
set -e

# Change directory to the root of apex-flow-backend
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "⚠️  Warning: .env file not found in $SCRIPT_DIR!"
    if [ -f ".env.example" ]; then
        echo "💡 Copying .env.example to .env..."
        cp .env.example .env
    fi
fi

# Activate virtual environment if it exists
if [ -d ".venv" ]; then
    echo "⚡ Activating virtual environment (.venv)..."
    source .venv/bin/activate
elif [ -n "$VIRTUAL_ENV" ]; then
    echo "⚡ Using active virtual environment: $VIRTUAL_ENV"
else
    echo "❌ Virtual environment .venv not found. Please run 'python3 -m venv .venv && pip install -r requirements.txt' first."
    exit 1
fi

HOST="${HOST:-127.0.0.1}"
PORT="${PORT:-8000}"

echo "🚀 Starting ApexFlow Backend on http://${HOST}:${PORT} ..."
exec uvicorn app.main:app --reload --host "$HOST" --port "$PORT"
