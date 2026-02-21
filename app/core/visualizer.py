from typing import List, Optional

import numpy as np
import pandas as pd
from pandas.api import types as pdt

from app.api.schemas import (
    BinPoint,
    BinsData,
    BinsMeta,
    CategoryValueData,
    CategoryValueMeta,
    CategoryValuePoint,
    ChartSpec,
    SeriesXYData,
    SeriesXYMeta,
    SeriesXYPoint,
)

# ── safety caps ──────────────────────────────────────────────
MAX_SERIES_POINTS = 500
MAX_CATEGORY_ITEMS = 200
MAX_HISTOGRAM_BINS = 100
DEFAULT_HISTOGRAM_BINS = 20


def _select_numeric_column(df: pd.DataFrame) -> Optional[str]:
    """Pick the most analytically relevant numeric column, skipping IDs."""
    # Skip columns that look like IDs or indexes
    id_patterns = {"id", "_id", "index", "key", "pk", "code", "zip", "pin", "phone"}
    numeric_cols = []
    for col in df.columns:
        if not pdt.is_numeric_dtype(df[col]):
            continue
        name_lower = str(col).lower().replace(" ", "_")
        # Skip if it looks like an ID column
        is_id = (
            name_lower in id_patterns
            or name_lower.endswith("_id")
            or name_lower.endswith("_code")
            or name_lower.startswith("id_")
        )
        # Also skip if all values are unique and monotonically increasing (likely a row ID)
        series = df[col].dropna()
        if not series.empty and is_id:
            continue
        if (
            not series.empty
            and series.nunique() == len(series)
            and series.is_monotonic_increasing
            and len(series) > 3
        ):
            continue
        numeric_cols.append(str(col))
    if not numeric_cols:
        return None
    # Prefer columns matching business-relevant keywords
    priority_keywords = [
        "revenue", "sales", "amount", "total", "profit", "income",
        "value", "price", "cost", "spend", "earning", "margin",
        "quantity", "units", "count",
    ]
    for kw in priority_keywords:
        for name in numeric_cols:
            if kw in name.lower():
                return name
    return numeric_cols[0]


def _select_categorical_column(df: pd.DataFrame) -> Optional[str]:
    candidates: list[str] = []
    for col in df.columns:
        series = df[col]
        if pdt.is_numeric_dtype(series):
            continue
        non_null = series.dropna()
        unique = non_null.nunique()
        if unique == 0:
            continue
        if unique <= max(10, int(len(non_null) * 0.1)):
            candidates.append(col)
    if not candidates:
        return None
    for name in candidates:
        if str(name).lower() in {"region", "segment", "category"}:
            return name
    return candidates[0]


def _select_datetime_column(df: pd.DataFrame) -> Optional[str]:
    datetime_cols = [col for col in df.columns if pdt.is_datetime64_any_dtype(df[col])]
    if datetime_cols:
        return datetime_cols[0]
    for col in df.columns:
        name = str(col).lower()
        if "date" in name or "time" in name:
            return col
    return None


# ── chart_data builders ──────────────────────────────────────


