from typing import List, Tuple

import pandas as pd

from app.api.schemas import TrendMetrics, TrendSummary, WowFinding
from app.core.visualizer import _select_datetime_column, _select_numeric_column


def _build_time_series(df: pd.DataFrame) -> Tuple[pd.DataFrame, str, str]:
    date_col = _select_datetime_column(df)
    kpi_col = _select_numeric_column(df)
    if date_col is None or kpi_col is None:
        raise ValueError("Missing datetime or numeric column for trend")
    data = df[[date_col, kpi_col]].dropna().copy()
    data[date_col] = pd.to_datetime(data[date_col], errors="coerce")
    data = data.dropna(subset=[date_col])
    if data.empty:
        raise ValueError("No valid rows for trend after cleaning")
    data = data.sort_values(by=date_col)
    return data, str(date_col), str(kpi_col)


def build_trend_and_findings(df: pd.DataFrame) -> Tuple[TrendSummary, List[WowFinding]]:
    try:
        data, date_col, kpi_col = _build_time_series(df)
    except Exception:
        trend = TrendSummary(available=False)
        return trend, []

    # Aggregate by date to handle transaction-level data correctly.
    # If there are multiple values on the same date, sum them.
    agg = data.groupby(date_col)[kpi_col].sum().reset_index()
    agg = agg.sort_values(by=date_col)

    if len(agg) < 2:
        # Not enough distinct dates for a trend
        start_value = float(agg[kpi_col].iloc[0]) if len(agg) == 1 else 0.0
        trend = TrendSummary(
            available=True,
            date_column=date_col,
            kpi_column=kpi_col,
            summary=[f"Only {len(agg)} data point(s) — insufficient for trend analysis."],
            metrics=TrendMetrics(
                start_value=start_value,
                end_value=start_value,
                pct_change=0.0,
            ),
        )
        return trend, []

    # Compare first-period vs last-period aggregate
    # For many distinct dates, average the first 10% and last 10% for stability
    n = len(agg)
    window = max(1, n // 10)  # at least 1 row
    start_value = float(agg[kpi_col].iloc[:window].mean())
    end_value = float(agg[kpi_col].iloc[-window:].mean())

    if start_value == 0:
        pct_change = 0.0
    else:
        pct_change = (end_value - start_value) / start_value * 100.0
    metrics = TrendMetrics(
        start_value=start_value,
        end_value=end_value,
        pct_change=pct_change,
    )
    summary_lines: List[str] = []
    if start_value == 0 and end_value == 0:
        summary_lines.append(f"{kpi_col} remained at 0 over the period.")
    else:
        if pct_change > 5:
            summary_lines.append(
                f"{kpi_col} increased {pct_change:.1f}% over the period."
            )
        elif pct_change < -5:
            summary_lines.append(
                f"{kpi_col} decreased {abs(pct_change):.1f}% over the period."
            )
        else:
            summary_lines.append(
                f"{kpi_col} was relatively stable (change within ±5%)."
            )
    trend = TrendSummary(
        available=True,
        date_column=date_col,
        kpi_column=kpi_col,
        summary=summary_lines,
        metrics=metrics,
    )
    findings: List[WowFinding] = []
    abs_change = abs(pct_change)
    severity: str | None
    if abs_change >= 20:
        severity = "high"
    elif abs_change >= 10:
        severity = "medium"
    else:
        severity = None
    if severity is not None:
        direction = "up" if pct_change > 0 else "down"
        title = f"{kpi_col} {direction} {abs_change:.1f}% over the period"
        evidence = (
            f"{kpi_col} moved from {start_value:.2f} to {end_value:.2f} "
            f"({pct_change:.1f}%)."
        )
        findings.append(
            WowFinding(
                type="trend_shift",
                severity=severity,
                title=title,
                evidence=evidence,
                related_columns=[date_col, kpi_col],
            )
        )
    return trend, findings

