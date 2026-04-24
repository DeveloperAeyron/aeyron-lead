#!/usr/bin/env python3
from __future__ import annotations

import argparse
import asyncio
import base64
import json
import math
import os
import re
import sys
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any
from urllib.parse import parse_qs, quote_plus, unquote, urlparse, urlunparse


DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/126.0.0.0 Safari/537.36"
)

BLOCKED_RESULT_HOSTS = {
    "bing.com",
    "www.bing.com",
    "duckduckgo.com",
    "www.duckduckgo.com",
    "go.microsoft.com",
    "support.microsoft.com",
    "search.brave.com",
    "yahoo.com",
    "search.yahoo.com",
    "r.search.yahoo.com",
}

TRACKING_QUERY_KEYS = {
    "utm_source",
    "utm_medium",
    "utm_campaign",
    "utm_term",
    "utm_content",
    "fbclid",
    "gclid",
    "msclkid",
    "ocid",
}


@dataclass
class SearchResult:
    company: str
    kind: str
    source: str
    rank: int
    title: str
    url: str
    snippet: str = ""
    raw_text: str = ""
    search_url: str = ""
    query: str = ""
    published: str = ""
    score: float = 0.0
    fetched_text: str = ""
    hf_summary: str = ""
    hf_relevance: float | None = None


@dataclass
class LinkedInResult:
    company: str
    profile_type: str
    source: str
    rank: int
    name: str
    headline: str
    url: str
    slug: str = ""
    snippet: str = ""
    evidence_text: str = ""
    search_url: str = ""
    query: str = ""
    matched_company_terms: list[str] = field(default_factory=list)
    matched_role_terms: list[str] = field(default_factory=list)
    seniority_level: str = ""
    snippet_chars: int = 0
    snippet_words: int = 0
    evidence_chars: int = 0
    evidence_words: int = 0
    detail_depth: str = "search_result"
    profile_page_status: str = "not_fetched"
    profile_page_text: str = ""
    confidence: float = 0.0
    score: float = 0.0


@dataclass
class InsightItem:
    theme: str
    summary: str
    evidence: str
    source_url: str = ""
    confidence: float = 0.0


@dataclass
class EmailAngle:
    persona: str
    subject: str
    opener: str
    pain_point: str
    why_now: str
    suggested_offer: str
    draft_email: str = ""
    evidence_url: str = ""
    linkedin_contact_hint: str = ""
    confidence: float = 0.0


@dataclass
class CompanyInsights:
    executive_brief: str = ""
    pain_points: list[InsightItem] = field(default_factory=list)
    major_changes: list[InsightItem] = field(default_factory=list)
    buying_triggers: list[InsightItem] = field(default_factory=list)
    email_angles: list[EmailAngle] = field(default_factory=list)
    recommended_contacts: list[LinkedInResult] = field(default_factory=list)


@dataclass
class CompanyReport:
    company: str
    summary: str
    results: list[SearchResult] = field(default_factory=list)
    linkedin: list[LinkedInResult] = field(default_factory=list)
    insights: CompanyInsights = field(default_factory=CompanyInsights)
    errors: list[str] = field(default_factory=list)


def _log(enabled: bool, message: str) -> None:
    if not enabled:
        return
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] {message}", file=sys.stderr, flush=True)


