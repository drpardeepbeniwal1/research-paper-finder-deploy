# Attaching Research Paper Finder to OpenClaw

## One-Time Setup

### 1. Start the Research Paper Finder backend
```bash
cd ~/research-paper-finder
./scripts/start.sh          # runs in tmux, persists after disconnect
```

### 2. Add these to your OpenClaw `.env`
```bash
RPF_BASE_URL=http://localhost:8000
RPF_API_KEY=                 # leave blank — get from pairing below
```

### 3. Pair OpenClaw with Research Paper Finder (3-step handshake)

**Option A — CLI (recommended)**
```bash
# In your terminal:
rpf keys create openclaw-main
# Copy the printed key → paste into RPF_API_KEY in OpenClaw .env
```

**Option B — Pairing flow (for programmatic attachment)**

In OpenClaw, call:
```
POST http://localhost:8000/openclaw/pair
{"agent_name": "openclaw-main", "agent_version": "1.0.0"}
```
Returns: `{"pairing_code": "A3F9", "expires_in": 600}`

In your terminal, approve it:
```bash
curl -X POST http://localhost:8000/openclaw/approve/A3F9
```

OpenClaw then calls:
```
POST http://localhost:8000/openclaw/attach
{"pairing_code": "A3F9"}
```
Returns the API key. Store it as `RPF_API_KEY`.

---

### 4. Register the tool in OpenClaw

Copy `openclaw/AGENT_CARD.md` and `openclaw/CONVERSATION_GUIDE.md` to your OpenClaw tools directory:
```bash
cp ~/research-paper-finder/openclaw/AGENT_CARD.md ~/.openclaw/tools/
cp ~/research-paper-finder/openclaw/CONVERSATION_GUIDE.md ~/.openclaw/tools/
```

Or use the YAML definition at the bottom of `CONVERSATION_GUIDE.md` if OpenClaw uses YAML tool configs.

---

### 5. Test the connection
```bash
rpf status
# or
curl -H "X-API-Key: $RPF_API_KEY" http://localhost:8000/health
```

---

## Usage from OpenClaw

Once attached, users can naturally chat with OpenClaw:

```
User: Find me recent papers on quantum error correction

OpenClaw: [calls RPF internally]
          Found 18 confirmed papers...
```

See `CONVERSATION_GUIDE.md` for the full intent→action mapping.

---

## For Hostinger Deployment

When you move from localhost to Hostinger server, update one line:
```bash
# In OpenClaw .env:
RPF_BASE_URL=https://your-hostinger-domain.com
```

Everything else stays the same — the API key works identically on production.

---

## Verify Pairing is Working
```bash
curl -H "X-API-Key: $RPF_API_KEY" http://localhost:8000/openclaw/verify
# → {"status": "valid", "service": "research-paper-finder"}
```
