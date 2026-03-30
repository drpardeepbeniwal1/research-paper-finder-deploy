#!/usr/bin/env python3
"""
Research Paper Finder CLI — OpenClaw Agent Interface
Usage: rpf search "transformer attention mechanisms"
       rpf search "CRISPR 2022" --year-from 2022 --year-to 2024 --associated
       rpf keys create my-agent
       rpf keys list
"""
import click, httpx, json, os, sys
from pathlib import Path
from datetime import datetime

CONFIG_FILE = Path.home() / ".openclaw" / "rpf_config.json"

def load_config() -> dict:
    if CONFIG_FILE.exists():
        return json.loads(CONFIG_FILE.read_text())
    return {}

def save_config(cfg: dict):
    CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(json.dumps(cfg, indent=2))

def get_client(ctx) -> tuple[httpx.Client, str]:
    cfg = load_config()
    base = ctx.obj.get("base") or cfg.get("base_url", "http://localhost:8000")
    key = ctx.obj.get("key") or cfg.get("api_key", "")
    if not key:
        click.echo("No API key. Run: rpf config set-key <key>", err=True)
        sys.exit(1)
    client = httpx.Client(base_url=base, headers={"X-API-Key": key}, timeout=300)
    return client, base

@click.group()
@click.option("--base", envvar="RPF_BASE_URL", default=None, help="API base URL")
@click.option("--key", envvar="RPF_API_KEY", default=None, help="API key")
@click.option("--json-output", is_flag=True, default=False, help="Output raw JSON")
@click.pass_context
def cli(ctx, base, key, json_output):
    """Research Paper Finder — AI-powered deep paper discovery."""
    ctx.ensure_object(dict)
    ctx.obj["base"] = base
    ctx.obj["key"] = key
    ctx.obj["json"] = json_output

# ── Search ──────────────────────────────────────────────────────────────────

