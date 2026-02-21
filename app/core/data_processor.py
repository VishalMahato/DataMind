import io
import time
from datetime import datetime
from pathlib import Path
from typing import BinaryIO, Optional
from uuid import uuid4

import pandas as pd
from pandas.api import types as pdt

from app.api.schemas import (
    ActionItem,
    Artifacts,
    ChatContext,
    CleaningLogItem,
    ColumnProfile,
    DataPreview,
    DatasetMeta,
    InsightItem,
    InsightPack,
    KpiTile,
    NumericStats,
    OutlierSummary,
    PipelineStep,
    ProfilingSummary,
    ReportResponse,
    TopValue,
)
from app.core.chart_renderer import render_charts
from app.core.llm_engine import generate_chat_context, generate_insights, generate_kpi_suggestions
from app.core.report_renderer import render_report_html
from app.core.trend_engine import build_trend_and_findings
from app.core.visualizer import generate_charts


BASE_DIR = Path(__file__).resolve().parents[2]


def _fmt_number(n: float) -> str:
    """Format a number for display: 1234567 -> '1.23M', 1234 -> '1.23K', etc."""
    abs_n = abs(n)
    if abs_n >= 1_000_000_000:
        return f"{n / 1_000_000_000:.2f}B"
    if abs_n >= 1_000_000:
        return f"{n / 1_000_000:.2f}M"
    if abs_n >= 1_000:
        return f"{n / 1_000:.2f}K"
    if n == int(n):
        return str(int(n))
    return f"{n:.2f}"


_AGG_FUNCTIONS = {
    "sum":            lambda s: float(s.sum(skipna=True)),
    "mean":           lambda s: float(s.mean(skipna=True)),
    "median":         lambda s: float(s.median(skipna=True)),
    "max":            lambda s: float(s.max(skipna=True)),
    "min":            lambda s: float(s.min(skipna=True)),
    "count":          lambda s: int(s.count()),
    "count_distinct": lambda s: int(s.nunique()),
    "range":          lambda s: float(s.max(skipna=True) - s.min(skipna=True)),
    "latest":         lambda s: float(s.dropna().iloc[-1]) if len(s.dropna()) else 0.0,
}


def _apply_agg(df: pd.DataFrame, column: str, agg: str) -> float:
    """Safely apply an aggregation to a column."""
    if column not in df.columns:
        return 0.0
    series = df[column]
    fn = _AGG_FUNCTIONS.get(agg, _AGG_FUNCTIONS["sum"])
    try:
        return fn(series)
    except Exception:
        return 0.0


def _sublabel_text(df: pd.DataFrame, column: str, sub_agg: str | None) -> str | None:
    """Compute a sublabel value using a secondary aggregation."""
    if not sub_agg or sub_agg == "null" or column not in df.columns:
        return None
    val = _apply_agg(df, column, sub_agg)
    agg_label = sub_agg.replace("_", " ").title()
    return f"{agg_label} {_fmt_number(val)}"


