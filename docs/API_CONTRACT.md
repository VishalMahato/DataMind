# 📜 API Contract / Spec (v1)

## Boardroom AI --- Next.js (Frontend) ↔ FastAPI (Backend)

> **Goal:** Keep frontend + backend in sync while building in parallel.\
> **Primary deliverables:** `report.json` from `/analyze` and a
> downloadable **A4 PDF** from `/pdf`.

------------------------------------------------------------------------

## 0) Environments

### Local Dev

-   Frontend: `http://localhost:3000`
-   Backend: `http://localhost:8000`

### CORS

Backend must allow: - `http://localhost:3000` - (optional)
`http://127.0.0.1:3000`

------------------------------------------------------------------------

## 1) Conventions

### Content Types

-   Upload: `multipart/form-data`
-   JSON responses: `application/json`
-   PDF response: `application/pdf`

### IDs

-   Backend returns a `report_id` for each analysis request.
-   Frontend uses `report_id` to request the PDF (recommended).

### Versioning

All responses include: - `report_version: "v1"`

### Error Format (standard)

All error responses return:

``` json
{
  "error": {
    "code": "STRING_CODE",
    "message": "Human-readable message",
    "details": {}
  }
}
```

------------------------------------------------------------------------

## 2) Endpoints

## 2.1 `POST /analyze`

Upload a CSV file and return the full `ReportResponse` JSON (used for UI
preview and later PDF generation).

### Route

-   **Method:** `POST`
-   **Path:** `/analyze`
-   **Content-Type:** `multipart/form-data`

### Request

Form fields:

-   `file` (required): CSV file
-   `options` (optional, JSON string): processing toggles

Example cURL:

``` bash
curl -X POST "http://localhost:8000/analyze" \
  -F "file=@./sample.csv" \
  -F 'options={"mode":"boardroom","max_charts":3}'
```

Example minimal request (no options):

``` http
POST /analyze HTTP/1.1
Host: localhost:8000
Content-Type: multipart/form-data; boundary=---123

---123
Content-Disposition: form-data; name="file"; filename="sample.csv"
Content-Type: text/csv

<file bytes>
---123--
```

### Response (200)

-   **Content-Type:** `application/json`
-   Body: `ReportResponse` (see Schema section)

Example (truncated) success:

``` json
{
  "report_version": "v1",
  "report_id": "rpt_20260221_demo1234",
  "generated_at": "2026-02-21T08:30:00Z",
  "mode": "boardroom",
  "dataset_meta": { "...": "..." },
  "data_preview": { "...": "..." },
  "cleaning_log": [ { "action": "drop_empty_columns", "description": "Dropped 1 empty column" } ],
  "profiling": { "...": "..." },
  "trend": { "...": "..." },
  "wow_findings": [ { "type": "kpi_conflict", "title": "Margin declined despite revenue growth", "...": "..." } ],
  "charts": [ { "id": "chart_1", "chart_type": "line", "image_url": "/static/rpt_.../chart_1.png" } ],
  "insights": { "executive_insights": [ { "text": "Top-line growth is positive", "evidence": "..." } ], "...": "..." },
  "status": "complete"
}
```

For a full example body, see `docs/report.sample.json`.

### Error responses

-   `400` invalid CSV / unsupported encoding
-   `413` file too large
-   `422` validation error
-   `500` internal error

------------------------------------------------------------------------

## 2.2 `POST /pdf`

Generate and return the A4 PDF for a report.

### Route

-   **Method:** `POST`
-   **Path:** `/pdf`
-   **Content-Type:** `application/json`

### Request (recommended)

Body:

``` json
{
  "report_id": "rpt_20260221_demo1234",
  "mode": "boardroom"
}
```

Alternative (fallback): send the whole `report` JSON (not recommended
for large payloads):

``` json
{
  "mode": "boardroom",
  "report": { ...ReportResponse }
}
```

Example HTTP request:

``` http
POST /pdf HTTP/1.1
Host: localhost:8000
Content-Type: application/json

{
  "report_id": "rpt_20260221_demo1234",
  "mode": "boardroom"
}
```

### Response (200)

-   **Content-Type:** `application/pdf`
-   Headers:
    -   `Content-Disposition: attachment; filename="BoardroomAI_Report_rpt_20260221_demo1234.pdf"`

Binary body contains the A4 PDF.

### Error responses

