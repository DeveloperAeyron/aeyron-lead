"""Shared email draft generation for API and CLI (Ollama + prompt.py)."""
from __future__ import annotations

import re
from dataclasses import dataclass
from types import SimpleNamespace
from typing import Any, Mapping, Sequence

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
    max_chars: int = 12_000,
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
    )


def generate_with_trimmed_context(
    row: dict[str, str],
    trimmed_news_context: list[dict[str, str]],
    inp: EmailGenerationInput,
    *,
    research_used: bool,
) -> dict[str, Any]:
    """Run Ollama after news context is finalised (trimmed). Shared by single and batch flows."""
    messages = build_email_generation_prompt(row, trimmed_news_context)
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

    extra = (inp.additional_context or "").strip()
    if extra:
        news_context.insert(
            0,
            {
                "title": "Additional context",
                "snippet": extra[:12_000],
                "url": "",
            },
        )

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