def _build_kpi_tiles(
    df: pd.DataFrame,
    profiling: 'ProfilingSummary',
    trend: 'TrendSummary',
) -> list[KpiTile]:
    """Build KPI tiles using LLM-decided aggregations per column."""
    tiles: list[KpiTile] = []

    # 1. Always include Total Rows + Data Completeness
    tiles.append(KpiTile(
        label="Total Rows",
        value=_fmt_number(len(df)),
        sublabel=f"{len(df.columns)} columns",
    ))

    total_missing = sum(profiling.missing_by_column.values())
    total_cells = len(df) * len(df.columns)
    pct_missing = (total_missing / total_cells * 100) if total_cells else 0
    tiles.append(KpiTile(
        label="Data Completeness",
        value=f"{100 - pct_missing:.1f}%",
        sublabel=f"{total_missing} missing value(s)" if total_missing else "No missing values",
    ))

    # 2. Ask LLM which columns to highlight and how to aggregate
    suggestions = generate_kpi_suggestions(profiling, rows=len(df))

    if suggestions:
        valid_cols = set(str(c) for c in df.columns)
        for item in suggestions[:6]:  # cap at 6 LLM tiles
            col = item.get("column", "")
            agg = item.get("agg", "sum")
            label = item.get("label", col)
            sub_agg = item.get("sublabel_agg")

            if col not in valid_cols:
                continue
            if agg == "count_distinct":
                val = int(df[col].nunique())
                tiles.append(KpiTile(
                    label=label,
                    value=_fmt_number(val),
                    sublabel=None,
                ))
            else:
                val = _apply_agg(df, col, agg)
                sublabel = _sublabel_text(df, col, sub_agg)
                tiles.append(KpiTile(
                    label=label,
                    value=_fmt_number(val),
                    sublabel=sublabel,
                ))
    else:
        # Fallback: heuristic when LLM unavailable
        numeric_profiles = [
            cp for cp in profiling.column_profiles if cp.dtype == "numeric" and cp.stats
        ]
        for cp in numeric_profiles[:3]:
            col_name = cp.name.replace("_", " ").title()
            actual_sum = float(df[cp.name].sum(skipna=True))
            tiles.append(KpiTile(
                label=f"Total {col_name}",
                value=_fmt_number(actual_sum),
                sublabel=f"Avg {_fmt_number(cp.stats.mean)}",
            ))

    # 3. Trend KPI (if available)
    if trend.available and trend.metrics:
        direction = "↑" if trend.metrics.pct_change >= 0 else "↓"
        tiles.append(KpiTile(
            label=f"{trend.kpi_column or 'KPI'} Trend",
            value=f"{direction} {abs(trend.metrics.pct_change):.1f}%",
            sublabel=f"{_fmt_number(trend.metrics.start_value)} → {_fmt_number(trend.metrics.end_value)}",
        ))

    # 4. Outlier count
    total_outliers = sum(
        cp.outliers.count for cp in profiling.column_profiles
        if cp.outliers and cp.outliers.count > 0
    )
    if total_outliers > 0:
        tiles.append(KpiTile(
            label="Outliers Detected",
            value=str(total_outliers),
            sublabel="Across all numeric columns",
        ))

    return tiles


def _read_dataframe(file_obj: BinaryIO) -> tuple[pd.DataFrame, int]:
    file_obj.seek(0)
    content = file_obj.read()
    size_bytes = len(content)
    buffer = io.BytesIO(content)
    df = pd.read_csv(buffer)
    return df, size_bytes


def _build_preview(df: pd.DataFrame, max_rows: int = 5) -> DataPreview:
    columns = [str(name) for name in df.columns]
    rows = df.head(max_rows).to_dict(orient="records")
    return DataPreview(columns=columns, rows=rows)


def _infer_dtype(series: pd.Series) -> str:
    if pdt.is_bool_dtype(series):
        return "boolean"
    if pdt.is_datetime64_any_dtype(series):
        return "datetime"
    if pdt.is_numeric_dtype(series):
        return "numeric"
    non_null = series.dropna()
    if non_null.empty:
        return "unknown"
    # Check if string values look like dates before classifying as categorical
    if pdt.is_string_dtype(series) or pdt.is_object_dtype(series):
        sample = non_null.head(20)
        try:
            parsed = pd.to_datetime(sample, format="mixed", dayfirst=False)
            if parsed.notna().all():
                return "datetime"
        except (ValueError, TypeError):
            pass
    unique_count = non_null.nunique()
    if unique_count <= max(10, int(len(non_null) * 0.05)):
        return "categorical"
    return "text"


def _build_profiling(df: pd.DataFrame) -> ProfilingSummary:
    missing_by_column = {str(col): int(df[col].isna().sum()) for col in df.columns}
    unique_by_column = {
        str(col): int(df[col].nunique(dropna=True)) for col in df.columns
    }
    column_profiles: list[ColumnProfile] = []
    for col in df.columns:
        series = df[col]
        dtype = _infer_dtype(series)
        stats = None
        outliers = None
        top_value = None
        if dtype == "numeric":
            numeric = series.dropna().astype(float)
            if not numeric.empty:
                stats = NumericStats(
                    min=float(numeric.min()),
                    max=float(numeric.max()),
                    mean=float(numeric.mean()),
                    median=float(numeric.median()),
                    std=float(numeric.std(ddof=0)),
                )
                q1 = numeric.quantile(0.25)
                q3 = numeric.quantile(0.75)
                iqr = q3 - q1
                lower = float(q1 - 1.5 * iqr)
                upper = float(q3 + 1.5 * iqr)
                count = int((numeric < lower).sum() + (numeric > upper).sum())
                outliers = OutlierSummary(
                    method="iqr",
                    count=count,
                    lower_bound=lower,
                    upper_bound=upper,
                )
        elif dtype in {"categorical", "boolean"}:
            non_null = series.dropna()
            if not non_null.empty:
                value_counts = non_null.astype(str).value_counts()
                value = str(value_counts.index[0])
                count = int(value_counts.iloc[0])
                top_value = TopValue(value=value, count=count)
        column_profiles.append(
            ColumnProfile(
                name=str(col),
                dtype=dtype,
                stats=stats,
                outliers=outliers,
                top_value=top_value,
            )
        )
    return ProfilingSummary(
        missing_by_column=missing_by_column,
        unique_by_column=unique_by_column,
        column_profiles=column_profiles,
    )


