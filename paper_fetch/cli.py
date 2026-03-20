from __future__ import annotations

import argparse
import csv
import json
import random
import sys
import time
from pathlib import Path
from typing import List

import requests
from tqdm import tqdm

from .arxiv_client import fetch_arxiv_by_ids, search_arxiv
from .hf_trending import fetch_hf_search_arxiv_ids, fetch_hf_trending_arxiv_ids
from .llm_client import LLMConfigError, chat_completion, load_llm_config
from .openreview_client import fetch_openreview_notes, notes_to_records
from .report import render_basic_report, write_report
from .storage import download_pdf, record_dir, save_metadata_json

def _sleep_pdf_throttle(*, backoff_multiplier: float) -> None:
    s = random.uniform(1.5, 3.0) * max(1.0, backoff_multiplier)
    time.sleep(s)


def _parse_list(values: List[str]) -> List[str]:
    out: List[str] = []
    for v in values:
        v = v.strip()
        if not v:
            continue
        out.append(v)
    return out


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="paper-fetch")
    p.add_argument("--out", required=True, help="output directory")
    p.add_argument("--collection", default="", help="outer collection folder name under --out")
    p.add_argument("--keyword", action="append", default=[], help="arXiv keyword query snippet, can be repeated")
    p.add_argument("--category", action="append", default=[], help="arXiv category like cs.CV, can be repeated")

    p.add_argument("--arxiv-max", type=int, default=0, help="number of arXiv papers to fetch")
    p.add_argument("--hf-max", type=int, default=0, help="number of HuggingFace daily papers ids to fetch (for HOT marking)")
    p.add_argument(
        "--hf-search",
        action="append",
        default=[],
        help="HuggingFace Papers search query string (can be repeated)",
    )
    p.add_argument("--hf-search-max", type=int, default=0, help="number of HuggingFace search results to fetch")
    p.add_argument("--openreview-max", type=int, default=0, help="number of OpenReview notes to fetch")
    p.add_argument("--openreview-invitation", default="", help="OpenReview invitation id, e.g. <venue>/-/Submission")

    p.add_argument("--no-hf-trending", action="store_true", help="disable HuggingFace trending marking")
    p.add_argument("--no-pdf", action="store_true", help="do not download PDFs (save metadata only)")

    p.add_argument(
        "--allow-empty-arxiv-query",
        action="store_true",
        help="allow running arXiv fetch with no --keyword and no --category",
    )

    p.add_argument("--enable-llm", action="store_true", help="enable LLM analysis and write analysis.md")
    p.add_argument("--analysis-out", default="analysis.md", help="markdown report output path (default: ./analysis.md)")
    p.add_argument(
        "--llm-instruction",
        default="",
        help="LLM analysis instruction text. If empty and --enable-llm is set, will prompt interactively in terminal.",
    )
    p.add_argument(
        "--llm-no-interactive",
        action="store_true",
        help="do not prompt for LLM instruction (use default instruction if --llm-instruction is empty)",
    )
    p.add_argument(
        "--llm-max-papers",
        type=int,
        default=30,
        help="max number of local paper JSON metadata entries to include in LLM prompt",
    )
    return p


def _ensure_source_dirs(base_out: Path, collection: str) -> tuple[Path, dict[str, Path]]:
    root = base_out / collection
    d = {
        "arxiv": root / "_arXiv",
        "hf": root / "_Huggingface",
        "openreview": root / "_OpenReview",
    }
    root.mkdir(parents=True, exist_ok=True)
    for p in d.values():
        p.mkdir(parents=True, exist_ok=True)
    return root, d


def _read_llm_instruction_interactive() -> str:
    print("\nEnter LLM analysis instructions. End with an empty line (or Ctrl-D).", file=sys.stderr)
    lines: list[str] = []
    while True:
        try:
            line = input()
        except EOFError:
            break
        if line.strip() == "":
            break
        lines.append(line)
    return "\n".join(lines).strip()


def _iter_metadata_json_files(root: Path) -> List[Path]:
    if not root.exists():
        return []
    paths = sorted(root.rglob("*.json"))
    out: List[Path] = []
    for p in paths:
        if p.name in ("index.json", "index.csv", "index.jsonl"):
            continue
        out.append(p)
    return out


