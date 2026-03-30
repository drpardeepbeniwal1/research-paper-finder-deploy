# Research Paper Finder v3.0 — Verified Update Notes

## Changes Verified (2026-03-30)

### 1. NVIDIA model call updated
- Active default model in code: `nvidia/nemotron-3-super-120b-a12b`
- Removed unsupported thinking parameters from NVIDIA chat completions
- Current sampling in code: `temperature=0.7`, `top_p=0.9`
- File: `backend/services/nvidia_llm.py`

### 2. Optional email notifications added
- `POST /search` accepts an optional `email`
- Search completion triggers an SMTP email if SMTP is configured
- Email sending now accepts Pydantic result objects safely
- Files:
  - `backend/services/email_service.py`
  - `backend/models/schemas.py`
  - `backend/routers/search.py`
  - `backend/config.py`

### 3. Polling-based search status added
- Backend returns task `status`, `progress`, and `progress_percent`
- Frontend polls `/search/status/{task_id}` every 1.5 seconds
- Current backend progress is coarse-grained, not step-by-step per pipeline stage
- Files:
  - `backend/models/schemas.py`
  - `backend/routers/search.py`
  - `frontend/src/App.jsx`

### 4. Larger `max_results` options added
- Schema accepts `1-1000`
- Frontend quick options: `50`, `100`, `200`, `300`, `1000`
- Files:
  - `backend/models/schemas.py`
  - `frontend/src/components/SearchBar.jsx`

### 5. Deployment path handling fixed
- Backend now always loads config from `backend/.env`
- Data and context paths are now resolved from `backend/` instead of the shell working directory
- Hostinger deploy script now points systemd to `backend/.env`
- Nginx now proxies `/openapi.json` so `/docs` works correctly
- Files:
  - `backend/config.py`
  - `scripts/deploy_hostinger.sh`
  - `scripts/setup.sh`

---

## Important Reality Checks

### Config file used in production
Production uses:

```bash
/opt/research-paper-finder/backend/.env
```

Do not put production secrets only in repo-root `.env`.

### DEBUG must be boolean
Valid values:

```bash
DEBUG=false
# or
DEBUG=true
```

Do not use:

```bash
DEBUG=release
```

That value breaks backend startup.

### API auth in production
The app can require both:
- `X-Access-Token` for site access if `ACCESS_TOKEN` is set
- `X-API-Key` for `/search` and `/auth` routes

---

## Hostinger Deployment for `pardeepbeniwal.cloud`

### 1. SSH into the VPS
```bash
ssh root@pardeepbeniwal.cloud
```

### 2. Clone the project
```bash
cd /opt
git clone https://github.com/yourusername/research-paper-finder.git
cd /opt/research-paper-finder
```

### 3. Run first-time setup
```bash
bash scripts/setup.sh
```

### 4. Edit the real runtime env file
```bash
nano /opt/research-paper-finder/backend/.env
```

Use this template:

```env
NVIDIA_KEY_1=nvapi-xxxxx
NVIDIA_KEY_2=nvapi-yyyyy
NVIDIA_KEY_3=nvapi-zzzzz

SECRET_KEY=change-this-to-a-long-random-secret
API_HOST=0.0.0.0
API_PORT=8000
DEBUG=false

ACCESS_TOKEN=put-a-long-random-token-here

NVIDIA_RPM_PER_KEY=20
CONFIRMED_THRESHOLD=70
SUSPICIOUS_THRESHOLD=40
MAX_RESULTS_PER_SOURCE=30

DOWNLOAD_ACTUAL_PDFS=true
MAX_PDF_SIZE_MB=30
PDF_DOWNLOAD_CONCURRENCY=3
SCIHUB_ENABLED=true

CORE_API_KEY=
NCBI_API_KEY=
TOR_PROXY=

SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=you@example.com
SMTP_PASSWORD=your-app-password
SMTP_FROM=noreply@pardeepbeniwal.cloud
```

If you do not want email notifications yet, leave the SMTP fields blank.

### 5. Deploy with nginx + systemd + SSL
```bash
sudo bash scripts/deploy_hostinger.sh pardeepbeniwal.cloud
```

### 6. Check backend health
```bash
systemctl status rpf-backend --no-pager
journalctl -u rpf-backend -n 100 --no-pager
curl -i http://127.0.0.1:8000/health
curl -i https://pardeepbeniwal.cloud/health
```

### 7. Verify OpenAPI docs
```bash
curl -I https://pardeepbeniwal.cloud/openapi.json
curl -I https://pardeepbeniwal.cloud/docs
```

---

## Quick Production Test

### Create an API key
```bash
curl -X POST https://pardeepbeniwal.cloud/auth/keys \
  -H "X-Access-Token: your-access-token" \
  -H "Content-Type: application/json" \
  -d '{"name":"admin"}'
```

Save the returned API key.

### Start a search
```bash
curl -X POST https://pardeepbeniwal.cloud/search \
  -H "X-Access-Token: your-access-token" \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "transformer attention mechanisms",
    "max_results": 50,
    "email": "you@example.com"
  }'
```

### Check task status
```bash
curl https://pardeepbeniwal.cloud/search/status/TASK_ID \
  -H "X-Access-Token: your-access-token" \
  -H "X-API-Key: your-api-key"
```

---

## Troubleshooting

### Backend does not start
Check:

```bash
journalctl -u rpf-backend -n 200 --no-pager
```

Most likely causes:
- `DEBUG=release` instead of `true` or `false`
- Missing NVIDIA keys in `backend/.env`
- Bad Python dependency install

### `/docs` loads but API schema fails
Check:

```bash
curl -I https://pardeepbeniwal.cloud/openapi.json
```

The deploy script now proxies this route.

### Search returns 401
Make sure you send:
- `X-Access-Token`
- `X-API-Key`

### Email not sending
Check SMTP settings and logs:

```bash
journalctl -u rpf-backend -n 200 --no-pager | grep -i email
```

---

## What To Send Me If Deployment Fails

Send these outputs:

```bash
systemctl status rpf-backend --no-pager
journalctl -u rpf-backend -n 200 --no-pager
cat /etc/systemd/system/rpf-backend.service
nginx -T
curl -i http://127.0.0.1:8000/health
curl -i https://pardeepbeniwal.cloud/health
```
