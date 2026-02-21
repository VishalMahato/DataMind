import io
from datetime import datetime
from pathlib import Path
from typing import BinaryIO, Optional
from uuid import uuid4

import pandas as pd
from pandas.api import types as pdt

from app.api.schemas import (
    ActionItem,
    CleaningLogItem,
    ColumnProfile,
    DataPreview,
    DatasetMeta,
    InsightItem,
    InsightPack,
    NumericStats,
    OutlierSummary,
    ProfilingSummary,
    ReportResponse,
    TopValue,
)
from app.core.chart_renderer import render_charts
from app.core.trend_engine import build_trend_and_findings
from app.core.visualizer import generate_charts


BASE_DIR = Path(__file__).resolve().parents[2]


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
        if pdt.is_object_dtype(df[col]):
            sample = df[col].dropna().head(20)
            try:
                parsed = pd.to_datetime(sample, infer_datetime_format=True)
                if parsed.notna().all():
                    df[col] = pd.to_datetime(df[col], infer_datetime_format=True)
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

    # ── Read the uploaded file (raise on failure) ──────────────
    try:
        df, size_bytes = _read_dataframe(file_obj)
    except Exception as exc:
        raise ValueError(f"Unable to read CSV: {exc}") from exc

    # ── Clean ──────────────────────────────────────────────────
    df, cleaning_log = _clean_dataframe(df)

    # ── Metadata & profiling ──────────────────────────────────
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

    # ── Charts ────────────────────────────────────────────────
    charts = generate_charts(df, report_id)
    render_charts(df, report_id, charts)

    # ── Insights (placeholder until LLM engine is wired) ─────
    insights = InsightPack(
        executive_insights=[],
        risks=[],
        opportunities=[],
        actions=[],
    )

    return ReportResponse(
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
    )