@cli.command()
@click.argument("query")
@click.option("--year-from", "-yf", type=int, default=None, help="Filter from year")
@click.option("--year-to", "-yt", type=int, default=None, help="Filter to year")
@click.option("--max-results", "-n", type=int, default=10, help="Max papers to return")
@click.option("--associated", "-a", is_flag=True, default=False, help="Include associated papers per result")
@click.option("--save", "-s", default=None, help="Save results to JSON file")
@click.option("--download-pdfs", "-p", is_flag=True, default=False, help="Download top 3 summary PDFs")
@click.pass_context
def search(ctx, query, year_from, year_to, max_results, associated, save, download_pdfs):
    """Search for research papers using AI-powered query expansion."""
    client, base = get_client(ctx)
    payload = {
        "query": query,
        "year_from": year_from,
        "year_to": year_to,
        "max_results": max_results,
        "include_associated": associated,
    }

    click.echo(f"Searching: {query!r}", err=True)
    if year_from or year_to:
        click.echo(f"Year range: {year_from or '*'} – {year_to or '*'}", err=True)

    try:
        resp = client.post("/search", json=payload)
        resp.raise_for_status()
        data = resp.json()
    except httpx.HTTPStatusError as e:
        click.echo(f"Error {e.response.status_code}: {e.response.text}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"Connection error: {e}", err=True)
        sys.exit(1)

    if ctx.obj["json"]:
        click.echo(json.dumps(data, indent=2))
        return

    # Pretty output
    papers = data.get("papers", [])
    terms = data.get("generated_terms", [])
    total = data.get("total_found", 0)

    click.echo(f"\n{'='*60}")
    click.echo(f"  Found {total} papers · Showing {len(papers)}")
    click.echo(f"  Search terms: {', '.join(terms[:4])}...")
    click.echo(f"{'='*60}\n")

    for i, paper in enumerate(papers, 1):
        score = paper.get("relevance_score", 0)
        score_str = f"[{score:.0f}/100]"
        bar = "🟢" if score >= 70 else "🟡" if score >= 50 else "🔴"
        click.echo(f"{i:2}. {bar} {score_str} {paper.get('title','')[:80]}")
        authors = ", ".join((paper.get("authors") or [])[:2])
        year = paper.get("year") or "?"
        source = paper.get("source", "")
        click.echo(f"    {authors} · {year} · {source}")
        if paper.get("relevance_reasoning"):
            click.echo(f"    ↳ {paper['relevance_reasoning'][:100]}")
        if paper.get("url"):
            click.echo(f"    🔗 {paper['url']}")
        if paper.get("pdf_url"):
            click.echo(f"    📄 PDF: {paper['pdf_url']}")
        if associated and paper.get("associated_papers"):
            click.echo(f"    Associated ({len(paper['associated_papers'])}):")
            for ap in paper["associated_papers"]:
                click.echo(f"       · {ap.get('title','')[:60]} [{ap.get('relevance_score',0):.0f}]")
        click.echo()

    # PDF downloads
    if download_pdfs and data.get("top_pdfs"):
        key = ctx.obj.get("key") or load_config().get("api_key", "")
        out_dir = Path("./rpf_pdfs")
        out_dir.mkdir(exist_ok=True)
        for pdf_path in data["top_pdfs"]:
            filename = os.path.basename(pdf_path)
            try:
                r = client.get(f"/search/pdf/{filename}")
                r.raise_for_status()
                dest = out_dir / filename
                dest.write_bytes(r.content)
                click.echo(f"📄 Saved: {dest}")
            except Exception as e:
                click.echo(f"PDF download failed: {e}", err=True)

    if save:
        Path(save).write_text(json.dumps(data, indent=2))
        click.echo(f"\nSaved to {save}")

# ── Config ──────────────────────────────────────────────────────────────────

@cli.group()
def config():
    """Configure CLI settings."""

@config.command("set-key")
@click.argument("api_key")
def config_set_key(api_key):
    """Save API key to config."""
    cfg = load_config()
    cfg["api_key"] = api_key
    save_config(cfg)
    click.echo(f"API key saved to {CONFIG_FILE}")

@config.command("set-url")
@click.argument("url")
def config_set_url(url):
    """Set the backend base URL."""
    cfg = load_config()
    cfg["base_url"] = url.rstrip("/")
    save_config(cfg)
    click.echo(f"Base URL set: {url}")

@config.command("show")
def config_show():
    """Show current config."""
    cfg = load_config()
    key = cfg.get("api_key", "")
    click.echo(f"Base URL : {cfg.get('base_url','http://localhost:8000')}")
    click.echo(f"API Key  : {key[:12]}...{key[-4:] if len(key) > 16 else '(not set)'}")

# ── Keys ────────────────────────────────────────────────────────────────────

@cli.group()
def keys():
    """Manage API keys."""

@keys.command("create")
@click.argument("name")
@click.pass_context
def keys_create(ctx, name):
    """Create a new API key."""
    cfg = load_config()
    base = ctx.obj.get("base") or cfg.get("base_url", "http://localhost:8000")
    # Key creation doesn't need auth
    try:
        resp = httpx.post(f"{base}/auth/keys", json={"name": name}, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        click.echo(f"\nCreated key for: {name}")
        click.echo(f"Key: {data['key']}")
        click.echo(f"\nTo use: rpf config set-key {data['key']}")
    except Exception as e:
        click.echo(f"Error: {e}", err=True)

@keys.command("list")
@click.pass_context
def keys_list(ctx, **_):
    """List all API keys."""
    client, _ = get_client(ctx)
    try:
        resp = client.get("/auth/keys")
        resp.raise_for_status()
        for k in resp.json():
            click.echo(f"{k['name']:20} {k['key_prefix']}... created: {k['created_at'][:10]}")
    except Exception as e:
        click.echo(f"Error: {e}", err=True)

# ── OpenClaw pairing ─────────────────────────────────────────────────────────

@cli.group()
def openclaw():
    """Manage OpenClaw pairing and attachment."""

@openclaw.command("approve")
@click.argument("code")
@click.pass_context
def openclaw_approve(ctx, code):
    """Approve an OpenClaw pairing request (run this in your terminal after OpenClaw pairs)."""
    cfg = load_config()
    base = ctx.obj.get("base") or cfg.get("base_url", "http://localhost:8000")
    try:
        resp = httpx.post(f"{base}/openclaw/approve/{code}", timeout=10)
        resp.raise_for_status()
        click.echo(f"Pairing {code} approved: {resp.json().get('message')}")
    except Exception as e:
        click.echo(f"Error: {e}", err=True)

@openclaw.command("pending")
@click.pass_context
def openclaw_pending(ctx):
    """List pending OpenClaw pairing requests."""
    cfg = load_config()
    base = ctx.obj.get("base") or cfg.get("base_url", "http://localhost:8000")
    try:
        resp = httpx.get(f"{base}/openclaw/pending", timeout=10)
        resp.raise_for_status()
        items = resp.json()
        if not items:
            click.echo("No pending pairings.")
            return
        for item in items:
            approved = "✓ approved" if item["approved"] else "⏳ waiting"
            click.echo(f"{item['code']}  {item['agent']:20} {approved}  expires: {item['expires_at'][:19]}")
    except Exception as e:
        click.echo(f"Error: {e}", err=True)

# ── Health ───────────────────────────────────────────────────────────────────

@cli.command()
@click.pass_context
def status(ctx):
    """Check backend status."""
    cfg = load_config()
    base = ctx.obj.get("base") or cfg.get("base_url", "http://localhost:8000")
    try:
        resp = httpx.get(f"{base}/health", timeout=10)
        data = resp.json()
        click.echo(f"Status      : {data['status']}")
        click.echo(f"Model       : {data['model']}")
        click.echo(f"NVIDIA Keys : {data.get('active_keys', '?')} active → {data.get('total_rpm', '?')} RPM total")
        click.echo(f"Sources ({len(data.get('sources',[]))}): {', '.join(data.get('sources',[]))}")
        click.echo(f"PDF Tiers   : {', '.join(data.get('pdf_tiers',[]))}")
    except Exception as e:
        click.echo(f"Backend unreachable: {e}", err=True)

if __name__ == "__main__":
    cli(obj={})
