#!/usr/bin/env bash
# Deploy Research Paper Finder to Hostinger VPS (Ubuntu 20.04/22.04)
# Run as: bash deploy_hostinger.sh
set -e

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DOMAIN="${1:-your-domain.com}"
PORT=8000
ENV_FILE="$ROOT/backend/.env"

echo "=== Research Paper Finder — Hostinger VPS Deploy ==="
echo "Domain: $DOMAIN"
echo "Root:   $ROOT"
echo ""

# System dependencies
apt-get update -q
apt-get install -y -q python3.11 python3.11-venv python3-pip nodejs npm tmux nginx certbot python3-certbot-nginx

# Tor (optional — for Google Scholar stealth)
read -rp "Install Tor for Google Scholar stealth? (y/N): " install_tor
if [[ "$install_tor" == "y" ]]; then
    apt-get install -y -q tor
    systemctl enable tor
    systemctl start tor
    echo "Tor installed. TOR_PROXY=socks5://localhost:9050 already in .env.example"
fi

# Python environment
cd "$ROOT"
python3.11 -m venv .venv
source .venv/bin/activate
pip install -q --upgrade pip
pip install -q -r backend/requirements.txt

if [[ ! -f "$ENV_FILE" ]]; then
    cp "$ROOT/.env.example" "$ENV_FILE"
    echo "Created $ENV_FILE from .env.example"
    echo "Fill in NVIDIA keys, access token, and optional SMTP settings before restarting the service."
fi

# Install Playwright for future use (headless browser if needed)
# pip install playwright && playwright install chromium

# Frontend build (production)
cd "$ROOT/frontend"
npm install --silent
VITE_API_BASE_URL="https://$DOMAIN" npm run build
echo "Frontend built → dist/"

# Nginx config
cat > /etc/nginx/sites-available/rpf <<EOF
server {
    listen 80;
    server_name $DOMAIN;

    # Frontend (static)
    location / {
        root $ROOT/frontend/dist;
        try_files \$uri \$uri/ /index.html;
        gzip on;
        gzip_types text/plain text/css application/javascript application/json;
    }

    # Backend API (proxy to FastAPI)
    location /search {
        proxy_pass http://127.0.0.1:$PORT;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_read_timeout 300s;
        proxy_send_timeout 300s;
    }
    location /auth { proxy_pass http://127.0.0.1:$PORT; }
    location /openclaw { proxy_pass http://127.0.0.1:$PORT; }
    location /health { proxy_pass http://127.0.0.1:$PORT; }
    location /docs { proxy_pass http://127.0.0.1:$PORT; }
    location /openapi.json { proxy_pass http://127.0.0.1:$PORT; }

    client_max_body_size 10M;
}
EOF

ln -sf /etc/nginx/sites-available/rpf /etc/nginx/sites-enabled/rpf
nginx -t && systemctl reload nginx

# SSL
certbot --nginx -d "$DOMAIN" --non-interactive --agree-tos -m "admin@$DOMAIN" || true

# Systemd service for backend (auto-restart)
cat > /etc/systemd/system/rpf-backend.service <<EOF
[Unit]
Description=Research Paper Finder Backend
After=network.target

[Service]
User=root
WorkingDirectory=$ROOT/backend
EnvironmentFile=-$ENV_FILE
Environment="PATH=$ROOT/.venv/bin"
ExecStart=$ROOT/.venv/bin/python main.py
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable rpf-backend
systemctl restart rpf-backend

echo ""
echo "=== Deploy Complete ==="
echo "Backend : https://$DOMAIN (via nginx proxy)"
echo "API Docs: https://$DOMAIN/docs"
echo "Status  : systemctl status rpf-backend"
echo "Logs    : journalctl -u rpf-backend -f"
echo ""
echo "IMPORTANT: Edit $ENV_FILE with your NVIDIA keys, ACCESS_TOKEN, and optional SMTP settings"
