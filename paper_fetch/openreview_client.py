from __future__ import annotations

import datetime
from typing import Any, Dict, Iterable, List, Optional, Sequence
from urllib.parse import urlencode

import requests

from .models import PaperRecord


def _get_content_value(obj: Any) -> Any:
    if isinstance(obj, dict) and "value" in obj:
        return obj.get("value")
    return obj


def _ms_to_date_str(ms: Optional[int]) -> str:
    if not ms:
        return ""
    dt = datetime.datetime.utcfromtimestamp(ms / 1000.0)
    return dt.strftime("%Y-%m-%d")


def fetch_openreview_notes(
    *,
    invitation: str,
    max_results: int = 50,
    offset: int = 0,
    api_base: str = "https://api2.openreview.net",
    timeout_s: int = 30,
) -> List[Dict[str, Any]]:
    notes: List[Dict[str, Any]] = []
    remaining = max(0, max_results)
    cur = max(0, offset)

    while remaining > 0:
        limit = min(1000, remaining)
        qs = urlencode({"invitation": invitation, "limit": limit, "offset": cur})
        url = f"{api_base.rstrip('/')}/notes?{qs}"
        r = requests.get(url, timeout=timeout_s, headers={"User-Agent": "Mozilla/5.0"})
        r.raise_for_status()
        data = r.json()
        batch = data.get("notes", []) or []
        if not batch:
            break
        notes.extend(batch)
        cur += len(batch)
        remaining -= len(batch)
        if len(batch) < limit:
            break

    return notes


def notes_to_records(
    notes: Sequence[Dict[str, Any]],
    *,
    invitation: str,
) -> Iterable[PaperRecord]:
    for n in notes:
        content = n.get("content") or {}
        title = _get_content_value(content.get("title")) or ""
        abstract = _get_content_value(content.get("abstract")) or ""
        authors = _get_content_value(content.get("authors")) or []
        if isinstance(authors, str):
            authors = [authors]
        if not isinstance(authors, list):
            authors = []

        forum = n.get("forum") or ""
        paper_id = str(n.get("id") or forum or "")
        abs_url = f"https://openreview.net/forum?id={forum}" if forum else ""

        yield PaperRecord(
            source="openreview",
            paper_id=paper_id,
            title=str(title),
            authors=[str(a) for a in authors],
            summary=str(abstract),
            published=_ms_to_date_str(n.get("cdate")),
            abs_url=abs_url,
            pdf_url="",
            primary_category=None,
            github_url=None,
            is_hf_trending=False,
        )
