#!/usr/bin/env python3
from __future__ import annotations

import json
import re
from datetime import datetime
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Optional
from urllib.parse import urlparse
from urllib.request import Request, urlopen


EMAIL_RE = re.compile(r"\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[A-Za-z]{2,}\b")

URL = "https://www.oceansuds.com/"
MODEL = "qwen3.5:9b"
TIMEOUT_S = 12
MAX_STRIPPED_CHARS = 140_000
SAVE_STRIPPED_PATH = Path("oceansuds.stripped.txt")
VERBOSE = True
USE_LLM = False


def _require(module_name: str) -> Any:
    try:
        return __import__(module_name)
    except ModuleNotFoundError as exc:
        raise SystemExit(
            f'Missing dependency "{module_name}".\n'
            f"- If you use a venv, activate it first.\n"
            f"- Otherwise install deps: pip install -r requirements.txt\n"
        ) from exc


def _fetch_html(url: str, *, timeout_s: int, user_agent: str) -> tuple[Optional[str], Optional[str]]:
    try:
        req = Request(url, headers={"User-Agent": user_agent})
        with urlopen(req, timeout=timeout_s) as resp:
            raw = resp.read()
            html = raw.decode("utf-8", errors="ignore")
            return html, None
    except Exception as exc:
        return None, f"{type(exc).__name__}: {exc!s}"


def _log(msg: str) -> None:
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] {msg}", flush=True)


def _dns_debug(host: str) -> dict[str, Any]:
    import socket

    out: dict[str, Any] = {"host": host, "ok": False, "addrs": [], "error": None}
    try:
        infos = socket.getaddrinfo(host, None)
        addrs = []
        for _fam, _socktype, _proto, _canon, sockaddr in infos:
            ip = sockaddr[0] if sockaddr else None
            if ip:
                addrs.append(ip)
        out["addrs"] = sorted(set(addrs))
        out["ok"] = True
    except Exception as exc:
        out["error"] = f"{type(exc).__name__}: {exc!s}"
    return out


def _strip_html_for_llm(html: str, *, max_chars: int) -> str:
    """
    Turn raw HTML into mostly-visible text + useful links for the LLM.
    This massively reduces Squarespace/SPA boilerplate and keeps contact details.
    """
    import html as html_lib

    s = html
    # Drop high-noise sections.
    s = re.sub(r"(?is)<script[^>]*>.*?</script>", " ", s)
    s = re.sub(r"(?is)<style[^>]*>.*?</style>", " ", s)
    s = re.sub(r"(?is)<!--.*?-->", " ", s)
    s = re.sub(r"(?is)<svg[^>]*>.*?</svg>", " ", s)
    s = re.sub(r"(?is)<noscript[^>]*>.*?</noscript>", " ", s)
    s = re.sub(r"(?is)<head[^>]*>.*?</head>", " ", s)

    # Keep anchor text + href in a compact form before stripping tags.
    def _a_repl(m: re.Match) -> str:
        href = (m.group(1) or "").strip()
        text = re.sub(r"(?is)<[^>]+>", " ", (m.group(2) or ""))
        text = re.sub(r"\s+", " ", text).strip()
        href = href.split("#", 1)[0]
        if not href:
            return text
        if text and text.lower() not in href.lower():
            return f"{text} ({href})"
        return href if not text else f"{text} ({href})"

    s = re.sub(r'(?is)<a[^>]+href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', _a_repl, s)

    # Insert newlines for block-ish elements to avoid a single giant line.
    s = re.sub(r"(?is)</(p|div|section|article|header|footer|nav|li|h1|h2|h3|h4|h5|h6|br|tr)>", "\n", s)

    # Strip remaining tags.
    s = re.sub(r"(?is)<[^>]+>", " ", s)
    s = html_lib.unescape(s)

    # Normalise whitespace and de-duplicate blank lines.
    s = re.sub(r"[ \t\r\f\v]+", " ", s)
    s = re.sub(r"\n[ \t]*\n+", "\n\n", s)
    s = s.strip()

    if len(s) > max_chars:
        s = s[:max_chars]
    return s


def _extract_emails(text: str) -> list[str]:
    # `mailto:` links sometimes include querystrings; capture those too.
    candidates = set(EMAIL_RE.findall(text))
    for m in re.findall(r"(?i)mailto:([a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,})", text):
        candidates.add(m)

    out: list[str] = []
    for e in sorted(candidates, key=lambda s: s.lower()):
        e_norm = e.strip().strip(".,;:()[]{}<>\"'").lower()
        if not e_norm:
            continue
        # Common placeholders / junk that appear in templates.
        if e_norm in {"example@example.com", "name@example.com", "email@example.com"}:
            continue
        out.append(e_norm)
    return out


def _ollama_extract(*, model: str, url: str, html_stripped: str) -> str:
    ollama = _require("ollama")
    prompt = (
        "Extract business + contact details from the website text below.\n"
        "Return only what is present in the text.\n\n"
        f"Website: {url}\n\n"
        "WEBSITE TEXT:\n"
        f"{html_stripped}\n"
    )

    resp = ollama.chat(
        model=model,
        messages=[{"role": "user", "content": prompt}],
    )
    return resp.get("message", {}).get("content", "") if isinstance(resp, dict) else ""


@dataclass
class WebsiteResult:
    url: str
    llm: str


def main() -> int:
    url = URL.strip()
    ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
    _log("Starting")
    _log(f"URL: {url}")
    _log(f"Ollama model: {MODEL}")
    if VERBOSE:
        parsed = urlparse(url)
        host = parsed.hostname or ""
        _log(f"[debug] host={host!r} scheme={parsed.scheme!r}")
        if host:
            _log("[debug] dns: " + json.dumps(_dns_debug(host), ensure_ascii=False))
    _log(f"Fetching HTML (timeout={TIMEOUT_S}s)")
    html, err = _fetch_html(url, timeout_s=TIMEOUT_S, user_agent=ua)
    if not html:
        if VERBOSE:
            _log(f"[debug] fetch_error={err}")
        raise SystemExit(f"Fetch failed: {err}")

    _log(f"Fetched HTML ({len(html):,} chars)")
    stripped = _strip_html_for_llm(html, max_chars=MAX_STRIPPED_CHARS)
    _log(f"Stripped HTML ({len(stripped):,} chars; max={MAX_STRIPPED_CHARS:,})")

    out_path = SAVE_STRIPPED_PATH.expanduser().resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    # Also collapse whitespace so it is compact.
    compact = re.sub(r"\s+", " ", stripped).strip()
    out_path.write_text(compact, encoding="utf-8", errors="ignore")
    _log(f"Wrote stripped text to: {out_path}")

    emails = _extract_emails(compact)

    llm = ""
    if USE_LLM:
        _log("Calling Ollama (this may take a while)")
        llm = _ollama_extract(
            model=MODEL,
            url=url,
            html_stripped=compact,
        )
        _log("Ollama call complete")

    result = WebsiteResult(
        url=url,
        llm=llm,
    )

    _log("Done")
    if emails:
        print("\n".join(emails))
    elif result.llm:
        print(result.llm)
    else:
        print("No emails found.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