def _build_line_data(
    df: pd.DataFrame, x_col: str, y_col: str,
) -> SeriesXYData:
    """Aggregate time-series for a line chart (deduplicate by date, cap points)."""
    sub = df[[x_col, y_col]].dropna().copy()
    sample_size = len(sub)

    # Ensure x is string-serialisable datetime
    if pdt.is_datetime64_any_dtype(sub[x_col]):
        sub[x_col] = sub[x_col].dt.strftime("%Y-%m-%dT%H:%M:%S")
    else:
        sub[x_col] = sub[x_col].astype(str)

    # Aggregate duplicate dates
    agg = sub.groupby(x_col)[y_col].mean().reset_index().sort_values(x_col)

    # Down-sample if too many points
    if len(agg) > MAX_SERIES_POINTS:
        step = max(1, len(agg) // MAX_SERIES_POINTS)
        agg = agg.iloc[::step].head(MAX_SERIES_POINTS)

    points = [
        SeriesXYPoint(x=str(row[x_col]), y=round(float(row[y_col]), 2))
        for _, row in agg.iterrows()
    ]

    # Detect granularity heuristic
    granularity = None
    if pdt.is_datetime64_any_dtype(df[x_col]):
        diffs = df[x_col].dropna().sort_values().diff().dropna()
        if not diffs.empty:
            median_days = diffs.median().days
            if median_days <= 0:
                granularity = "hour"
            elif median_days <= 1:
                granularity = "day"
            elif median_days <= 7:
                granularity = "week"
            elif median_days <= 31:
                granularity = "month"
            else:
                granularity = "quarter"

    return SeriesXYData(
        data=points,
        meta=SeriesXYMeta(
            xLabel=str(x_col),
            yLabel=str(y_col),
            granularity=granularity,
        ),
        sample_size=sample_size,
    )


def _build_bar_data(
    df: pd.DataFrame, x_col: str, y_col: str,
) -> CategoryValueData:
    """Aggregate a bar chart: sum by category, cap items."""
    sub = df[[x_col, y_col]].dropna()
    sample_size = len(sub)
    agg = sub.groupby(x_col)[y_col].sum().reset_index()
    agg = agg.sort_values(y_col, ascending=False).head(MAX_CATEGORY_ITEMS)

    points = [
        CategoryValuePoint(category=str(row[x_col]), value=round(float(row[y_col]), 2))
        for _, row in agg.iterrows()
    ]
    return CategoryValueData(
        data=points,
        meta=CategoryValueMeta(
            categoryLabel=str(x_col),
            valueLabel=str(y_col),
            agg="sum",
        ),
        sample_size=sample_size,
    )


def _build_histogram_data(
    df: pd.DataFrame, x_col: str,
) -> BinsData:
    """Bucket a numeric column into histogram bins."""
    series = df[x_col].dropna().astype(float)
    sample_size = len(series)
    bin_count = min(DEFAULT_HISTOGRAM_BINS, max(5, int(np.sqrt(sample_size))))
    bin_count = min(bin_count, MAX_HISTOGRAM_BINS)

    counts, edges = np.histogram(series, bins=bin_count)
    points = [
        BinPoint(
            bin_start=round(float(edges[i]), 2),
            bin_end=round(float(edges[i + 1]), 2),
            count=int(counts[i]),
        )
        for i in range(len(counts))
    ]
    return BinsData(
        data=points,
        meta=BinsMeta(valueLabel=str(x_col), bin_count=bin_count),
        sample_size=sample_size,
    )


def generate_charts(df: pd.DataFrame, report_id: str) -> List[ChartSpec]:
    charts: list[ChartSpec] = []
    main_numeric = _select_numeric_column(df)
    categorical = _select_categorical_column(df)
    datetime_col = _select_datetime_column(df)
    if datetime_col is not None and main_numeric is not None:
        line_data = _build_line_data(df, str(datetime_col), str(main_numeric))
        charts.append(
            ChartSpec(
                id="chart_1",
                chart_type="line",
                title=f"{main_numeric} over Time",
                reason="A datetime column and numeric KPI were detected; line chart shows trend.",
                x=str(datetime_col),
                y=str(main_numeric),
                image_url=f"/static/{report_id}/chart_1.png",
                alt=f"Line chart of {main_numeric} over {datetime_col}.",
                width=960,
                height=480,
                chart_data=line_data,
            )
        )
    if categorical is not None and main_numeric is not None:
        bar_data = _build_bar_data(df, str(categorical), str(main_numeric))
        charts.append(
            ChartSpec(
                id="chart_2",
                chart_type="bar",
                title=f"{main_numeric} by {categorical}",
                reason="Categorical and numeric columns detected; bar chart compares segments.",
                x=str(categorical),
                y=str(main_numeric),
                image_url=f"/static/{report_id}/chart_2.png",
                alt=f"Bar chart of {main_numeric} by {categorical}.",
                width=960,
                height=480,
                chart_data=bar_data,
            )
        )
    if main_numeric is not None:
        hist_data = _build_histogram_data(df, str(main_numeric))
        charts.append(
            ChartSpec(
                id="chart_3",
                chart_type="histogram",
                title=f"{main_numeric} Distribution",
                reason="Histogram reveals distribution shape and extreme values.",
                x=str(main_numeric),
                y=None,
                image_url=f"/static/{report_id}/chart_3.png",
                alt=f"Histogram of {main_numeric}.",
                width=960,
                height=480,
                chart_data=hist_data,
            )
        )
    return charts

