from __future__ import annotations

import json
import re
from typing import Any, Mapping, Sequence


AEYRON_POSITIONING = (
    "Aeyron builds AI automation, custom web/mobile applications, document "
    "intelligence, workflow automation, dashboards, cloud infrastructure, IoT, "
    "and computer vision systems for teams that need practical modernization."
)


STYLE_RULES = [
    "Match the sample emails: short, direct, professional, and low-pressure.",
    "Write in first person plural from Aeyron.",
    "Use the recipient first name in the greeting when available; otherwise use 'Hi there,'.",
    "Include one sentence that starts with 'At Aeyron,' and explains what we do.",
    "Use one concrete pain point tied to the role, company, or scraped news.",
    "Do not overstate the news. If evidence is weak, say 'teams like yours' instead of claiming a fact.",
    "Do not mention scraping, web search, AI prompt, model, or dataset.",
    "Do not invent exact metrics, contract details, compliance issues, or internal problems.",
    "Avoid hype, buzzwords, exclamation marks, and long paragraphs.",
    "Keep the email body under 130 words.",
    "End with 'Best regards,' and do not add a sender name.",
]


SAMPLE_EMAILS = [
    {
        "subject": "AI solutions for document-heavy workflows",
        "body": (
            "Hi Samantha,\n\n"
            "Managing and retrieving information from extensive documents can be "
            "time-consuming for many federal teams.\n\n"
            "At Aeyron, we provide AI-powered document management solutions, custom "
            "automation tools, and intelligent search capabilities that streamline "
            "information workflows.\n\n"
            "Happy to share more if this aligns with your current priorities.\n\n"
            "Best regards,"
        ),
    },
    {
        "subject": "Reducing administrative workload at City Of Las Vegas",
        "body": (
            "Hi Nicole,\n\n"
            "Retrieving information from extensive files and coordinating across "
            "multiple systems consumes valuable administrative time.\n\n"
            "At Aeyron, we build document automation tools, AI-powered search "
            "solutions, and workflow management systems that reduce repetitive tasks "
            "and improve information access.\n\n"
            "Happy to share more if this aligns with your current priorities.\n\n"
            "Best regards,"
        ),
    },
    {
        "subject": "Streamlining IT infrastructure management",
        "body": (
            "Hi Trevor,\n\n"
            "Managing complex IT systems and ensuring seamless integration across "
            "legacy and modern infrastructure can be challenging for public-sector teams.\n\n"
            "At Aeyron, we develop custom AI/ML solutions, computer vision systems, "
            "and cloud infrastructure that modernize IT operations while maintaining "
            "security and compliance standards.\n\n"
            "Happy to share more if this aligns with your current priorities.\n\n"
            "Best regards,"
        ),
    },
]


OUTPUT_CONTRACT = {
    "subject": "string, 4-8 words when possible",
    "email_body": "string, complete email body only",
    "pain_point": "string, the specific pain point used",
    "why_now": "string, short reason this is timely",
    "evidence_used": "string, cite the news/source detail used or empty string",
    "offer": "string, the Aeyron offer selected",
    "confidence": "low|medium|high",
}


def _clean(value: Any, *, max_chars: int = 900) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 3].rstrip() + "..."


def _row_value(row: Mapping[str, Any], *keys: str) -> str:
    lower = {str(k).strip().lower(): v for k, v in row.items()}
    for key in keys:
        value = lower.get(key.lower())
        if value not in (None, ""):
            return _clean(value)
    return ""


def _format_examples() -> str:
    return json.dumps(SAMPLE_EMAILS, ensure_ascii=False, indent=2)


def _format_news_context(news_context: Sequence[Mapping[str, Any]] | Mapping[str, Any] | str | None) -> str:
    if not news_context:
        return "No scraped news context was provided."

    if isinstance(news_context, str):
        return _clean(news_context, max_chars=4_000)

    if isinstance(news_context, Mapping):
        return json.dumps(news_context, ensure_ascii=False, indent=2)[:4_000]

    bullets = []
    for item in news_context[:8]:
        if not isinstance(item, Mapping):
            continue
        title = _clean(item.get("title") or item.get("summary") or item.get("theme"), max_chars=220)
        snippet = _clean(item.get("snippet") or item.get("evidence") or item.get("fetched_text"), max_chars=550)
        url = _clean(item.get("url") or item.get("source_url"), max_chars=220)
        if title or snippet:
            bullets.append({"title": title, "snippet": snippet, "url": url})

    if not bullets:
        return "No usable scraped news context was provided."
    return json.dumps(bullets, ensure_ascii=False, indent=2)


def build_email_generation_prompt(
    row: Mapping[str, Any],
    news_context: Sequence[Mapping[str, Any]] | Mapping[str, Any] | str | None = None,
) -> list[dict[str, str]]:
    """Build Ollama chat messages for personalized email generation.

    Keep this module deliberately boring and easy to edit. The generator script
    imports only this function, so future prompt experiments can happen here.
    """

    first_name = _row_value(row, "First Name", "first_name", "first")
    last_name = _row_value(row, "Last Name", "last_name", "last")
    company = _row_value(row, "Company Name", "company", "company_name", "organization")
    position = _row_value(row, "Position", "title", "job_title", "role")
    email = _row_value(row, "Email", "email_address")

    user_prompt = (
        "Generate one personalized cold email for this prospect.\n\n"
        "Prospect:\n"
        f"- First name: {first_name or 'unknown'}\n"
        f"- Last name: {last_name or 'unknown'}\n"
        f"- Email: {email or 'unknown'}\n"
        f"- Company: {company or 'unknown'}\n"
        f"- Position: {position or 'unknown'}\n\n"
        "Scraped company/news context:\n"
        f"{_format_news_context(news_context)}\n\n"
        "Aeyron positioning:\n"
        f"{AEYRON_POSITIONING}\n\n"
        "Sample style to imitate:\n"
        f"{_format_examples()}\n\n"
        "Return strict JSON only with this schema:\n"
        f"{json.dumps(OUTPUT_CONTRACT, ensure_ascii=False, indent=2)}"
    )

    system_prompt = (
        "You are an expert B2B cold email copywriter for Aeyron.\n"
        "Your job is to turn role context and scraped company/news context into "
        "a concise, helpful, credible email.\n\n"
        "Rules:\n"
        + "\n".join(f"- {rule}" for rule in STYLE_RULES)
    )

    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]
