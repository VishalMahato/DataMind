from typing import Dict, List, Optional, Literal, Union

from pydantic import BaseModel, Field, field_validator


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


# ── chart_data: aggregated payloads for frontend rendering ────────────


class SeriesXYPoint(BaseModel):
    """Single point in a time-series (line chart)."""
    x: str = Field(..., description="ISO-8601 datetime string")
    y: float


class SeriesXYMeta(BaseModel):
    xLabel: str
    yLabel: str
    unit: Optional[str] = None
    granularity: Optional[Literal["minute", "hour", "day", "week", "month", "quarter", "year"]] = None


class SeriesXYData(BaseModel):
    """chart_data payload for line charts."""
    format: Literal["series_xy"] = "series_xy"
    data: List[SeriesXYPoint] = Field(..., max_length=500)
    meta: SeriesXYMeta
    sample_size: Optional[int] = Field(None, description="Number of source rows that contributed")


class CategoryValuePoint(BaseModel):
    """Single category slice (bar / pie chart)."""
    category: str
    value: float


class CategoryValueMeta(BaseModel):
    categoryLabel: str
    valueLabel: str
    agg: Literal["sum", "avg", "count", "min", "max"]
    unit: Optional[str] = None


class CategoryValueData(BaseModel):
    """chart_data payload for bar and pie charts."""
    format: Literal["category_value"] = "category_value"
    data: List[CategoryValuePoint] = Field(..., max_length=200)
    meta: CategoryValueMeta
    sample_size: Optional[int] = None


class BinPoint(BaseModel):
    """Single histogram bin."""
    bin_start: float
    bin_end: float
    count: int


class BinsMeta(BaseModel):
    valueLabel: str
    bin_count: int


class BinsData(BaseModel):
    """chart_data payload for histogram charts."""
    format: Literal["bins"] = "bins"
    data: List[BinPoint] = Field(..., max_length=200)
    meta: BinsMeta
    sample_size: Optional[int] = None


class XYPointRaw(BaseModel):
    """Single point in a scatter plot."""
    x: float
    y: float


class XYPointsMeta(BaseModel):
    xLabel: str
    yLabel: str
    unitX: Optional[str] = None
    unitY: Optional[str] = None
    sampling: Optional[Literal["all", "random", "top"]] = None
    max_points: Optional[int] = Field(None, le=500)


class XYPointsData(BaseModel):
    """chart_data payload for scatter charts."""
    format: Literal["xy_points"] = "xy_points"
    data: List[XYPointRaw] = Field(..., max_length=500)
    meta: XYPointsMeta
    sample_size: Optional[int] = None


# Union discriminated by the 'format' field
ChartDataPayload = Union[SeriesXYData, CategoryValueData, BinsData, XYPointsData]


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
    chart_data: Optional[ChartDataPayload] = Field(
        None,
        description="Pre-aggregated data payload for frontend chart rendering. "
                    "Falls back to image_url when absent.",
    )


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


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, description="The user's question")
    chat_context: ChatContext = Field(..., description="The chat_context from the /analyze response")
    history: List[ChatMessage] = Field(
        default_factory=list,
        description="Previous conversation turns (newest last). Max 20 messages.",
        max_length=20,
    )


class ChatResponse(BaseModel):
    reply: str
    suggested_followups: List[str] = Field(
        default_factory=list,
        description="2-3 suggested follow-up questions",
    )
