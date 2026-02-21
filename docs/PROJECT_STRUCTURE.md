# 📁 Project Structure

## Boardroom AI -- Next.js + FastAPI Architecture

------------------------------------------------------------------------

# 🏗️ Monorepo Structure

Boardroom AI follows a clean separation between frontend and backend
services.

    boardroom-ai/
    │
    ├── frontend/                  # Next.js Application
    │   ├── app/                   # App Router pages
    │   │   ├── page.tsx           # Landing + Upload page
    │   │   ├── report/[id]/       # Report preview page
    │   │   └── layout.tsx         # Root layout
    │   │
    │   ├── components/            # Reusable UI components
    │   │   ├── UploadCard.tsx
    │   │   ├── CleaningLog.tsx
    │   │   ├── MetricsTable.tsx
    │   │   ├── ChartsGallery.tsx
    │   │   ├── InsightsPanel.tsx
    │   │   └── DownloadButton.tsx
    │   │
    │   ├── lib/                   # API helpers & utilities
    │   │   ├── api.ts             # Backend API calls
    │   │   └── types.ts           # TypeScript interfaces
    │   │
    │   ├── styles/                # Tailwind + global styles
    │   │   └── globals.css
    │   │
    │   ├── public/                # Static assets
    │   │
    │   ├── package.json
    │   └── tsconfig.json
    │
    ├── backend/                   # FastAPI Application
    │   ├── app/
    │   │   ├── main.py            # FastAPI entry point
    │   │   │
    │   │   ├── api/               # API route definitions
    │   │   │   ├── routes.py
    │   │   │   └── schemas.py
    │   │   │
    │   │   ├── core/              # Core processing logic
    │   │   │   ├── data_processor.py
    │   │   │   ├── trend_engine.py
    │   │   │   ├── visualizer.py
    │   │   │   ├── llm_engine.py
    │   │   │   ├── report_renderer.py
    │   │   │   └── pdf_generator.py
    │   │   │
    │   │   ├── templates/         # HTML templates for PDF
    │   │   │   └── report_template.html
    │   │   │
    │   │   ├── static/            # Generated chart images
    │   │   │
    │   │   └── utils/             # Utility helpers
    │   │       ├── file_handler.py
    │   │       └── validators.py
    │   │
    │   ├── requirements.txt
    │   └── Dockerfile
    │
    ├── docker-compose.yml         # Local dev setup
    ├── .env                       # Environment variables
    ├── README.md
    └── HLD.md

------------------------------------------------------------------------

# 🧠 Backend Module Responsibilities

## data_processor.py

-   CSV ingestion
-   Data cleaning
-   Missing value handling
-   Duplicate removal
-   Type inference
-   Statistical profiling
-   IQR outlier detection

## trend_engine.py

-   Date column detection
-   Time-based grouping
-   Growth rate calculation
-   Period-over-period comparison
-   Trend shift detection

## visualizer.py

-   Generate candidate charts
-   Select appropriate chart types
-   Export PNG images via Kaleido
-   Provide chart metadata (title, reason)

## llm_engine.py

-   Structured prompt templates
-   Azure OpenAI integration
-   Generate:
    -   Executive insights
    -   Risks
    -   Opportunities
    -   Action recommendations

## report_renderer.py

-   Assemble structured HTML
-   Inject metrics + insights + charts
-   Apply print CSS styling

## pdf_generator.py

-   Convert HTML → A4 PDF using WeasyPrint
-   Return final downloadable file

------------------------------------------------------------------------

# 🌐 Frontend Responsibilities

## Upload Flow

-   Drag-and-drop CSV
-   Preview first 5 rows
-   Call backend /analyze endpoint

## Report Preview

-   Display:
    -   Cleaning log
    -   Metrics summary
    -   Charts
    -   AI insights
-   Show "Generate PDF" button

## Download Flow

-   Call /pdf endpoint
-   Trigger file download
-   Handle loading & error states

------------------------------------------------------------------------

# 🔌 API Layer Structure

## POST /analyze

-   Input: CSV file
-   Output: Structured report JSON

## POST /pdf

-   Input: Report JSON or report_id
-   Output: A4 PDF file

------------------------------------------------------------------------

# 🧩 Environment Variables (.env)

    AZURE_OPENAI_API_KEY=
    AZURE_OPENAI_ENDPOINT=
    AZURE_OPENAI_DEPLOYMENT_NAME=
    BACKEND_URL=

------------------------------------------------------------------------

# 🚀 Deployment Ready Structure

Frontend: - Deploy via Vercel or Azure Static Web Apps

Backend: - Deploy via Azure App Service or Container Apps

Docker-ready backend for smooth deployment.

------------------------------------------------------------------------

# 🏁 Final Structure Philosophy

-   Clear separation of UI and compute logic
-   Modular backend design
-   Dedicated PDF rendering pipeline
-   Scalable beyond hackathon MVP
-   Production-ready foundation
