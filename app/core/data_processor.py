import json
from pathlib import Path
from typing import BinaryIO

from app.api.schemas import ReportResponse


BASE_DIR = Path(__file__).resolve().parents[2]
SAMPLE_REPORT_PATH = BASE_DIR / "docs" / "report.sample.json"


def generate_report_from_file(file_obj: BinaryIO) -> ReportResponse:
    if SAMPLE_REPORT_PATH.exists():
        data = json.loads(SAMPLE_REPORT_PATH.read_text(encoding="utf-8"))
        return ReportResponse.parse_obj(data)
    data = {
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
    return ReportResponse.parse_obj(data)
