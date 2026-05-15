"""On-disk cache for company research payloads (reduces repeated Playwright runs)."""
from __future__ import annotations

import hashlib
import json
import os
import tempfile
import time
from pathlib import Path
from typing import Any, Mapping


def default_cache_root() -> Path:
    return (Path(__file__).resolve().parent / ".research_cache").resolve()


def resolve_cache_root(explicit: str | None) -> Path | None:
    """Return cache directory, or None if caching is disabled."""
    env_dir = (os.getenv("AEYRON_RESEARCH_CACHE_DIR") or "").strip()
    if env_dir:
        return Path(env_dir).expanduser().resolve()
    flag = (os.getenv("AEYRON_RESEARCH_CACHE", "1") or "1").strip().lower()
    if flag in ("0", "false", "no", "off"):
        return None
    if explicit:
        return Path(explicit).expanduser().resolve()
    return default_cache_root()


def fingerprint_key(
    company: str,
    *,
    limit: int,
    per_source_limit: int,
    fetch_page_limit: int,
    fetch_pages: bool,
    no_linkedin: bool,
    disable_hf: bool,
) -> str:
    payload = json.dumps(
        {
            "company": company.strip().lower(),
            "limit": int(limit),
            "per_source_limit": int(per_source_limit),
            "fetch_page_limit": int(fetch_page_limit),
            "fetch_pages": bool(fetch_pages),
            "no_linkedin": bool(no_linkedin),
            "disable_hf": bool(disable_hf),
        },
        sort_keys=True,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:48]


def _ttl_hours() -> float:
    raw = (os.getenv("AEYRON_RESEARCH_CACHE_HOURS") or "168").strip()
    try:
        v = float(raw)
        return max(0.25, v)
    except ValueError:
        return 168.0


def read_cached_payload(
    cache_root: Path,
    key: str,
    *,
    ttl_hours: float | None = None,
) -> Mapping[str, Any] | None:
    path = cache_root / f"{key}.json"
    if not path.is_file():
        return None
    ttl = float(ttl_hours) if ttl_hours is not None else _ttl_hours()
    age_s = max(0.0, time.time() - path.stat().st_mtime)
    if age_s > ttl * 3600.0:
        try:
            path.unlink()
        except OSError:
            pass
        return None
    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError):
        return None
    return data if isinstance(data, Mapping) else None


def write_cached_payload(cache_root: Path, key: str, payload: Mapping[str, Any]) -> None:
    cache_root.mkdir(parents=True, exist_ok=True)
    path = cache_root / f"{key}.json"
    text = json.dumps(dict(payload), ensure_ascii=False, indent=2) + "\n"
    fd, tmp = tempfile.mkstemp(prefix="rc-", suffix=".json", dir=str(cache_root))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(text)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    except OSError:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise
