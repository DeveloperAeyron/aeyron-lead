"""Shared email draft generation for API and CLI (Ollama + prompt.py)."""
from __future__ import annotations

import re
from dataclasses import dataclass
from types import SimpleNamespace
from typing import Any, Mapping, Sequence
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from prompt import build_email_generation_prompt

# Reuse the CLI implementation to avoid drift.
from generate_news_emails_ollama import (
    _company_report_context,
    _normalise_generation_payload,
    _normalise_ollama_chat_url,
    _ollama_chat,
    _research_company,
    _row_news_context,
    _trim_news_context,
)


def news_based_summary_from_context(
    items: Sequence[Mapping[str, str]],
    *,
    max_chars: int = 24_000,
) -> str:
    """Readable summary of research snippets sent to the model (for CSV export)."""
    blocks: list[str] = []
    for it in items:
        title = (it.get("title") or "").strip()
        snip = (it.get("snippet") or "").strip()
        url = (it.get("url") or "").strip()
        parts: list[str] = []
        if title:
            parts.append(title)
        if snip:
            parts.append(snip)
        line = "\n".join(parts) if parts else ""
        if url:
            line = f"{line}\nURL: {url}" if line else f"URL: {url}"
        if line.strip():
            blocks.append(line.strip())
    text = "\n\n---\n\n".join(blocks)
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 3].rstrip() + "..."


@dataclass
class EmailGenerationInput:
    company_name: str
    email: str = ""
    first_name: str = ""
    last_name: str = ""
    position: str = ""
    industry: str = ""
    news_report: Mapping[str, Any] | None = None
    additional_context: str = ""
    do_research: bool = True
    ollama_url: str = "http://localhost:11434"
    model: str = "gemma3:12b"
    temperature: float = 0.25
    timeout_s: int = 300
    context_items: int = 8
    context_snippet_chars: int = 3800
    research_limit: int = 12
    per_source_limit: int = 8
    fetch_page_limit: int = 5
    no_fetch_pages: bool = False
    no_linkedin: bool = False
    headed: bool = False
    website_url: str = ""
    # When True (default), research skips Hugging Face inference (faster, no token). Set False if HF_TOKEN is set.
    research_disable_hf: bool = True
    # Disk cache for Playwright research payloads (same company + settings hits skip browser).
    research_disk_cache: bool = True
    research_cache_ttl_hours: float = 168.0
    research_cache_dir: str = ""


def fetch_website_plain_text(
    url: str,
    *,
    timeout_s: int = 20,
    max_bytes: int = 1_500_000,
    max_chars: int = 12_000,
) -> str:
    """Lightweight HTTP fetch + tag strip. Many corporate sites still need Playwright; this covers simple cases."""
    raw = (url or "").strip()
    if not raw:
        return ""
    if not raw.startswith(("http://", "https://")):
        raw = "https://" + raw
    try:
        req = Request(
            raw,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"
                ),
                "Accept": "text/html,application/xhtml+xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-GB,en;q=0.9",
            },
        )
        with urlopen(req, timeout=timeout_s) as resp:
            html = resp.read(max_bytes).decode("utf-8", errors="replace")
    except (HTTPError, URLError, TimeoutError, OSError, ValueError):
        return ""

    html = re.sub(r"(?is)<script[^>]*>.*?</script>", " ", html)
    html = re.sub(r"(?is)<style[^>]*>.*?</style>", " ", html)
    html = re.sub(r"<[^>]+>", " ", html)
    text = re.sub(r"\s+", " ", html).strip()
    return text[:max_chars]


def prepend_prospect_website_block(news_context: list[dict[str, str]], website_url: str) -> None:
    """Inline homepage copy when callers pass a prospect website URL (spreadsheet column or API field)."""
    u = (website_url or "").strip()
    if not u:
        return
    canon = u if u.startswith(("http://", "https://")) else f"https://{u}"
    canon_lower = canon.rstrip("/").lower()
    for it in news_context:
        uu = (it.get("url") or "").strip().rstrip("/").lower()
        if uu and (uu == canon_lower or canon_lower.endswith(uu) or uu.endswith(canon_lower)):
            return
    body = fetch_website_plain_text(canon)
    news_context.insert(
        0,
        {
            "title": "Prospect website (from your spreadsheet or form)",
            "snippet": (
                body
                if body
                else "(No readable body returned — site may block simple fetches or need JavaScript. URL is still attached.)"
            ),
            "url": canon,
        },
    )


