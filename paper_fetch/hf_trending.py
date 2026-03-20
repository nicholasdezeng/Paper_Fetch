from __future__ import annotations

import re
from typing import List, Set
from urllib.parse import quote_plus

import requests
from bs4 import BeautifulSoup


def fetch_hf_trending_arxiv_ids(max_items: int | None = None, timeout_s: int = 20) -> Set[str]:
    url = "https://huggingface.co/papers"
    headers = {"User-Agent": "Mozilla/5.0"}
    resp = requests.get(url, headers=headers, timeout=timeout_s)
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")
    ordered: list[str] = []
    seen: set[str] = set()
    for a in soup.find_all("a", href=re.compile(r"/papers/\d+\.\d+")):
        href = a.get("href")
        if not href:
            continue
        pid = href.split("/")[-1]
        pid = pid.split("#", 1)[0]
        pid = pid.split("?", 1)[0]
        if pid in seen:
            continue
        seen.add(pid)
        ordered.append(pid)
        if max_items is not None and len(ordered) >= max_items:
            break
    return set(ordered)


def fetch_hf_search_arxiv_ids(*, query: str, max_items: int | None = None, timeout_s: int = 20) -> List[str]:
    q = (query or "").strip()
    if not q:
        return []

    url = f"https://huggingface.co/papers?q={quote_plus(q)}"
    headers = {"User-Agent": "Mozilla/5.0"}
    resp = requests.get(url, headers=headers, timeout=timeout_s)
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")
    ordered: list[str] = []
    seen: set[str] = set()
    for a in soup.find_all("a", href=re.compile(r"/papers/\d+\.\d+")):
        href = a.get("href")
        if not href:
            continue
        pid = href.split("/")[-1]
        pid = pid.split("#", 1)[0]
        pid = pid.split("?", 1)[0]
        if pid in seen:
            continue
        seen.add(pid)
        ordered.append(pid)
        if max_items is not None and len(ordered) >= max_items:
            break
    return ordered
