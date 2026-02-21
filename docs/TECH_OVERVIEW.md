# 🏗️ Technical Overview

## Boardroom AI -- Next.js + FastAPI Architecture

------------------------------------------------------------------------

# 1️⃣ High-Level Architecture

Boardroom AI follows a modern full-stack architecture:

Frontend (Next.js) ↓ Backend API (FastAPI) ↓ Data Processing + AI Engine
↓ PDF Report Generator ↓ Downloadable Executive Report (A4 PDF)

This separation ensures: - Clean UI experience - Reliable data
processing - Stable server-side PDF generation - Scalability for future
production use

------------------------------------------------------------------------

# 2️⃣ Frontend Technology Stack

## 🔹 Next.js (App Router)

**Purpose:** Product UI and user experience layer.

Used for: - File upload interface - Dataset preview - Cleaning log
display - Metrics and insights preview - Chart rendering preview -
Download PDF button - UI routing and navigation

Why Next.js: - Production-grade UI framework - Server and client
rendering support - Excellent developer experience - Easy deployment
(Vercel / Azure Static Web Apps)

------------------------------------------------------------------------

## 🔹 TypeScript

**Purpose:** Type safety and predictable code structure.

Used for: - API response typing - Report data model structure - Safer
frontend development

------------------------------------------------------------------------

## 🔹 Tailwind CSS

**Purpose:** Rapid, clean, responsive styling.

Used for: - Professional dashboard layout - Print-friendly layout -
Consistent spacing and typography - Boardroom-style report preview
design

------------------------------------------------------------------------

## 🔹 React Dropzone

**Purpose:** Enhanced file upload experience.

Used for: - Drag-and-drop CSV upload - File validation on client side

------------------------------------------------------------------------

# 3️⃣ Backend Technology Stack

## 🔹 FastAPI

**Purpose:** Core backend API service.

Used for: - File ingestion (multipart/form-data) - Data cleaning
pipeline - EDA computation - LLM orchestration - Chart generation - PDF
rendering - Returning JSON + PDF responses

Why FastAPI: - Extremely fast - Async support - Easy OpenAPI
documentation - Python ecosystem integration

------------------------------------------------------------------------

## 🔹 Polars (or Pandas)

**Purpose:** Data processing engine.

Used for: - Data ingestion - Data cleaning - Column type detection -
Statistical profiling - Outlier detection (IQR) - Summary statistics
computation

Why Polars: - Faster than Pandas for large datasets - Memory efficient -
Ideal for hackathon speed

------------------------------------------------------------------------

## 🔹 Plotly + Kaleido

**Purpose:** Chart generation and export.

Used for: - Histogram - Bar charts - Line charts - Scatter plots - Pie
charts (when meaningful)

Kaleido is used to: - Convert charts to PNG images - Embed charts inside
PDF reports

------------------------------------------------------------------------

## 🔹 Azure OpenAI (GPT-4o / GPT-4.1)

**Purpose:** AI Executive Insight Engine.

Used for: - Generating Executive Summary - Producing 5 key insights -
Identifying risks and opportunities - Creating business
recommendations - Selecting most relevant visualisations (ranking)

Why Azure OpenAI: - Enterprise-grade reliability - Secure API access -
High-context models for structured output

------------------------------------------------------------------------

# 4️⃣ PDF Generation Layer

## 🔹 WeasyPrint

**Purpose:** Server-side A4 PDF rendering.

Used for: - Converting structured HTML into PDF - Applying print CSS
styling - Ensuring consistent formatting across devices - Embedding
charts as images - Maintaining professional layout

Why WeasyPrint: - True HTML → PDF conversion - Clean A4 formatting -
More reliable than browser print dialog

------------------------------------------------------------------------

# 5️⃣ Optional Infrastructure Components

## 🔹 Azure Blob Storage

Used for: - Storing uploaded datasets - Storing generated PDF reports -
Enabling download history

------------------------------------------------------------------------

## 🔹 Azure App Service / Container Apps

Used for: - Hosting FastAPI backend - Scaling compute - Deployment
management

------------------------------------------------------------------------

## 🔹 Vercel / Azure Static Web Apps

Used for: - Hosting Next.js frontend - CI/CD integration - Global
delivery

------------------------------------------------------------------------

# 6️⃣ Workflow Pipeline

1.  User uploads CSV via Next.js
2.  File sent to FastAPI backend
3.  Backend performs:
    -   Data validation
    -   Auto-cleaning
    -   Statistical profiling
    -   Outlier detection
4.  Chart candidates generated
5.  Azure OpenAI generates insights
6.  Structured HTML report created
7.  WeasyPrint converts HTML to A4 PDF
8.  PDF returned to frontend for download

------------------------------------------------------------------------

# 7️⃣ Why This Stack Is Optimal

✅ Clear separation of concerns\
✅ Reliable server-side PDF generation\
✅ Strong AI integration\
✅ Production-ready architecture\
✅ Hackathon-friendly implementation\
✅ Easily scalable beyond MVP

------------------------------------------------------------------------

# 🏁 Final Technical Positioning

Boardroom AI is built using a modern, scalable, enterprise-ready
architecture that combines:

-   A polished product UI (Next.js)
-   High-performance data processing (Polars)
-   Intelligent AI reasoning (Azure OpenAI)
-   Reliable server-side PDF generation (WeasyPrint)

This ensures both hackathon-level impact and real-world production
viability.