-   `404` report not found (if using `report_id`)
-   `422` invalid payload
-   `500` PDF generation failed

------------------------------------------------------------------------

## 2.3 `GET /health`

Simple health check.

### Route

-   **Method:** `GET`
-   **Path:** `/health`

### Response (200)

``` json
{ "status": "ok" }
```

------------------------------------------------------------------------

## 3) Report JSON Schema (v1)

### 3.1 Top-level: `ReportResponse`

``` json
{
  "report_version": "v1",
  "report_id": "rpt_20260221_abcdef",
  "generated_at": "2026-02-21T08:30:00Z",
  "mode": "boardroom",

  "dataset_meta": {
    "filename": "sample.csv",
    "rows": 1000,
    "columns": 25,
    "size_bytes": 523123,
    "detected_delimiter": ",",
    "encoding": "utf-8"
  },

  "data_preview": {
    "columns": ["col1", "col2"],
    "rows": [
      { "col1": "A", "col2": 10 },
      { "col1": "B", "col2": 20 }
    ]
  },

  "cleaning_log": [
    {
      "action": "drop_empty_columns",
      "description": "Dropped 2 empty columns",
      "before": { "columns": 27 },
      "after": { "columns": 25 }
    }
  ],

  "profiling": {
    "missing_by_column": { "colA": 12, "colB": 0 },
    "unique_by_column": { "colA": 3, "colB": 1000 },
    "column_profiles": [
      {
        "name": "sales",
        "dtype": "numeric",
        "stats": { "min": 10, "max": 1000, "mean": 250.2, "median": 220.0, "std": 95.4 },
        "outliers": { "method": "iqr", "count": 12, "lower_bound": -50.0, "upper_bound": 850.0 }
      },
      {
        "name": "region",
        "dtype": "categorical",
        "top_value": { "value": "North", "count": 420 }
      }
    ]
  },

  "trend": {
    "available": true,
    "date_column": "date",
    "kpi_column": "sales",
    "summary": [
      "Sales increased 12.4% over the analyzed period.",
      "Volatility rose in Q3."
    ],
    "metrics": {
      "start_value": 100.0,
      "end_value": 112.4,
      "pct_change": 12.4
    }
  },

  "wow_findings": [
    {
      "type": "trend_shift",
      "severity": "high",
      "title": "Profit margin declined despite revenue growth",
      "evidence": "Revenue +12.4% vs Margin -4.1%",
      "related_columns": ["revenue", "margin"]
    }
  ],

  "charts": [
    {
      "id": "chart_1",
      "chart_type": "line",
      "title": "Sales over Time",
      "reason": "Date column detected; line chart best shows trend.",
      "x": "date",
      "y": "sales",
      "image_url": "/static/rpt_.../chart_1.png"
    }
  ],

  "insights": {
    "executive_insights": [
      { "text": "Revenue grew 12.4% driven by Region North performance.", "evidence": "revenue mean=..., trend pct_change=12.4%" }
    ],
    "risks": [
      { "text": "High missingness in Region may bias segment analysis.", "evidence": "region missing=320 (32%)" }
    ],
    "opportunities": [
      { "text": "Improve margin by reviewing discounting in Q3.", "evidence": "margin trend -4.1% in Q3" }
    ],
    "actions": [
      { "text": "Audit cost drivers for Q3 to restore margin.", "priority": "high" }
    ]
  },

  "status": "complete",

  "pipeline": [
    { "step": "validation", "ok": true, "ms": 120 },
    { "step": "cleaning", "ok": true, "ms": 340, "note": "Filled margin_pct with median (22 values)" },
    { "step": "eda", "ok": true, "ms": 480 },
    { "step": "charts", "ok": true, "ms": 410 },
    { "step": "llm", "ok": true, "ms": 2100 },
    { "step": "html", "ok": true, "ms": 95 },
    { "step": "pdf", "ok": true, "ms": 260 }
  ],

  "artifacts": {
    "report_json_url": "https://blob.example.com/reports/rpt_20260221_abcdef/report.json",
    "report_html_url": "https://blob.example.com/reports/rpt_20260221_abcdef/report.html",
    "pdf_url": "https://blob.example.com/reports/rpt_20260221_abcdef/report.pdf"
  },

  "quality_score": {
    "score": 88,
    "issues": [
      "18 high-end revenue outliers may skew averages"
    ],
    "strengths": [
      "No missing values in KPI columns",
      "Stable revenue growth over the analyzed period"
    ]
  },

  "kpi_tiles": [
    { "label": "Total Revenue", "value": "$135.4M", "sublabel": "+12.4% vs prior period" },
    { "label": "Avg Margin %", "value": "26.4%", "sublabel": "-4.1 pts in Q3" },
    { "label": "Top Region", "value": "North", "sublabel": "420 records (highest density)" },
    { "label": "Revenue Outliers", "value": "18 deals", "sublabel": "Flagged via IQR" }
  ],

  "warnings": [
    { "code": "REVENUE_OUTLIERS", "message": "Revenue distribution contains 18 high-end outliers." },
    { "code": "MARGIN_DROP_Q3", "message": "Margin percentage declined in Q3 while revenue increased." }
  ],

  "chat_context": {
    "dataset_brief": "Daily revenue, cost, units, and margin percentage by region and product for a single quarter.",
    "evidence_pack": [
      "Revenue increased 12.4% over the analyzed period.",
      "Margin percentage declined about 4.1 points in Q3.",
      "North region appears as the leading contributor by record count and revenue.",
      "18 revenue outliers detected using IQR."
    ],
    "suggested_questions": [
      "Which regions are driving most of the revenue growth?",
      "How do margin trends differ by region and product?",
      "What is the impact of high-value outlier deals on average revenue?"
    ]
  }
}
```

