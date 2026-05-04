"""Batch email generation from spreadsheet rows (research + Ollama)."""
from __future__ import annotations

import csv
import io
import time
from io import BytesIO
from typing import Any, Mapping

from openpyxl import load_workbook

from email_generation import (
    EmailGenerationInput,
    _research_namespace,
    company_cache_key,
    generate_with_trimmed_context,
    make_prompt_row,
    split_full_name,
)
from generate_news_emails_ollama import (
    _company_report_context,
    _research_company,
    _trim_news_context,
)

_EMAIL_KEYS = ("email", "e-mail", "e mail", "email address", "mail")
_NAME_KEYS = ("name", "full name", "contact name", "recipient name", "contact")
_COMPANY_KEYS = (
    "company name",
    "company",
    "organisation",
    "organization",
    "org",
    "business name",
    "employer",
)


def _norm_header(h: str) -> str:
    return " ".join((h or "").strip().lower().split())


def _pick_field(row: Mapping[str, Any], candidates: tuple[str, ...]) -> str:
    """Match spreadsheet column to canonical field (case-insensitive, flexible naming)."""
    lower_map = {_norm_header(str(k)): v for k, v in row.items()}
    for c in candidates:
        if c in lower_map:
            v = lower_map[c]
            if v is not None and str(v).strip():
                return str(v).strip()
    # Substring fallbacks
    cand_set = set(candidates)
    for k, v in lower_map.items():
        if v is None or not str(v).strip():
            continue
        for c in cand_set:
            if c in k or (len(c) >= 5 and k in c):
                return str(v).strip()
    return ""


def extract_contact_fields(row: Mapping[str, Any]) -> tuple[str, str, str]:
    """Return (email, full name, company) from a flexible spreadsheet row."""
    email = _pick_field(row, _EMAIL_KEYS)
    name = _pick_field(row, _NAME_KEYS)
    company = _pick_field(row, _COMPANY_KEYS)
    return email, name, company


def load_rows_from_xlsx(content: bytes) -> list[dict[str, Any]]:
    """Read the first worksheet; first row = headers. All columns preserved."""
    bio = BytesIO(content)
    wb = load_workbook(bio, read_only=True, data_only=True)
    try:
        ws = wb.active
        rows_iter = ws.iter_rows(values_only=True)
        header_row = next(rows_iter, None)
        if not header_row:
            return []
        headers = [str(c).strip() if c is not None else "" for c in header_row]
        out: list[dict[str, Any]] = []
        for row in rows_iter:
            if row is None:
                continue
            if all((c is None or str(c).strip() == "") for c in row):
                continue
            record: dict[str, Any] = {}
            for i, h in enumerate(headers):
                if not h:
                    continue
                val = row[i] if i < len(row) else None
                record[h] = "" if val is None else str(val).strip()
            out.append(record)
        return out
    finally:
        wb.close()


def process_batch(
    rows: list[dict[str, Any]],
    base: EmailGenerationInput,
    *,
    max_rows: int = 50,
    sleep_ms: int = 0,
) -> tuple[list[dict[str, Any]], list[str]]:
    """
    For each row: company research (cached per company), personalised email, news summary.
    Returns (result dicts for CSV, list of fieldnames order).
    """
    if not rows:
        raise ValueError("No data rows in spreadsheet.")

    capped = rows[: max(1, max_rows)]
    research_cache: dict[str, list[dict[str, str]]] = {}
    outputs: list[dict[str, Any]] = []

    # Stable column order: original keys from first row, then new columns
    base_keys = list(capped[0].keys())
    extra_cols = ["subject", "body", "news based summary", "generation_error"]
    fieldnames = base_keys + [c for c in extra_cols if c not in base_keys]

    for i, raw in enumerate(capped):
        line_out = {k: raw.get(k, "") for k in base_keys}
        for c in extra_cols:
            line_out.setdefault(c, "")

        email, full_name, company = extract_contact_fields(raw)
        first, last = split_full_name(full_name)

        if not company:
            line_out["generation_error"] = "Missing company name (use a column named e.g. company name or company)."
            outputs.append(line_out)
            continue

        row_dict = make_prompt_row(
            email=email,
            first_name=first,
            last_name=last,
            company_name=company,
            position=base.position,
            industry=base.industry,
        )

        raw_news: list[dict[str, str]] = []
        research_used = False
        try:
            ck = company_cache_key(company)
            if ck and ck in research_cache:
                raw_news = list(research_cache[ck])
            else:
                if base.do_research:
                    report = _research_company(company, _research_namespace(base))
                    raw_news = list(_company_report_context(report))
                    if ck:
                        research_cache[ck] = list(raw_news)
                    research_used = True
                else:
                    raw_news = []

            trimmed = _trim_news_context(
                raw_news,
                max_items=max(1, base.context_items),
                snippet_chars=base.context_snippet_chars,
            )
            result = generate_with_trimmed_context(row_dict, trimmed, base, research_used=research_used)
            line_out["subject"] = result.get("subject", "")
            line_out["body"] = result.get("email_body", "")
            line_out["news based summary"] = result.get("news_based_summary", "")
            line_out["generation_error"] = ""
        except Exception as exc:
            line_out["generation_error"] = str(exc)

        outputs.append(line_out)

        if sleep_ms > 0 and i + 1 < len(capped):
            time.sleep(sleep_ms / 1000.0)

    return outputs, fieldnames


def rows_to_csv_bytes(rows: list[dict[str, Any]], fieldnames: list[str]) -> bytes:
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=fieldnames, extrasaction="ignore", restval="")
    w.writeheader()
    w.writerows(rows)
    return buf.getvalue().encode("utf-8-sig")
