#!/usr/bin/env bash
# VPS launch — binds to 0.0.0.0 (for nginx proxy). Use start_local.sh for laptop.
set -e

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SESSION="research-paper-finder"

tmux has-session -t "$SESSION" 2>/dev/null && tmux kill-session -t "$SESSION"

# Override host for VPS (nginx proxies to 8000)
export API_HOST=0.0.0.0

tmux new-session -d -s "$SESSION" -n "backend" -x 220 -y 50
tmux new-window   -t "$SESSION" -n "frontend"

tmux send-keys -t "$SESSION:backend" \
    "export API_HOST=0.0.0.0 && cd '$ROOT/backend' && source ../.venv/bin/activate && python main.py 2>&1 | tee ../data/backend.log" Enter
tmux send-keys -t "$SESSION:frontend" \
    "sleep 3 && cd '$ROOT/frontend' && npm run dev -- --host 0.0.0.0" Enter

tmux select-window -t "$SESSION:backend"

echo ""
echo "  VPS session started: $SESSION"
echo "  tmux attach -t $SESSION"
echo "  Backend: http://0.0.0.0:8000  (use nginx for external access)"
