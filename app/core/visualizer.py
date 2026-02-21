from typing import List, Optional

import pandas as pd
from pandas.api import types as pdt

from app.api.schemas import ChartSpec


def _select_numeric_column(df: pd.DataFrame) -> Optional[str]:
    numeric_cols = [col for col in df.columns if pdt.is_numeric_dtype(df[col])]
    if not numeric_cols:
        return None
    for name in numeric_cols:
        if str(name).lower() in {"revenue", "sales", "amount", "value"}:
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


def generate_charts(df: pd.DataFrame, report_id: str) -> List[ChartSpec]:
    charts: list[ChartSpec] = []
    main_numeric = _select_numeric_column(df)
    categorical = _select_categorical_column(df)
    datetime_col = _select_datetime_column(df)
    if datetime_col is not None and main_numeric is not None:
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
            )
        )
    if categorical is not None and main_numeric is not None:
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
            )
        )
    if main_numeric is not None:
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
            )
        )
    return charts

