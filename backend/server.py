#!/usr/bin/env python3
"""FastAPI backend that wraps spawn-radius-scraper.py and streams leads via SSE."""
from __future__ import annotations

import asyncio
import json
import logging
import os
import signal
import sys
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from fastapi import FastAPI, File, Form, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from email_batch import load_rows_from_xlsx, process_batch, rows_to_csv_bytes
from email_generation import EmailGenerationInput, generate_email_draft

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
LOG = logging.getLogger("lead-radar-backend")

# ── Paths ──────────────────────────────────────────────────────────────
BACKEND_ROOT = Path(__file__).resolve().parent
SCRAPER_PATH = BACKEND_ROOT / "spawn-radius-scraper-v2.py"
SESSIONS_DIR = BACKEND_ROOT / "sessions"
SESSIONS_DIR.mkdir(parents=True, exist_ok=True)

# ── App ────────────────────────────────────────────────────────────────
app = FastAPI(title="Lead Radar API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── State ──────────────────────────────────────────────────────────────
_active_process: Optional[asyncio.subprocess.Process] = None
_active_session_id: Optional[str] = None


# ── Models ─────────────────────────────────────────────────────────────
class ScrapeRequest(BaseModel):
    query: str = "car wash"
    location: str = "Delaware"
    limit: int = 50
    # Advanced settings
    radius_km: float = 1.0
    max_depth: int = 3
    root_count: int = 50
    root_skip: int = 0
    per_seed_candidates: int = 60
    per_seed_keep_cap: int = 10
    zoom: int = 15


# ── Endpoints ──────────────────────────────────────────────────────────

@app.post("/api/scrape")
async def start_scrape(req: ScrapeRequest):
    """Start a scrape session and return SSE stream of leads."""
    global _active_process, _active_session_id

    if _active_process is not None and _active_process.returncode is None:
        raise HTTPException(status_code=409, detail="A scrape is already running. Stop it first.")

    session_id = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S") + "-" + uuid.uuid4().hex[:8]
    session_dir = SESSIONS_DIR / session_id
    session_dir.mkdir(parents=True, exist_ok=True)

    xlsx_path = session_dir / "leads.xlsx"
    txt_path = session_dir / "leads.txt"

    # Always spawn the scraper with the same interpreter as the backend.
    # This avoids mismatches where Playwright is installed in a venv but the scraper
    # is executed with system Python (common on Windows).
    python_exe = sys.executable or "python"

    cmd = [
        python_exe,
        str(SCRAPER_PATH),
        "--query", req.query,
        "--location", req.location,
        "--max-total", str(req.limit),
        "--radius-km", str(req.radius_km),
        "--max-depth", str(req.max_depth),
        "--root-count", str(req.root_count),
        "--root-skip", str(req.root_skip),
        "--per-seed-candidates", str(req.per_seed_candidates),
        "--per-seed-keep-cap", str(req.per_seed_keep_cap),
        "--zoom", str(req.zoom),
        "--checkpoint-every", "1",
        "--workers", "10",
        "--json-stream",
        "--out", str(xlsx_path),
    ]

    LOG.info("Starting scrape session %s: %s", session_id, " ".join(cmd))

    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        # Avoid deadlocks if the scraper logs heavily to stderr (common on Windows).
        # Merging keeps the SSE stream flowing and prevents the stderr pipe buffer filling.
        stderr=asyncio.subprocess.STDOUT,
        cwd=str(BACKEND_ROOT),
    )
    _active_process = process
    _active_session_id = session_id

    async def event_generator():
        global _active_process, _active_session_id
        lead_count = 0
        txt_file = open(txt_path, "w", encoding="utf-8")

        # Send session start event
        yield {
            "event": "session_start",
            "data": json.dumps({"session_id": session_id}),
        }

        try:
            async for line in process.stdout:
                decoded = line.decode("utf-8", errors="replace").strip()
                if not decoded:
                    continue

                # Try to parse as JSON lead
                try:
                    lead_data = json.loads(decoded)
                    lead_count += 1
                    lead_data["_index"] = lead_count

                    # Write to txt file
                    txt_file.write(json.dumps(lead_data) + "\n")
                    txt_file.flush()

                    yield {
                        "event": "lead",
                        "data": json.dumps(lead_data),
                    }
                except json.JSONDecodeError:
                    # It's a log line, forward as status
                    yield {
                        "event": "log",
                        "data": json.dumps({"message": decoded}),
                    }

            # Wait for process to finish
            await process.wait()

            yield {
                "event": "complete",
                "data": json.dumps({
                    "session_id": session_id,
                    "total_leads": lead_count,
                    "exit_code": process.returncode,
                }),
            }
        except asyncio.CancelledError:
            LOG.info("SSE stream cancelled for session %s", session_id)
            if process.returncode is None:
                try:
                    process.terminate()
                except Exception:
                    pass
            raise
        finally:
            txt_file.close()
            _active_process = None
            _active_session_id = None

    return EventSourceResponse(event_generator())


