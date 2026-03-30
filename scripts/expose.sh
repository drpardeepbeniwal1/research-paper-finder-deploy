#!/usr/bin/env bash
# Securely expose Research Paper Finder from VPS to phone/laptop.
# Uses Cloudflare Tunnel — free, HTTPS, random URL, no port forwarding needed.
#
# Usage:
#   ./scripts/expose.sh            ← generates a random Cloudflare URL
#   ./scripts/expose.sh persistent ← sets up a persistent named tunnel (requires CF account)
set -e

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PORT=8000

# ── Install cloudflared if not present ───────────────────────────────────────
if ! command -v cloudflared &>/dev/null; then
    echo "Installing cloudflared..."
    ARCH=$(uname -m)
    if [ "$ARCH" = "x86_64" ]; then
        URL="https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64"
    elif [ "$ARCH" = "aarch64" ]; then
        URL="https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-arm64"
    else
        echo "Unsupported arch: $ARCH. Download cloudflared manually from github.com/cloudflare/cloudflared"
        exit 1
    fi
    curl -sSL "$URL" -o /usr/local/bin/cloudflared
    chmod +x /usr/local/bin/cloudflared
    echo "cloudflared installed."
fi

# ── Generate access token if not set ─────────────────────────────────────────
ENV_FILE="$ROOT/backend/.env"
CURRENT_TOKEN=$(grep "^ACCESS_TOKEN=" "$ENV_FILE" 2>/dev/null | cut -d= -f2)

if [ -z "$CURRENT_TOKEN" ]; then
    NEW_TOKEN=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
    echo "ACCESS_TOKEN=$NEW_TOKEN" >> "$ENV_FILE"
    CURRENT_TOKEN="$NEW_TOKEN"
    echo "Generated new access token and saved to backend/.env"
fi

# ── Change API_HOST to 0.0.0.0 for tunnel access ─────────────────────────────
sed -i 's/^API_HOST=127\.0\.0\.1/API_HOST=0.0.0.0/' "$ENV_FILE"
grep -q "^API_HOST=" "$ENV_FILE" || echo "API_HOST=0.0.0.0" >> "$ENV_FILE"

# ── Build frontend if not built ───────────────────────────────────────────────
if [ ! -d "$ROOT/frontend/dist" ]; then
    echo "Building frontend..."
    cd "$ROOT/frontend"
    VITE_API_BASE_URL="" npm run build
    echo "Frontend built."
fi

# ── Start backend if not running ─────────────────────────────────────────────
if ! curl -s "http://127.0.0.1:$PORT/health" &>/dev/null; then
    echo "Starting backend..."
    SESSION="rpf-vps"
    tmux has-session -t "$SESSION" 2>/dev/null && tmux kill-session -t "$SESSION" || true
    tmux new-session -d -s "$SESSION" -n "backend"
    tmux send-keys -t "$SESSION:backend" \
        "cd '$ROOT/backend' && source ../.venv/bin/activate && python main.py" Enter
    sleep 5
fi

# ── Print access instructions ─────────────────────────────────────────────────
echo ""
echo "  ╔══════════════════════════════════════════════════════════════╗"
echo "  ║  Research Paper Finder — Secure Remote Access               ║"
echo "  ╠══════════════════════════════════════════════════════════════╣"
echo "  ║  Access Token: $CURRENT_TOKEN"
echo "  ║  (required as header: X-Access-Token or ?token= in URL)     ║"
echo "  ╠══════════════════════════════════════════════════════════════╣"
echo "  ║  Starting Cloudflare Tunnel...                               ║"
echo "  ║  A HTTPS URL will appear below. Open it on phone/laptop.    ║"
echo "  ║  Append ?token=$CURRENT_TOKEN to the URL first time.        ║"
echo "  ╚══════════════════════════════════════════════════════════════╝"
echo ""
echo "  NOTE: Save the Cloudflare URL + token. This is your secure link."
echo "  NOTE: Rotate your NVIDIA keys at build.nvidia.com after sharing."
echo ""

# ── Run Cloudflare tunnel (blocking — shows URL) ──────────────────────────────
cloudflared tunnel --url "http://127.0.0.1:$PORT" --no-autoupdate 2>&1 | grep -E "trycloudflare|https://|INF|ERR" &

CF_PID=$!
sleep 5

# Extract and display the URL clearly
echo ""
echo "  ════════════════════════════════════════════════════"
echo "  Your secure URL will appear in the output above."
echo "  Look for a line containing: trycloudflare.com"
echo ""
echo "  USAGE ON PHONE/LAPTOP:"
echo "  1. Open the https://xxx.trycloudflare.com URL"
echo "  2. When prompted for access token, use:"
echo "     $CURRENT_TOKEN"
echo "  ════════════════════════════════════════════════════"

wait $CF_PID