------------------------------------------------------------------------

## 4) Field Definitions (Frontend-critical)

### 4.1 `mode`

-   `"boardroom"` (default): concise, decision-ready writing
-   `"analyst"`: more technical / detailed

### 4.2 `charts[].image_url`

-   Must be directly fetchable by the frontend.
-   For local dev: backend serves `backend/app/static/` at `/static`.

### 4.3 `data_preview`

-   Must contain **first 5 rows** (max) to keep payload small.

------------------------------------------------------------------------

## 5) Processing Options (optional)

`options` form field in `/analyze` can include:

``` json
{
  "mode": "boardroom",
  "max_charts": 3,
  "max_preview_rows": 5,
  "outlier_method": "iqr"
}
```

Backend can ignore unknown keys (forward-compatible).

------------------------------------------------------------------------

## 6) Frontend Integration Checklist

-   Use `multipart/form-data` for `/analyze`
-   Render UI from returned `ReportResponse`
-   Download PDF by calling `/pdf` with `report_id`
-   Show chart thumbnails using `charts[].image_url`
-   Display `wow_findings` at the top as the "autonomous" section

------------------------------------------------------------------------

## 7) Backend Implementation Checklist

-   Enforce file size limit (return 413)
-   Always return `report_id`
-   Store report JSON temporarily in memory or filesystem keyed by
    `report_id`
-   Serve chart PNGs under `/static/<report_id>/...`
-   Guarantee PDF generation even if LLM fails (fallback template)

------------------------------------------------------------------------

## 8) Example Minimal Responses

### 8.1 Minimal `/analyze` success (tiny)

``` json
{
  "report_version": "v1",
  "report_id": "rpt_20260221_abcdef",
  "generated_at": "2026-02-21T08:30:00Z",
  "mode": "boardroom",
  "dataset_meta": { "filename": "x.csv", "rows": 10, "columns": 4, "size_bytes": 1024, "detected_delimiter": ",", "encoding": "utf-8" },
  "data_preview": { "columns": ["a","b"], "rows": [{"a":1,"b":2}] },
  "cleaning_log": [],
  "profiling": { "missing_by_column": {}, "unique_by_column": {}, "column_profiles": [] },
  "trend": { "available": false },
  "wow_findings": [],
  "charts": [],
  "insights": { "executive_insights": [], "risks": [], "opportunities": [], "actions": [] }
}
```

### 8.2 Error example

``` json
{
  "error": {
    "code": "INVALID_CSV",
    "message": "Unable to parse the uploaded file as CSV.",
    "details": { "hint": "Check delimiter/encoding." }
  }
}
```

------------------------------------------------------------------------

## 9) Notes for Hackathon Speed

-   Frontend can build UI using a saved `report.sample.json` with this
    schema.
-   Backend should first implement `/analyze` returning mocked JSON,
    then replace internals.
-   Keep the contract stable: **add fields, don't rename**.
