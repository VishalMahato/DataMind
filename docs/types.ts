// ─────────────────────────────────────────────────────────────
// Boardroom AI — Frontend TypeScript types (v1)
// Auto-mirrors backend Pydantic models in app/api/schemas.py
// ─────────────────────────────────────────────────────────────

// ── chart_data: aggregated payloads for frontend rendering ──

/** A single point in a time-series line chart. */
export interface SeriesXYPoint {
  /** ISO-8601 datetime string */
  x: string;
  y: number;
}

export interface SeriesXYMeta {
  xLabel: string;
  yLabel: string;
  unit?: string | null;
  granularity?:
    | "minute"
    | "hour"
    | "day"
    | "week"
    | "month"
    | "quarter"
    | "year"
    | null;
}

export interface SeriesXYData {
  format: "series_xy";
  data: SeriesXYPoint[];
  meta: SeriesXYMeta;
  /** Number of source rows that contributed. */
  sample_size?: number | null;
}

/** A single category slice for bar / pie charts. */
export interface CategoryValuePoint {
  category: string;
  value: number;
}

export interface CategoryValueMeta {
  categoryLabel: string;
  valueLabel: string;
  agg: "sum" | "avg" | "count" | "min" | "max";
  unit?: string | null;
}

export interface CategoryValueData {
  format: "category_value";
  data: CategoryValuePoint[];
  meta: CategoryValueMeta;
  sample_size?: number | null;
}

/** A single histogram bin. */
export interface BinPoint {
  bin_start: number;
  bin_end: number;
  count: number;
}

export interface BinsMeta {
  valueLabel: string;
  bin_count: number;
}

export interface BinsData {
  format: "bins";
  data: BinPoint[];
  meta: BinsMeta;
  sample_size?: number | null;
}

/** A single point in a scatter plot. */
export interface XYPointRaw {
  x: number;
  y: number;
}

export interface XYPointsMeta {
  xLabel: string;
  yLabel: string;
  unitX?: string | null;
  unitY?: string | null;
  sampling?: "all" | "random" | "top" | null;
  max_points?: number | null;
}

export interface XYPointsData {
  format: "xy_points";
  data: XYPointRaw[];
  meta: XYPointsMeta;
  sample_size?: number | null;
}

/** Discriminated union — switch on `format`. */
export type ChartDataPayload =
  | SeriesXYData
  | CategoryValueData
  | BinsData
  | XYPointsData;

// ── Core report types ───────────────────────────────────────

export interface DatasetMeta {
  filename: string;
  rows: number;
  columns: number;
  size_bytes: number;
  detected_delimiter: string;
  encoding: string;
}

export interface DataPreview {
  columns: string[];
  rows: Record<string, unknown>[];
}

export interface CleaningLogItem {
  action: string;
  description: string;
  before: Record<string, unknown>;
  after: Record<string, unknown>;
}

export interface NumericStats {
  min: number;
  max: number;
  mean: number;
  median: number;
  std: number;
}

export interface OutlierSummary {
  method: "iqr";
  count: number;
  lower_bound: number;
  upper_bound: number;
}

export interface TopValue {
  value: string;
  count: number;
}

export interface ColumnProfile {
  name: string;
  dtype:
    | "numeric"
    | "categorical"
    | "datetime"
    | "boolean"
    | "text"
    | "unknown";
  stats?: NumericStats | null;
  outliers?: OutlierSummary | null;
  top_value?: TopValue | null;
}

export interface ProfilingSummary {
  missing_by_column: Record<string, number>;
  unique_by_column: Record<string, number>;
  column_profiles: ColumnProfile[];
}

export interface TrendMetrics {
  start_value: number;
  end_value: number;
  pct_change: number;
}

export interface TrendSummary {
  available: boolean;
  date_column?: string | null;
  kpi_column?: string | null;
  summary?: string[] | null;
  metrics?: TrendMetrics | null;
}

export interface WowFinding {
  type: "anomaly" | "kpi_conflict" | "trend_shift" | "data_quality";
  severity: "low" | "medium" | "high";
  title: string;
  evidence: string;
  related_columns: string[];
}

export interface ChartSpec {
  id: string;
  chart_type:
    | "histogram"
    | "bar"
    | "pie"
    | "line"
    | "scatter"
    | "heatmap";
  title: string;
  reason: string;
  x?: string | null;
  y?: string | null;
  image_url: string;
  alt?: string | null;
  width?: number | null;
  height?: number | null;
  /** Pre-aggregated data for frontend chart rendering. Falls back to image_url when absent. */
  chart_data?: ChartDataPayload | null;
}

export interface InsightItem {
  text: string;
  evidence: string;
}

export interface ActionItem {
  text: string;
  priority: "low" | "medium" | "high";
}

export interface InsightPack {
  executive_insights: InsightItem[];
  risks: InsightItem[];
  opportunities: InsightItem[];
  actions: ActionItem[];
}

export interface PipelineStep {
  step:
    | "validation"
    | "cleaning"
    | "eda"
    | "charts"
    | "llm"
    | "html"
    | "pdf";
  ok: boolean;
  ms?: number | null;
  note?: string | null;
}

export interface Artifacts {
  report_json_url?: string | null;
  report_html_url?: string | null;
  pdf_url?: string | null;
}

export interface QualityScore {
  score: number;
  issues: string[];
  strengths: string[];
}

export interface KpiTile {
  label: string;
  value: string;
  sublabel?: string | null;
}

export interface WarningItem {
  code: string;
  message: string;
}

export interface ChatContext {
  dataset_brief: string;
  evidence_pack: string[];
  suggested_questions: string[];
}

export interface ReportResponse {
  report_version: "v1";
  report_id: string;
  generated_at: string;
  mode: "boardroom" | "analyst";
  dataset_meta: DatasetMeta;
  data_preview: DataPreview;
  cleaning_log: CleaningLogItem[];
  profiling: ProfilingSummary;
  trend: TrendSummary;
  wow_findings: WowFinding[];
  charts: ChartSpec[];
  insights: InsightPack;
  status?: string | null;
  pipeline?: PipelineStep[] | null;
  artifacts?: Artifacts | null;
  quality_score?: QualityScore | null;
  kpi_tiles?: KpiTile[] | null;
  warnings?: WarningItem[] | null;
  chat_context?: ChatContext | null;
}

export interface PdfRequest {
  report_id?: string | null;
  mode?: "boardroom" | "analyst" | null;
  report?: ReportResponse | null;
}
