import logging
from pathlib import Path
from typing import List

import pandas as pd
import plotly.graph_objects as go
from PIL import Image

from app.api.schemas import ChartSpec

logger = logging.getLogger(__name__)


BASE_DIR = Path(__file__).resolve().parents[2]
STATIC_DIR = BASE_DIR / "static"


def _ensure_report_dir(report_id: str) -> Path:
    report_dir = STATIC_DIR / report_id
    report_dir.mkdir(parents=True, exist_ok=True)
    return report_dir


def _create_placeholder_png(path: Path, label: str = "Chart unavailable", width: int = 960, height: int = 480) -> None:
    from PIL import ImageDraw, ImageFont

    image = Image.new("RGB", (width, height), color=(240, 240, 240))
    draw = ImageDraw.Draw(image)
    try:
        font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 24)
    except Exception:
        font = ImageFont.load_default()
    text = f"⚠ {label}"
    bbox = draw.textbbox((0, 0), text, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    draw.text(((width - tw) / 2, (height - th) / 2), text, fill=(120, 120, 120), font=font)
    image.save(path, format="PNG")


def _render_line_chart(df: pd.DataFrame, chart: ChartSpec, target: Path) -> None:
    if chart.x is None or chart.y is None:
        raise ValueError("Line chart requires both x and y")
    if chart.x not in df.columns or chart.y not in df.columns:
        raise ValueError("Line chart columns not found in DataFrame")
    data = df[[chart.x, chart.y]].dropna()
    fig = go.Figure(
        go.Scatter(
            x=data[chart.x],
            y=data[chart.y],
            mode="lines+markers",
        )
    )
    fig.update_layout(
        title=chart.title,
        xaxis_title=chart.x,
        yaxis_title=chart.y,
        width=chart.width or 960,
        height=chart.height or 480,
        margin=dict(l=40, r=20, t=60, b=40),
    )
    fig.write_image(str(target))


def _render_bar_chart(df: pd.DataFrame, chart: ChartSpec, target: Path) -> None:
    if chart.x is None or chart.y is None:
        raise ValueError("Bar chart requires both x and y")
    if chart.x not in df.columns or chart.y not in df.columns:
        raise ValueError("Bar chart columns not found in DataFrame")
    grouped = (
        df[[chart.x, chart.y]]
        .dropna()
        .groupby(chart.x)[chart.y]
        .sum()
        .reset_index()
    )
    fig = go.Figure(
        go.Bar(
            x=grouped[chart.x],
            y=grouped[chart.y],
        )
    )
    fig.update_layout(
        title=chart.title,
        xaxis_title=chart.x,
        yaxis_title=chart.y,
        width=chart.width or 960,
        height=chart.height or 480,
        margin=dict(l=40, r=20, t=60, b=40),
    )
    fig.write_image(str(target))


def _render_histogram(df: pd.DataFrame, chart: ChartSpec, target: Path) -> None:
    if chart.x is None:
        raise ValueError("Histogram chart requires x")
    if chart.x not in df.columns:
        raise ValueError("Histogram column not found in DataFrame")
    data = df[chart.x].dropna()
    fig = go.Figure(go.Histogram(x=data))
    fig.update_layout(
        title=chart.title,
        xaxis_title=chart.x,
        yaxis_title="Count",
        width=chart.width or 960,
        height=chart.height or 480,
        margin=dict(l=40, r=20, t=60, b=40),
    )
    fig.write_image(str(target))


def _render_chart(df: pd.DataFrame, chart: ChartSpec, target: Path) -> None:
    if chart.chart_type == "line":
        _render_line_chart(df, chart, target)
    elif chart.chart_type == "bar":
        _render_bar_chart(df, chart, target)
    elif chart.chart_type == "histogram":
        _render_histogram(df, chart, target)
    else:
        raise ValueError(f"Unsupported chart type: {chart.chart_type}")


def render_charts(df: pd.DataFrame, report_id: str, charts: List[ChartSpec]) -> None:
    report_dir = _ensure_report_dir(report_id)
    for chart in charts:
        target = report_dir / f"{chart.id}.png"
        if target.exists():
            continue
        try:
            _render_chart(df, chart, target)
        except Exception as exc:
            logger.error("Chart %s render failed: %s — writing placeholder", chart.id, exc)
            _create_placeholder_png(target, chart.title)