def _write_index_files(root: Path, records: list[object]) -> None:
    jsonl_path = root / "index.jsonl"
    csv_path = root / "index.csv"

    source_dir = {
        "arxiv": root / "_arXiv",
        "hf": root / "_Huggingface",
        "openreview": root / "_OpenReview",
    }

    rows: list[dict[str, object]] = []
    for rec in records:
        if not hasattr(rec, "paper_id"):
            continue
        r = rec  # PaperRecord
        src = str(getattr(r, "source", ""))
        base = source_dir.get(src)
        if base is None:
            base = root / f"_{src}"

        ydir = record_dir(base, r)
        local_pdf_path = str(ydir / f"{r.paper_id}.pdf")
        local_meta_path = str(ydir / f"{r.paper_id}.json")
        rows.append(
            {
                "source": src,
                "paper_id": getattr(r, "paper_id", ""),
                "title": getattr(r, "title", ""),
                "authors": "; ".join([str(a) for a in (getattr(r, "authors", []) or [])]),
                "published": getattr(r, "published", ""),
                "primary_category": getattr(r, "primary_category", ""),
                "abs_url": getattr(r, "abs_url", ""),
                "pdf_url": getattr(r, "pdf_url", ""),
                "github_url": getattr(r, "github_url", ""),
                "local_meta_path": local_meta_path,
                "local_pdf_path": local_pdf_path,
            }
        )

    try:
        with open(jsonl_path, "w", encoding="utf-8") as f:
            for row in rows:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")
    except OSError:
        pass

    try:
        fieldnames = [
            "source",
            "paper_id",
            "title",
            "authors",
            "published",
            "primary_category",
            "abs_url",
            "pdf_url",
            "github_url",
            "local_meta_path",
            "local_pdf_path",
        ]
        with open(csv_path, "w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=fieldnames)
            w.writeheader()
            for row in rows:
                w.writerow({k: row.get(k, "") for k in fieldnames})
    except OSError:
        pass


def _build_llm_metadata_digest(paths: List[Path], max_papers: int) -> str:
    lines: list[str] = []
    count = 0
    for p in paths:
        if max_papers > 0 and count >= max_papers:
            break
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue

        title = str(data.get("title", ""))
        paper_id = str(data.get("paper_id", ""))
        source = str(data.get("source", ""))
        published = str(data.get("published", ""))
        primary_category = str(data.get("primary_category", ""))
        github_url = data.get("github_url")
        authors = data.get("authors") or []
        if not isinstance(authors, list):
            authors = []
        author_str = ", ".join([str(a) for a in authors[:10]])
        summary = str(data.get("summary", ""))
        summary = " ".join(summary.split())
        if len(summary) > 500:
            summary = summary[:500] + "..."

        lines.append(f"- source: {source}")
        lines.append(f"  id: {paper_id}")
        lines.append(f"  title: {title}")
        if author_str:
            lines.append(f"  authors: {author_str}")
        if published:
            lines.append(f"  published: {published}")
        if primary_category and primary_category != "None":
            lines.append(f"  category: {primary_category}")
        if github_url:
            lines.append(f"  github: {github_url}")
        if summary:
            lines.append(f"  summary: {summary}")
        lines.append("")
        count += 1

    return "\n".join(lines).strip() + "\n"


def main(argv: List[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    base_out_dir = Path(args.out).expanduser().resolve()
    collection = (args.collection or "").strip()
    if not collection:
        print("[WARN] --collection is empty. Please provide --collection for the outer folder name.", file=sys.stderr)
        return 2
    root_dir, src_dirs = _ensure_source_dirs(base_out_dir, collection)
    keywords = _parse_list(args.keyword)
    categories = _parse_list(args.category)
    hf_search_queries = _parse_list(args.hf_search)

    if int(args.arxiv_max) > 0 and not keywords and not categories and not args.allow_empty_arxiv_query:
        print(
            "[WARN] Refuse to run arXiv fetch with empty query. Provide --keyword/--category, or pass --allow-empty-arxiv-query.",
            file=sys.stderr,
        )
        return 2

    hf_ids = set()
    hf_search_ids: List[str] = []

    if (int(args.hf_max) > 0) and (not args.no_hf_trending):
        try:
            hf_ids = fetch_hf_trending_arxiv_ids(max_items=args.hf_max)
        except Exception as e:
            print(f"[HUGGINGFACE_ERROR] {e}", file=sys.stderr)
            hf_ids = set()

    hf_search_max = max(0, int(args.hf_search_max))
    if hf_search_max > 0 and hf_search_queries:
        remaining = hf_search_max
        for q in hf_search_queries:
            if remaining <= 0:
                break
            try:
                batch = fetch_hf_search_arxiv_ids(query=q, max_items=remaining)
            except Exception as e:
                print(f"[HUGGINGFACE_SEARCH_ERROR] {e}", file=sys.stderr)
                batch = []
            for pid in batch:
                if pid in hf_ids:
                    continue
                if pid in hf_search_ids:
                    continue
                hf_search_ids.append(pid)
                remaining -= 1
                if remaining <= 0:
                    break

    try:
        (src_dirs["hf"] / "trending_arxiv_ids.txt").write_text(
            "\n".join(sorted(hf_ids)),
            encoding="utf-8",
        )
    except OSError:
        pass

    if hf_search_ids:
        try:
            (src_dirs["hf"] / "search_arxiv_ids.txt").write_text(
                "\n".join(hf_search_ids),
                encoding="utf-8",
            )
        except OSError:
            pass

    arxiv_records = []
    hf_records = []
    openreview_records = []

    arxiv_total = max(0, int(args.arxiv_max))
    if arxiv_total > 0:
        arxiv_meta_start = time.time()
        with tqdm(total=arxiv_total, desc="arXiv meta", unit="paper") as pbar:
            for rec in search_arxiv(
                keywords=keywords,
                categories=categories,
                max_results=args.arxiv_max,
                hf_trending_ids=hf_ids,
            ):
                pbar.update(1)
                d = record_dir(src_dirs["arxiv"], rec)
                save_metadata_json(d, rec)
                arxiv_records.append(rec)

                hot = "HOT" if rec.is_hf_trending else ""
                code = "CODE" if rec.github_url else ""
                tail = " ".join([x for x in [hot, code] if x])
                if tail:
                    tail = " [" + tail + "]"
                print(f"{rec.paper_id}{tail} {rec.title}")

    if arxiv_total > 0:
        arxiv_meta_elapsed = max(0.0, time.time() - arxiv_meta_start)
        print(f"[INFO] arXiv metadata done: {len(arxiv_records)}/{arxiv_total} elapsed={arxiv_meta_elapsed:0.1f}s", file=sys.stderr)
        if len(arxiv_records) == 0:
            print(
                "[WARN] arXiv returned 0 results for the given --keyword/--category. Stop.",
                file=sys.stderr,
            )
            return 2

    if arxiv_records and (not args.no_pdf):
        pdf_start = time.time()
        pdf_total = len(arxiv_records)
        pdf_backoff = 1.0
        for rec in tqdm(arxiv_records, total=pdf_total, desc="PDF", unit="paper"):
            d = record_dir(src_dirs["arxiv"], rec)
            try:
                download_pdf(d, rec)
                _sleep_pdf_throttle(backoff_multiplier=pdf_backoff)
            except Exception as e:
                if isinstance(e, requests.exceptions.HTTPError) and e.response is not None:
                    if int(e.response.status_code) in (429, 503):
                        pdf_backoff *= 2
                print(f"{rec.paper_id} [PDF_ERROR] {e}")
                _sleep_pdf_throttle(backoff_multiplier=pdf_backoff)
        pdf_elapsed = max(0.0, time.time() - pdf_start)
        print(f"[INFO] PDF download done: {pdf_total} elapsed={pdf_elapsed:0.1f}s", file=sys.stderr)

    hf_total = len(hf_ids) + len(hf_search_ids)
    if hf_total > 0:
        hf_meta_start = time.time()
        with tqdm(total=hf_total, desc="HF meta", unit="paper") as pbar:
            if hf_ids:
                for rec in fetch_arxiv_by_ids(paper_ids=sorted(hf_ids), source="hf", is_hf_trending=True):
                    pbar.update(1)
                    d = record_dir(src_dirs["hf"], rec)
                    save_metadata_json(d, rec)
                    hf_records.append(rec)
                    code = "CODE" if rec.github_url else ""
                    tail = f" [{code}]" if code else ""
                    print(f"{rec.paper_id}{tail} {rec.title}")

            if hf_search_ids:
                for rec in fetch_arxiv_by_ids(paper_ids=hf_search_ids, source="hf", is_hf_trending=False):
                    pbar.update(1)
                    d = record_dir(src_dirs["hf"], rec)
                    save_metadata_json(d, rec)
                    hf_records.append(rec)
                    code = "CODE" if rec.github_url else ""
                    tail = f" [{code}]" if code else ""
                    print(f"{rec.paper_id}{tail} {rec.title}")

        hf_meta_elapsed = max(0.0, time.time() - hf_meta_start)
        print(f"[INFO] HF metadata done: {len(hf_records)}/{hf_total} elapsed={hf_meta_elapsed:0.1f}s", file=sys.stderr)

        if hf_records and (not args.no_pdf):
            hf_pdf_start = time.time()
            hf_pdf_total = len(hf_records)
            hf_pdf_backoff = 1.0
            for rec in tqdm(hf_records, total=hf_pdf_total, desc="HF PDF", unit="paper"):
                d = record_dir(src_dirs["hf"], rec)
                try:
                    download_pdf(d, rec)
                    _sleep_pdf_throttle(backoff_multiplier=hf_pdf_backoff)
                except Exception as e:
                    if isinstance(e, requests.exceptions.HTTPError) and e.response is not None:
                        if int(e.response.status_code) in (429, 503):
                            hf_pdf_backoff *= 2
                    print(f"{rec.paper_id} [HF_PDF_ERROR] {e}")
                    _sleep_pdf_throttle(backoff_multiplier=hf_pdf_backoff)
            hf_pdf_elapsed = max(0.0, time.time() - hf_pdf_start)
            print(f"[INFO] HF PDF download done: {hf_pdf_total} elapsed={hf_pdf_elapsed:0.1f}s", file=sys.stderr)

    if args.openreview_max and args.openreview_invitation:
        try:
            notes = fetch_openreview_notes(
                invitation=args.openreview_invitation,
                max_results=args.openreview_max,
            )
            or_start = time.time()
            or_total = len(notes)
            for rec in tqdm(
                list(notes_to_records(notes, invitation=args.openreview_invitation)),
                total=max(1, or_total),
                desc="OpenReview",
                unit="paper",
            ):
                d = record_dir(src_dirs["openreview"], rec)
                save_metadata_json(d, rec)
                openreview_records.append(rec)
                print(f"{rec.paper_id} {rec.title}")
            or_elapsed = max(0.0, time.time() - or_start)
            print(f"[INFO] OpenReview done: {len(openreview_records)}/{max(1, int(args.openreview_max))} elapsed={or_elapsed:0.1f}s", file=sys.stderr)
        except Exception as e:
            print(f"[OPENREVIEW_ERROR] {e}")

    if args.enable_llm:
        report_path = Path(args.analysis_out).expanduser().resolve()
        md = render_basic_report(arxiv_records=arxiv_records, hf_records=hf_records, openreview_records=openreview_records)

        default_instruction = (
            "Write a concise research digest for the fetched papers. "
            "Include: key themes, 5 papers to read first with reasons, and 3 potential research ideas."
        )

        instruction = (args.llm_instruction or "").strip()
        if not instruction and (not args.llm_no_interactive) and sys.stdin.isatty():
            instruction = _read_llm_instruction_interactive()
        if not instruction:
            instruction = default_instruction

        meta_paths: List[Path] = []
        meta_paths.extend(_iter_metadata_json_files(src_dirs["arxiv"]))
        meta_paths.extend(_iter_metadata_json_files(src_dirs["hf"]))
        meta_paths.extend(_iter_metadata_json_files(src_dirs["openreview"]))
        digest = _build_llm_metadata_digest(meta_paths, int(args.llm_max_papers))

        try:
            base_url, api_key, model = load_llm_config()
            prompt = (
                instruction.strip()
                + "\n\n"
                + "IMPORTANT: Analyze ONLY the local metadata below (extracted from local paper JSON metadata files). Do NOT assume you read PDFs.\n\n"
                + "Local metadata digest:\n\n"
                + digest
                + "\n\n"
                + "Also keep the response concise."
            )
            analysis = chat_completion(base_url=base_url, api_key=api_key, model=model, prompt=prompt)
            md = md + "\n## LLM Analysis\n\n" + analysis.strip() + "\n"
            write_report(report_path, md)
            print(f"[INFO] analysis written: {report_path}", file=sys.stderr)
        except LLMConfigError as e:
            print(f"[LLM_CONFIG_ERROR] {e}", file=sys.stderr)
            return 2
        except Exception as e:
            print(f"[LLM_ERROR] {e}", file=sys.stderr)
            return 2

    try:
        _write_index_files(root_dir, arxiv_records + hf_records + openreview_records)
    except Exception:
        pass

    return 0