@app.post("/api/stop")
async def stop_scrape():
    """Stop the currently running scrape."""
    global _active_process
    if _active_process is None or _active_process.returncode is not None:
        return {"status": "no_active_scrape"}

    try:
        _active_process.terminate()
    except Exception:
        try:
            _active_process.kill()
        except Exception:
            pass

    return {"status": "stopped"}


@app.get("/api/export/{session_id}")
async def export_xlsx(session_id: str):
    """Download the XLSX file for a completed session."""
    xlsx_path = SESSIONS_DIR / session_id / "leads.xlsx"
    if not xlsx_path.exists():
        raise HTTPException(status_code=404, detail="XLSX not found for this session.")
    return FileResponse(
        path=str(xlsx_path),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename=f"leads-{session_id}.xlsx",
    )


@app.get("/api/sessions")
async def list_sessions():
    """List all available sessions."""
    sessions = []
    for d in sorted(SESSIONS_DIR.iterdir(), reverse=True):
        if d.is_dir():
            xlsx_exists = (d / "leads.xlsx").exists()
            txt_exists = (d / "leads.txt").exists()
            lead_count = 0
            if txt_exists:
                try:
                    with open(d / "leads.txt", "r") as f:
                        lead_count = sum(1 for line in f if line.strip())
                except Exception:
                    pass
            sessions.append({
                "session_id": d.name,
                "has_xlsx": xlsx_exists,
                "lead_count": lead_count,
            })
    return sessions


