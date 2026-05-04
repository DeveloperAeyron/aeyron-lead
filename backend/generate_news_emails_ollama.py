#!/usr/bin/env python3
from __future__ import annotations

import argparse
import asyncio
import csv
import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Any, Mapping, Sequence
from urllib.error import URLError
from urllib.request import Request, urlopen

BACKEND_ROOT = Path(__file__).resolve().parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from prompt import build_email_generation_prompt


GENERATED_COLUMNS = [
    "Subject",
    "Email Body",
    "Generated Pain Point",
    "Generated Why Now",
    "Generated Evidence",
    "Generated Offer",
    "Generation Confidence",
    "Generated Alternatives (JSON)",
    "Generation Error",
]


NEWS_ROW_COLUMNS = [
    "news",
    "news context",
    "news_context",
    "company news",
    "company_news",
    "pain point",
    "pain_point",
    "trigger",
    "buying trigger",
    "summary",
]


LEGAL_SUFFIXES = {
    "inc",
    "incorporated",
    "llc",
    "l.l.c",
    "ltd",
    "limited",
    "corp",
    "corporation",
    "company",
    "co",
    "plc",
}


def _log(enabled: bool, message: str) -> None:
    if enabled:
        print(message, file=sys.stderr, flush=True)


def _log_ollama_prompt(enabled: bool, messages: Sequence[Mapping[str, Any]]) -> None:
    """Print the exact chat payload sent to Ollama (stderr) when verbose is enabled."""
    if not enabled:
        return
    print("\n--- Ollama messages (prompt) ---", file=sys.stderr, flush=True)
    for msg in messages:
        role = str(msg.get("role") or "?")
        content = str(msg.get("content") or "")
        print(f"\n[{role.upper()}]", file=sys.stderr, flush=True)
        print(content, file=sys.stderr, flush=True)
    print("\n--- end Ollama messages ---\n", file=sys.stderr, flush=True)


def _clean(value: Any, *, max_chars: int = 1_500) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 3].rstrip() + "..."


def _normalise_company(value: Any) -> str:
    text = str(value or "").lower()
    text = text.replace("&", " and ")
    text = re.sub(r"[^a-z0-9]+", " ", text)
    parts = [p for p in text.split() if p not in LEGAL_SUFFIXES]
    return " ".join(parts).strip()


def _row_value(row: Mapping[str, Any], *keys: str) -> str:
    lower = {str(k).strip().lower(): v for k, v in row.items()}
    for key in keys:
        value = lower.get(key.lower())
        if value not in (None, ""):
            return _clean(value)
    return ""


def _read_csv(path: Path, *, encoding: str) -> list[dict[str, str]]:
    with path.open("r", encoding=encoding, newline="") as f:
        return list(csv.DictReader(f))


def _write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str], *, encoding: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding=encoding, newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def _normalise_ollama_chat_url(value: str) -> str:
    url = (value or "").strip().rstrip("/")
    if not url:
        url = "http://localhost:11434"
    if url.endswith("/api/chat"):
        return url
    return url + "/api/chat"


def _extract_json_object(text: str) -> dict[str, Any]:
    raw = (text or "").strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?", "", raw, flags=re.I).strip()
        raw = re.sub(r"```$", "", raw).strip()
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass

    start = raw.find("{")
    end = raw.rfind("}")
    if start >= 0 and end > start:
        parsed = json.loads(raw[start : end + 1])
        if isinstance(parsed, dict):
            return parsed
    raise ValueError("Ollama response did not contain a JSON object.")


