# Paper Fetch（中文说明）

本项目是一个轻量的论文抓取与本地保存工具，支持：

- arXiv：按关键词/分类检索论文，保存 `metadata.json`，并可选下载 PDF
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
  --arxiv-max 20 \
  --keyword '"<你的关键词>"' \
  --category cs.CV \
  --category cs.LG
```

参数说明：

- `--keyword`：arXiv 查询片段（遵循 arXiv 查询语法，可使用 `ti:` / `abs:` 等字段前缀与布尔运算）。
- `--category`：arXiv 分类过滤。

### 3）抓取 HuggingFace Papers（Trending）

```bash
python -m paper_fetch \
  --out ./papers \
  --hf-max 30
```

参数说明：

- `--hf-max`：抓取 HuggingFace Papers 的每日 trending 列表，并将对应论文保存到 `_Huggingface`。

### 4）抓取 HuggingFace Papers（关键词搜索）

```bash
python -m paper_fetch \
  --out ./papers \
  --hf-search '<你的查询>' \
  --hf-search-max 30
```

参数说明：

- `--hf-search`：HuggingFace Papers 的搜索查询（用于 https://huggingface.co/papers?q=... 的纯文本查询；不是 arXiv 查询语法）。
- `--hf-search-max`：HuggingFace Papers 搜索结果抓取总数上限。

输出目录结构（每次运行会自动创建当天日期文件夹）：

- `./papers/<YYYY-MM-DD>/_arXiv/<论文标题>/metadata.json`
- `./papers/<YYYY-MM-DD>/_arXiv/<论文标题>/<paper_id> - <title>.pdf`（仅 arXiv，且未开启 `--no-pdf` 时才会下载）
- `./papers/<YYYY-MM-DD>/_Huggingface/trending_arxiv_ids.txt`
- `./papers/<YYYY-MM-DD>/_Huggingface/search_arxiv_ids.txt`
- `./papers/<YYYY-MM-DD>/_Huggingface/<paper_id>/metadata.json`
- `./papers/<YYYY-MM-DD>/_Huggingface/<paper_id>/<paper_id> - <title>.pdf`（未开启 `--no-pdf` 时才会下载）
- `./papers/<YYYY-MM-DD>/_OpenReview/<论文标题>/metadata.json`

目录命名说明：

- 按数据源分目录：`_arXiv` / `_Huggingface` / `_OpenReview`
- 每篇论文用“论文标题”创建子目录；若出现重名冲突，会自动在目录名后追加论文 id

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
  --openreview-max 200 \
  --openreview-invitation '<OpenReview invitation id>' \
  --no-pdf
```

说明：

- 由于 OpenReview 的 PDF 链接结构不统一，本实现默认只保存 `metadata.json`，建议加 `--no-pdf`

### 6）可选：启用 LLM 分析（默认不使用）

默认行为：

- **不加 `--enable-llm`**：只抓取/保存，不会生成 `analysis.md`

启用方式：

```bash
python -m paper_fetch \
  --out ./papers \
  --arxiv-max 20 \
  --enable-llm
```

非交互示例：

```bash
python -m paper_fetch \
  --out ./papers \
  --arxiv-max 20 \
  --enable-llm \
  --llm-no-interactive \
  --llm-instruction '<你的分析指令>' \
  --llm-max-papers 30
```

## `--keyword` 支持哪些关键词/写法？

结论：

- `--keyword` 是 **arXiv 的查询语句片段**。
- 语法上你可以输入各种关键词（如 `LLM` / `RL` / `flow matching` / 冷门主题）。
- 但是否能抓到取决于 arXiv 是否有匹配结果：若返回 0 条，本工具会停止并警告（不会强行抓取）。

常用写法示例：

```text
# 直接短语
--keyword '"large language model"'

# 指定字段：ti=标题 abs=摘要 au=作者
--keyword 'ti:"transformer"'
--keyword 'abs:"reinforcement learning"'
--keyword 'au:"Yann LeCun"'

# 布尔组合
--keyword '(ti:"transformer" AND abs:"efficient")'
```