@app.get("/api/sessions/{session_id}/leads")
async def get_session_leads(session_id: str):
    """Return all leads from a session's leads.txt as a JSON array."""
    txt_path = SESSIONS_DIR / session_id / "leads.txt"
    if not txt_path.exists():
        raise HTTPException(status_code=404, detail="No leads file found for this session.")
    leads = []
    try:
        with open(txt_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        leads.append(json.loads(line))
                    except json.JSONDecodeError:
                        pass
    except Exception:
        raise HTTPException(status_code=500, detail="Failed to read leads file.")
    return leads


# ── Website Enrichment ─────────────────────────────────────────────────
import re

_EMAIL_RE = re.compile(r"\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[A-Za-z]{2,}\b")
_SOCIAL_PATTERNS = {
    "facebook": re.compile(r"https?://(?:www\.)?facebook\.com/[^\s\"'<>]+", re.I),
    "instagram": re.compile(r"https?://(?:www\.)?instagram\.com/[^\s\"'<>]+", re.I),
    "twitter": re.compile(r"https?://(?:www\.)?(?:twitter|x)\.com/[^\s\"'<>]+", re.I),
    "linkedin": re.compile(r"https?://(?:[a-z]{2,3}\.)?linkedin\.com/[^\s\"'<>]+", re.I),
    "youtube": re.compile(r"https?://(?:www\.)?youtube\.com/[^\s\"'<>]+", re.I),
    "tiktok": re.compile(r"https?://(?:www\.)?tiktok\.com/@[^\s\"'<>]+", re.I),
    "pinterest": re.compile(r"https?://(?:www\.)?pinterest\.com/[^\s\"'<>]+", re.I),
    "yelp": re.compile(r"https?://(?:www\.)?yelp\.com/biz/[^\s\"'<>]+", re.I),
}

class EnrichRequest(BaseModel):
    url: str


class GenerateEmailRequest(BaseModel):
    company_name: str
    email: str = ""
    first_name: str = ""
    last_name: str = ""
    position: str = ""
    industry: str = ""
    news_report: Optional[dict[str, Any]] = None
    additional_context: str = ""
    do_research: bool = True
    ollama_url: str = "http://localhost:11434"
    model: str = "qwen2.5:3b"
    temperature: float = 0.25
    timeout_s: int = 300
    context_items: int = 5
    context_snippet_chars: int = 2800
    research_limit: int = 12
    per_source_limit: int = 8
    fetch_page_limit: int = 5
    no_fetch_pages: bool = False
    no_linkedin: bool = False
    headed: bool = False


@app.post("/api/generate-email")
async def generate_email(req: GenerateEmailRequest):
    """Generate a personalised outreach draft via local Ollama (same pipeline as the CLI)."""
    inp = EmailGenerationInput(
        company_name=req.company_name.strip(),
        email=req.email.strip(),
        first_name=req.first_name.strip(),
        last_name=req.last_name.strip(),
        position=req.position.strip(),
        industry=req.industry.strip(),
        news_report=req.news_report,
        additional_context=req.additional_context.strip(),
        do_research=req.do_research,
        ollama_url=req.ollama_url.strip() or "http://localhost:11434",
        model=req.model.strip() or "qwen2.5:3b",
        temperature=req.temperature,
        timeout_s=req.timeout_s,
        context_items=req.context_items,
        context_snippet_chars=req.context_snippet_chars,
        research_limit=req.research_limit,
        per_source_limit=req.per_source_limit,
        fetch_page_limit=req.fetch_page_limit,
        no_fetch_pages=req.no_fetch_pages,
        no_linkedin=req.no_linkedin,
        headed=req.headed,
    )
    try:
        return await asyncio.to_thread(generate_email_draft, inp)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        LOG.exception("Email generation failed")
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@app.post("/api/generate-email/batch")
async def generate_email_batch(
    file: UploadFile = File(...),
    model: str = Form("qwen2.5:3b"),
    ollama_url: str = Form("http://localhost:11434"),
    temperature: float = Form(0.22),
    timeout_s: int = Form(420),
    do_research: str = Form("true"),
    max_rows: int = Form(40),
    sleep_ms: int = Form(250),
    context_items: int = Form(8),
    context_snippet_chars: int = Form(4000),
):
    """
    Accept a .xlsx with columns such as email, name, company name.
    Returns a CSV download with subject, body, news based summary, plus any errors per row.
    Research is cached per company; context limits are raised for richer personalisation.
    """
    name = (file.filename or "").lower()
    if not name.endswith((".xlsx", ".xlsm")):
        raise HTTPException(
            status_code=400,
            detail="Upload an Excel workbook (.xlsx or .xlsm).",
        )
    raw = await file.read()
    if len(raw) > 25 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="File too large (max 25 MB).")

    def load_sheet() -> list[dict[str, Any]]:
        return load_rows_from_xlsx(raw)

    try:
        rows = await asyncio.to_thread(load_sheet)
    except Exception as exc:
        LOG.exception("Excel read failed")
        raise HTTPException(status_code=400, detail=f"Could not read spreadsheet: {exc}") from exc

    if not rows:
        raise HTTPException(status_code=400, detail="No data rows found under the header row.")

    research_on = (do_research or "").strip().lower() in ("1", "true", "yes", "on")

    base = EmailGenerationInput(
        company_name="batch",
        email="",
        do_research=research_on,
        ollama_url=(ollama_url or "").strip() or "http://localhost:11434",
        model=(model or "").strip() or "qwen2.5:3b",
        temperature=float(temperature),
        timeout_s=int(timeout_s),
        context_items=max(3, int(context_items)),
        context_snippet_chars=max(600, int(context_snippet_chars)),
        research_limit=14,
        per_source_limit=10,
        fetch_page_limit=6,
    )

    cap = max(1, min(int(max_rows), 200))
    gap = max(0, int(sleep_ms))

    def run_batch() -> bytes:
        out_rows, fieldnames = process_batch(rows, base, max_rows=cap, sleep_ms=gap)
        return rows_to_csv_bytes(out_rows, fieldnames)

    try:
        csv_bytes = await asyncio.to_thread(run_batch)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        LOG.exception("Batch email generation failed")
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return Response(
        content=csv_bytes,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="email-campaigns.csv"'},
    )


