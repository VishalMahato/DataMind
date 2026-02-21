# Boardroom AI — Implementation & Logic Documentation

> Auto-generated documentation describing every module, its internal logic, and how they connect in the analysis pipeline.

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [Request Lifecycle](#2-request-lifecycle)
3. [Module Reference](#3-module-reference)
   - [app/main.py — Application Bootstrap](#31-appmainpy--application-bootstrap)
   - [app/api/routes.py — HTTP Endpoints](#32-appapiroutespy--http-endpoints)
   - [app/api/schemas.py — Pydantic Models](#33-appapischemaspy--pydantic-models)
   - [app/core/data_processor.py — Pipeline Orchestrator](#34-appcoredata_processorpy--pipeline-orchestrator)
   - [app/core/visualizer.py — Chart Specification & Data Aggregation](#35-appcorevisualizerpy--chart-specification--data-aggregation)
   - [app/core/chart_renderer.py — PNG Rendering](#36-appcorechart_rendererpy--png-rendering)
   - [app/core/trend_engine.py — Time-Series Trend Detection](#37-appcoretrend_enginepy--time-series-trend-detection)
   - [app/core/llm_engine.py — GPT-4o-mini Integration](#38-appcorellm_enginepy--gpt-4o-mini-integration)
   - [app/core/pdf_generator.py — PDF Export](#39-appcorepdf_generatorpy--pdf-export)
   - [app/core/report_renderer.py — HTML Rendering](#310-appcorereport_rendererpy--html-rendering)
4. [Data Flow Diagram](#4-data-flow-diagram)
5. [Key Algorithms & Design Decisions](#5-key-algorithms--design-decisions)

---

## 1. Architecture Overview

```
┌─────────────┐       POST /analyze        ┌──────────────┐
│   Frontend   │ ────────────────────────▶  │  FastAPI App  │
│  (React/Next)│ ◀────────────────────────  │   main.py     │
└─────────────┘     ReportResponse JSON     └──────┬───────┘
                                                   │
                          ┌────────────────────────┼────────────────────────┐
                          │                        │                        │
                   routes.py              data_processor.py           llm_engine.py
                  (endpoints)            (pipeline orchestrator)      (GPT-4o-mini)
                          │                        │
              ┌───────────┼────────────────────────┼──────────────┐
              │           │                        │              │
        visualizer.py  trend_engine.py    chart_renderer.py  pdf_generator.py
        (chart specs)  (trend + wow)      (Plotly → PNG)     (WeasyPrint/RL)
```

**Stack:**  FastAPI · Pydantic v2 · Pandas · Plotly + Kaleido · OpenAI GPT-4o-mini · WeasyPrint · ReportLab · Jinja2

---

## 2. Request Lifecycle

### POST /analyze (main flow)

```
  ┌──────────────────────────────────────────────────────────────────────┐
  │                     generate_report_from_file()                      │
  │                                                                      │
  │  Step 1 ─ VALIDATION          _read_dataframe()                     │
  │             ▼                  Read bytes → pd.read_csv()            │
  │  Step 2 ─ CLEANING            _clean_dataframe()                    │
  │             ▼                  Drop empties, dedup, strip, dates     │
  │  Step 3 ─ EDA                 _build_profiling() + trend_engine     │
  │             ▼                  Per-column stats, dtype, outliers     │
  │  Step 4 ─ CHARTS              visualizer + chart_renderer           │
  │             ▼                  Spec generation + Plotly PNG render   │
  │  Step 5 ─ LLM                 llm_engine (3 calls)                  │
  │             ▼                  Insights + KPI suggestions + Chat ctx │
  │  Step 6 ─ KPI TILES           _build_kpi_tiles()                    │
  │             ▼                  LLM-decided agg per column            │
  │  Step 7 ─ ARTIFACTS           Save JSON + HTML to /static/          │
  │                                                                      │
  │  ──▶  Return ReportResponse                                         │
  └──────────────────────────────────────────────────────────────────────┘
```

Each step is timed via `time.perf_counter()` and recorded as a `PipelineStep` with `ok`, `ms`, and `note` fields. The pipeline array is included in the response so the frontend can display step-by-step progress.

### POST /chat (conversational)

```
  ChatRequest { message, chat_context, history[] }
         │
         ▼
  chat_with_data()  →  GPT-4o-mini  →  { reply, suggested_followups }
         │
         ▼
  ChatResponse
```

### POST /pdf (export)

```
  PdfRequest { report }
         │
         ▼
  render_report_html()  →  WeasyPrint (or ReportLab fallback)  →  PDF file
```

---

## 3. Module Reference

### 3.1 `app/main.py` — Application Bootstrap

**Responsibility:** Create the FastAPI application instance, load environment variables, configure middleware, and mount routes.

| Action | Detail |
|--------|--------|
| `load_dotenv()` | Loads `.env` from project root so `OPENAI_API_KEY` is available via `os.getenv()` |
| `CORSMiddleware` | `allow_origins=["*"]` — permits any frontend origin (dev convenience) |
| `StaticFiles` | Mounts `BASE_DIR/static/` at `/static` for chart PNGs, report JSON/HTML |
| `include_router` | Attaches all API endpoints from `app/api/routes.py` |

---

### 3.2 `app/api/routes.py` — HTTP Endpoints

Four endpoints, all async. Synchronous CPU-bound work is offloaded via `loop.run_in_executor()` to avoid blocking the event loop.

#### `POST /analyze`

| Aspect | Detail |
|--------|--------|
| Input | `UploadFile` (multipart form) |
| Validation | Rejects non-`.csv` filenames → `400 INVALID_CSV` |
| Processing | `generate_report_from_file(file.file, file.filename)` in thread executor |
| Error | CSV parse failure → `422 CSV_PARSE_ERROR` |
| Output | `ReportResponse` (full JSON contract) |

#### `POST /pdf`

| Aspect | Detail |
|--------|--------|
| Input | `PdfRequest` containing a full `ReportResponse` body |
| Output | `FileResponse` (PDF binary download) |

#### `POST /chat`

| Aspect | Detail |
|--------|--------|
| Input | `ChatRequest` — message, chat_context, history (max 20 turns) |
| Processing | `chat_with_data()` in thread executor |
| Output | `ChatResponse` — reply + suggested followups |

#### `GET /health`

Returns `{"status": "ok"}`.

---

### 3.3 `app/api/schemas.py` — Pydantic Models

All request/response models in one file (~295 lines). Key types:

| Model | Purpose |
|-------|---------|
| `ReportResponse` | Top-level analysis result (18 fields) |
| `DatasetMeta` | File info: name, rows, cols, bytes, delimiter, encoding |
| `DataPreview` | First 5 rows as `List[Dict]` |
| `CleaningLogItem` | Each cleaning action with before/after state |
| `ProfilingSummary` | Per-column profiles + missing/unique counts |
| `ColumnProfile` | dtype, NumericStats, OutlierSummary, TopValue |
| `NumericStats` | min, max, mean, median, std |
| `OutlierSummary` | IQR method, count, bounds |
| `TrendSummary` | Availability, date/kpi column, summary text, metrics |
| `TrendMetrics` | start_value, end_value, pct_change |
| `WowFinding` | Anomaly/trend finding with severity + evidence |
| `ChartSpec` | Chart kind, axes, image URL, optional `chart_data` |
| `ChartDataPayload` | Discriminated union of 4 formats (see below) |
| `InsightPack` | executive_insights, risks, opportunities, actions |
| `KpiTile` | label, formatted value, sublabel |
| `PipelineStep` | Step name, ok flag, ms timing, note |
| `Artifacts` | URLs to saved JSON, HTML, PDF |
| `ChatContext` | dataset_brief, evidence_pack, suggested_questions |
| `ChatRequest/Response` | Multi-turn chat models |

#### ChartDataPayload — 4 Formats

| Format | Discriminator | Use Case |
|--------|--------------|----------|
| `series_xy` | `SeriesXYData` | Line charts — `[{x: "2025-01-01", y: 100}]` |
| `category_value` | `CategoryValueData` | Bar/pie — `[{category: "North", value: 500}]` |
| `bins` | `BinsData` | Histogram — `[{bin_start, bin_end, count}]` |
| `xy_points` | `XYPointsData` | Scatter — `[{x: 1.5, y: 2.3}]` |

---

### 3.4 `app/core/data_processor.py` — Pipeline Orchestrator

**The heart of the system.** Orchestrates the entire CSV → Report pipeline.

#### Helper Functions

| Function | Logic |
|----------|-------|
| `_fmt_number(n)` | Human-friendly formatting: `1234567 → "1.23M"`, `1234 → "1.23K"`, integers kept whole |
| `_read_dataframe(file_obj)` | Reads uploaded bytes into `pd.DataFrame` + records `size_bytes` |
| `_build_preview(df, max_rows=5)` | Extracts column names + first 5 rows as list-of-dicts |
| `_infer_dtype(series)` | Classifies a pandas Series into one of: `boolean`, `datetime`, `numeric`, `categorical`, `text`, `unknown` |
| `_build_profiling(df)` | Iterates all columns → `ColumnProfile` with stats, outliers (IQR), top values |
| `_clean_dataframe(df)` | 5-step cleaning pipeline (see below) |
| `_apply_agg(df, col, agg)` | Applies a named aggregation safely with fallback to 0.0 |
| `_sublabel_text(df, col, sub_agg)` | Formats a secondary aggregation as a sublabel string |
| `_build_kpi_tiles(df, profiling, trend)` | KPI tile builder using LLM-decided aggregations |

#### `_infer_dtype` Logic

```
  Series
    │
    ├── is_bool_dtype?     → "boolean"
    ├── is_datetime64?     → "datetime"
    ├── is_numeric_dtype?  → "numeric"
    ├── all null?          → "unknown"
    ├── is_string/object?
    │     └── pd.to_datetime(sample) succeeds?  → "datetime"
    ├── nunique ≤ max(10, 5% of rows)?          → "categorical"
    └── otherwise                                → "text"
```

**Key design choice:** Checks both `is_string_dtype` and `is_object_dtype` to handle pandas 2.x which uses `str` (not `object`) for string columns. Date-like strings (e.g. `"2025-01-01"`) are detected via `pd.to_datetime(sample, format="mixed")` before the categorical fallback.

#### `_clean_dataframe` — 5-Step Cleaning Pipeline

| Step | Action | Logic |
|------|--------|-------|
| 1 | Drop empty rows | `df.dropna(how="all")` |
| 2 | Drop empty columns | `df.dropna(axis=1, how="all")` |
| 3 | Drop duplicates | `df.drop_duplicates()` |
| 4 | Strip whitespace | `.str.strip()` on all object columns |
| 5 | Parse dates | For each string/object column, try `pd.to_datetime(sample, format="mixed")`. If all 20 sample values parse successfully, convert the full column. |

Each step logs a `CleaningLogItem` with action name, description, and before/after state. If no changes were needed, a single `"no_action"` entry is logged.

#### `_build_kpi_tiles` — LLM-Driven Aggregation

```
  Always included:
    ├── "Total Rows" (row count, col count sublabel)
    └── "Data Completeness" (100% − missing% , missing count sublabel)

  LLM path (generate_kpi_suggestions):
    │   GPT-4o-mini receives column names, dtypes, stats
    │   Returns: [{column, agg, label, sublabel_agg}, ...]
    │
    │   For each suggestion (max 6):
    │     ├── "count_distinct" → df[col].nunique()
    │     └── other agg        → _apply_agg(df, col, agg)
    │
    │   Examples of LLM decisions:
    │     revenue     → sum   (monetary, additive)
    │     margin_pct  → mean  (it's a percentage/rate)
    │     region      → count_distinct (categorical entity)
    │     order_id    → SKIP  (it's an ID column)

  Fallback (no API key):
    └── Sum first 3 numeric columns with avg sublabel

  Always appended:
    ├── Trend KPI tile (↑/↓ pct_change)
    └── Outlier count (if any)
```

Supported aggregation functions: `sum`, `mean`, `median`, `max`, `min`, `count`, `count_distinct`, `range`, `latest`.

#### `generate_report_from_file` — Main Orchestrator

| Pipeline Step | Key Call | Timed |
|---------------|----------|-------|
| `validation` | `_read_dataframe()` | ✓ |
| `cleaning` | `_clean_dataframe()` | ✓ |
| `eda` | `_build_profiling()` + `build_trend_and_findings()` | ✓ |
| `charts` | `generate_charts()` + `render_charts()` | ✓ |
| `llm` | `generate_insights()` | ✓ |
| — | `_build_kpi_tiles()` (includes LLM call) | — |
| — | `generate_chat_context()` (LLM call) | — |
| — | Save JSON + HTML artifacts to `static/{report_id}/` | — |

---

### 3.5 `app/core/visualizer.py` — Chart Specification & Data Aggregation

**Responsibility:** Decide which charts to generate based on the data shape, and build pre-aggregated `chart_data` payloads for frontend rendering.

#### Column Selection Heuristics

| Function | Logic |
|----------|-------|
| `_select_numeric_column(df)` | Iterates numeric columns, **skips IDs** (name matching `_id`, `_code`, `id_*` patterns + monotonically-increasing unique sequences). Prefers columns matching business keywords: `revenue`, `sales`, `amount`, `total`, `profit`, `income`, `value`, `price`, `cost`, `spend`, `earning`, `margin`, `quantity`, `units`, `count`. Falls back to first non-ID numeric. |
| `_select_categorical_column(df)` | Picks non-numeric columns with ≤ max(10, 10% of rows) unique values. Prefers names like `region`, `segment`, `category`. |
| `_select_datetime_column(df)` | First column with `datetime64` dtype, or fallback to column names containing `"date"` or `"time"`. |

#### Chart Generation Rules

| Chart Type | Condition | chart_data Format |
|-----------|-----------|-------------------|
| **Line** | datetime col + numeric col | `series_xy` — aggregates by date (mean), detects granularity (hour/day/week/month/quarter), caps at 500 points |
| **Bar** | categorical col + numeric col | `category_value` — sums by category, top 200 categories |
| **Histogram** | numeric col exists | `bins` — `np.histogram()` with `√n` bins (min 5, max 100) |

#### Data Aggregation Details

**Line (`_build_line_data`):**
- Groups by date, takes mean of duplicates
- Converts datetime to ISO-8601 strings
- Downsamples if > 500 points (even step)
- Auto-detects granularity from median diff between dates

**Bar (`_build_bar_data`):**
- Groups by category, sums numeric values
- Sorts descending by value
- Caps at 200 categories

**Histogram (`_build_histogram_data`):**
- Bin count = `min(20, max(5, √n))`, capped at 100
- Uses `numpy.histogram()` for even bin edges

---

### 3.6 `app/core/chart_renderer.py` — PNG Rendering

**Responsibility:** Take `ChartSpec` objects + DataFrame and produce PNG image files using Plotly + Kaleido.

| Function | Detail |
|----------|--------|
| `_render_line_chart()` | `go.Scatter(mode="lines+markers")`, layout with axis titles |
| `_render_bar_chart()` | `go.Bar()`, groups and sums by x-axis category |
| `_render_histogram()` | `go.Histogram(x=data)` |
| `_create_placeholder_png()` | Gray 960×480 image with "⚠ Chart unavailable" text (Pillow) |
| `render_charts()` | Iterates chart specs, renders each to `static/{report_id}/{chart_id}.png`. On failure, writes a placeholder. |

**Kaleido pinned to 0.2.1** — version 1.x has async Chromium issues that cause blank PNGs.

---

### 3.7 `app/core/trend_engine.py` — Time-Series Trend Detection

**Responsibility:** Detect time-series trends and generate "wow findings" (notable anomalies).

#### `build_trend_and_findings(df)` Logic

```
  1. Select date column + numeric KPI column
     (reuses _select_datetime_column / _select_numeric_column from visualizer)

  2. Build time series: filter to [date, kpi], parse dates, drop NaT, sort

  3. AGGREGATE by date — sum duplicate dates
     (handles transaction-level data like multiple orders on the same day)

  4. Compute trend:
     ├── < 2 distinct dates → "insufficient for trend analysis"
     └── ≥ 2 dates:
           window = max(1, n // 10)        ← 10% of periods
           start_value = mean of first `window` rows
           end_value   = mean of last `window` rows
           pct_change  = (end − start) / start × 100

  5. Generate summary text:
     ├── pct_change > +5%  → "increased X% over the period"
     ├── pct_change < −5%  → "decreased X% over the period"
     └── otherwise         → "relatively stable (within ±5%)"

  6. Generate WowFinding if |pct_change| ≥ 10%:
     ├── ≥ 20%  → severity "high"
     └── ≥ 10%  → severity "medium"
     Type = "trend_shift"
```

**Key design choice — windowed averaging:** Instead of comparing the raw first and last individual values (which is fragile with noisy transaction data), we use the first/last 10% of aggregated periods. This stabilizes the trend for datasets where a single date may have unusually high or low values.

**Example:** An ecommerce CSV with 5 dates and multiple transactions per date. Raw first/last comparison gave −93.5%, but windowed period averages correctly show +10%.

---

### 3.8 `app/core/llm_engine.py` — GPT-4o-mini Integration

**Responsibility:** All OpenAI API interactions. Three distinct LLM capabilities + one KPI suggestion call.

#### Configuration

| Setting | Value |
|---------|-------|
| Model | `gpt-4o-mini` |
| Temperature | 0.4 (insights), 0.2 (KPI), 0.5 (chat) |
| Max tokens | 2048 (insights), 1024 (KPI, chat context, chat) |
| Response format | `json_object` (all calls) |

#### LLM Call 1 — `generate_insights()`

| Aspect | Detail |
|--------|--------|
| System prompt | "You are Boardroom AI, a senior data analyst…" |
| Input | JSON context: dataset meta, column profiles with stats, trend, wow findings, chart summaries |
| Output parsing | JSON → `InsightPack` with `executive_insights`, `risks`, `opportunities`, `actions` |
| Fallback | Returns single "unavailable" insight if no API key or call fails |

**Context building (`_build_data_context`):**
- Compact profiling: name, dtype, stats (min/max/mean/median), outlier count, top value
- Missing values: only columns with missing > 0
- Trend: availability, date/kpi columns, metrics, summary
- Wow findings: type, severity, title, evidence

#### LLM Call 2 — `generate_kpi_suggestions()`

| Aspect | Detail |
|--------|--------|
| System prompt | Guidelines mapping column semantics → aggregation type |
| Input | Column list with dtypes, stats, unique counts |
| Output | `[{column, agg, label, sublabel_agg}]` — 3-8 tiles |
| Rules | monetary → sum · rates → mean · counts → sum · IDs → skip · categories → count_distinct |

#### LLM Call 3 — `generate_chat_context()`

| Aspect | Detail |
|--------|--------|
| Output | `ChatContext`: dataset_brief (2-3 sentence summary), evidence_pack (4-8 facts), suggested_questions (4-6) |
| Fallback | Returns empty context on failure |

#### LLM Call 4 — `chat_with_data()`

| Aspect | Detail |
|--------|--------|
| Input | User message, dataset_brief, evidence_pack, conversation history (max 20 turns) |
| System prompt | Includes the dataset brief + evidence pack as grounding context |
| Output | `{reply, suggested_followups}` |
| Guard | Instructed to answer ONLY from evidence, say "I don't know" otherwise |

**Graceful degradation:** Every LLM function catches exceptions and returns a meaningful fallback. The pipeline never crashes due to LLM failure.

---

### 3.9 `app/core/pdf_generator.py` — PDF Export

**Responsibility:** Generate a downloadable PDF from a `ReportResponse`.

#### Strategy: WeasyPrint with ReportLab Fallback

```
  1. Try to import weasyprint
     ├── Success → render HTML via Jinja2, convert to PDF with WeasyPrint
     └── Failure (OS dependency missing) → use ReportLab
```

**WeasyPrint path:** Calls `render_report_html(report)` → HTML string → `HTML(string=...).write_pdf()`

**ReportLab path (fallback):**
- Manual A4 canvas layout
- Sections: title, metadata, trend summary, wow findings, chart images
- Auto page-break when y-position < 20mm
- Embeds chart PNGs from `static/{report_id}/`

---

### 3.10 `app/core/report_renderer.py` — HTML Rendering

**Responsibility:** Render a `ReportResponse` into a standalone HTML document using Jinja2.

| Component | Detail |
|-----------|--------|
| Template engine | `jinja2.Environment` with `FileSystemLoader` |
| Template path | `app/templates/report_template.html` |
| Auto-escape | Enabled for HTML/XML |
| Usage | `render_report_html(report)` → HTML string |

The rendered HTML is saved as an artifact at `static/{report_id}/report.html`.

---

## 4. Data Flow Diagram

```
                           ┌──────────────────────┐
                           │    CSV Upload File    │
                           └──────────┬───────────┘
                                      │
                                      ▼
                           ┌──────────────────────┐
                           │   _read_dataframe()   │
                           │   Bytes → DataFrame   │
                           └──────────┬───────────┘
                                      │
                                      ▼
                           ┌──────────────────────┐
                           │  _clean_dataframe()   │
                           │  5-step cleaning      │
                           └──────────┬───────────┘
                                      │
                        ┌─────────────┼─────────────┐
                        │             │             │
                        ▼             ▼             ▼
              ┌─────────────┐ ┌─────────────┐ ┌─────────────┐
              │  _build_    │ │  build_trend │ │  generate_  │
              │  profiling()│ │  _and_       │ │  charts()   │
              │             │ │  findings()  │ │  (specs)    │
              │  Per-column │ │  Aggregate   │ │  + render   │
              │  stats,     │ │  by date,    │ │  _charts()  │
              │  outliers,  │ │  windowed %  │ │  (PNGs)     │
              │  dtypes     │ │  wow flags   │ │             │
              └──────┬──────┘ └──────┬──────┘ └──────┬──────┘
                     │               │               │
                     └───────────────┼───────────────┘
                                     │
                                     ▼
                     ┌───────────────────────────────┐
                     │        LLM Engine              │
                     │  ┌─────────────────────────┐  │
                     │  │ generate_insights()     │  │
                     │  │ Exec insights, risks,   │  │
                     │  │ opportunities, actions   │  │
                     │  └─────────────────────────┘  │
                     │  ┌─────────────────────────┐  │
                     │  │ generate_kpi_suggestions│  │
                     │  │ Column → agg mapping    │  │
                     │  └─────────────────────────┘  │
                     │  ┌─────────────────────────┐  │
                     │  │ generate_chat_context() │  │
                     │  │ Brief, evidence, Qs     │  │
                     │  └─────────────────────────┘  │
                     └───────────────┬───────────────┘
                                     │
                                     ▼
                     ┌───────────────────────────────┐
                     │       _build_kpi_tiles()       │
                     │  Apply LLM-decided aggs to df  │
                     │  + always: rows, completeness,  │
                     │    trend, outliers              │
                     └───────────────┬───────────────┘
                                     │
                                     ▼
                     ┌───────────────────────────────┐
                     │       ReportResponse           │
                     │  + Save artifacts (JSON, HTML) │
                     └───────────────────────────────┘
```

---

## 5. Key Algorithms & Design Decisions

### 5.1 ID Column Detection (`visualizer.py`)

Numeric columns that represent identifiers (e.g. `order_id`, `customer_code`) must not be selected as the primary KPI column. Detection uses two heuristics:

1. **Name-based:** Column name matches patterns like `*_id`, `id_*`, `*_code`, `index`, `key`, `pk`, `zip`, `pin`, `phone`.
2. **Shape-based:** All values are unique AND monotonically increasing AND there are more than 3 values → likely a row index/auto-increment ID.

### 5.2 Date Column Detection (`data_processor.py`)

Pandas 2.x uses `StringDtype` (`str`) instead of `object` for CSV string columns. This means `is_object_dtype()` returns `False` for actual text. Both `_infer_dtype()` and `_clean_dataframe()` check `is_string_dtype(series) or is_object_dtype(series)` to handle both old and new pandas.

Date parsing uses `pd.to_datetime(sample, format="mixed")` which handles multiple date formats in the same column (ISO-8601, US dates, etc.).

### 5.3 Trend Windowed Averaging (`trend_engine.py`)

Raw first/last value comparison is unreliable for transaction-level data (e.g. 100 orders/day). Instead:

1. **Aggregate by date** — sum all values on the same date.
2. **Window = 10% of distinct periods** (minimum 1) — average the first window and last window values.

This smooths out intra-day variance and gives a stable trend percentage.

### 5.4 LLM-Driven KPI Aggregation (`llm_engine.py` + `data_processor.py`)

Rather than hardcoding "sum everything", the system asks GPT-4o-mini to decide the aggregation per column based on its **name and semantics**:

| Column Semantics | Chosen Agg | Reasoning |
|-----------------|------------|-----------|
| `revenue`, `cost`, `sales` | `sum` | Monetary / additive quantities should be totalled |
| `margin_pct`, `score`, `rating` | `mean` | Rates and percentages should be averaged |
| `units`, `orders`, `tickets` | `sum` | Discrete counts should be totalled |
| `region`, `product`, `customer` | `count_distinct` | Entities are counted, not summed |
| `order_id`, `user_id` | Skipped | IDs are not KPI-worthy |
| `date`, `created_at` | Skipped | Dates are not KPI-worthy |

The fallback (no API key) sums the first 3 numeric columns.

### 5.5 Outlier Detection (IQR Method)

For every numeric column in profiling:

```
  Q1 = 25th percentile
  Q3 = 75th percentile
  IQR = Q3 − Q1
  Lower bound = Q1 − 1.5 × IQR
  Upper bound = Q3 + 1.5 × IQR
  Outlier count = values below lower + values above upper
```

### 5.6 Async Architecture

FastAPI is async, but the data processing pipeline is CPU-bound (pandas, numpy, plotly). To avoid blocking the event loop:

```python
loop = asyncio.get_running_loop()
report = await loop.run_in_executor(None, partial(generate_report_from_file, file.file, file.filename))
```

This runs the entire pipeline in a thread-pool worker. Same pattern is used for `/chat`.

### 5.7 Chart Rendering: Kaleido 0.2.1

Kaleido ≥ 1.0 launches an async Chromium process that conflicts with the existing event loop, producing blank/blue PNGs. Pinning to `kaleido==0.2.1` uses the older synchronous engine that works reliably in executor threads.

### 5.8 PDF Generation: Dual Strategy

WeasyPrint produces high-quality PDFs from HTML but requires OS-level dependencies (`libcairo`, `libpango`). If those aren't installed, `_get_weasyprint_html()` returns `None` and the system falls back to ReportLab, which generates a simpler but dependency-free PDF.
