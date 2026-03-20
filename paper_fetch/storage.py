from __future__ import annotations

import json
import os
import re
import time
from pathlib import Path
from typing import Dict

import requests

from .models import PaperRecord


def _safe_filename(name: str, max_len: int = 160) -> str:
    name = re.sub(r"[\\/:*?\"<>|]", "_", name)
    name = re.sub(r"\s+", " ", name).strip()
    if not name:
        name = "paper"
    return name[:max_len]


def paper_dir(base_dir: Path, paper_id: str) -> Path:
    return base_dir / paper_id


def record_dir(base_dir: Path, record: PaperRecord) -> Path:
    year = "unknown"
    p = (record.published or "").strip()
    if len(p) >= 4 and p[:4].isdigit():
        year = p[:4]
    return base_dir / year


def save_metadata_json(target_dir: Path, record: PaperRecord) -> Path:
    target_dir.mkdir(parents=True, exist_ok=True)
    path = target_dir / f"{record.paper_id}.json"
    payload: Dict[str, object] = {
        "source": record.source,
        "paper_id": record.paper_id,
        "title": record.title,
        "authors": list(record.authors),
        "summary": record.summary,
        "published": record.published,
        "abs_url": record.abs_url,
        "pdf_url": record.pdf_url,
        "primary_category": record.primary_category,
        "github_url": record.github_url,
        "is_hf_trending": record.is_hf_trending,
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def download_pdf(
    target_dir: Path,
    record: PaperRecord,
    timeout_s: int = 60,
    retries: int = 3,
    backoff_s: float = 1.0,
) -> Path:
    target_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{record.paper_id}.pdf"
    pdf_path = target_dir / filename

    if not record.pdf_url:
        raise ValueError("pdf_url is empty")

    if pdf_path.exists() and pdf_path.stat().st_size > 0:
        return pdf_path

    headers = {"User-Agent": "Mozilla/5.0"}
    last_exc: Exception | None = None
    for attempt in range(max(1, retries)):
        tmp_path = pdf_path.with_suffix(pdf_path.suffix + ".part")
        try:
            if tmp_path.exists():
                tmp_path.unlink()

            with requests.get(record.pdf_url, headers=headers, stream=True, timeout=timeout_s) as r:
                r.raise_for_status()
                with open(tmp_path, "wb") as f:
                    for chunk in r.iter_content(chunk_size=1024 * 256):
                        if chunk:
                            f.write(chunk)

            os.replace(tmp_path, pdf_path)
            return pdf_path
        except requests.exceptions.RequestException as e:
            last_exc = e
            if tmp_path.exists():
                try:
                    tmp_path.unlink()
                except OSError:
                    pass
            if attempt >= max(1, retries) - 1:
                break
            time.sleep(backoff_s * (2**attempt))

    assert last_exc is not None
    raise last_exc
