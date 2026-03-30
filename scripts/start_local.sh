#!/usr/bin/env bash
# Local laptop testing — runs on 127.0.0.1 only, no external access.
# Uses tmux so you can close the terminal and it keeps running.
set -e

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SESSION="rpf-local"

# Kill existing session
tmux has-session -t "$SESSION" 2>/dev/null && tmux kill-session -t "$SESSION"

# Check .env exists in backend/
if [ ! -f "$ROOT/backend/.env" ]; then
    echo "ERROR: $ROOT/backend/.env not found."
    echo "       Copy .env.example to backend/.env and fill in your NVIDIA keys."
    exit 1
fi

# Verify Python venv
if [ ! -f "$ROOT/.venv/bin/python" ]; then
    echo "Run ./scripts/setup.sh first."
    exit 1
fi

tmux new-session -d -s "$SESSION" -n "backend" -x 220 -y 50
tmux new-window   -t "$SESSION" -n "frontend"
tmux new-window   -t "$SESSION" -n "status"

# Backend (localhost:8000)
tmux send-keys -t "$SESSION:backend" \
    "cd '$ROOT/backend' && source ../.venv/bin/activate && python main.py 2>&1 | tee ../data/backend.log" Enter

# Frontend dev server (localhost:5173) — wait 3s for backend
tmux send-keys -t "$SESSION:frontend" \
    "sleep 3 && cd '$ROOT/frontend' && npm run dev" Enter

# Status window
tmux send-keys -t "$SESSION:status" \
    "echo '=== Research Paper Finder (LOCAL) ===' && sleep 4 && curl -s http://127.0.0.1:8000/health | python3 -m json.tool" Enter

tmux select-window -t "$SESSION:backend"

echo ""
echo "  ╔══════════════════════════════════════════════════╗"
echo "  ║   Research Paper Finder — LOCAL TESTING          ║"
echo "  ╠══════════════════════════════════════════════════╣"
echo "  ║   Frontend  → http://localhost:5173              ║"
echo "  ║   API        → http://localhost:8000             ║"
echo "  ║   API Docs   → http://localhost:8000/docs        ║"
echo "  ║   Papers     → $ROOT/backend/data/papers/  ║"
echo "  ╠══════════════════════════════════════════════════╣"
echo "  ║   tmux attach -t rpf-local                       ║"
echo "  ║   Ctrl+B then 0/1/2 to switch windows            ║"
echo "  ║   tmux kill-session -t rpf-local  ← to stop      ║"
echo "  ╚══════════════════════════════════════════════════╝"
echo ""
echo "  Bound to 127.0.0.1 only — not accessible from network."
