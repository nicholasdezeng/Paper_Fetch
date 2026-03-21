# Paper Fetch（中文说明）

本项目是一个轻量的论文抓取与本地保存工具，支持：

- arXiv：按关键词/分类检索论文，保存元数据（每篇论文一个 `<paper_id>.json`），并可选下载 PDF
- HuggingFace Papers：抓取每日论文页面的 arXiv id，用于 HOT 标记（并落盘保存）
- OpenReview：按 `invitation` 抓取指定会议/期刊/Workshop 的 notes 元数据
- 可选 LLM 分析：兼容 OpenAI 接口风格（默认不启用），生成 `analysis.md`

注意：

- OpenReview 暂不支持完整功能。
- LLM 功能仍在测试中。

## 快速开始

### 1）安装依赖

在项目根目录执行：

```bash
python -m pip install -r requirements.txt
```

### 2）抓取 arXiv

```bash
python -m paper_fetch \
  --out ./papers \
  --collection '<你的 collection>' \
  --arxiv-max 20 \
  --keyword '"<你的关键词>"' \
  --category cs.CV \
  --category cs.LG \
  --pdf-dir _pdf
```

参数说明：

- `--keyword`：arXiv 查询片段（遵循 arXiv 查询语法，可使用 `ti:` / `abs:` 等字段前缀与布尔运算）。
- `--category`：arXiv 分类过滤。

arXiv 字段前缀（arXiv 查询语法；本工具会原样传递给 arXiv）：

- `ti:` 标题（title）
- `abs:` 摘要（abstract）
- `au:` 作者（author）
- `co:` 备注/评论（comment）
- `jr:` 期刊引用（journal reference）
- `cat:` 学科分类（subject category）
- `rn:` 报告编号（report number）
- `id:` arXiv 标识符（arXiv identifier）
- `all:` 所有字段（all fields）

AI 领域常用 `--category`（可多选）：

- `cs.AI`：Artificial Intelligence
- `cs.CL`：Computation and Language
- `cs.CV`：Computer Vision and Pattern Recognition
- `cs.GR`：Computer Graphics
- `cs.LG`：Machine Learning
- `cs.MA`：Multiagent Systems
- `cs.NE`：Neural and Evolutionary Computing
- `cs.RO`：Robotics
- `eess.AS`：Audio and Speech Processing
- `eess.IV`：Image and Video Processing
- `eess.SP`：Signal Processing
- `stat.ML`：Machine Learning

多个 `--keyword` / `--category` 的组合规则：

- 多个 `--keyword` 会按 `(kw1 OR kw2 OR ...)` 合并
- 多个 `--category` 会按 `(cat1 OR cat2 OR ...)` 合并
- 最终查询为：`(keywords_part) AND (categories_part)`

最多支持几个？

- 本工具本身没有写死上限（参数使用 `action="append"`，可重复传入）。
- 实际上限主要来自：命令行长度限制（shell/操作系统）以及 arXiv 查询字符串过长导致的失败/效果变差。

示例：

```bash
python -m paper_fetch \
  --out ./papers \
  --collection '<你的 collection>' \
  --arxiv-max 20 \
  --keyword 'ti:"diffusion"' \
  --keyword 'abs:"flow matching"' \
  --category cs.CV \
  --category cs.LG \
  --pdf-dir _pdf
```

Zotero 7 本地阅读/管理（推荐的最稳流程：Linked Attachments）：

- 先在 Zotero 设置 `设置 -> 高级 -> 文件和文件夹 -> 链接附件的基本目录（Linked Attachment Base Directory）` 为 `./papers` 这样的父目录（建议设更上层而不是只设 `_pdf`）。
- 在 Finder 打开 `./papers/<collection>/_pdf/`，全选 PDF 拖进 Zotero。
- 弹窗选择 `Link to File`（链接到文件），不要选择复制到 Zotero 存储。
- 需要自动元数据时：选中这些 PDF，右键 `Retrieve Metadata for PDF`。

### 3）抓取 HuggingFace Papers（Trending）

```bash
python -m paper_fetch \
  --out ./papers \
  --collection '<你的 collection>' \
  --hf-max 30
```

参数说明：

- `--hf-max`：抓取 HuggingFace Papers 的每日 trending 列表，并将对应论文保存到 `_Huggingface`。

