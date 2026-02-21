# Boardroom AI — The 10-Second Analyst

Boardroom AI is an AI-powered data intelligence system that transforms raw CSV
files into structured, executive-ready A4 PDF reports. It performs automatic
data cleaning, exploratory data analysis, AI-driven insight generation, and
professional report rendering.

The goal is simple:

> Upload CSV → Get a boardroom-ready decision report.

The name references a “10-second analyst”, but the product promise is an
executive report in under a minute (typically 10–20 seconds), depending on
dataset size and model latency.

## High-Level Architecture

- Frontend: Next.js (TypeScript, Tailwind, React Dropzone)
- Backend: FastAPI (Python)
- Data processing: Polars (or Pandas)
- Charts: Plotly + Kaleido (PNG export)
- AI engine: Azure OpenAI (GPT-4o / GPT-4.1)
- PDF generation: WeasyPrint (HTML → A4 PDF)

Typical deployment story:

- Next.js on Vercel or Azure Static Web Apps
- FastAPI on Azure App Service or Azure Container Apps
- Optional Azure Blob Storage for uploaded CSVs and generated PDFs

## Core Workflow

1. User uploads a CSV file from the Next.js frontend.
2. Frontend sends the file to FastAPI via `POST /analyze`.
3. Backend:
   - Validates and cleans the data
   - Profiles columns and detects outliers/trends
   - Generates chart candidates
   - Calls Azure OpenAI to produce executive insights, risks, opportunities, and actions
   - Returns a structured `ReportResponse` JSON (`report.json`)
4. Frontend renders a live preview:
   - Cleaning log
   - Metrics and profiling
   - Charts
   - AI insights and wow findings
5. User clicks “Generate PDF”.
6. Frontend calls `POST /pdf` with `report_id` (or full report JSON).
7. Backend renders HTML, embeds chart images, and uses WeasyPrint to return an A4 PDF.

## API Surface (Source of Truth)

Backend APIs:

- `POST /analyze`
  - Input: CSV file (`multipart/form-data`)
  - Output: `ReportResponse` JSON
- `POST /pdf`
  - Input: `{ "report_id": string, "mode": "boardroom" | "analyst" }` or
    `{ "mode": ..., "report": ReportResponse }`
  - Output: `application/pdf` (A4 report)
- `GET /health`
  - Output: `{ "status": "ok" }`

For full request/response examples and error formats, see
`docs/API_CONTRACT.md`.

## ReportResponse Schema (Top-Level Fields)

The `ReportResponse` object is the single shared contract between backend and
frontend. Top-level fields:

- `report_version`: `"v1"`
- `report_id`: unique report identifier
- `generated_at`: ISO timestamp
- `mode`: `"boardroom"` or `"analyst"`
- `dataset_meta`: basic file metadata
- `data_preview`: first few rows and column names
- `cleaning_log`: list of cleaning operations
- `profiling`: column statistics, missingness, uniques, outliers
- `trend`: optional trend analysis for time-based KPIs
- `wow_findings`: autonomous highlights (anomaly, KPI conflict, trend shift, data quality)
- `charts`: selected visualisations with metadata
- `insights`: executive insights, risks, opportunities, and actions

These field names and structures are defined in detail in:

- `docs/SCHEMAS.md` (schema documentation)
- `docs/API_CONTRACT.md` (API contract and examples)
- `docs/report.sample.json` (concrete sample payload)

## Wow Findings and Insight Philosophy

Boardroom AI is designed to be an “AI analyst”, not just a chart generator.

- **Wow findings (`wow_findings`)**:
  - Types: `anomaly`, `kpi_conflict`, `trend_shift`, `data_quality`
  - Each item includes: `type`, `severity`, `title`, `evidence`, `related_columns`
- **Insights (`insights`)**:
  - `executive_insights`, `risks`, `opportunities`, `actions`
  - Each insight is paired with explicit `evidence` so judges and users can
    trace every claim back to metrics and charts.

This “insight → evidence” pattern is the core product philosophy.

## Document Map (Single Source of Truth)

This README, together with the following documents, forms the single source of
truth for Boardroom AI:

- `docs/PRODUCT_OVERVIEW.md` – problem statement and product value
- `docs/HLD.md` – high-level design and workflow
- `docs/TECH_OVERVIEW.md` – technology stack and rationale
- `docs/PROJECT_STRUCTURE.md` – monorepo layout
- `docs/API_CONTRACT.md` – API endpoints and contracts
- `docs/SCHEMAS.md` – detailed data models
- `docs/report.sample.json` – end-to-end example report payload

All documents are aligned on:

- Top-level `ReportResponse` field names
- Presence of the `wow_findings` section
- The Next.js + FastAPI + Azure OpenAI + WeasyPrint architecture

