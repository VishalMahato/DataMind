import io
import json
from pathlib import Path
from typing import BinaryIO, Optional

import pandas as pd

from app.api.schemas import DataPreview, DatasetMeta, ReportResponse


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
    report.dataset_meta = dataset_meta
    report.data_preview = preview
    return report
