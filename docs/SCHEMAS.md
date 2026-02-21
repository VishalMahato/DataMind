# 📦 Schemas Documentation (v1)

## Boardroom AI -- Backend ↔ Frontend Data Models

This document describes all core schemas used in Boardroom AI.\
These schemas define the contract between:

-   🧠 Backend (FastAPI + Pydantic)
-   🌐 Frontend (Next.js + TypeScript)

All models follow **report_version = "v1"**.

------------------------------------------------------------------------

# 1️⃣ Error Schemas

## 🔹 ErrorObject

  Field     Type     Description
  --------- -------- -----------------------------
  code      string   Machine-readable error code
  message   string   Human-readable message
  details   object   Optional extra metadata

## 🔹 ErrorResponse

``` json
{
  "error": {
    "code": "INVALID_CSV",
    "message": "Unable to parse file",
    "details": {}
  }
}
```

------------------------------------------------------------------------

# 2️⃣ Core Report Schema

## 🔹 ReportResponse (Top-Level)

  Field            Type                       Description
  ---------------- -------------------------- -------------------------------
  report_version   "v1"                       Schema version
  report_id        string                     Unique report identifier
  generated_at     string (ISO datetime)      Generation timestamp
  mode             "boardroom" \| "analyst"   Tone of report
  dataset_meta     DatasetMeta                Dataset information
  data_preview     DataPreview                First 5 rows
  cleaning_log     CleaningLogItem\[\]        Data cleaning actions
  profiling        ProfilingSummary           Column statistics
  trend            TrendSummary               Trend analysis (if available)
  wow_findings     WowFinding\[\]             Autonomous AI highlights
  charts           ChartSpec\[\]              Selected visualisations
  insights         InsightPack                Executive insights
  status           string (optional)          Pipeline status: processing/complete/partial/failed
  pipeline         PipelineStep\[\] (optional) Execution timeline of processing steps
  artifacts        Artifacts (optional)       URLs for persisted outputs
  quality_score    QualityScore (optional)    Data/report quality summary
  kpi_tiles        KpiTile\[\] (optional)     High-level KPI tiles for UI
  warnings         WarningItem\[\] (optional) Non-fatal processing warnings
  chat_context     ChatContext (optional)     Seed context for chat UX

## 🔹 PipelineStep

  Field     Type                                                   Description
  --------- ------------------------------------------------------ -------------------------------
  step      validation \| cleaning \| eda \| charts \| llm \| html \| pdf   Pipeline stage name
  ok        boolean                                               Whether this step succeeded
  ms        number (optional)                                     Duration in milliseconds
  note      string (optional)                                     Additional diagnostic info

## 🔹 Artifacts

  Field             Type            Description
  ----------------- --------------- -----------------------------------------
  report_json_url   string (opt.)   Location of stored report JSON
  report_html_url   string (opt.)   Location of rendered HTML report
  pdf_url           string (opt.)   Location of generated PDF

## 🔹 QualityScore

  Field        Type            Description
  ------------ --------------- ---------------------------------------------
  score        number          Overall quality score (0–100)
  issues       string\[\]      Key data or report issues
  strengths    string\[\]      Notable data or report strengths

## 🔹 KpiTile

  Field       Type            Description
  ----------- --------------- -----------------------------
  label       string          KPI name (e.g. "Revenue")
  value       string          Display value (e.g. "$1.2M")
  sublabel    string (opt.)   Secondary text (e.g. "+12.4% vs prev.")

## 🔹 WarningItem

  Field       Type            Description
  ----------- --------------- ------------------------------
  code        string          Machine-readable warning code
  message     string          Human-readable warning message

## 🔹 ChatContext

  Field               Type        Description
  ------------------- ----------- --------------------------------------
  dataset_brief       string      One-paragraph dataset summary
  evidence_pack       string\[\]  Key facts for grounding chat answers
  suggested_questions string\[\]  Seed questions for follow-up chat

------------------------------------------------------------------------

# 3️⃣ DatasetMeta

  Field                Type     Description
  -------------------- -------- --------------------
  filename             string   Uploaded file name
  rows                 number   Total row count
  columns              number   Total column count
  size_bytes           number   File size
  detected_delimiter   string   CSV delimiter
  encoding             string   File encoding