@app.post("/api/enrich-website")
async def enrich_website(req: EnrichRequest):
    """Visit a website with Playwright, extract emails and social links."""
    url = req.url.strip()
    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    # Use the backend interpreter so Playwright dependencies match.
    python_exe = sys.executable or "python"

    # Inline script to visit and extract
    script = f'''
import json, re, sys
from playwright.sync_api import sync_playwright

url = {repr(url)}
EMAIL_RE = re.compile(r"\\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[A-Za-z]{{2,}}\\b")
SOCIAL = {{
    "facebook": re.compile(r"https?://(?:www\\.)?facebook\\.com/[^\\s\\"\\'>]+", re.I),
    "instagram": re.compile(r"https?://(?:www\\.)?instagram\\.com/[^\\s\\"\\'>]+", re.I),
    "twitter": re.compile(r"https?://(?:www\\.)?(?:twitter|x)\\.com/[^\\s\\"\\'>]+", re.I),
    "linkedin": re.compile(r"https?://(?:[a-z]{{2,3}}\\.)?linkedin\\.com/[^\\s\\"\\'>]+", re.I),
    "youtube": re.compile(r"https?://(?:www\\.)?youtube\\.com/[^\\s\\"\\'>]+", re.I),
    "tiktok": re.compile(r"https?://(?:www\\.)?tiktok\\.com/@[^\\s\\"\\'>]+", re.I),
    "pinterest": re.compile(r"https?://(?:www\\.)?pinterest\\.com/[^\\s\\"\\'>]+", re.I),
    "yelp": re.compile(r"https?://(?:www\\.)?yelp\\.com/biz/[^\\s\\"\\'>]+", re.I),
}}

pages_to_check = [url]
contact_paths = ["/contact", "/contact-us", "/about", "/about-us"]
for cp in contact_paths:
    base = url.rstrip("/")
    pages_to_check.append(base + cp)

result = {{"emails": [], "socials": {{}}, "pages_checked": []}}

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    page.set_default_timeout(12000)
    
    for page_url in pages_to_check:
        try:
            resp = page.goto(page_url, wait_until="domcontentloaded", timeout=12000)
            if resp and resp.status >= 400:
                continue
            page.wait_for_timeout(800)
            html = page.content()
            result["pages_checked"].append(page_url)
            
            for em in EMAIL_RE.findall(html):
                if em not in result["emails"] and not em.endswith((".png", ".jpg", ".gif", ".svg")):
                    result["emails"].append(em)
            
            for name, pat in SOCIAL.items():
                for match in pat.findall(html):
                    clean = match.split("?")[0].split("#")[0].rstrip("/")
                    if name not in result["socials"]:
                        result["socials"][name] = []
                    if clean not in result["socials"][name]:
                        result["socials"][name].append(clean)
        except Exception:
            pass
    
    browser.close()

print(json.dumps(result))
'''

    try:
        process = await asyncio.create_subprocess_exec(
            python_exe, "-c", script,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(BACKEND_ROOT),
        )
        stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=60)
        output = stdout.decode("utf-8", errors="replace").strip()
        if process.returncode != 0:
            err_msg = stderr.decode("utf-8", errors="replace").strip()
            LOG.error("Enrich script failed: %s", err_msg)
            return {"emails": [], "socials": {}, "error": "Script failed", "pages_checked": []}
        
        result = json.loads(output)
        return result
    except asyncio.TimeoutError:
        return {"emails": [], "socials": {}, "error": "Timeout (60s)", "pages_checked": []}
    except Exception as e:
        LOG.exception("Enrich failed for %s", url)
        return {"emails": [], "socials": {}, "error": str(e), "pages_checked": []}


@app.get("/api/health")
async def health():
    return {"status": "ok", "scraper_exists": SCRAPER_PATH.exists()}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
