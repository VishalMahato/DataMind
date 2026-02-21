# What’s Done vs What’s Left

Branch: `feat4-charts-deterministic`

## ✅ What’s Done

- Project documentation written and aligned:
  - Product overview, HLD, tech overview
  - Project structure, API contract, schemas
  - Sample `report.sample.json` matching `ReportResponse v1`
  - Root `README.md` as single source of truth
- Backend skeleton created:
  - FastAPI `app/main.py` with router wiring
  - Core API routes in `app/api/routes.py`:
    - `POST /analyze` (returns mocked `ReportResponse` from `report.sample.json`)
    - `POST /pdf` (stub, returns 501)
    - `GET /health`
- Pydantic models implemented in `app/api/schemas.py`:
  - Full `ReportResponse v1` including:
    - dataset_meta, data_preview, cleaning_log, profiling, trend, wow_findings
    - charts (with alt/width/height), insights
    - status, pipeline, artifacts, quality_score, kpi_tiles, warnings, chat_context
  - `PdfRequest` schema
- Data processor stub added in `app/core/data_processor.py`:
  - Reads `docs/report.sample.json` and returns a validated `ReportResponse`
  - Provides minimal fallback if sample file is missing
- Basic backend dependencies defined in `requirements.txt`
- `.gitignore` updated for Python, venvs, logs, editor files, and local env files
- Git branch `feat1-basics` created and pushed to GitHub with initial backend + docs
- Real CSV ingestion added in `app/core/data_processor.py`:
  - Reads the uploaded CSV into a pandas DataFrame
  - Updates `dataset_meta` (filename, rows, columns, size_bytes, delimiter, encoding)
  - Updates `data_preview` columns and first rows from the real data
- Real profiling added in `app/core/data_processor.py`:
  - Computes `missing_by_column` and `unique_by_column` from the DataFrame
  - Builds `column_profiles` with inferred dtype, numeric stats, outlier summary, and top categorical values
- Deterministic charts added in `app/core/visualizer.py` and wired via `data_processor`:
  - Selects main numeric, categorical, and datetime columns from the DataFrame
  - Generates a line chart (KPI over time), bar chart (KPI by category), and histogram (KPI distribution) with stable ids and titles

## ⏳ What’s Left (High-Level)

- Backend data/AI logic:
  - Implement PNG export via Plotly + Kaleido for generated charts
  - Implement trend detection (`trend_engine.py`)
  - Implement Azure OpenAI integration (`llm_engine.py`) for insights, risks, opportunities, actions, chat_context
  - Implement HTML report rendering (`report_renderer.py`) and PDF generation (`pdf_generator.py`) using WeasyPrint
  - Wire `/pdf` to generate and return real A4 PDF
  - Populate `status`, `pipeline`, `artifacts`, `quality_score`, `kpi_tiles`, and `warnings` from real processing
- Frontend:
  - Create Next.js app with upload page and report preview page
  - Implement calls to `/analyze` and `/pdf`
  - Render cleaning log, metrics, charts, wow_findings, insights, and KPI tiles
  - Add basic styling (Tailwind) and UX polish
- Testing and quality:
  - Add unit tests for core backend modules
  - Add simple integration tests for `/health`, `/analyze`, `/pdf`
  - Add linting/formatting configuration and commands
- Deployment:
  - Add Docker configuration for backend (if needed) and document `uvicorn` run command
  - Prepare Azure/Vercel deployment notes (matching TECH_OVERVIEW)

> This document should be updated with every meaningful commit: add bullets under **What’s Done**, and adjust **What’s Left** as tasks are completed or re-scoped.