------------------------------------------------------------------------

# 4️⃣ DataPreview

  Field     Type         Description
  --------- ------------ -------------------
  columns   string\[\]   Column names
  rows      object\[\]   First 5 rows only

------------------------------------------------------------------------

# 5️⃣ CleaningLogItem

  Field         Type     Description
  ------------- -------- ---------------------
  action        string   Cleaning operation
  description   string   Human explanation
  before        object   State before change
  after         object   State after change

------------------------------------------------------------------------

# 6️⃣ ProfilingSummary

## 🔹 missing_by_column

Dictionary of column → missing count

## 🔹 unique_by_column

Dictionary of column → unique count

## 🔹 column_profiles

Each profile:

  ------------------------------------------------------------------------
  Field               Type              Description
  ------------------- ----------------- ----------------------------------
  name                string            Column name

  dtype               numeric \|        
                      categorical \|    
                      datetime \|       
                      boolean \| text   
                      \| unknown        

  stats               NumericStats      Only for numeric columns

  outliers            OutlierSummary    Only for numeric columns

  top_value           TopValue          Only for categorical columns
  ------------------------------------------------------------------------

------------------------------------------------------------------------

# 7️⃣ NumericStats

  Field    Type
  -------- --------
  min      number
  max      number
  mean     number
  median   number
  std      number

------------------------------------------------------------------------

# 8️⃣ OutlierSummary

  Field         Type     Description
  ------------- -------- --------------------
  method        "iqr"    Outlier method
  count         number   Number of outliers
  lower_bound   number   Lower bound
  upper_bound   number   Upper bound

------------------------------------------------------------------------

# 9️⃣ TrendSummary

  Field         Type           Description
  ------------- -------------- -------------------------
  available     boolean        Whether trend exists
  date_column   string         Detected date column
  kpi_column    string         Primary KPI
  summary       string\[\]     Human-readable findings
  metrics       TrendMetrics   Computed trend numbers

## TrendMetrics

  Field         Type
  ------------- --------
  start_value   number
  end_value     number
  pct_change    number

------------------------------------------------------------------------

# 🔟 WowFinding

  Field             Type                                                     Description
  ----------------- -------------------------------------------------------- -------------
  type              anomaly \| kpi_conflict \| trend_shift \| data_quality   
  severity          low \| medium \| high                                    
  title             string                                                   
  evidence          string                                                   
  related_columns   string\[\]                                               

------------------------------------------------------------------------

# 1️⃣1️⃣ ChartSpec

  Field        Type                                                    Description
  ------------ ------------------------------------------------------- -----------------------------
  id           string                                                  Unique chart ID
  chart_type   histogram \| bar \| pie \| line \| scatter \| heatmap   
  title        string                                                  
  reason       string                                                  Why this chart was selected
  x            string                                                  X-axis column
  y            string                                                  Y-axis column
  image_url    string                                                  Path to PNG file
  alt          string (optional)                                       Accessible description of chart
  width        number (optional)                                       Suggested width in pixels
  height       number (optional)                                      Suggested height in pixels

------------------------------------------------------------------------

# 1️⃣2️⃣ InsightPack

## 🔹 executive_insights

List of InsightItem

## 🔹 risks

List of InsightItem

## 🔹 opportunities

List of InsightItem

## 🔹 actions

List of ActionItem

------------------------------------------------------------------------

## InsightItem

  Field      Type
  ---------- --------
  text       string
  evidence   string

------------------------------------------------------------------------

## ActionItem

  Field      Type
  ---------- -----------------------
  text       string
  priority   low \| medium \| high

------------------------------------------------------------------------

# 1️⃣3️⃣ PDF Request Schema

## PdfRequest

  Field       Type
  ----------- ----------------------
  report_id   string
  mode        boardroom \| analyst
  report      ReportResponse

------------------------------------------------------------------------

# 🏁 Schema Philosophy

-   Contract-first development
-   Add fields, do not rename
-   Keep report_version updated if schema changes
-   Frontend types must mirror backend Pydantic models

This ensures stable parallel development between frontend and backend
teams.
