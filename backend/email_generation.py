"""Shared email draft generation for API and CLI (Ollama + prompt.py)."""
from __future__ import annotations

from dataclasses import dataclass
from types import SimpleNamespace
from typing import Any, Mapping

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

    news_context = _trim_news_context(
        news_context,
        max_items=max(1, inp.context_items),
        snippet_chars=inp.context_snippet_chars,
    )

    messages = build_email_generation_prompt(row, news_context)
    generation = _ollama_chat(
        url=_normalise_ollama_chat_url(inp.ollama_url),
        model=inp.model,
        messages=messages,
        timeout_s=int(inp.timeout_s),
        temperature=float(inp.temperature),
    )
    normalised = _normalise_generation_payload(generation)
    return {
        "subject": normalised.get("subject") or "",
        "email_body": normalised.get("email_body") or "",
        "pain_point": normalised.get("pain_point") or "",
        "why_now": normalised.get("why_now") or "",
        "evidence_used": normalised.get("evidence_used") or "",
        "offer": normalised.get("offer") or "",
        "confidence": normalised.get("confidence") or "",
        "generated_alternatives_json": normalised.get("generated_alternatives_json") or "",
        "news_context": news_context,
        "research_used": research_used,
        "news_context_item_count": len(news_context),
    }
