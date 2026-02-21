from pathlib import Path
from typing import List

import pandas as pd
from PIL import Image

from app.api.schemas import ChartSpec


BASE_DIR = Path(__file__).resolve().parents[2]
STATIC_DIR = BASE_DIR / "static"


def _ensure_report_dir(report_id: str) -> Path:
    report_dir = STATIC_DIR / report_id
    report_dir.mkdir(parents=True, exist_ok=True)
    return report_dir


def _create_placeholder_png(path: Path, width: int = 960, height: int = 480) -> None:
    image = Image.new("RGB", (width, height), color=(32, 64, 160))
    image.save(path, format="PNG")


def render_charts(df: pd.DataFrame, report_id: str, charts: List[ChartSpec]) -> None:
    report_dir = _ensure_report_dir(report_id)
    for chart in charts:
        target = report_dir / f"{chart.id}.png"
        if not target.exists():
            _create_placeholder_png(target)