def _ollama_chat(
    *,
    url: str,
    model: str,
    messages: list[dict[str, str]],
    timeout_s: int,
    temperature: float,
) -> dict[str, Any]:
    payload = {
        "model": model,
        "messages": messages,
        "stream": False,
        "format": "json",
        "options": {"temperature": temperature},
    }
    body = json.dumps(payload).encode("utf-8")
    req = Request(
        url,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(req, timeout=timeout_s) as resp:
            data = json.loads(resp.read().decode("utf-8", errors="replace"))
    except TimeoutError as exc:
        raise RuntimeError(
            f"Ollama timed out after {timeout_s}s while generating the email. "
            "Try --timeout-s 300, --context-items 3, or a smaller/faster model."
        ) from exc
    except URLError as exc:
        raise RuntimeError(f"Could not reach Ollama at {url}: {exc}") from exc

    content = ""
    if isinstance(data, dict):
        message = data.get("message")
        if isinstance(message, dict):
            content = str(message.get("content") or "")
        elif "response" in data:
            content = str(data.get("response") or "")
    if not content:
        raise RuntimeError(f"Ollama returned no message content: {data}")
    return _extract_json_object(content)


def _result_to_context(item: Mapping[str, Any]) -> dict[str, str]:
    return {
        "title": _clean(item.get("title") or item.get("summary") or item.get("theme"), max_chars=180),
        "snippet": _clean(
            item.get("snippet") or item.get("evidence") or item.get("fetched_text") or item.get("raw_text"),
            max_chars=550,
        ),
        "url": _clean(item.get("url") or item.get("source_url"), max_chars=220),
    }


def _company_report_context(report: Mapping[str, Any]) -> list[dict[str, str]]:
    context: list[dict[str, str]] = []

    summary = report.get("summary")
    if summary:
        context.append({"title": "Company summary", "snippet": _clean(summary, max_chars=700), "url": ""})

    insights = report.get("insights")
    if isinstance(insights, Mapping):
        for key in ("pain_points", "buying_triggers", "major_changes"):
            items = insights.get(key)
            if not isinstance(items, list):
                continue
            for item in items[:4]:
                if isinstance(item, Mapping):
                    context.append(_result_to_context(item))

    results = report.get("results")
    if isinstance(results, list):
        for item in results[:8]:
            if isinstance(item, Mapping):
                context.append(_result_to_context(item))

    seen: set[str] = set()
    deduped = []
    for item in context:
        key = f"{item.get('title')}|{item.get('snippet')}|{item.get('url')}"
        if key in seen:
            continue
        seen.add(key)
        if item.get("title") or item.get("snippet"):
            deduped.append(item)
    return deduped[:10]


def _trim_news_context(
    context: list[dict[str, str]],
    *,
    max_items: int,
    snippet_chars: int,
) -> list[dict[str, str]]:
    trimmed = []
    for item in context[: max(1, max_items)]:
        trimmed.append(
            {
                "title": _clean(item.get("title"), max_chars=180),
                "snippet": _clean(item.get("snippet"), max_chars=max(120, snippet_chars)),
                "url": _clean(item.get("url"), max_chars=220),
            }
        )
    return trimmed


def _load_news_index(path: Path | None) -> dict[str, list[dict[str, str]]]:
    if not path:
        return {}
    with path.open("r", encoding="utf-8-sig") as f:
        payload = json.load(f)

    reports: list[Mapping[str, Any]] = []
    if isinstance(payload, Mapping):
        companies = payload.get("companies")
        if isinstance(companies, list):
            reports = [item for item in companies if isinstance(item, Mapping)]
        elif "company" in payload:
            reports = [payload]
    elif isinstance(payload, list):
        reports = [item for item in payload if isinstance(item, Mapping)]

    index: dict[str, list[dict[str, str]]] = {}
    for report in reports:
        company = report.get("company") or report.get("Company Name") or report.get("company_name")
        key = _normalise_company(company)
        if key:
            index[key] = _company_report_context(report)
    return index


def _load_company_report_from_news_json(path: Path, company: str) -> Mapping[str, Any] | None:
    with path.open("r", encoding="utf-8-sig") as f:
        payload = json.load(f)

    reports: list[Mapping[str, Any]] = []
    if isinstance(payload, Mapping):
        companies = payload.get("companies")
        if isinstance(companies, list):
            reports = [item for item in companies if isinstance(item, Mapping)]
        elif "company" in payload:
            reports = [payload]
    elif isinstance(payload, list):
        reports = [item for item in payload if isinstance(item, Mapping)]

    wanted = _normalise_company(company)
    for report in reports:
        name = report.get("company") or report.get("Company Name") or report.get("company_name")
        if _normalise_company(name) == wanted:
            return report
    for report in reports:
        name = _normalise_company(report.get("company") or report.get("Company Name") or report.get("company_name"))
        if wanted and name and (wanted in name or name in wanted):
            return report
    return None


def _research_company(company: str, args: argparse.Namespace) -> Mapping[str, Any]:
    try:
        from company_news_web_search import _parse_args as parse_research_args
        from company_news_web_search import _run as run_research
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "Could not import company_news_web_search.py. Run this script from the repo root "
            "or keep it inside the backend folder."
        ) from exc

    research_argv = [
        company,
        "--limit",
        str(args.research_limit),
        "--per-source-limit",
        str(args.per_source_limit),
        "--fetch-page-limit",
        str(args.fetch_page_limit),
        "--no-hf",
    ]
    if not args.no_fetch_pages:
        research_argv.append("--fetch-pages")
    if args.no_linkedin:
        research_argv.append("--no-linkedin")
    if args.headed:
        research_argv.append("--headed")
    else:
        research_argv.append("--headless")
    if args.verbose:
        research_argv.append("--verbose")

    research_args = parse_research_args(research_argv)
    payload = asyncio.run(run_research(research_args))
    companies = payload.get("companies") if isinstance(payload, Mapping) else None
    if not isinstance(companies, list) or not companies:
        raise RuntimeError(f"No research report came back for {company}.")

    report = companies[0]
    if not isinstance(report, Mapping):
        raise RuntimeError(f"Unexpected research payload for {company}.")

    if args.research_output:
        research_path = Path(args.research_output).expanduser().resolve()
        research_path.parent.mkdir(parents=True, exist_ok=True)
        with research_path.open("w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
            f.write("\n")

    return report


def _find_news_context(company: str, index: Mapping[str, list[dict[str, str]]]) -> list[dict[str, str]]:
    key = _normalise_company(company)
    if not key or not index:
        return []
    if key in index:
        return index[key]

    # Simple fallback for slightly different names, e.g. "City of San Jose" vs
    # "San Jose". Keep it conservative so we do not attach the wrong news.
    for candidate, context in index.items():
        if len(candidate) < 5:
            continue
        if candidate in key or key in candidate:
            return context
    return []


def _row_news_context(row: Mapping[str, Any]) -> list[dict[str, str]]:
    items = []
    lower = {str(k).strip().lower(): v for k, v in row.items()}
    for col in NEWS_ROW_COLUMNS:
        value = lower.get(col)
        if value:
            items.append({"title": col.replace("_", " ").title(), "snippet": _clean(value), "url": ""})
    return items


def _normalise_generation_payload(generation: Mapping[str, Any]) -> dict[str, Any]:
    """Map nested master-prompt JSON (or legacy flat keys) onto pipeline field names."""
    if isinstance(generation.get("primary_email"), Mapping):
        pe = generation["primary_email"]
        meta = generation["metadata"] if isinstance(generation.get("metadata"), Mapping) else {}
        conf_raw = str(meta.get("confidence") or "").strip().lower()
        confidence = ""
        for token in re.split(r"[^\w]+", conf_raw):
            if token in {"low", "medium", "high"}:
                confidence = token
                break
        alts = {
            "subject_lines": generation.get("subject_lines"),
            "variation_1": generation.get("variation_1"),
            "variation_2": generation.get("variation_2"),
        }
        return {
            "subject": pe.get("subject"),
            "email_body": pe.get("body") or pe.get("email_body"),
            "pain_point": meta.get("pain_point"),
            "why_now": meta.get("why_now"),
            "evidence_used": meta.get("evidence_used"),
            "offer": meta.get("product_used"),
            "confidence": confidence,
            "generated_alternatives_json": json.dumps(alts, ensure_ascii=False, indent=2),
        }

    return {
        "subject": generation.get("subject"),
        "email_body": generation.get("email_body"),
        "pain_point": generation.get("pain_point"),
        "why_now": generation.get("why_now"),
        "evidence_used": generation.get("evidence_used"),
        "offer": generation.get("offer"),
        "confidence": str(generation.get("confidence") or "").strip().lower(),
        "generated_alternatives_json": "",
    }


def _prepare_output_fieldnames(rows: list[dict[str, str]]) -> list[str]:
    fieldnames: list[str] = []
    for row in rows[:1]:
        fieldnames.extend(list(row.keys()))
    for column in GENERATED_COLUMNS:
        if column not in fieldnames:
            fieldnames.append(column)
    return fieldnames


def _apply_generation(row: dict[str, Any], generation: Mapping[str, Any]) -> dict[str, Any]:
    gen = _normalise_generation_payload(generation)
    output = dict(row)
    output["Subject"] = _clean(gen.get("subject"), max_chars=180) or output.get("Subject", "")
    output["Email Body"] = str(gen.get("email_body") or output.get("Email Body", "")).strip()
    output["Generated Pain Point"] = _clean(gen.get("pain_point"))
    output["Generated Why Now"] = _clean(gen.get("why_now"))
    output["Generated Evidence"] = _clean(gen.get("evidence_used"))
    output["Generated Offer"] = _clean(gen.get("offer"))
    confidence = str(gen.get("confidence") or "").strip().lower()
    output["Generation Confidence"] = confidence if confidence in {"low", "medium", "high"} else ""
    output["Generated Alternatives (JSON)"] = str(gen.get("generated_alternatives_json") or "").strip()
    output["Generation Error"] = ""
    return output


def _error_row(row: dict[str, Any], error: Exception) -> dict[str, Any]:
    output = dict(row)
    for col in GENERATED_COLUMNS:
        output.setdefault(col, "")
    output["Generation Error"] = str(error)
    return output


def _single_company_row(args: argparse.Namespace) -> dict[str, str]:
    return {
        "Email": args.email or "",
        "First Name": args.first_name or "",
        "Last Name": args.last_name or "",
        "Company Name": args.company_name,
        "Position": args.position or "relevant leader",
    }


def _print_single_email(row: Mapping[str, Any], generation: Mapping[str, Any]) -> None:
    gen = _normalise_generation_payload(generation)
    company = _row_value(row, "Company Name", "company", "company_name")
    print(f"Company: {company}")
    print(f"Subject: {_clean(gen.get('subject'), max_chars=180)}")
    print()
    print(str(gen.get("email_body") or "").strip())

    pain = _clean(gen.get("pain_point"))
    evidence = _clean(gen.get("evidence_used"))
    if pain or evidence:
        print()
        if pain:
            print(f"Pain point: {pain}")
        if evidence:
            print(f"Evidence used: {evidence}")

    alts = gen.get("generated_alternatives_json") or ""
    if alts.strip():
        print()
        print("--- Alternatives (JSON) ---")
        print(alts.strip())


def _run_single_company(args: argparse.Namespace) -> int:
    company = args.company_name
    news_report: Mapping[str, Any] | None = None

    if args.news_json:
        news_path = Path(args.news_json).expanduser().resolve()
        if not news_path.exists():
            raise SystemExit(f"News JSON not found: {news_path}")
        news_report = _load_company_report_from_news_json(news_path, company)

    if news_report is None and not args.no_research:
        _log(args.verbose, f"Researching {company} before generating the email...")
        news_report = _research_company(company, args)

    news_context = _company_report_context(news_report) if news_report else []
    news_context = _trim_news_context(
        news_context,
        max_items=int(args.context_items),
        snippet_chars=int(args.context_snippet_chars),
    )
    row = _single_company_row(args)
    messages = build_email_generation_prompt(row, news_context)
    _log_ollama_prompt(args.verbose, messages)
    _log(
        args.verbose,
        f"Generating email with Ollama model {args.model} using {len(news_context)} context item(s)...",
    )
    generation = _ollama_chat(
        url=_normalise_ollama_chat_url(args.ollama_url),
        model=args.model,
        messages=messages,
        timeout_s=int(args.timeout_s),
        temperature=float(args.temperature),
    )

    if args.output:
        output_path = Path(args.output).expanduser().resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open("w", encoding="utf-8") as f:
            json.dump(
                {
                    "company": company,
                    "row": row,
                    "generation": generation,
                    "news_context": news_context,
                },
                f,
                ensure_ascii=False,
                indent=2,
            )
            f.write("\n")

    _print_single_email(row, generation)
    return 0


def _run_batch_csv(args: argparse.Namespace) -> int:
    input_path = Path(args.input).expanduser().resolve()
    if not input_path.exists():
        raise SystemExit(f"Input CSV not found: {input_path}")

    output_path = (
        Path(args.output).expanduser().resolve()
        if args.output
        else input_path.with_name(input_path.stem + ".news_emails.csv")
    )
    news_path = Path(args.news_json).expanduser().resolve() if args.news_json else None

    rows = _read_csv(input_path, encoding=args.encoding)
    if not rows:
        raise SystemExit(f"No rows found in {input_path}")

    news_index = _load_news_index(news_path)
    chat_url = _normalise_ollama_chat_url(args.ollama_url)
    fieldnames = _prepare_output_fieldnames(rows)
    processed: list[dict[str, Any]] = []
    limit = int(args.limit or 0)

    for index, row in enumerate(rows, start=1):
        if limit > 0 and index > limit:
            processed.append(dict(row))
            continue

        company = _row_value(row, "Company Name", "company", "company_name", "organization")
        news_context = _find_news_context(company, news_index) or _row_news_context(row)
        news_context = _trim_news_context(
            news_context,
            max_items=int(args.context_items),
            snippet_chars=int(args.context_snippet_chars),
        )
        _log(args.verbose, f"[{index}/{len(rows)}] Generating email for {company or 'unknown company'}")

        try:
            messages = build_email_generation_prompt(row, news_context)
            _log_ollama_prompt(args.verbose, messages)
            generation = _ollama_chat(
                url=chat_url,
                model=args.model,
                messages=messages,
                timeout_s=int(args.timeout_s),
                temperature=float(args.temperature),
            )
            processed.append(_apply_generation(row, generation))
        except Exception as exc:
            processed.append(_error_row(row, exc))
            _log(args.verbose, f"  error: {exc}")

        if int(args.sleep_ms) > 0:
            time.sleep(int(args.sleep_ms) / 1000.0)

    _write_csv(output_path, processed, fieldnames, encoding=args.encoding)
    print(f"Wrote {len(processed)} row(s) to: {output_path}")
    return 0


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Generate Aeyron personalized email drafts from a company name or "
            "from a contact CSV using local Ollama."
        )
    )
    parser.add_argument("company", nargs="?", help='Company name for one-off mode, e.g. "Jones Day".')
    parser.add_argument("--company", dest="company_flag", help="Company name for one-off mode.")
    parser.add_argument("--first-name", default="", help="Optional recipient first name for one-off mode.")
    parser.add_argument("--last-name", default="", help="Optional recipient last name for one-off mode.")
    parser.add_argument("--email", default="", help="Optional recipient email for one-off mode.")
    parser.add_argument("--position", default="", help='Optional recipient role. Default: "relevant leader".')
    parser.add_argument("--input", "-i", help="Input contact CSV for batch mode.")
    parser.add_argument(
        "--output",
        "-o",
        help="Output file. Batch mode writes CSV; one-off company mode writes JSON if provided.",
    )
    parser.add_argument(
        "--news-json",
        help=(
            "Optional JSON produced by backend/company_news_web_search.py. In one-off mode, "
            "this is used before live research."
        ),
    )
    parser.add_argument("--model", default="qwen2.5:3b", help='Ollama model name. Default: "qwen2.5:3b"')
    parser.add_argument(
        "--ollama-url",
        default=os.getenv("OLLAMA_URL", "http://localhost:11434"),
        help="Ollama base URL or /api/chat URL. Default: http://localhost:11434",
    )
    parser.add_argument("--limit", type=int, default=0, help="Only process first N rows. Default: all rows.")
    parser.add_argument("--timeout-s", type=int, default=300, help="Ollama request timeout seconds.")
    parser.add_argument("--temperature", type=float, default=0.25, help="Generation temperature.")
    parser.add_argument("--context-items", type=int, default=5, help="Max research context items sent to Ollama.")
    parser.add_argument("--context-snippet-chars", type=int, default=350, help="Max chars per context snippet sent to Ollama.")
    parser.add_argument("--sleep-ms", type=int, default=0, help="Delay between Ollama calls.")
    parser.add_argument("--encoding", default="utf-8-sig", help="CSV encoding.")
    parser.add_argument("--no-research", action="store_true", help="One-off mode only: skip live company research.")
    parser.add_argument("--research-output", help="Optional path to save live research JSON.")
    parser.add_argument("--research-limit", type=int, default=12, help="One-off mode: final research result limit.")
    parser.add_argument("--per-source-limit", type=int, default=8, help="One-off mode: result limit per search source.")
    parser.add_argument("--fetch-page-limit", type=int, default=5, help="One-off mode: pages to fetch for richer context.")
    parser.add_argument("--no-fetch-pages", action="store_true", help="One-off mode: do not fetch result pages.")
    parser.add_argument("--no-linkedin", action="store_true", help="One-off mode: skip LinkedIn result discovery.")
    parser.add_argument("--headed", action="store_true", help="One-off mode: show Chromium during research.")
    parser.add_argument(
        "--verbose",
        default=True,
        action=argparse.BooleanOptionalAction,
        help="Print progress to stderr (default: on). Use --no-verbose to silence.",
    )
    args = parser.parse_args(argv)
    args.company_name = args.company_flag or args.company or ""
    if not args.input and not args.company_name:
        parser.error("provide a company name for one-off mode, or --input for batch CSV mode")
    return args


def main(argv: list[str]) -> int:
    args = _parse_args(argv)
    if args.input:
        return _run_batch_csv(args)
    return _run_single_company(args)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
