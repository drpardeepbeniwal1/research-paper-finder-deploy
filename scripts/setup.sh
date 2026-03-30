#!/usr/bin/env bash
# One-time setup for Research Paper Finder
set -e

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
echo "Setting up Research Paper Finder at: $ROOT"

# Check system deps
command -v python3 >/dev/null || { echo "Python 3.10+ required"; exit 1; }
command -v node >/dev/null    || { echo "Node.js 18+ required"; exit 1; }
command -v tmux >/dev/null    || { echo "tmux required: sudo apt install tmux"; exit 1; }

ENV_FILE="$ROOT/backend/.env"

# Create .env in backend/ if not exists
if [ ! -f "$ENV_FILE" ]; then
    cp "$ROOT/.env.example" "$ENV_FILE"
    echo ""
    echo "  ⚠  Created backend/.env from .env.example"
     echo "     EDIT IT and add your NVIDIA_KEY_1/2/3 before starting."
    echo ""
fi

# Python venv
echo "Setting up Python environment..."
cd "$ROOT"
python3 -m venv .venv
source .venv/bin/activate
pip install -q --upgrade pip
pip install -q -r backend/requirements.txt

# CLI install
pip install -q -e cli/

# Frontend
echo "Installing frontend dependencies..."
cd "$ROOT/frontend"
npm install --silent

# Data directories
mkdir -p "$ROOT/backend/data/pdfs"
mkdir -p "$ROOT/backend/data/papers/accepted"
mkdir -p "$ROOT/backend/data/papers/maybe"
mkdir -p "$ROOT/backend/data/papers/rejected"

echo ""
echo "Setup complete!"
echo ""
echo "Next steps:"
echo "  1. Confirm backend/.env has your NVIDIA_KEY_1, KEY_2, KEY_3"
echo "  2. ./scripts/start_local.sh   ← for laptop testing"
echo "  3. Open http://localhost:5173"
echo "  4. Create first API key: rpf keys create my-key"