def _clean_dataframe(df: pd.DataFrame) -> tuple[pd.DataFrame, list[CleaningLogItem]]:
    """Clean the dataframe and return the cleaned df + a log of actions taken."""
    log: list[CleaningLogItem] = []

    # 1. Drop fully-empty rows
    before_rows = len(df)
    df = df.dropna(how="all")
    after_rows = len(df)
    dropped = before_rows - after_rows
    if dropped:
        log.append(CleaningLogItem(
            action="drop_empty_rows",
            description=f"Removed {dropped} completely empty row(s)",
            before={"rows": before_rows},
            after={"rows": after_rows},
        ))

    # 2. Drop fully-empty columns
    before_cols = list(df.columns)
    df = df.dropna(axis=1, how="all")
    dropped_cols = set(before_cols) - set(df.columns)
    if dropped_cols:
        log.append(CleaningLogItem(
            action="drop_empty_columns",
            description=f"Removed empty column(s): {', '.join(sorted(dropped_cols))}",
            before={"columns": len(before_cols)},
            after={"columns": len(df.columns)},
        ))

    # 3. Drop duplicate rows
    before_rows = len(df)
    df = df.drop_duplicates()
    after_rows = len(df)
    dropped = before_rows - after_rows
    if dropped:
        log.append(CleaningLogItem(
            action="drop_duplicates",
            description=f"Removed {dropped} duplicate row(s)",
            before={"rows": before_rows},
            after={"rows": after_rows},
        ))

    # 4. Strip whitespace from string columns
    str_cols = df.select_dtypes(include="object").columns.tolist()
    if str_cols:
        df[str_cols] = df[str_cols].apply(lambda c: c.str.strip())
        log.append(CleaningLogItem(
            action="strip_whitespace",
            description=f"Trimmed whitespace in {len(str_cols)} text column(s)",
            before={"columns": str_cols},
            after={"columns": str_cols},
        ))

    # 5. Parse date-like columns
    for col in df.columns:
        if pdt.is_string_dtype(df[col]) or pdt.is_object_dtype(df[col]):
            sample = df[col].dropna().head(20)
            try:
                parsed = pd.to_datetime(sample, format="mixed", dayfirst=False)
                if parsed.notna().all():
                    df[col] = pd.to_datetime(df[col], format="mixed", dayfirst=False)
                    log.append(CleaningLogItem(
                        action="parse_dates",
                        description=f"Parsed column '{col}' as datetime",
                        before={"dtype": "object"},
                        after={"dtype": str(df[col].dtype)},
                    ))
            except (ValueError, TypeError):
                pass

    if not log:
        log.append(CleaningLogItem(
            action="no_action",
            description="Dataset was already clean — no changes needed",
            before={},
            after={},
        ))

    return df, log