def _research_namespace(inp: EmailGenerationInput) -> SimpleNamespace:
    return SimpleNamespace(
        research_limit=inp.research_limit,
        per_source_limit=inp.per_source_limit,
        fetch_page_limit=inp.fetch_page_limit,
        no_fetch_pages=inp.no_fetch_pages,
        no_linkedin=inp.no_linkedin,
        headed=inp.headed,
        verbose=False,
        research_output=None,
        research_disable_hf=inp.research_disable_hf,
        research_disk_cache=inp.research_disk_cache,
        research_cache_ttl_hours=inp.research_cache_ttl_hours,
        research_cache_dir=(inp.research_cache_dir or "").strip() or None,
    )


def generate_with_trimmed_context(
    row: dict[str, str],
    trimmed_news_context: list[dict[str, str]],
    inp: EmailGenerationInput,
    *,
    research_used: bool,
    website_url_override: str = "",
    additional_context_override: str = "",
) -> dict[str, Any]:
    """Run Ollama after news context is finalised (trimmed). Shared by single and batch flows."""
    messages = build_email_generation_prompt(
        row,
        trimmed_news_context,
        website_url=website_url_override or inp.website_url,
        additional_context=additional_context_override or inp.additional_context,
    )
    generation = _ollama_chat(
        url=_normalise_ollama_chat_url(inp.ollama_url),
        model=inp.model,
        messages=messages,
        timeout_s=int(inp.timeout_s),
        temperature=float(inp.temperature),
    )
    normalised = _normalise_generation_payload(generation)
    news_summary = news_based_summary_from_context(trimmed_news_context)
    return {
        "subject": normalised.get("subject") or "",
        "email_body": normalised.get("email_body") or "",
        "pain_point": normalised.get("pain_point") or "",
        "why_now": normalised.get("why_now") or "",
        "evidence_used": normalised.get("evidence_used") or "",
        "offer": normalised.get("offer") or "",
        "confidence": normalised.get("confidence") or "",
        "generated_alternatives_json": normalised.get("generated_alternatives_json") or "",
        "news_context": trimmed_news_context,
        "news_based_summary": news_summary,
        "research_used": research_used,
        "news_context_item_count": len(trimmed_news_context),
    }


def generate_email_draft(inp: EmailGenerationInput) -> dict[str, Any]:
    """Build prompts, call Ollama, return normalised fields plus context metadata."""
    company = (inp.company_name or "").strip()
    if not company:
        raise ValueError("company_name is required.")

    row: dict[str, str] = {
        "Email": (inp.email or "").strip(),
        "First Name": (inp.first_name or "").strip(),
        "Last Name": (inp.last_name or "").strip(),
        "Company Name": company,
        "Position": (inp.position or "").strip() or "relevant leader",
        "Industry": (inp.industry or "").strip(),
    }

    news_context: list[dict[str, str]] = []
    research_used = False

    if inp.news_report is not None:
        news_context = list(_company_report_context(inp.news_report))
    elif inp.do_research:
        ns = _research_namespace(inp)
        report = _research_company(company, ns)
        news_context = list(_company_report_context(report))
        research_used = True
    else:
        news_context = list(_row_news_context(row))

    prepend_prospect_website_block(news_context, inp.website_url)

    trimmed = _trim_news_context(
        news_context,
        max_items=max(1, inp.context_items),
        snippet_chars=inp.context_snippet_chars,
    )
    return generate_with_trimmed_context(row, trimmed, inp, research_used=research_used)


def split_full_name(name: str) -> tuple[str, str]:
    name = (name or "").strip()
    if not name:
        return "", ""
    parts = name.split(None, 1)
    if len(parts) == 1:
        return parts[0], ""
    return parts[0], parts[1]


def make_prompt_row(
    *,
    email: str,
    first_name: str,
    last_name: str,
    company_name: str,
    position: str = "",
    industry: str = "",
) -> dict[str, str]:
    fn = (first_name or "").strip()
    ln = (last_name or "").strip()
    co = (company_name or "").strip()
    return {
        "Email": (email or "").strip(),
        "First Name": fn,
        "Last Name": ln,
        "Company Name": co,
        "Position": (position or "").strip() or "relevant leader",
        "Industry": (industry or "").strip(),
    }


def company_cache_key(company: str) -> str:
    text = (company or "").lower()
    text = text.replace("&", " and ")
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return " ".join(text.split()).strip()
