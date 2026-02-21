from typing import Dict, List, Optional, Literal

from pydantic import BaseModel


class DatasetMeta(BaseModel):
    filename: str
    rows: int
    columns: int
    size_bytes: int
    detected_delimiter: str
    encoding: str


class DataPreview(BaseModel):
    columns: List[str]
    rows: List[Dict[str, object]]


class CleaningLogItem(BaseModel):
    action: str
    description: str
    before: Dict[str, object]
    after: Dict[str, object]


class NumericStats(BaseModel):
    min: float
    max: float
    mean: float
    median: float
    std: float


class OutlierSummary(BaseModel):
    method: Literal["iqr"]
    count: int
    lower_bound: float
    upper_bound: float


class TopValue(BaseModel):
    value: str
    count: int


class ColumnProfile(BaseModel):
    name: str
    dtype: Literal["numeric", "categorical", "datetime", "boolean", "text", "unknown"]
    stats: Optional[NumericStats] = None
    outliers: Optional[OutlierSummary] = None
    top_value: Optional[TopValue] = None


class ProfilingSummary(BaseModel):
    missing_by_column: Dict[str, int]
    unique_by_column: Dict[str, int]
    column_profiles: List[ColumnProfile]


class TrendMetrics(BaseModel):
    start_value: float
    end_value: float
    pct_change: float


class TrendSummary(BaseModel):
    available: bool
    date_column: Optional[str] = None
    kpi_column: Optional[str] = None
    summary: Optional[List[str]] = None
    metrics: Optional[TrendMetrics] = None


class WowFinding(BaseModel):
    type: Literal["anomaly", "kpi_conflict", "trend_shift", "data_quality"]
    severity: Literal["low", "medium", "high"]
    title: str
    evidence: str
    related_columns: List[str]


class ChartSpec(BaseModel):
    id: str
    chart_type: Literal["histogram", "bar", "pie", "line", "scatter", "heatmap"]
    title: str
    reason: str
    x: Optional[str] = None
    y: Optional[str] = None
    image_url: str
    alt: Optional[str] = None
    width: Optional[int] = None
    height: Optional[int] = None


class InsightItem(BaseModel):
    text: str
    evidence: str


class ActionItem(BaseModel):
    text: str
    priority: Literal["low", "medium", "high"]


class InsightPack(BaseModel):
    executive_insights: List[InsightItem]
    risks: List[InsightItem]
    opportunities: List[InsightItem]
    actions: List[ActionItem]


class PipelineStep(BaseModel):
    step: Literal["validation", "cleaning", "eda", "charts", "llm", "html", "pdf"]
    ok: bool
    ms: Optional[int] = None
    note: Optional[str] = None


class Artifacts(BaseModel):
    report_json_url: Optional[str] = None
    report_html_url: Optional[str] = None
    pdf_url: Optional[str] = None


class QualityScore(BaseModel):
    score: int
    issues: List[str]
    strengths: List[str]


class KpiTile(BaseModel):
    label: str
    value: str
    sublabel: Optional[str] = None


class WarningItem(BaseModel):
    code: str
    message: str


class ChatContext(BaseModel):
    dataset_brief: str
    evidence_pack: List[str]
    suggested_questions: List[str]


class ReportResponse(BaseModel):
    report_version: Literal["v1"]
    report_id: str
    generated_at: str
    mode: Literal["boardroom", "analyst"]
    dataset_meta: DatasetMeta
    data_preview: DataPreview
    cleaning_log: List[CleaningLogItem]
    profiling: ProfilingSummary
    trend: TrendSummary
    wow_findings: List[WowFinding]
    charts: List[ChartSpec]
    insights: InsightPack
    status: Optional[str] = None
    pipeline: Optional[List[PipelineStep]] = None
    artifacts: Optional[Artifacts] = None
    quality_score: Optional[QualityScore] = None
    kpi_tiles: Optional[List[KpiTile]] = None
    warnings: Optional[List[WarningItem]] = None
    chat_context: Optional[ChatContext] = None


class PdfRequest(BaseModel):
    report_id: Optional[str] = None
    mode: Optional[Literal["boardroom", "analyst"]] = None
    report: Optional[ReportResponse] = None
