import io
import json
from pathlib import Path
from typing import BinaryIO, Optional

import pandas as pd
from pandas.api import types as pdt

from app.api.schemas import (
    ColumnProfile,
    DataPreview,
    DatasetMeta,
    NumericStats,
    OutlierSummary,
    ProfilingSummary,
    ReportResponse,
    TopValue,
)
from app.core.chart_renderer import render_charts
from app.core.visualizer import generate_charts


BASE_DIR = Path(__file__).resolve().parents[2]
SAMPLE_REPORT_PATH = BASE_DIR / "docs" / "report.sample.json"


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


def generate_report_from_file(file_obj: BinaryIO, filename: Optional[str] = None) -> ReportResponse:
    if SAMPLE_REPORT_PATH.exists():
        base_data = json.loads(SAMPLE_REPORT_PATH.read_text(encoding="utf-8"))
    else:
        base_data = {
            "report_version": "v1",
            "report_id": "rpt_placeholder",
            "generated_at": "1970-01-01T00:00:00Z",
            "mode": "boardroom",
            "dataset_meta": {
                "filename": "unknown.csv",
                "rows": 0,
                "columns": 0,
                "size_bytes": 0,
                "detected_delimiter": ",",
                "encoding": "utf-8",
            },
            "data_preview": {"columns": [], "rows": []},
            "cleaning_log": [],
            "profiling": {
                "missing_by_column": {},
                "unique_by_column": {},
                "column_profiles": [],
            },
            "trend": {"available": False},
            "wow_findings": [],
            "charts": [],
            "insights": {
                "executive_insights": [],
                "risks": [],
                "opportunities": [],
                "actions": [],
            },
        }
    report = ReportResponse.parse_obj(base_data)
    try:
        df, size_bytes = _read_dataframe(file_obj)
    except Exception:
        return report
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
    charts = generate_charts(df, report.report_id)
    render_charts(df, report.report_id, charts)
    report.dataset_meta = dataset_meta
    report.data_preview = preview
    report.profiling = profiling
    report.charts = charts
    return report
