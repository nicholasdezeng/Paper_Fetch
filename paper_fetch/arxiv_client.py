from __future__ import annotations

import re
from typing import Iterable, List, Optional, Sequence

import arxiv

from .models import PaperRecord


def _build_query(keywords: Sequence[str], categories: Sequence[str]) -> str:
    parts: List[str] = []
    if keywords:
        parts.append(f"({' OR '.join(keywords)})")
    if categories:
        parts.append(f"({' OR '.join(categories)})")
    return " AND ".join(parts) if parts else "all:electron"


def search_arxiv(
    *,
    keywords: Sequence[str],
    categories: Sequence[str],
    max_results: int,
    sort_by: arxiv.SortCriterion = arxiv.SortCriterion.SubmittedDate,
    hf_trending_ids: Optional[set[str]] = None,
) -> Iterable[PaperRecord]:
    query = _build_query(keywords, categories)
    search = arxiv.Search(query=query, max_results=max_results, sort_by=sort_by)

    trending = hf_trending_ids or set()

    for res in search.results():
        paper_id = res.entry_id.split("/")[-1]
        github_links = re.findall(r"https?://github\.com/[\w/-]+", res.summary or "")
        authors = [a.name for a in (res.authors or [])]

        yield PaperRecord(
            source="arxiv",
            paper_id=paper_id,
            title=res.title or "",
            authors=authors,
            summary=res.summary or "",
            published=res.published.strftime("%Y-%m-%d") if res.published else "",
            abs_url=res.entry_id,
            pdf_url=res.pdf_url,
            primary_category=getattr(res, "primary_category", None),
            github_url=github_links[0] if github_links else None,
            is_hf_trending=paper_id in trending,
        )


def fetch_arxiv_by_ids(
    *,
    paper_ids: Sequence[str],
    source: str,
    is_hf_trending: bool = False,
) -> Iterable[PaperRecord]:
    """Fetch arXiv metadata by explicit arXiv ids.

    This is used to turn external arXiv-id lists (e.g. HuggingFace Papers trending)
    into local saved records.
    """

    for pid in paper_ids:
        search = arxiv.Search(id_list=[pid], max_results=1)
        for res in search.results():
            paper_id = res.entry_id.split("/")[-1]
            github_links = re.findall(r"https?://github\.com/[\w/-]+", res.summary or "")
            authors = [a.name for a in (res.authors or [])]

            yield PaperRecord(
                source=source,
                paper_id=paper_id,
                title=res.title or "",
                authors=authors,
                summary=res.summary or "",
                published=res.published.strftime("%Y-%m-%d") if res.published else "",
                abs_url=res.entry_id,
                pdf_url=res.pdf_url,
                primary_category=getattr(res, "primary_category", None),
                github_url=github_links[0] if github_links else None,
                is_hf_trending=is_hf_trending,
            )
