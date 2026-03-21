# Paper Fetch

A minimal paper fetching & saving tool for:

- arXiv search (with optional HuggingFace Papers HOT marking)
- OpenReview notes fetching by invitation (conference/journal configurable)
- Optional LLM analysis (OpenAI-compatible API)

NOTE:

- OpenReview support is not fully stable yet.
- LLM features are still in testing.

English | [中文](#中文说明) | [完整中文文档](./README_zh.md)

## Quick Start

### 1) Install

```bash
python -m pip install -r requirements.txt
```

### 2) Run (arXiv + flat PDFs for Zotero linked attachments)

```bash
python -m paper_fetch \
  --out ./papers \
  --collection '<your collection>' \
  --arxiv-max 20 \
  --keyword '"<your keyword>"' \
  --category cs.CV \
  --category cs.LG \
  --pdf-dir _pdf
```

Parameters:

- `--keyword`: arXiv query snippet (arXiv query syntax; can use field prefixes like `ti:` / `abs:` and boolean operators).
- `--category`: arXiv category filter.
- `--pdf-dir _pdf`: write all PDFs into `./papers/<collection>/_pdf/` (flat directory), which is convenient for Zotero "Linked Attachments".

arXiv field prefixes (arXiv query syntax; this tool passes them through):

- `ti:` title
- `abs:` abstract
- `au:` author
- `co:` comment
- `jr:` journal reference
- `cat:` subject category
- `rn:` report number
- `id:` id (arXiv identifier)
- `all:` all fields

Common AI categories for `--category`:

- `cs.AI`: Artificial Intelligence
- `cs.CL`: Computation and Language
- `cs.CV`: Computer Vision and Pattern Recognition
- `cs.GR`: Computer Graphics
- `cs.LG`: Machine Learning
- `cs.MA`: Multiagent Systems
- `cs.NE`: Neural and Evolutionary Computing
- `cs.RO`: Robotics
- `eess.AS`: Audio and Speech Processing
- `eess.IV`: Image and Video Processing
- `eess.SP`: Signal Processing
- `stat.ML`: Machine Learning

Multiple `--keyword` / `--category`:

- All `--keyword` values are OR'ed: `(kw1 OR kw2 OR ...)`
- All `--category` values are OR'ed: `(cat1 OR cat2 OR ...)`
- Final query is: `(keywords_part) AND (categories_part)`

How many can you pass?

- There is no hard-coded max in this tool (they use `action="append"`).
- Practical limits come from your shell/OS command length and overly long arXiv query strings.

Example:

```bash
python -m paper_fetch \
  --out ./papers \
  --collection '<your collection>' \
  --arxiv-max 20 \
  --keyword 'ti:"diffusion"' \
  --keyword 'abs:"flow matching"' \
  --category cs.CV \
  --category cs.LG \
  --pdf-dir _pdf
```

Zotero (manual, recommended / most stable):

- Set `Settings -> Advanced -> Files and Folders -> Linked Attachment Base Directory` to the parent folder (e.g. `.../papers`).
- In Finder, open `./papers/<collection>/_pdf/`, select PDFs and drag them into Zotero.
- Choose `Link to File`, then (optional) right click PDFs: `Retrieve Metadata for PDF`.

### 3) Run (HuggingFace Papers: trending)

```bash
python -m paper_fetch \
  --out ./papers \
  --collection '<your collection>' \
  --hf-max 30
```

Parameters:

- `--hf-max`: fetch the daily HuggingFace Papers trending list and save those papers under `_Huggingface`.

### 4) Run (HuggingFace Papers: keyword search)

```bash
python -m paper_fetch \
  --out ./papers \
  --collection '<your collection>' \
  --hf-search '<your query>' \
  --hf-search-max 30
```

Parameters:

- `--hf-search`: HuggingFace Papers search query (plain text query for https://huggingface.co/papers?q=...; not arXiv query syntax).
- `--hf-search-max`: how many HuggingFace search results to fetch in total.

Notes:

- `--hf-search` is a best-effort scraper over the HuggingFace Papers search page. The matching behavior depends on HuggingFace and may change.
- Author-name queries (e.g. searching a person name) are not guaranteed to behave like an exact author filter.
- If you need author-precise search, use arXiv query syntax with `--keyword`, for example:

  ```text
  --keyword 'au:"<author name>"'
  ```

Optional LLM analysis (disabled by default):

- If you do nothing, **LLM analysis is not used** and no `analysis.md` is generated.
- To enable LLM analysis and generate `analysis.md`:

```bash
python -m paper_fetch \
  --out ./papers \
  --collection '<your collection>' \
  --arxiv-max 20 \
  --enable-llm
```

LLM behavior notes:

- LLM analyzes **local paper JSON metadata files only** (title/authors/summary/etc). It does **not** read PDFs.
- LLM runs **after fetching has been saved locally**, to reduce token usage.
- You can type your own analysis instruction in terminal (multi-line, end with empty line), or provide it non-interactively:

```bash
python -m paper_fetch \
  --out ./papers \
  --collection '<your collection>' \
  --arxiv-max 20 \
  --enable-llm \
  --llm-instruction 'Write a short digest of the fetched papers.'
```

Outputs:

- `./papers/<collection>/index.jsonl`
- `./papers/<collection>/index.csv`

- `./papers/<collection>/_arXiv/<YYYY>/<paper_id>.json`
- `./papers/<collection>/_arXiv/<YYYY>/<paper_id>.pdf` (only if `--no-pdf` is not set)

- `./papers/<collection>/_Huggingface/trending_arxiv_ids.txt`
- `./papers/<collection>/_Huggingface/search_arxiv_ids.txt`
- `./papers/<collection>/_Huggingface/<YYYY>/<paper_id>.json`
- `./papers/<collection>/_Huggingface/<YYYY>/<paper_id>.pdf` (only if `--no-pdf` is not set)

- `./papers/<collection>/_OpenReview/<YYYY>/<paper_id>.json`

When `--pdf-dir _pdf` is used:

- `./papers/<collection>/_pdf/<paper_id>.pdf`

No report is generated by default.

Notes:

- If arXiv returns **0 results**, the program stops with a warning and exit code `2`.

Folder naming:

- Outputs are written under `./papers/<collection>/` (controlled by `--collection`).
- Under that folder, outputs are separated by source: `_arXiv`, `_Huggingface`, `_OpenReview`.
- Under each source, papers are grouped by year: `<YYYY>/`.
- Each paper is stored as flat files: `<paper_id>.json` and (if enabled) `<paper_id>.pdf`.

### 5) Run (OpenReview)

You need an OpenReview `invitation` id.

How to find an `invitation` id (generic):

- Go to https://openreview.net
- Open the venue/group page you want to fetch (conference/journal/workshop/track).
- Find a submission invitation on that page (often contains `/-/Submission` or similar).
- Use the full invitation id string as the value of `--openreview-invitation`.

Invitation id examples (reference only):

```text
<VenueID>/<Year>/<Track>/-/Submission
<VenueID>/<Year>/<Track>/-/Blind_Submission
<VenueID>/<Year>/<Track>/-/Paper
```

Example:

```bash
python -m paper_fetch \
  --out ./papers \
  --collection '<your collection>' \
  --openreview-max 200 \
  --openreview-invitation '<OpenReview invitation id>' \
  --no-pdf
```

Note:

- OpenReview records usually do not include a direct `pdf_url` in this implementation, so `--no-pdf` is recommended.

### 4) LLM configuration (only needed when using `--enable-llm`)

Set environment variables:

```bash
export LLM_BASE_URL='https://api.openai.com/v1'
export LLM_API_KEY='YOUR_API_KEY'
export LLM_MODEL='<your model id>'
```

The report will be written to `./analysis.md` with an extra `LLM Analysis` section.

Supported / usable models:

- This project sends `LLM_MODEL` directly to the OpenAI-compatible provider specified by `LLM_BASE_URL`.
- Therefore, any chat/completions model that your provider exposes can be used.
- Examples (provider-dependent): `gpt-4o-mini`, `gpt-4o`, `gpt-4.1-mini`.

## What papers / topics can this project fetch?

This project does not hardcode a topic list. What you can fetch depends on the upstream data sources.

### arXiv (topic coverage)

- arXiv fetch is **query-based**.
- `--keyword` is passed into the arXiv search query (see examples below).
- Therefore, **any topic that arXiv indexes can be searched**, including common AI topics (LLM / RL / diffusion / flow matching) and rare topics.
- However, for rare topics or very strict queries, arXiv may return **0 results**. In that case this tool will stop and warn.

Practical guidance:

- If a term is rare, try:
  - removing quotes
  - searching in title/abstract only: `ti:` / `abs:`
  - using multiple synonyms as separate `--keyword` values (they are OR'ed)

Examples (query templates; not a full command):

```text
# simple phrase
--keyword '"<your phrase>"'

# field-specific query: ti=title abs=abstract au=author all=all fields
--keyword 'ti:"<term>"'
--keyword 'abs:"<term>"'
--keyword 'au:"<name>"'

# boolean composition
--keyword '(ti:"<term1>" AND abs:"<term2>")'
```

Keyword examples (concrete examples; not a full command):

```text
--keyword '"large language model"'
--keyword 'ti:"diffusion"'
--keyword 'abs:"reinforcement learning"'
--keyword '(ti:"transformer" AND abs:"efficient")'
```

Recommended arXiv categories for AI (you can combine multiple):

- `cs.LG` (Machine Learning)
- `cs.AI` (Artificial Intelligence)
- `cs.CV` (Computer Vision)
- `cs.CL` (Computation and Language / NLP)
- `cs.RO` (Robotics)
- `stat.ML` (Machine Learning)
- `eess.IV` (Image and Video Processing)

### OpenReview (topic coverage)

- OpenReview fetch is **venue/invitation-based**.
- If a conference/journal/workshop uses OpenReview, you can fetch it by providing `--openreview-invitation`.
- This means the coverage depends on whether that venue is hosted on OpenReview (many top ML venues are, but not all AI conferences are).

## CLI Options

All options are available from:

```bash
python -m paper_fetch --help
```

### Output

- `--out`
  - Output directory for all fetched records (required).

- `--analysis-out`
  - Path to write the markdown report.
  - Default: `analysis.md` (in current working directory).

### arXiv

- `--arxiv-max`
  - Number of arXiv papers to fetch.
  - Default: `0`.

- `--keyword`
  - arXiv query snippet (passed into the arXiv query string).
  - Supports field prefixes (e.g. `ti:`, `abs:`, `au:`, `all:`) and boolean operators.
  - Can be repeated.

    ```bash
    --keyword '"<phrase 1>"' --keyword '"<phrase 2>"'
    ```

    ```bash
    --keyword 'ti:"<term>"' --keyword 'abs:"<term>"'
    ```

    ```bash
    --keyword '(ti:"<term1>" AND abs:"<term2>")'
    ```

  - How this tool combines inputs:

    - All `--keyword` values are combined as:
      - `(kw1 OR kw2 OR kw3 ...)`

    - All `--category` values are combined as:
      - `(cat1 OR cat2 OR cat3 ...)`

    - Final query is:
      - `(keywords_part) AND (categories_part)`

  - Shell quoting tip:
    - Use single quotes `'...'` around each `--keyword` to avoid your shell interpreting parentheses and quotes.

- `--category`
  - arXiv category (e.g. `cs.CV`, `cs.LG`).
  - Can be repeated.

- `--allow-empty-arxiv-query`
  - By default, this tool refuses to run arXiv fetching when both `--keyword` and `--category` are empty.
  - Use this flag to explicitly allow an empty query.

### HuggingFace Papers (HOT marking)

- `--hf-max`
  - How many HuggingFace Papers ids to fetch from https://huggingface.co/papers.
  - Used only for HOT marking for arXiv IDs.
  - Default: `0`.

HuggingFace modes:

- Trending mode (download daily trending list and save those papers under `_Huggingface`):

```bash
python -m paper_fetch \
  --out ./papers \
  --hf-max 30
```

- Keyword search mode (search HuggingFace Papers and save matched papers under `_Huggingface`):

```bash
python -m paper_fetch \
  --out ./papers \
  --hf-search '<your query>' \
  --hf-search-max 30
```

- `--no-hf-trending`
  - Disable HuggingFace HOT marking.

- `--hf-search`
  - HuggingFace Papers search query string.
  - Can be repeated.

  Notes:

  - This is a plain search query for HuggingFace Papers (the `/papers?q=...` page).
  - This is different from arXiv `--keyword` which follows arXiv query syntax.

- `--hf-search-max`
  - Number of HuggingFace search results to fetch.
  - Default: `0`.

### PDF

- `--no-pdf`
  - Do not download PDFs. Only save local paper JSON metadata files.

- `--pdf-dir`
  - Override PDF output directory.
  - If relative, it is under `--out/--collection`.
  - Example: `--pdf-dir _pdf`.

### OpenReview

- `--openreview-max`
  - Number of OpenReview notes to fetch.
  - Default: `0` (disabled).

- `--openreview-invitation`
  - OpenReview invitation id.
  - Required when `--openreview-max > 0`.

### LLM

- `--enable-llm`
  - Enable LLM analysis and append results to the markdown report.
  - Default: disabled.

- `--llm-instruction`
  - Provide instruction text for LLM analysis.
  - If empty and `--enable-llm` is used, the CLI will prompt you interactively in the terminal.

- `--llm-no-interactive`
  - Disable the interactive prompt.
  - If `--llm-instruction` is empty, a default instruction will be used.

Environment variables (OpenAI-compatible):

- `LLM_BASE_URL`
  - Default: `https://api.openai.com/v1`

- `LLM_API_KEY`
  - Required when `--enable-llm` is used.

- `LLM_MODEL`
  - Default: `gpt-4o-mini`

## 中文说明

请直接阅读完整中文文档：[`README_zh.md`](./README_zh.md)

## Notes

- arXiv PDF downloads include retry + backoff; per-paper failures will not stop the whole run.
- OpenReview fetching requires a correct `invitation` id; different venues/years can differ.
