from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Sequence


@dataclass(frozen=True)
class PaperRecord:
    source: str
    paper_id: str
    title: str
    authors: Sequence[str]
    summary: str
    published: str
    abs_url: str
    pdf_url: str
    primary_category: Optional[str]
    github_url: Optional[str]
    is_hf_trending: bool
