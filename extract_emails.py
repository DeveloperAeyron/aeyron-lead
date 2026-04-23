#!/usr/bin/env python3
import argparse
import re
import sys
from pathlib import Path
from typing import Iterable
from urllib.parse import unquote
from urllib.request import Request, urlopen


EMAIL_RE = re.compile(
    r"""
    (?<![\w.+-])
    [a-z0-9][a-z0-9._%+-]{0,63}
    @
    (?:[a-z0-9-]+\.)+[a-z]{2,63}
    (?![\w.+-])
    """,
    re.IGNORECASE | re.VERBOSE,
)

NON_EMAIL_TLDS = {
    "css",
    "eot",
    "gif",
    "ico",
    "jpeg",
    "jpg",
    "js",
    "map",
    "mp4",
    "pdf",
    "png",
    "svg",
    "ttf",
    "webm",
    "webp",
    "woff",
    "woff2",
}

URL_RE = re.compile(
    r"""https?://[^\s"'<>]+""",
    re.IGNORECASE,
)

SOCIAL_HOSTS = {
    "linkedin.com",
    "www.linkedin.com",
    "facebook.com",
    "www.facebook.com",
    "instagram.com",
    "www.instagram.com",
    "twitter.com",
    "www.twitter.com",
    "x.com",
    "www.x.com",
    "youtube.com",
    "www.youtube.com",
    "youtu.be",
    "tiktok.com",
    "www.tiktok.com",
}


def extract_social_links_from_html(text: str) -> set[str]:
    urls = {m.group(0).rstrip(").,;]}'\"") for m in URL_RE.finditer(text)}
    socials: set[str] = set()

    for u in urls:
        # Quick host check without full URL parsing (keep it regex/simple as requested).
        m = re.match(r"^https?://([^/]+)", u, flags=re.IGNORECASE)
        if not m:
            continue
        host = m.group(1).lower()
        if host in SOCIAL_HOSTS:
            socials.add(u.rstrip("/"))
            continue

        # Handle common subdomains like "m.facebook.com", "uk.linkedin.com", etc.
        if any(host.endswith("." + h) for h in SOCIAL_HOSTS):
            socials.add(u.rstrip("/"))

    return socials


def _normalise_text_for_obfuscated_emails(text: str) -> str:
    # Common obfuscations seen in HTML pages.
    t = text
    t = unquote(t)
    t = t.replace("\u00a0", " ")
    t = re.sub(r"\s+", " ", t)

    # Replace standalone "at" / "[at]" / "(at)" variants with @ (avoid matching inside words)
    t = re.sub(
        r"(?i)(?<![a-z0-9])(?:\(|\[|\{)?\s*at\s*(?:\)|\]|\})?(?![a-z0-9])",
        "@",
        t,
    )
    # Replace standalone "dot" / "[dot]" / "(dot)" variants with . (avoid matching inside words)
    t = re.sub(
        r"(?i)(?<![a-z0-9])(?:\(|\[|\{)?\s*dot\s*(?:\)|\]|\})?(?![a-z0-9])",
        ".",
        t,
    )

    return t


def iter_html_files(root: Path, recursive: bool) -> Iterable[Path]:
    exts = {".html", ".htm"}
    if recursive:
        for p in root.rglob("*"):
            if p.is_file() and p.suffix.lower() in exts:
                yield p
    else:
        for p in root.iterdir():
            if p.is_file() and p.suffix.lower() in exts:
                yield p


def extract_emails_from_text(text: str) -> set[str]:
    emails: set[str] = set()

    # First pass: raw HTML (catches normal emails + mailto:foo@bar.com)
    for m in EMAIL_RE.finditer(text):
        emails.add(m.group(0).lower())

    # Second pass: normalised for basic obfuscation patterns.
    normalised = _normalise_text_for_obfuscated_emails(text)
    for m in EMAIL_RE.finditer(normalised):
        emails.add(m.group(0).lower())

    filtered: set[str] = set()
    for e in emails:
        tld = e.rsplit(".", 1)[-1]
        if tld in NON_EMAIL_TLDS:
            continue
        filtered.add(e)

    return filtered


def fetch_url_html(url: str, timeout_s: float = 20.0) -> str:
    u = url.strip()
    if not u:
        return ""
    if not re.match(r"^https?://", u, flags=re.IGNORECASE):
        u = "https://" + u

    req = Request(
        u,
        headers={
            "User-Agent": "Mozilla/5.0 (compatible; EmailExtractor/1.0)",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        },
        method="GET",
    )
    with urlopen(req, timeout=timeout_s) as resp:
        raw = resp.read()
        charset = getattr(resp.headers, "get_content_charset", lambda: None)() or "utf-8"
        return raw.decode(charset, errors="ignore")


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Extract email addresses from a website or local HTML files using regex."
    )
    ap.add_argument(
        "target",
        nargs="?",
        default="crashchampions.com",
        help="URL or folder (default: crashchampions.com).",
    )
    ap.add_argument(
        "--recursive",
        action="store_true",
        help="Scan subfolders as well.",
    )
    ap.add_argument(
        "--per-file",
        action="store_true",
        help="Print emails grouped by file.",
    )
    ap.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress progress information.",
    )
    args = ap.parse_args()

    verbose = not args.quiet

    target = str(args.target).strip()
    if re.match(r"^https?://", target, flags=re.IGNORECASE) or re.match(r"^[a-z0-9.-]+\.[a-z]{2,}$", target, flags=re.IGNORECASE):
        if verbose:
            print(f"[info] fetching: {target}", file=sys.stderr)
        html = fetch_url_html(target)
        if verbose:
            print(f"[info] downloaded: {len(html)} chars", file=sys.stderr)
        emails = extract_emails_from_text(html)
        socials = extract_social_links_from_html(html)
        if verbose:
            print(f"[info] emails found: {len(emails)}", file=sys.stderr)
            print(f"[info] social links found: {len(socials)}", file=sys.stderr)

        if emails:
            print("Emails:")
            for e in sorted(emails):
                print(f"- {e}")
        else:
            print("Emails:\n- (none found)")

        if socials:
            print("\nSocials:")
            for u in sorted(socials):
                print(f"- {u}")
        else:
            print("\nSocials:\n- (none found)")
        return 0

    root = Path(target).expanduser().resolve()
    if not root.exists() or not root.is_dir():
        raise SystemExit(f"Not a URL or folder: {target}")

    all_emails: set[str] = set()
    per_file: dict[Path, set[str]] = {}

    if verbose:
        print(f"[info] scanning folder: {root}", file=sys.stderr)
    for html_file in iter_html_files(root, recursive=args.recursive):
        try:
            text = html_file.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue

        emails = extract_emails_from_text(text)
        if not emails:
            continue

        all_emails |= emails
        per_file[html_file] = emails
        if verbose:
            try:
                rel = html_file.relative_to(root)
            except ValueError:
                rel = html_file
            print(f"[info] {rel}: {len(emails)}", file=sys.stderr)

    if args.per_file:
        for f in sorted(per_file):
            rel = f.relative_to(root)
            print(f"\n{rel}")
            for e in sorted(per_file[f]):
                print(f"  {e}")
    else:
        for e in sorted(all_emails):
            print(e)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