### 4）抓取 HuggingFace Papers（关键词搜索）

```bash
python -m paper_fetch \
  --out ./papers \
  --collection '<你的 collection>' \
  --hf-search '<你的查询>' \
  --hf-search-max 30
```

参数说明：

- `--hf-search`：HuggingFace Papers 的搜索查询（用于 https://huggingface.co/papers?q=... 的纯文本查询；不是 arXiv 查询语法）。
- `--hf-search-max`：HuggingFace Papers 搜索结果抓取总数上限。

说明：

- `--hf-search` 是对 HuggingFace Papers 搜索页面的尽力抓取（匹配规则由 HuggingFace 决定，可能变化）。
- 用人名做查询不保证等价于“精确按作者过滤”。
- 如果你需要精确按作者检索，建议使用 arXiv 的查询语法（`--keyword`），例如：

  ```text
  --keyword 'au:"<作者名>"'
  ```

输出目录结构（以 collection 为外层；按年份归档；不再创建日期文件夹；不再“一篇一个文件夹”）：

- `./papers/<collection>/index.jsonl`
- `./papers/<collection>/index.csv`

- `./papers/<collection>/_arXiv/<YYYY>/<paper_id>.json`
- `./papers/<collection>/_arXiv/<YYYY>/<paper_id>.pdf`（未开启 `--no-pdf` 时才会下载）

- `./papers/<collection>/_Huggingface/trending_arxiv_ids.txt`
- `./papers/<collection>/_Huggingface/search_arxiv_ids.txt`
- `./papers/<collection>/_Huggingface/<YYYY>/<paper_id>.json`
- `./papers/<collection>/_Huggingface/<YYYY>/<paper_id>.pdf`（未开启 `--no-pdf` 时才会下载）

- `./papers/<collection>/_OpenReview/<YYYY>/<paper_id>.json`

当使用 `--pdf-dir _pdf` 时，所有 PDF 会平铺保存到：

- `./papers/<collection>/_pdf/<paper_id>.pdf`

目录命名说明：

- 按数据源分目录：`_arXiv` / `_Huggingface` / `_OpenReview`
- 在每个数据源目录下按年份归档：`<YYYY>/...`
- 单篇论文不再创建子目录；PDF 与元数据采用平铺文件：`<paper_id>.pdf` / `<paper_id>.json`

### 5）OpenReview 抓取

OpenReview 是“按会议/期刊 invitation”抓取，示例：

如何找到 `invitation id`（通用方法）：

- 打开 https://openreview.net
- 进入你要抓取的 venue/group 页面
- 在页面里找到“投稿/Submission”对应的 invitation（通常包含 `/-/Submission` 或类似形式）
- 把完整的 invitation 字符串填到 `--openreview-invitation`

invitation 形式示例（仅参考，不是一键命令）：

```text
<VenueID>/<Year>/<Track>/-/Submission
<VenueID>/<Year>/<Track>/-/Blind_Submission
<VenueID>/<Year>/<Track>/-/Paper
```

```bash
python -m paper_fetch \
  --out ./papers \
  --collection '<你的 collection>' \
  --openreview-max 200 \
  --openreview-invitation '<OpenReview invitation id>' \
  --no-pdf
```

说明：

- 由于 OpenReview 的 PDF 链接结构不统一，本实现默认只保存元数据（每篇论文一个 `<paper_id>.json`），建议加 `--no-pdf`

### 6）可选：启用 LLM 分析（默认不使用）

默认行为：

- **不加 `--enable-llm`**：只抓取/保存，不会生成 `analysis.md`

启用方式：

```bash
python -m paper_fetch \
  --out ./papers \
  --collection '<你的 collection>' \
  --arxiv-max 20 \
  --enable-llm
```

非交互示例：

```bash
python -m paper_fetch \
  --out ./papers \
  --collection '<你的 collection>' \
  --arxiv-max 20 \
  --enable-llm \
  --llm-no-interactive \
  --llm-instruction '<你的分析指令>' \
  --llm-max-papers 30
```

## 更多参数

请运行：

```bash
python -m paper_fetch --help
```

提示：复杂 `--keyword`（含括号/引号）建议用单引号包起来，避免 shell 解析出错。
