# Deployment Checklist for `pardeepbeniwal.cloud`

## Before Deployment

- Confirm DNS for `pardeepbeniwal.cloud` points to the Hostinger VPS
- Confirm ports `80` and `443` are open
- Confirm secrets are ready:
  - `NVIDIA_KEY_1`
  - `NVIDIA_KEY_2`
  - `NVIDIA_KEY_3`
  - `ACCESS_TOKEN`
  - SMTP settings if email is needed

## Server Setup

```bash
ssh root@pardeepbeniwal.cloud
cd /opt
git clone https://github.com/yourusername/research-paper-finder.git
cd /opt/research-paper-finder
bash scripts/setup.sh
nano /opt/research-paper-finder/backend/.env
sudo bash scripts/deploy_hostinger.sh pardeepbeniwal.cloud
```

## Required `backend/.env` Values

```env
NVIDIA_KEY_1=nvapi-xxxxx
NVIDIA_KEY_2=nvapi-yyyyy
NVIDIA_KEY_3=nvapi-zzzzz
SECRET_KEY=change-this
API_HOST=0.0.0.0
API_PORT=8000
DEBUG=false
ACCESS_TOKEN=change-this-too
```

## Verification

```bash
systemctl status rpf-backend --no-pager
journalctl -u rpf-backend -n 100 --no-pager
nginx -t
curl -i http://127.0.0.1:8000/health
curl -i https://pardeepbeniwal.cloud/health
curl -I https://pardeepbeniwal.cloud/openapi.json
curl -I https://pardeepbeniwal.cloud/docs
```

## Create First API Key

```bash
curl -X POST https://pardeepbeniwal.cloud/auth/keys \
  -H "X-Access-Token: your-access-token" \
  -H "Content-Type: application/json" \
  -d '{"name":"admin"}'
```

## First Search Test

```bash
curl -X POST https://pardeepbeniwal.cloud/search \
  -H "X-Access-Token: your-access-token" \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "transformer attention mechanisms",
    "max_results": 50
  }'
```

## If Deployment Fails

Send me:

```bash
systemctl status rpf-backend --no-pager
journalctl -u rpf-backend -n 200 --no-pager
cat /etc/systemd/system/rpf-backend.service
nginx -T
curl -i http://127.0.0.1:8000/health
curl -i https://pardeepbeniwal.cloud/health
```