本工具的拼接规则：

- 多个 `--keyword` 会按 `(kw1 OR kw2 OR ...)` 合并
- 多个 `--category` 会按 `(cat1 OR cat2 OR ...)` 合并
- 最终查询为：`(keywords_part) AND (categories_part)`

推荐 AI 方向常用分类（可多选）：

- `cs.LG`（机器学习）
- `cs.AI`（人工智能）
- `cs.CV`（计算机视觉）
- `cs.CL`（自然语言处理）
- `cs.RO`（机器人）
- `stat.ML`（统计机器学习）

## 可选：启用 LLM 分析（默认不使用）

默认行为：

- **不加 `--enable-llm`**：只抓取/保存，不会生成 `analysis.md`

启用方式：

```bash
python -m paper_fetch \
  --out ./papers \
  --arxiv-max 20 \
  --enable-llm
```

LLM 分析说明（省 token 的关键点）：

- LLM 只分析本地落盘的 `metadata.json`（标题/作者/摘要等），**不会读取 PDF**
- LLM 会在抓取完成并保存到本地后再执行分析
- 你可以在终端交互输入“如何分析”（多行输入，空行结束）；也可以用参数非交互指定

非交互示例：

```bash
python -m paper_fetch \
  --out ./papers \
  --arxiv-max 20 \
  --enable-llm \
  --llm-no-interactive \
  --llm-instruction '<你的分析指令>' \
  --llm-max-papers 30
```

配置环境变量（OpenAI 接口兼容）：

```bash
export LLM_BASE_URL='https://api.openai.com/v1'
export LLM_API_KEY='YOUR_API_KEY'
export LLM_MODEL='<你的模型 id>'
```

支持/可用的模型：

- 本项目会把 `LLM_MODEL` 原样传给 `LLM_BASE_URL` 对应的 OpenAI 兼容接口。
- 因此你可以使用你的服务端实际提供的任意模型 id。
- 示例（取决于服务端/平台）：`gpt-4o-mini`、`gpt-4o`、`gpt-4.1-mini`。

## 常用参数速查

- `--out`
  - 输出根目录

- `--arxiv-max`
  - arXiv 抓取数量
  - 默认：`0`

- `--hf-max`
  - HuggingFace Papers 页面抓取前 N 条 arXiv id（用于 HOT 标记）
  - 默认：`0`

HuggingFace 两种模式：

- Trending 模式（抓取每日 trending 列表，并将对应论文保存到 `_Huggingface`）：

```bash
python -m paper_fetch \
  --out ./papers \
  --hf-max 30
```

- 关键词搜索模式（在 HuggingFace Papers 里按关键词搜索，并将匹配论文保存到 `_Huggingface`）：

```bash
python -m paper_fetch \
  --out ./papers \
  --hf-search '<你的查询>' \
  --hf-search-max 30
```

- `--hf-search`
  - HuggingFace Papers 搜索查询字符串
  - 可重复传入

- `--hf-search-max`
  - HuggingFace Papers 搜索结果抓取数量
  - 默认：`0`

- `--openreview-max`
  - OpenReview 抓取数量（默认 0，不抓取）

- `--openreview-invitation`
  - OpenReview invitation（决定抓哪个会议/期刊/轨道）

- `--no-pdf`
  - 不下载 PDF，仅保存 `metadata.json`

- `--enable-llm`
  - 启用 LLM 分析并生成 `analysis.md`

- `--analysis-out`
  - 分析报告输出路径（默认 `analysis.md`）

- `--llm-instruction`
  - LLM 分析指令文本（为空则终端交互输入）

- `--llm-no-interactive`
  - 禁止交互输入（为空则使用默认指令）

- `--llm-max-papers`
  - 限制写入 LLM prompt 的论文条目数量，用于控制 token
