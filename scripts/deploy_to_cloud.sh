#!/usr/bin/env bash
# Quick deployment to pardeepbeniwal.cloud
# Usage: bash deploy_to_cloud.sh

set -e

DOMAIN="pardeepbeniwal.cloud"
REPO_URL="${REPO_URL:-https://github.com/yourusername/research-paper-finder.git}"

echo "=== Deploying to $DOMAIN ==="

# 1. SSH into server and clone repo
read -p "SSH into $DOMAIN and deploy? (y/N): " proceed
if [[ "$proceed" != "y" ]]; then
    echo "Cancelled"
    exit 1
fi

ssh root@$DOMAIN << 'EOSSH'
set -e

# Stop existing service
systemctl stop rpf-backend || true

# Clone/update repo
if [ -d /opt/research-paper-finder ]; then
    cd /opt/research-paper-finder
    git pull origin main
else
    cd /opt
    git clone $REPO_URL research-paper-finder
    cd research-paper-finder
fi

# Install dependencies
python3.11 -m venv .venv
source .venv/bin/activate
pip install -q --upgrade pip
pip install -q -r backend/requirements.txt

# Build frontend
cd frontend
npm install --silent
VITE_API_BASE_URL="https://pardeepbeniwal.cloud" npm run build
cd ..

# Deploy nginx + SSL (if first time)
if [ ! -f /etc/nginx/sites-enabled/rpf ]; then
    bash scripts/deploy_hostinger.sh pardeepbeniwal.cloud
fi

# Restart backend
systemctl restart rpf-backend

# Verify
sleep 2
systemctl status rpf-backend
echo "✓ Deployment complete!"
EOSSH

echo ""
echo "=== Deployment Successful ==="
echo "Frontend: https://$DOMAIN"
echo "API Docs: https://$DOMAIN/docs"
echo "Health:   https://$DOMAIN/health"
echo ""
echo "To configure:"
echo "  ssh root@$DOMAIN"
echo "  nano /opt/research-paper-finder/backend/.env"
echo "  systemctl restart rpf-backend"
