from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Mapping, Sequence


# ── Persistence ────────────────────────────────────────────────────────
_PROMPTS_FILE = Path(__file__).resolve().parent / "prompts_override.json"


def _load_overrides() -> dict[str, str]:
    """Load user-edited prompt sections from disk (empty dict if no file)."""
    if _PROMPTS_FILE.exists():
        try:
            return json.loads(_PROMPTS_FILE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    return {}


def save_prompts(sections: dict[str, str]) -> None:
    """Persist prompt section overrides to disk."""
    _PROMPTS_FILE.write_text(json.dumps(sections, ensure_ascii=False, indent=2), encoding="utf-8")


# ── Default prompt sections ────────────────────────────────────────────

_DEFAULT_PRODUCT_PORTFOLIO = """
AEYRON PRODUCT PORTFOLIO (use at most ONE per email, only if it fits naturally)

1. Legisys — OCR plus semantic search for scanned legal and compliance documents.
   Fits: legal, government, compliance, insurance, finance teams drowning in paperwork.

2. MedAide — Healthcare assistant chatbot for differential diagnosis and patient guidance.
   Fits: clinics, digital health startups, hospital admin teams.

3. MedED Global — Voice-AI platform where practitioners validate diagnoses in real time
   against best-practice guidelines. Fits: medical education, hospital quality teams,
   residency programmes.

4. Telehealth — Unified platform connecting doctors, patients, and hospital staff.
   Includes EMR, appointment booking, patient transport, and role-specific dashboards.
   Fits: hospitals, multi-site clinics, health-tech.

5. Graid — AI-powered trading card grading plus community marketplace (mobile).
   Fits: collectibles platforms, hobby marketplaces, consumer app founders.

6. Appetite — Snap-a-photo food analysis: object detection, ingredient breakdown,
   calorie and macro estimates. Fits: nutrition apps, fitness platforms, wellness startups.

7. SmoothPay — Digital loyalty plus payment platform with merchant analytics and
   inventory management. Fits: retail chains, F&B groups, franchise operators.

8. AI Writing Assistant — Automates cold email and content generation workflows.
   Fits: sales teams, marketing agencies, growth teams with high-volume outreach.

9. Trip Rec App — Personalised travel recommendations via Google Maps plus a custom LLM.
   Fits: travel platforms, hospitality tech, concierge apps.

If no product is a clear fit, do NOT force one. Reference Aeyron's general capability instead.
""".strip()


_DEFAULT_NON_NEGOTIABLE_RULES = """
1. Subject line: 5–9 words, specific to the role or company, no hype words
   (unlock, revolutionise, game-changer, transform).

2. Language: write in British English (UK spelling and phrasing). Avoid Americanisms
   (e.g. optimise not optimize; programme not program; organisation not organization).

3. Opening line: use ONE concrete observation from the provided context (website snippet or
   news context) if available. If context is weak, state a credible role/industry pain in a
   cautious way. Do not open with "I hope this finds you well" or a compliment.

4. Aeyron line: include exactly one sentence starting with "At Aeyron," that connects
   our work to their pain. Do not list every service we offer.

5. Product reference: at most one sentence. Frame it as proof, not a feature dump.
   Example shape: "We built [X] for [type of team], which [outcome]."

6. CTA: one soft question. Never say "book a call", "schedule a demo", or
   "let me know if you are interested." Prefer: "Happy to share more if this is on your radar."
   or "Worth a quick conversation?" or similar.

7. Structure: 2–4 short paragraphs (max 2 sentences each). No bullets.

8. Length: 80–130 words in the body (excluding "Best regards,"). If you cannot be specific,
   be shorter rather than padding.

9. Never invent metrics, contracts, or internal problems. If context is thin, say
   "teams like yours" rather than asserting a fact about their team.

10. No exclamation marks. No emoji. No filler ("As you know", "In today's world",
   "I wanted to reach out").

11. End with "Best regards," — no sender name.

12. Forbidden words: unlock, access, leverage (as a verb), cutting-edge, seamless,
    robust, innovative, solution (as a standalone noun), excited, passionate.

SPAM TRIGGER WORDS TO AVOID

Free, guarantee, earn money, winner, urgent, act now, limited time, click here,
    unsubscribe, congratulations, offer.
""".strip()


_DEFAULT_TONE_ANCHOR = """
SHORT SHAPE EXAMPLE (fictional prospect — imitate structure, not wording)

Subject: Compliance filings and slow document retrieval

Hi Alex,

When matter teams live in scanned bundles and email threads, retrieval before hearings
or filings quietly becomes the bottleneck.

At Aeyron, we build document intelligence workflows that make scanned counsel and
exhibit material searchable without another manual pass.

We shipped Legisys for teams with similar volumes, cutting retrieval time for routine
requests.

Happy to share more if this is on your radar.

Best regards,
""".strip()


_DEFAULT_SYSTEM_PROMPT_TEMPLATE = f"""You are a senior B2B cold email copywriter for Aeyron — a software
development agency that builds AI automation, document intelligence, custom web and mobile
applications, workflow automation, dashboards, cloud infrastructure, IoT, and computer vision
systems for teams that need practical modernisation.

Your only job is to turn a prospect's role, company, industry, and any available context into
one short, credible, low-pressure email package that could earn a reply. You also produce
controlled variations for testing.

Write in British English (UK spelling and phrasing).

{_DEFAULT_PRODUCT_PORTFOLIO}

RULES (non-negotiable)
{_DEFAULT_NON_NEGOTIABLE_RULES}

TONE ANCHOR (structure only)
{_DEFAULT_TONE_ANCHOR}

OUTPUT FORMAT

Return strict JSON only (no markdown fences). Match this shape — keys and nesting must match:
{{OUTPUT_CONTRACT_JSON}}

The email bodies inside primary_email and the two variations must each obey all rules above.
subject_lines must contain exactly five strings."""


def get_prompt_sections() -> dict[str, str]:
    """Return the active prompt sections (overrides take precedence over defaults)."""
    overrides = _load_overrides()
    return {
        "product_portfolio": overrides.get("product_portfolio", _DEFAULT_PRODUCT_PORTFOLIO),
        "non_negotiable_rules": overrides.get("non_negotiable_rules", _DEFAULT_NON_NEGOTIABLE_RULES),
        "tone_anchor": overrides.get("tone_anchor", _DEFAULT_TONE_ANCHOR),
    }


def get_default_prompt_sections() -> dict[str, str]:
    """Return the hardcoded default prompt sections (ignoring overrides)."""
    return {
        "product_portfolio": _DEFAULT_PRODUCT_PORTFOLIO,
        "non_negotiable_rules": _DEFAULT_NON_NEGOTIABLE_RULES,
        "tone_anchor": _DEFAULT_TONE_ANCHOR,
    }


def get_system_prompt_template() -> str:
    """Return the active system prompt template (editable as one block).

    The template must contain the token ``{OUTPUT_CONTRACT_JSON}``, which will be
    replaced at runtime with the current JSON contract.
    """
    overrides = _load_overrides()
    text = str(overrides.get("system_prompt_template") or "").strip()
    if text:
        return text
    return _DEFAULT_SYSTEM_PROMPT_TEMPLATE


def get_default_system_prompt_template() -> str:
    """Return the hardcoded default system prompt template (ignoring overrides)."""
    return _DEFAULT_SYSTEM_PROMPT_TEMPLATE


# Keep module-level aliases for any legacy imports
PRODUCT_PORTFOLIO = _DEFAULT_PRODUCT_PORTFOLIO
NON_NEGOTIABLE_RULES = _DEFAULT_NON_NEGOTIABLE_RULES
TONE_ANCHOR = _DEFAULT_TONE_ANCHOR


# Prefer fetched page text over SERP snippets when building Ollama context.
_FETCHED_BODY_MIN_CHARS = 280


def best_evidence_body(item: Mapping[str, Any]) -> str:
    """Return the richest available text for a search or insight row.

    Fetched page bodies (when ``--fetch-pages`` ran in research) should win over
    short search snippets; Hugging Face summaries sit between the two.
    """
    fetched = str(item.get("fetched_text") or "").strip()
    if len(fetched) >= _FETCHED_BODY_MIN_CHARS:
        return fetched
    hf_summary = str(item.get("hf_summary") or "").strip()
    if hf_summary:
        return hf_summary
    if fetched:
        return fetched
    for key in ("evidence", "snippet", "raw_text"):
        text = str(item.get(key) or "").strip()
        if text:
            return text
    return ""


OUTPUT_CONTRACT: dict[str, Any] = {
    "subject_lines": "array of exactly 5 strings; each 5–9 words; role- or company-specific; no hype",
    "primary_email": {
        "subject": "string — chosen subject line",
        "body": "string — full email body (80–130 words)",
    },
    "variation_1": {
        "subject": "string — same or alternate subject",
        "body": "string — same structure, different angle or opener than primary",
    },
    "variation_2": {
        "subject": "string — same or alternate subject",
        "body": "string — softer or more direct tone than variation_1",
    },
    "metadata": {
        "product_used": "product name from the portfolio, or 'general capability'",
        "pain_point": "one-line summary of the pain point used",
        "evidence_used": "specific news or context detail used — empty string if none",
        "confidence": "low | medium | high",
        "why_now": "one sentence on why this is timely for this prospect",
    },
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


def _format_news_context(news_context: Sequence[Mapping[str, Any]] | Mapping[str, Any] | str | None) -> str:
    if not news_context:
        return "No scraped company or news context was provided."

    if isinstance(news_context, str):
        return _clean(news_context, max_chars=24_000)

    if isinstance(news_context, Mapping):
        blob = json.dumps(news_context, ensure_ascii=False, indent=2)
        return blob[:24_000] if len(blob) > 24_000 else blob

    bullets = []
    for item in news_context[:14]:
        if not isinstance(item, Mapping):
            continue
        title = _clean(item.get("title") or item.get("summary") or item.get("theme"), max_chars=220)
        snippet = _clean(best_evidence_body(item), max_chars=8_000)
        url = _clean(item.get("url") or item.get("source_url"), max_chars=220)
        if title or snippet:
            bullets.append({"title": title, "snippet": snippet, "url": url})

    if not bullets:
        return "No usable scraped company or news context was provided."
    serialised = json.dumps(bullets, ensure_ascii=False, indent=2)
    # Cap whole block so system prompt plus user context stays within typical model limits.
    return serialised[:24_000] if len(serialised) > 24_000 else serialised


def build_email_generation_prompt(
    row: Mapping[str, Any],
    news_context: Sequence[Mapping[str, Any]] | Mapping[str, Any] | str | None = None,
    *,
    website_url: str = "",
    additional_context: str = "",
) -> list[dict[str, str]]:
    """Build Ollama chat messages for personalised email generation.

    Keep this module deliberately boring and easy to edit. The generator script
    imports only this function, so future prompt experiments can happen here.
    """

    first_name = _row_value(row, "First Name", "first_name", "first")
    last_name = _row_value(row, "Last Name", "last_name", "last")
    company = _row_value(row, "Company Name", "company", "company_name", "organisation", "organization")
    position = _row_value(row, "Position", "title", "job_title", "role")
    email = _row_value(row, "Email", "email_address")
    industry = _row_value(row, "Industry", "industry", "sector", "vertical")

    template = get_system_prompt_template()
    contract_json = json.dumps(OUTPUT_CONTRACT, ensure_ascii=False, indent=2)
    system_prompt = template.replace("{OUTPUT_CONTRACT_JSON}", contract_json)

    # Build the prospect details block
    prospect_lines = [
        f"- First name:    {first_name or 'unknown'}",
        f"- Last name:     {last_name or 'unknown'}",
        f"- Company:       {company or 'unknown'}",
        f"- Position/role: {position or 'unknown'}",
        f"- Industry:      {industry or 'unknown'}",
        f"- Email:         {email or 'unknown'}",
    ]
    if website_url.strip():
        prospect_lines.append(f"- Website:       {website_url.strip()}")

    prospect_block = "\n".join(prospect_lines)

    # Build additional context block (user-provided notes — high priority)
    additional_block = ""
    extra = (additional_context or "").strip()
    if extra:
        additional_block = f"""

USER-PROVIDED NOTES (treat as high-priority personalisation signals — use these
observations to shape your angle, opener, or pain point):
{extra}"""

    user_prompt = f"""Generate the JSON package for this prospect.

PROSPECT DETAILS
{prospect_block}
{additional_block}

RESEARCHED COMPANY & NEWS CONTEXT (use the most relevant details; if context is weak
or generic, prefer cautious phrasing and "teams like yours" rather than inventing facts):
{_format_news_context(news_context)}

INSTRUCTIONS
- Use the prospect details and any context above to personalise the opener and pain point.
- If a website snippet or news item reveals a specific challenge, reference it concretely.
- Match at most one product from the portfolio to the pain point. If nothing fits cleanly,
  use general capability only.
- Never reference scraping, AI prompts, models, or datasets in the email text itself.
- Address the prospect by first name in the greeting (use "Hi [First Name],")."""

    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]
