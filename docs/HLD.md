# 🏗️ High Level Design (HLD)

## Boardroom AI -- The 10-Second Analyst

------------------------------------------------------------------------

# 1️⃣ System Overview

Boardroom AI is an AI-powered data intelligence platform that transforms
raw CSV datasets into structured, executive-ready A4 PDF reports.

Workflow:

Upload CSV\
→ Data Validation & Cleaning\
→ Auto Profiling & Trend Analysis\
→ AI Insight Generation\
→ Intelligent Visualisation Selection\
→ Structured Executive PDF Export

The primary deliverable is a professionally formatted PDF report
designed for decision-makers.

------------------------------------------------------------------------

# 2️⃣ Goals and Non-Goals

## 🎯 Goals

-   Always generate a valid downloadable PDF report\
-   Provide evidence-backed AI insights\
-   Perform automatic data cleaning and profiling\
-   Detect trends and anomalies\
-   Select meaningful visualisations automatically\
-   Maintain professional A4 formatting

## 🚫 Non-Goals

-   Full BI dashboard replacement\
-   Advanced forecasting or ML modeling\
-   Multi-user authentication (MVP scope)\
-   Real-time streaming analytics

------------------------------------------------------------------------

# 3️⃣ High-Level Architecture

Frontend (Next.js) ↓ Backend API (FastAPI) ↓ Data Processing Engine
(Polars/Pandas) ↓ Chart Engine (Plotly + Kaleido) ↓ AI Insight Engine
(Azure OpenAI) ↓ HTML Report Renderer ↓ PDF Generator (WeasyPrint) ↓
Downloadable A4 PDF

------------------------------------------------------------------------

# 4️⃣ Core Workflow Sequence

1.  User uploads CSV via Next.js.
2.  File sent to FastAPI backend (`POST /analyze`).
3.  Backend performs:
    -   Validation
    -   Cleaning
    -   Profiling
    -   Outlier detection (IQR method)
    -   Trend analysis (if datetime column exists)
4.  Chart candidates generated based on detected data types.
5.  Azure OpenAI generates:
    -   Executive insights
    -   Risks
    -   Opportunities
    -   Action recommendations
6.  Backend returns structured `report.json` to frontend.
7.  User clicks "Generate PDF".
8.  Backend renders structured HTML + embeds chart images.
9.  WeasyPrint converts HTML to A4 PDF.
10. PDF returned to frontend for download.

------------------------------------------------------------------------

# 5️⃣ Core Modules & Responsibilities

## 🔹 API Layer (FastAPI)

-   File ingestion
-   Endpoint routing
-   Request validation
-   Response handling

## 🔹 Data Processor

-   Column type detection
-   Missing value handling
-   Duplicate removal
-   Statistical profiling
-   IQR-based outlier detection
-   Trend computation

## 🔹 Visualisation Engine

-   Generate candidate charts
-   Export charts as PNG
-   Provide metadata for report

## 🔹 AI Insight Engine

-   Structured prompt templates
-   Grounded insight generation
-   Risk and opportunity extraction
-   Action recommendation synthesis

## 🔹 Report Renderer

-   HTML template assembly
-   Data injection into sections
-   Chart embedding

## 🔹 PDF Generator

-   HTML → A4 PDF conversion
-   Print stylesheet application
-   Final document output

------------------------------------------------------------------------

# 6️⃣ API Contracts

## POST /analyze

Input: - CSV file (multipart/form-data)

Output: - JSON object containing: - dataset_meta - data_preview -
cleaning_log - profiling - trend - wow_findings - charts (type, title,
reason, image path) - insights (executive_insights, risks,
opportunities, actions) - report_id - report_version - generated_at -
mode

------------------------------------------------------------------------

## POST /pdf

Input: - report JSON or report_id

Output: - application/pdf (A4 formatted report)

------------------------------------------------------------------------

# 7️⃣ Report Data Model (High-Level Schema)

{ report_version: "v1", report_id: "", generated_at: "", mode:
"boardroom", dataset_meta: {}, data_preview: {}, cleaning_log: \[\],
profiling: {}, trend: {}, wow_findings: \[\], charts: \[\], insights: {
executive_insights: \[\], risks: \[\], opportunities: \[\], actions:
\[\] } }

------------------------------------------------------------------------

# 8️⃣ Reliability & Fallback Strategy

-   If LLM fails → Use template-based executive summary
-   If chart generation fails → Render tables only
-   If trend detection not applicable → Skip trend section
-   File size limits enforced
-   API timeouts handled gracefully

PDF generation must never fail.

------------------------------------------------------------------------

# 9️⃣ Security & Privacy

-   No dataset stored permanently (unless enabled)
-   Environment variables for API keys
-   Secure backend-only AI calls
-   Optional future PII masking layer

------------------------------------------------------------------------

# 🔟 Deployment Strategy

Frontend: - Vercel or Azure Static Web Apps

Backend: - Azure App Service or Azure Container Apps

Optional: - Azure Blob Storage for file persistence

------------------------------------------------------------------------

# 🏁 Final Architecture Positioning

Boardroom AI uses a modular, scalable architecture combining:

-   A production-grade frontend (Next.js)
-   High-performance data processing (Polars)
-   Intelligent AI reasoning (Azure OpenAI)
-   Reliable server-side PDF generation (WeasyPrint)

This ensures hackathon readiness and real-world scalability.