def generate_report_from_file(file_obj: BinaryIO, filename: Optional[str] = None) -> ReportResponse:
    now = datetime.utcnow()
    report_id = f"rpt_{now:%Y%m%d_%H%M%S}_{uuid4().hex[:6]}"
    generated_at = now.replace(microsecond=0).isoformat() + "Z"
    pipeline: list[PipelineStep] = []

    # ── Read / validate the uploaded file ──────────────────────
    t0 = time.perf_counter()
    try:
        df, size_bytes = _read_dataframe(file_obj)
        pipeline.append(PipelineStep(
            step="validation", ok=True,
            ms=int((time.perf_counter() - t0) * 1000),
            note=f"Parsed CSV: {df.shape[0]} rows × {df.shape[1]} cols",
        ))
    except Exception as exc:
        pipeline.append(PipelineStep(
            step="validation", ok=False,
            ms=int((time.perf_counter() - t0) * 1000),
            note=str(exc),
        ))
        raise ValueError(f"Unable to read CSV: {exc}") from exc

    # ── Clean ──────────────────────────────────────────────────
    t0 = time.perf_counter()
    df, cleaning_log = _clean_dataframe(df)
    pipeline.append(PipelineStep(
        step="cleaning", ok=True,
        ms=int((time.perf_counter() - t0) * 1000),
        note=f"{len(cleaning_log)} action(s) applied",
    ))

    # ── Metadata & profiling ──────────────────────────────────
    t0 = time.perf_counter()
    dataset_meta = DatasetMeta(
        filename=filename or "uploaded.csv",
        rows=int(df.shape[0]),
        columns=int(df.shape[1]),
        size_bytes=size_bytes,
        detected_delimiter=",",
        encoding="utf-8",
    )
    preview = _build_preview(df)
    profiling = _build_profiling(df)

    # ── Trends & wow findings ─────────────────────────────────
    trend, trend_findings = build_trend_and_findings(df)
    pipeline.append(PipelineStep(
        step="eda", ok=True,
        ms=int((time.perf_counter() - t0) * 1000),
        note=f"Profiled {len(profiling.column_profiles)} columns, trend={'yes' if trend.available else 'no'}",
    ))

    # ── Charts ────────────────────────────────────────────────
    t0 = time.perf_counter()
    charts = generate_charts(df, report_id)
    render_charts(df, report_id, charts)
    pipeline.append(PipelineStep(
        step="charts", ok=True,
        ms=int((time.perf_counter() - t0) * 1000),
        note=f"Generated {len(charts)} chart(s)",
    ))

    # ── LLM-powered Insights ─────────────────────────────────
    t0 = time.perf_counter()
    chart_summaries = [
        {"chart_type": c.chart_type, "title": c.title}
        for c in charts
    ]
    insights = generate_insights(
        filename=filename or "uploaded.csv",
        rows=int(df.shape[0]),
        columns=int(df.shape[1]),
        profiling=profiling,
        trend=trend,
        wow_findings=trend_findings,
        chart_summaries=chart_summaries,
    )
    llm_ok = len(insights.executive_insights) > 0 and not any(
        "unavailable" in i.text.lower() or "could not be generated" in i.text.lower()
        for i in insights.executive_insights
    )
    pipeline.append(PipelineStep(
        step="llm", ok=llm_ok,
        ms=int((time.perf_counter() - t0) * 1000),
        note="GPT-4o-mini insights generated" if llm_ok else "LLM skipped or failed",
    ))

    # ── KPI Tiles ─────────────────────────────────────────────
    kpi_tiles = _build_kpi_tiles(df, profiling, trend)

    # ── Chat Context (LLM-powered) ───────────────────────────
    chat_context = generate_chat_context(
        filename=filename or "uploaded.csv",
        rows=int(df.shape[0]),
        columns=int(df.shape[1]),
        profiling=profiling,
        trend=trend,
        wow_findings=trend_findings,
        chart_summaries=chart_summaries,
    )

    # ── Build report (without artifacts first) ─────────────
    report = ReportResponse(
        report_version="v1",
        report_id=report_id,
        generated_at=generated_at,
        mode="boardroom",
        dataset_meta=dataset_meta,
        data_preview=preview,
        cleaning_log=cleaning_log,
        profiling=profiling,
        trend=trend,
        wow_findings=trend_findings,
        charts=charts,
        insights=insights,
        pipeline=pipeline,
        kpi_tiles=kpi_tiles,
        chat_context=chat_context,
    )

    # ── Artifacts: save JSON + HTML to static/ ─────────────
    report_dir = BASE_DIR / "static" / report_id
    report_dir.mkdir(parents=True, exist_ok=True)

    json_path = report_dir / "report.json"
    json_path.write_text(report.model_dump_json(indent=2), encoding="utf-8")

    html_path = report_dir / "report.html"
    try:
        html_content = render_report_html(report)
        html_path.write_text(html_content, encoding="utf-8")
        html_url = f"/static/{report_id}/report.html"
    except Exception:
        html_url = None

    report.artifacts = Artifacts(
        report_json_url=f"/static/{report_id}/report.json",
        report_html_url=html_url,
        pdf_url=None,  # Generated on-demand via POST /pdf
    )

    return report
