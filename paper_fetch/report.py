from __future__ import annotations

import datetime
from pathlib import Path
from typing import Iterable, List, Sequence

from .models import PaperRecord


def render_basic_report(
    *,
    arxiv_records: Sequence[PaperRecord],
    openreview_records: Sequence[PaperRecord],
) -> str:
    today = datetime.date.today().isoformat()

    lines: List[str] = []
    lines.append(f"# Paper Fetch Report ({today})")
    lines.append("")

    if arxiv_records:
        lines.append(f"## arXiv ({len(arxiv_records)})")
        lines.append("")
        for r in arxiv_records:
            tags: List[str] = []
            if r.is_hf_trending:
                tags.append("HOT")
            if r.github_url:
                tags.append("CODE")
            tag = f" [{' '.join(tags)}]" if tags else ""
            lines.append(f"- **{r.paper_id}**{tag} {r.title}")
            lines.append(f"  - published: {r.published}")
            lines.append(f"  - pdf: {r.pdf_url}")
            lines.append(f"  - abs: {r.abs_url}")
            if r.github_url:
                lines.append(f"  - code: {r.github_url}")
        lines.append("")

    if openreview_records:
        lines.append(f"## OpenReview ({len(openreview_records)})")
        lines.append("")
        for r in openreview_records:
            lines.append(f"- **{r.paper_id}** {r.title}")
            if r.abs_url:
                lines.append(f"  - url: {r.abs_url}")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def write_report(path: Path, markdown: str) -> Path:
    path.write_text(markdown, encoding="utf-8")
    return path