def _collapse_ws(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def _clean_url(raw_url: str) -> str:
    url = (raw_url or "").strip()
    if not url:
        return ""

    if url.startswith("//"):
        url = "https:" + url

    parsed = urlparse(url)

    # DuckDuckGo redirect links look like /l/?uddg=<encoded target>.
    qs = parse_qs(parsed.query)
    for key in ("uddg", "u", "url"):
        if key in qs and qs[key]:
            candidate = unquote(qs[key][0])
            if candidate.startswith(("http://", "https://")):
                url = candidate
                parsed = urlparse(url)
                qs = parse_qs(parsed.query)
                break

    # Bing can emit wrapped URLs in query params on some layouts.
    if parsed.netloc.endswith("bing.com"):
        for key in ("u", "url"):
            if key in qs and qs[key]:
                candidate = unquote(qs[key][0])
                if candidate.startswith("a1"):
                    decoded = _decode_bing_target(candidate)
                    if decoded:
                        candidate = decoded
                if candidate.startswith(("http://", "https://")):
                    url = candidate
                    parsed = urlparse(url)
                    qs = parse_qs(parsed.query)
                    break

    filtered_query = []
    for key, values in parse_qs(parsed.query, keep_blank_values=True).items():
        if key.lower() in TRACKING_QUERY_KEYS:
            continue
        for value in values:
            filtered_query.append((key, value))

    query = "&".join(
        f"{quote_plus(str(key))}={quote_plus(str(value))}" for key, value in filtered_query
    )
    cleaned = parsed._replace(query=query, fragment="")
    return urlunparse(cleaned)


def _decode_bing_target(value: str) -> str:
    encoded = value[2:] if value.startswith("a1") else value
    try:
        padded = encoded + ("=" * (-len(encoded) % 4))
        decoded = base64.urlsafe_b64decode(padded.encode("ascii")).decode("utf-8", errors="ignore")
    except Exception:
        return ""
    return decoded if decoded.startswith(("http://", "https://")) else ""


def _host(url: str) -> str:
    return (urlparse(url).netloc or "").lower().removeprefix("www.")


def _is_linkedin_url(url: str) -> bool:
    parsed = urlparse(url)
    host = (parsed.netloc or "").lower()
    if not host.endswith("linkedin.com"):
        return False
    path = parsed.path.rstrip("/")
    return path.startswith(("/in/", "/company/", "/pub/"))


def _linkedin_profile_type(url: str) -> str:
    path = urlparse(url).path
    if path.startswith("/in/") or path.startswith("/pub/"):
        return "person"
    if path.startswith("/company/"):
        return "company"
    return "other"


def _linkedin_slug(url: str) -> str:
    parts = [part for part in urlparse(url).path.split("/") if part]
    if len(parts) >= 2 and parts[0] in {"in", "pub", "company"}:
        return parts[1]
    return ""


def _is_probable_result(url: str, title: str) -> bool:
    if not url.startswith(("http://", "https://")):
        return False
    host = _host(url)
    if not host or host in BLOCKED_RESULT_HOSTS:
        return False
    if len(_collapse_ws(title)) < 4:
        return False
    if any(host.endswith(blocked) for blocked in ("bing.com", "duckduckgo.com", "search.brave.com", "search.yahoo.com")):
        return False
    return True


def _normalise_title(title: str) -> str:
    title = re.sub(r"[^a-z0-9\s]", " ", title.lower())
    title = re.sub(r"\b(the|a|an|and|or|of|to|for|in|on|with|by|from|at)\b", " ", title)
    return _collapse_ws(title)


def _token_set(value: str) -> set[str]:
    return {token for token in re.findall(r"[a-z0-9]+", value.lower()) if len(token) > 2}


def _looks_duplicate(a: SearchResult, b: SearchResult) -> bool:
    a_url = urlparse(a.url)
    b_url = urlparse(b.url)
    if a_url.netloc == b_url.netloc and a_url.path.rstrip("/") == b_url.path.rstrip("/"):
        return True

    a_title = _normalise_title(a.title)
    b_title = _normalise_title(b.title)
    if not a_title or not b_title:
        return False

    a_tokens = _token_set(a_title)
    b_tokens = _token_set(b_title)
    if not a_tokens or not b_tokens:
        return False
    overlap = len(a_tokens & b_tokens) / len(a_tokens | b_tokens)
    return overlap >= 0.82


def _dedupe(results: list[SearchResult]) -> list[SearchResult]:
    unique: list[SearchResult] = []
    for item in results:
        if any(_looks_duplicate(item, existing) for existing in unique):
            continue
        unique.append(item)
    return unique


def _dedupe_linkedin(results: list[LinkedInResult]) -> list[LinkedInResult]:
    unique: list[LinkedInResult] = []
    seen_urls: set[str] = set()
    for item in sorted(results, key=lambda value: value.score, reverse=True):
        key = urlparse(item.url)._replace(query="", fragment="").geturl().rstrip("/")
        if key in seen_urls:
            continue
        if any(item.name.lower() == existing.name.lower() and item.profile_type == existing.profile_type for existing in unique):
            continue
        seen_urls.add(key)
        unique.append(item)
    return unique


def _parse_recency_hint(value: str) -> float:
    text = value.lower()
    if not text:
        return 0.0
    if any(word in text for word in ("minute", "hour", "today")):
        return 2.0
    if "yesterday" in text:
        return 1.5
    match = re.search(r"(\d+)\s*(day|week|month|year)s?\s+ago", text)
    if not match:
        return 0.0
    amount = int(match.group(1))
    unit = match.group(2)
    if unit == "day":
        return max(0.0, 1.5 - amount / 10)
    if unit == "week":
        return max(0.0, 1.0 - amount / 8)
    if unit == "month":
        return max(0.0, 0.5 - amount / 12)
    return 0.0


def _score_result(company: str, result: SearchResult) -> float:
    query_terms = _token_set(company)
    haystack = f"{result.title} {result.snippet}".lower()
    term_hits = sum(1 for term in query_terms if term in haystack)
    title_bonus = 1.5 if any(term in result.title.lower() for term in query_terms) else 0.0
    kind_bonus = 1.0 if result.kind == "news" else 0.2
    freshness_bonus = _parse_recency_hint(result.published)
    rank_penalty = math.log1p(max(result.rank - 1, 0)) * 0.35
    return round(term_hits + title_bonus + kind_bonus + freshness_bonus - rank_penalty, 4)


def _score_linkedin(company: str, result: SearchResult) -> float:
    query_terms = _token_set(company)
    haystack = f"{result.title} {result.snippet}".lower()
    term_hits = sum(1 for term in query_terms if term in haystack)
    seniority_terms = {
        "founder",
        "cofounder",
        "co-founder",
        "ceo",
        "chief",
        "president",
        "owner",
        "partner",
        "director",
        "head",
        "vp",
        "vice president",
        "manager",
        "lead",
    }
    seniority_bonus = 1.0 if any(term in haystack for term in seniority_terms) else 0.0
    type_bonus = 1.0 if _linkedin_profile_type(result.url) == "person" else 0.5
    rank_penalty = math.log1p(max(result.rank - 1, 0)) * 0.25
    return round(term_hits + seniority_bonus + type_bonus - rank_penalty, 4)


ROLE_TERMS = {
    "founder": "executive",
    "cofounder": "executive",
    "co-founder": "executive",
    "ceo": "executive",
    "chief": "executive",
    "president": "executive",
    "owner": "executive",
    "partner": "executive",
    "director": "senior",
    "head": "senior",
    "vp": "senior",
    "vice president": "senior",
    "manager": "manager",
    "lead": "lead",
    "recruiter": "recruiting",
    "talent": "recruiting",
    "people": "people",
    "hr": "people",
    "sales": "sales",
    "business development": "sales",
    "marketing": "marketing",
    "engineer": "technical",
    "research": "technical",
}


INSIGHT_THEMES: dict[str, list[str]] = {
    "growth_or_funding": [
        "funding",
        "raises",
        "raised",
        "valuation",
        "growth",
        "expansion",
        "hiring",
        "new office",
        "scale",
    ],
    "product_or_platform_change": [
        "launch",
        "launched",
        "unveils",
        "released",
        "upgrade",
        "platform",
        "integration",
        "workspace",
        "agent",
        "api",
    ],
    "leadership_change": [
        "appoints",
        "appointed",
        "joins",
        "ceo",
        "chief",
        "president",
        "founder",
        "leadership",
        "executive",
    ],
    "market_pressure": [
        "competition",
        "competitor",
        "surpass",
        "overtake",
        "market cap",
        "demand",
        "pressure",
        "customers",
    ],
    "risk_or_regulation": [
        "lawsuit",
        "regulation",
        "regulatory",
        "privacy",
        "security",
        "compliance",
        "risk",
        "ban",
        "probe",
    ],
    "cost_or_efficiency": [
        "layoff",
        "cuts",
        "cost",
        "efficiency",
        "profit",
        "margin",
        "restructure",
        "automation",
    ],
    "partnership_or_acquisition": [
        "partner",
        "partnership",
        "acquire",
        "acquisition",
        "merger",
        "invests",
        "investment",
    ],
}


THEME_EMAIL_OFFERS = {
    "growth_or_funding": "a quick plan for scaling outbound and account research without adding manual workload",
    "product_or_platform_change": "a way to turn the launch into targeted account messaging for the right buyer segments",
    "leadership_change": "a concise executive brief showing where new leadership can find near-term pipeline leverage",
    "market_pressure": "competitive account intelligence that helps prioritize high-intent segments before rivals do",
    "risk_or_regulation": "a research-backed messaging map that addresses trust, risk, and compliance objections",
    "cost_or_efficiency": "a workflow to personalize prospecting while reducing manual research time",
    "partnership_or_acquisition": "partner/account mapping to identify new warm-intro and expansion opportunities",
}


def _matched_terms(terms: set[str] | list[str], text: str) -> list[str]:
    haystack = text.lower()
    return sorted({term for term in terms if term and term.lower() in haystack})


def _seniority_level(role_terms: list[str]) -> str:
    levels = [ROLE_TERMS.get(term, "") for term in role_terms]
    if "executive" in levels:
        return "executive"
    if "senior" in levels:
        return "senior"
    if "manager" in levels:
        return "manager"
    if "lead" in levels:
        return "lead"
    if any(level for level in levels):
        return "specialist"
    return "unknown"


def _confidence(company_terms: list[str], role_terms: list[str], evidence_words: int, profile_type: str) -> float:
    score = 0.15
    score += min(len(company_terms), 3) * 0.18
    score += 0.2 if role_terms else 0.0
    score += 0.15 if evidence_words >= 18 else 0.05 if evidence_words >= 8 else 0.0
    score += 0.1 if profile_type == "person" else 0.05 if profile_type == "company" else 0.0
    return round(min(score, 0.98), 4)


def _parse_linkedin_title(title: str) -> tuple[str, str]:
    clean = re.sub(r"\s*\|\s*LinkedIn\s*$", "", title, flags=re.I)
    clean = re.sub(r"\s*-\s*LinkedIn\s*$", "", clean, flags=re.I)
    parts = [_collapse_ws(part) for part in re.split(r"\s+-\s+", clean) if _collapse_ws(part)]
    if not parts:
        return clean, ""
    name = parts[0]
    headline = " - ".join(parts[1:])
    return name, headline


def _to_linkedin_result(company: str, item: SearchResult, query: str) -> LinkedInResult:
    name, headline = _parse_linkedin_title(item.title)
    profile_type = _linkedin_profile_type(item.url)
    evidence = _collapse_ws(item.raw_text or f"{item.title}. {item.snippet}")
    snippet_words = len(item.snippet.split())
    evidence_words = len(evidence.split())
    company_terms = _matched_terms(_token_set(company), evidence)
    role_terms = _matched_terms(list(ROLE_TERMS), evidence)
    seniority = _seniority_level(role_terms)
    score = _score_linkedin(company, item)
    return LinkedInResult(
        company=company,
        profile_type=profile_type,
        source=item.source,
        rank=item.rank,
        name=name,
        headline=headline,
        url=item.url,
        slug=_linkedin_slug(item.url),
        snippet=item.snippet,
        evidence_text=evidence[:1800],
        search_url=item.search_url,
        query=query,
        matched_company_terms=company_terms,
        matched_role_terms=role_terms,
        seniority_level=seniority,
        snippet_chars=len(item.snippet),
        snippet_words=snippet_words,
        evidence_chars=len(evidence),
        evidence_words=evidence_words,
        detail_depth="search_result_full_container" if evidence_words > snippet_words else "search_result_snippet",
        confidence=_confidence(company_terms, role_terms, evidence_words, profile_type),
        score=score,
    )


async def _extract_search_results(
    page: Any,
    *,
    company: str,
    kind: str,
    source: str,
    limit: int,
) -> list[SearchResult]:
    raw_results = await page.evaluate(
        """
        () => {
          const containers = Array.from(document.querySelectorAll(
            [
              'li.b_algo',
              'div.news-card',
              'div.newsitem',
              'article',
              'div.result',
              'div.snippet',
              'div.fdb',
              'ol.searchCenterMiddle li',
              'div[data-testid="result"]',
              'li'
            ].join(',')
          ));

          const picked = [];
          const seenNodes = new Set();

          function textOf(node) {
            return (node && node.innerText ? node.innerText : '')
              .replace(/\\s+/g, ' ')
              .trim();
          }

          function firstText(node, selectors) {
            for (const selector of selectors) {
              const found = node.querySelector(selector);
              const text = textOf(found);
              if (text) return text;
            }
            return '';
          }

          function addFromNode(node) {
            if (!node || seenNodes.has(node)) return;
            seenNodes.add(node);

            const a = node.querySelector('a[href]');
            if (!a) return;

            const title =
              firstText(node, ['h1', 'h2', 'h3', '.title', '.result__title', 'a']) ||
              textOf(a);
            const snippet =
              firstText(node, ['p', '.b_caption', '.snippet', '.result__snippet', '.news-card-snippet']) ||
              '';
            const published =
              firstText(node, ['time', '.source', '.news-source', '.caption', 'cite']) ||
              '';
            const rawText = textOf(node);

            picked.push({
              title,
              url: a.href || '',
              snippet,
              published,
              rawText
            });
          }

          for (const node of containers) addFromNode(node);

          if (picked.length < 3) {
            for (const a of Array.from(document.querySelectorAll('a[href]'))) {
              const title = textOf(a);
              const parent = a.closest('article, li, div') || a.parentElement;
              picked.push({
                title,
                url: a.href || '',
                snippet: textOf(parent).replace(title, '').trim(),
                published: '',
                rawText: textOf(parent)
              });
            }
          }

          return picked;
        }
        """
    )

    results: list[SearchResult] = []
    for item in raw_results:
        title = _collapse_ws(str(item.get("title", "")))
        url = _clean_url(str(item.get("url", "")))
        snippet = _collapse_ws(str(item.get("snippet", "")))
        raw_text = _collapse_ws(str(item.get("rawText", "")))
        published = _collapse_ws(str(item.get("published", "")))
        if not _is_probable_result(url, title):
            continue
        result = SearchResult(
            company=company,
            kind=kind,
            source=source,
            rank=len(results) + 1,
            title=title,
            url=url,
            snippet=snippet[:900],
            raw_text=raw_text[:3000],
            published=published[:220],
        )
        result.score = _score_result(company, result)
        if kind == "web" and result.score < 0.8:
            continue
        if kind == "news" and result.score < 0.5:
            continue
        results.append(result)
        if len(results) >= limit:
            break
    return results


async def _search_source(
    page: Any,
    *,
    company: str,
    kind: str,
    source: str,
    url: str,
    query: str = "",
    limit: int,
    timeout_ms: int,
    verbose: bool,
) -> list[SearchResult]:
    _log(verbose, f"{company}: searching {source} {kind}")
    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
        await page.wait_for_timeout(900)
        results = await _extract_search_results(
            page,
            company=company,
            kind=kind,
            source=source,
            limit=limit,
        )
        for item in results:
            item.search_url = url
            item.query = query
        return results
    except Exception as exc:
        if exc.__class__.__name__ == "TimeoutError":
            _log(verbose, f"{company}: timeout from {source} {kind}")
        else:
            _log(verbose, f"{company}: {source} {kind} failed: {type(exc).__name__}: {exc}")
    return []


def _source_urls(company: str) -> list[tuple[str, str, str, str]]:
    web_query = quote_plus(f'"{company}" company official recent')
    news_query = quote_plus(f'"{company}" news recent')
    return [
        ("web", "duckduckgo", f"https://duckduckgo.com/html/?q={web_query}", "DuckDuckGo web"),
        ("web", "brave", f"https://search.brave.com/search?q={web_query}&source=web", "Brave web"),
        ("web", "yahoo", f"https://search.yahoo.com/search?p={web_query}", "Yahoo web"),
        ("web", "bing", f"https://www.bing.com/search?q={web_query}", "Bing web"),
        ("news", "bing_news", f"https://www.bing.com/news/search?q={news_query}", "Bing News"),
    ]


def _linkedin_source_urls(company: str) -> list[tuple[str, str, str, str, str]]:
    people_queries = [
        f'site:linkedin.com/in "{company}" CEO Founder Owner President Director Manager',
        f'"{company}" LinkedIn CEO Founder Owner President Director Manager',
        f'"{company}" "people" "LinkedIn"',
    ]
    company_queries = [
        f'site:linkedin.com/company "{company}"',
        f'"{company}" LinkedIn company page',
    ]
    queries = [
        *[("linkedin_people", query, "LinkedIn people") for query in people_queries],
        *[("linkedin_company", query, "LinkedIn company") for query in company_queries],
    ]

    urls: list[tuple[str, str, str, str, str]] = []
    for kind, query, label in queries:
        encoded = quote_plus(query)
        urls.extend(
            [
                (kind, "bing", f"https://www.bing.com/search?q={encoded}", label, query),
                (kind, "yahoo", f"https://search.yahoo.com/search?p={encoded}", label, query),
            ]
        )
    return urls


async def _fetch_page_text(page: Any, url: str, *, timeout_ms: int) -> str:
    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
        await page.wait_for_timeout(700)
        text = await page.evaluate(
            """
            () => {
              for (const selector of ['script', 'style', 'noscript', 'svg', 'nav', 'footer']) {
                for (const node of document.querySelectorAll(selector)) node.remove();
              }
              const article = document.querySelector('article, main, [role="main"]');
              const source = article || document.body;
              return source ? source.innerText : '';
            }
            """
        )
        return _collapse_ws(str(text))[:12_000]
    except Exception:
        return ""


async def _fetch_linkedin_profile_text(page: Any, url: str, *, timeout_ms: int) -> tuple[str, str]:
    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
        await page.wait_for_timeout(900)
        text = await page.evaluate(
            """
            () => {
              const meta = Array.from(document.querySelectorAll('meta[name], meta[property]'))
                .map((m) => `${m.getAttribute('name') || m.getAttribute('property')}: ${m.getAttribute('content') || ''}`)
                .filter((v) => v.trim().length > 5)
                .slice(0, 25)
                .join(' | ');
              const body = (document.body && document.body.innerText ? document.body.innerText : '')
                .replace(/\\s+/g, ' ')
                .trim();
              return [meta, body].filter(Boolean).join(' | ');
            }
            """
        )
        clean = _collapse_ws(str(text))
        if not clean:
            return "empty", ""
        lowered = clean.lower()
        if "sign in" in lowered and "linkedin" in lowered and len(clean.split()) < 120:
            return "login_wall", clean[:3000]
        return "public_text", clean[:5000]
    except Exception as exc:
        return f"fetch_failed:{type(exc).__name__}", ""


class HuggingFaceClient:
    def __init__(
        self,
        *,
        token: str | None,
        summarization_model: str,
        zero_shot_model: str,
        timeout_s: int,
        disabled: bool,
    ) -> None:
        self.token = token
        self.summarization_model = summarization_model
        self.zero_shot_model = zero_shot_model
        self.timeout_s = timeout_s
        self.disabled = disabled

    @property
    def enabled(self) -> bool:
        return bool(self.token) and not self.disabled

    def _post(self, model: str, payload: dict[str, Any]) -> Any:
        if not self.enabled:
            return None
        try:
            import requests
        except ModuleNotFoundError as exc:
            raise SystemExit(
                'Missing dependency "requests" for Hugging Face calls. Install backend deps:\n'
                "  pip install -r backend/requirements.txt\n"
                "Or run with --no-hf."
            ) from exc

        response = requests.post(
            f"https://api-inference.huggingface.co/models/{model}",
            headers={"Authorization": f"Bearer {self.token}"},
            json={**payload, "options": {"wait_for_model": True}},
            timeout=self.timeout_s,
        )
        response.raise_for_status()
        return response.json()

    def summarize(self, text: str, *, max_chars: int = 10_000) -> str:
        text = _collapse_ws(text)[:max_chars]
        if not text:
            return ""
        if not self.enabled:
            return _fallback_summary(text)

        try:
            data = self._post(
                self.summarization_model,
                {
                    "inputs": text,
                    "parameters": {
                        "max_length": 180,
                        "min_length": 35,
                        "do_sample": False,
                    },
                },
            )
            if isinstance(data, list) and data and isinstance(data[0], dict):
                return _collapse_ws(str(data[0].get("summary_text", "")))
            if isinstance(data, dict) and "summary_text" in data:
                return _collapse_ws(str(data["summary_text"]))
        except Exception:
            return _fallback_summary(text)
        return _fallback_summary(text)

    def relevance(self, *, company: str, text: str) -> float | None:
        text = _collapse_ws(text)[:1800]
        if not text or not self.enabled:
            return None
        try:
            data = self._post(
                self.zero_shot_model,
                {
                    "inputs": text,
                    "parameters": {
                        "candidate_labels": [
                            f"about {company}",
                            "not about the company",
                        ],
                        "multi_label": False,
                    },
                },
            )
            if isinstance(data, dict):
                labels = data.get("labels") or []
                scores = data.get("scores") or []
                for label, score in zip(labels, scores):
                    if str(label).startswith("about "):
                        return round(float(score), 4)
        except Exception:
            return None
        return None


def _fallback_summary(text: str) -> str:
    sentences = re.split(r"(?<=[.!?])\s+", text)
    clean = [_collapse_ws(sentence) for sentence in sentences if len(sentence.split()) >= 7]
    if not clean:
        return _collapse_ws(text)[:500]
    return " ".join(clean[:4])[:900]


def _build_company_summary(company: str, results: list[SearchResult], hf: HuggingFaceClient) -> str:
    if not results:
        return f"No search results were collected for {company}."

    parts = []
    for item in results[:12]:
        body = item.fetched_text or item.snippet
        parts.append(f"{item.kind.upper()}: {item.title}. {body}")
    return hf.summarize("\n".join(parts), max_chars=12_000)


def _result_evidence(item: SearchResult) -> str:
    return _collapse_ws(
        " ".join(
            part
            for part in [
                item.title,
                item.snippet,
                item.raw_text,
                item.fetched_text[:2500] if item.fetched_text else "",
            ]
            if part
        )
    )


def _theme_hits(text: str) -> list[str]:
    lowered = text.lower()
    hits = []
    for theme, keywords in INSIGHT_THEMES.items():
        if any(keyword in lowered for keyword in keywords):
            hits.append(theme)
    return hits


def _short_evidence(text: str, *, max_chars: int = 360) -> str:
    clean = _collapse_ws(text)
    if len(clean) <= max_chars:
        return clean
    return clean[: max_chars - 3].rstrip() + "..."


def _insight_confidence(item: SearchResult, theme: str, evidence: str) -> float:
    confidence = 0.35
    if item.kind == "news":
        confidence += 0.15
    if item.fetched_text:
        confidence += 0.15
    if item.raw_text or item.snippet:
        confidence += 0.1
    keyword_hits = sum(1 for keyword in INSIGHT_THEMES.get(theme, []) if keyword in evidence.lower())
    confidence += min(keyword_hits, 3) * 0.08
    if item.score >= 3:
        confidence += 0.08
    return round(min(confidence, 0.95), 4)


def _make_insight_item(company: str, item: SearchResult, theme: str) -> InsightItem:
    evidence = _result_evidence(item)
    theme_label = theme.replace("_", " ")
    summary = f"{company} shows a {theme_label} signal: {item.title}"
    return InsightItem(
        theme=theme,
        summary=summary,
        evidence=_short_evidence(evidence),
        source_url=item.url,
        confidence=_insight_confidence(item, theme, evidence),
    )


def _pick_contacts(linkedin: list[LinkedInResult], theme: str) -> list[LinkedInResult]:
    preferred_terms = {
        "growth_or_funding": {"sales", "business development", "chief", "ceo", "president", "director", "vp"},
        "product_or_platform_change": {"product", "engineer", "research", "chief", "director", "head", "lead"},
        "leadership_change": {"ceo", "chief", "president", "founder", "director"},
        "market_pressure": {"sales", "marketing", "business development", "director", "vp", "chief"},
        "risk_or_regulation": {"chief", "security", "privacy", "legal", "compliance", "director"},
        "cost_or_efficiency": {"operations", "manager", "director", "head", "chief"},
        "partnership_or_acquisition": {"partner", "business development", "sales", "director", "vp"},
    }.get(theme, {"ceo", "chief", "director", "manager", "head"})

    scored = []
    for contact in linkedin:
        text = f"{contact.name} {contact.headline} {contact.snippet}".lower()
        role_bonus = sum(1 for term in preferred_terms if term in text)
        type_bonus = 1 if contact.profile_type == "person" else 0
        scored.append((role_bonus + type_bonus + contact.confidence, contact))
    return [contact for _score, contact in sorted(scored, key=lambda pair: pair[0], reverse=True)[:3]]


def _make_email_angle(company: str, insight: InsightItem, contacts: list[LinkedInResult]) -> EmailAngle:
    theme_label = insight.theme.replace("_", " ")
    offer = THEME_EMAIL_OFFERS.get(
        insight.theme,
        "a short research-backed outreach idea based on the latest company signals",
    )
    contact = contacts[0] if contacts else None
    persona = contact.headline or contact.seniority_level or "relevant leader" if contact else "relevant leader"
    contact_hint = ""
    if contact:
        contact_hint = f"{contact.name} ({contact.headline or contact.profile_type}) - {contact.url}"
    recipient = contact.name if contact else "there"
    draft_email = (
        f"Hi {recipient},\n\n"
        f"{company} caught my attention because of this recent signal: {insight.evidence}\n\n"
        f"That usually creates a window where teams need {offer}. "
        "I can put together a short account-research brief with the highest-fit segments, "
        "relevant trigger events, and a few personalized outbound angles your team could test.\n\n"
        "Worth a quick look?"
    )
    return EmailAngle(
        persona=persona,
        subject=f"Idea after {company}'s recent {theme_label} signal",
        opener=f"Saw this recent signal about {company}: {insight.evidence}",
        pain_point=insight.summary,
        why_now=f"This matters now because the signal suggests active {theme_label.replace('_', ' ')} priorities.",
        suggested_offer=offer,
        draft_email=draft_email,
        evidence_url=insight.source_url,
        linkedin_contact_hint=contact_hint,
        confidence=insight.confidence,
    )


def _build_insights(
    company: str,
    results: list[SearchResult],
    linkedin: list[LinkedInResult],
    hf: HuggingFaceClient,
) -> CompanyInsights:
    theme_items: dict[str, list[InsightItem]] = {}
    for item in results:
        evidence = _result_evidence(item)
        for theme in _theme_hits(evidence):
            theme_items.setdefault(theme, []).append(_make_insight_item(company, item, theme))

    for theme in list(theme_items):
        theme_items[theme] = sorted(theme_items[theme], key=lambda value: value.confidence, reverse=True)[:3]

    major_change_themes = {
        "growth_or_funding",
        "product_or_platform_change",
        "leadership_change",
        "partnership_or_acquisition",
    }
    pain_point_themes = {
        "market_pressure",
        "risk_or_regulation",
        "cost_or_efficiency",
        "product_or_platform_change",
        "growth_or_funding",
    }

    major_changes = [
        item
        for theme in major_change_themes
        for item in theme_items.get(theme, [])
    ][:6]
    pain_points = [
        item
        for theme in pain_point_themes
        for item in theme_items.get(theme, [])
    ][:6]
    buying_triggers = sorted(
        [item for items in theme_items.values() for item in items],
        key=lambda value: value.confidence,
        reverse=True,
    )[:8]

    recommended_contacts = sorted(
        [contact for contact in linkedin if contact.profile_type == "person"],
        key=lambda value: (value.confidence, value.score),
        reverse=True,
    )[:6]

    email_angles = []
    for insight in buying_triggers[:5]:
        contacts = _pick_contacts(recommended_contacts, insight.theme)
        email_angles.append(_make_email_angle(company, insight, contacts))

    brief_source = " ".join(
        [f"{item.theme}: {item.summary}. Evidence: {item.evidence}" for item in buying_triggers[:6]]
    )
    executive_brief = hf.summarize(brief_source, max_chars=8000) if brief_source else ""
    if not executive_brief and buying_triggers:
        executive_brief = " ".join(item.summary for item in buying_triggers[:3])

    return CompanyInsights(
        executive_brief=executive_brief,
        pain_points=pain_points,
        major_changes=major_changes,
        buying_triggers=buying_triggers,
        email_angles=email_angles,
        recommended_contacts=recommended_contacts,
    )


async def _collect_company(
    browser_context: Any,
    *,
    company: str,
    per_source_limit: int,
    final_limit: int,
    timeout_ms: int,
    fetch_pages: bool,
    fetch_page_limit: int,
    linkedin: bool,
    linkedin_limit: int,
    linkedin_fetch_pages: bool,
    hf: HuggingFaceClient,
    hf_relevance: bool,
    verbose: bool,
) -> CompanyReport:
    errors: list[str] = []
    collected: list[SearchResult] = []
    linkedin_results: list[LinkedInResult] = []
    for kind, source, url, label in _source_urls(company):
        page = await browser_context.new_page()
        try:
            source_results = await _search_source(
                page,
                company=company,
                kind=kind,
                source=source,
                url=url,
                limit=per_source_limit,
                timeout_ms=timeout_ms,
                verbose=verbose,
            )
            if not source_results:
                errors.append(f"No results from {label}.")
            collected.extend(source_results)
        finally:
            await page.close()

    if linkedin:
        for kind, source, url, label, query in _linkedin_source_urls(company):
            page = await browser_context.new_page()
            try:
                scan_limit = max(linkedin_limit * 8, 25, per_source_limit)
                source_results = await _search_source(
                    page,
                    company=company,
                    kind=kind,
                    source=source,
                    url=url,
                    query=query,
                    limit=scan_limit,
                    timeout_ms=timeout_ms,
                    verbose=verbose,
                )
                filtered = [
                    _to_linkedin_result(company, item, query)
                    for item in source_results
                    if _is_linkedin_url(item.url)
                ]
                if not filtered:
                    errors.append(f"No results from {label} via {source}.")
                linkedin_results.extend(filtered)
            finally:
                await page.close()

    collected = _dedupe(sorted(collected, key=lambda item: item.score, reverse=True))
    collected = collected[:final_limit]
    linkedin_results = _dedupe_linkedin(linkedin_results)[:linkedin_limit]

    if linkedin_fetch_pages and linkedin_results:
        linkedin_page = await browser_context.new_page()
        try:
            for item in linkedin_results:
                _log(verbose, f"{company}: fetching LinkedIn public text for {item.url}")
                status, text = await _fetch_linkedin_profile_text(
                    linkedin_page,
                    item.url,
                    timeout_ms=timeout_ms,
                )
                item.profile_page_status = status
                item.profile_page_text = text
                if text:
                    item.detail_depth = "linkedin_public_page" if status == "public_text" else status
                    item.evidence_chars += len(text)
                    item.evidence_words += len(text.split())
                    extra_roles = _matched_terms(list(ROLE_TERMS), text)
                    item.matched_role_terms = sorted(set(item.matched_role_terms + extra_roles))
                    item.seniority_level = _seniority_level(item.matched_role_terms)
        finally:
            await linkedin_page.close()

    if fetch_pages and collected:
        fetch_page = await browser_context.new_page()
        try:
            for item in collected[:fetch_page_limit]:
                _log(verbose, f"{company}: fetching page text for {item.url}")
                item.fetched_text = await _fetch_page_text(fetch_page, item.url, timeout_ms=timeout_ms)
        finally:
            await fetch_page.close()

    for item in collected:
        if item.fetched_text:
            item.hf_summary = hf.summarize(f"{item.title}. {item.fetched_text}", max_chars=10_000)
        if hf_relevance:
            item.hf_relevance = hf.relevance(
                company=company,
                text=f"{item.title}. {item.snippet}. {item.fetched_text}",
            )

    summary = _build_company_summary(company, collected, hf)
    insights = _build_insights(company, collected, linkedin_results, hf)
    return CompanyReport(
        company=company,
        summary=summary,
        results=collected,
        linkedin=linkedin_results,
        insights=insights,
        errors=errors,
    )


async def _run(args: argparse.Namespace) -> dict[str, Any]:
    try:
        from playwright.async_api import async_playwright
    except ModuleNotFoundError as exc:
        raise SystemExit(
            'Missing dependency "playwright". Install backend deps first:\n'
            "  pip install -r backend/requirements.txt\n"
            "Then install Chromium:\n"
            "  python -m playwright install chromium"
        ) from exc

    token = os.getenv(args.hf_token_env) or os.getenv("HF_TOKEN") or os.getenv("HUGGINGFACEHUB_API_TOKEN")
    hf = HuggingFaceClient(
        token=token,
        summarization_model=args.hf_summarization_model,
        zero_shot_model=args.hf_zero_shot_model,
        timeout_s=args.hf_timeout_s,
        disabled=args.no_hf,
    )

    if not hf.enabled:
        _log(
            args.verbose,
            "Hugging Face token not available or disabled; using local fallback summaries.",
        )

    async with async_playwright() as p:
        try:
            browser = await p.chromium.launch(headless=args.headless and not args.headed)
        except Exception as exc:
            detail = str(exc)
            if (
                "BrowserType.launch" in detail
                or "MachPortRendezvous" in detail
                or "Permission denied" in detail
            ):
                raise SystemExit(
                    "Playwright could not launch Chromium in this environment. "
                    "Run the script from a normal terminal, or grant browser-launch "
                    "permission in the sandbox and try again."
                ) from exc
            raise
        context = await browser.new_context(
            user_agent=DEFAULT_USER_AGENT,
            viewport={"width": 1440, "height": 1000},
            locale="en-US",
        )
        try:
            reports = []
            for company in args.companies:
                clean_company = _collapse_ws(company)
                if not clean_company:
                    continue
                _log(args.verbose, f"Collecting search results for {clean_company}")
                report = await _collect_company(
                    context,
                    company=clean_company,
                    per_source_limit=args.per_source_limit,
                    final_limit=args.limit,
                    timeout_ms=args.timeout_ms,
                    fetch_pages=args.fetch_pages,
                    fetch_page_limit=args.fetch_page_limit,
                    linkedin=not args.no_linkedin,
                    linkedin_limit=args.linkedin_limit,
                    linkedin_fetch_pages=args.linkedin_fetch_pages,
                    hf=hf,
                    hf_relevance=args.hf_relevance,
                    verbose=args.verbose,
                )
                reports.append(report)
        finally:
            await context.close()
            await browser.close()

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "hf_enabled": hf.enabled,
        "companies": [
            {
                "company": report.company,
                "summary": report.summary,
                "errors": report.errors,
                "results": [asdict(item) for item in report.results],
                "linkedin": [asdict(item) for item in report.linkedin],
                "insights": asdict(report.insights),
            }
            for report in reports
        ],
    }


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Backend-only company news/web search script. Uses Playwright to browse "
            "public search pages and Hugging Face for optional NLP summaries/relevance."
        )
    )
    parser.add_argument("companies", nargs="+", help='Company names, e.g. "OpenAI" "Microsoft"')
    parser.add_argument("--limit", type=int, default=12, help="Final result limit per company.")
    parser.add_argument("--per-source-limit", type=int, default=8, help="Result limit per search source.")
    parser.add_argument("--timeout-ms", type=int, default=25_000, help="Playwright page timeout in ms.")
    parser.add_argument("--headless", action="store_true", help="Run Chromium hidden. Default opens a visible browser.")
    parser.add_argument("--headed", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--fetch-pages", action="store_true", help="Fetch top result pages for richer summaries.")
    parser.add_argument("--fetch-page-limit", type=int, default=5, help="How many result pages to fetch.")
    parser.add_argument("--linkedin-limit", type=int, default=12, help="LinkedIn people/company result limit per company.")
    parser.add_argument("--linkedin-fetch-pages", action="store_true", help="Try fetching public LinkedIn pages for extra profile text/status.")
    parser.add_argument("--no-linkedin", action="store_true", help="Disable public LinkedIn result discovery.")
    parser.add_argument("--hf-relevance", action="store_true", help="Use Hugging Face zero-shot relevance scoring.")
    parser.add_argument("--hf-token-env", default="HF_TOKEN", help="Env var containing a Hugging Face token.")
    parser.add_argument("--hf-timeout-s", type=int, default=45, help="Hugging Face request timeout.")
    parser.add_argument(
        "--hf-summarization-model",
        default="facebook/bart-large-cnn",
        help="Hugging Face summarization model.",
    )
    parser.add_argument(
        "--hf-zero-shot-model",
        default="facebook/bart-large-mnli",
        help="Hugging Face zero-shot classification model.",
    )
    parser.add_argument("--no-hf", action="store_true", help="Disable Hugging Face calls.")
    parser.add_argument("--output", help="Optional JSON output file path.")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON.")
    parser.add_argument("--verbose", action="store_true", help="Print progress logs to stderr.")
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = _parse_args(argv)
    start = time.time()
    try:
        payload = asyncio.run(_run(args))
    except RuntimeError as exc:
        if "Executable doesn't exist" in str(exc) or "playwright install" in str(exc):
            raise SystemExit(
                "Playwright Chromium is not installed. Run:\n"
                "  python -m playwright install chromium"
            ) from exc
        raise

    payload["elapsed_s"] = round(time.time() - start, 2)
    json_text = json.dumps(payload, ensure_ascii=False, indent=2 if args.pretty else None)
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(json_text + "\n")
    print(json_text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
