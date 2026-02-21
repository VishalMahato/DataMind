import asyncio
from functools import partial
from typing import Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import JSONResponse, Response

from app.api.schemas import PdfRequest, ReportResponse
from app.core.data_processor import generate_report_from_file


router = APIRouter()


@router.post("/analyze", response_model=ReportResponse)
async def analyze(
    file: UploadFile = File(...),
    options: Optional[str] = Form(None),
) -> ReportResponse:
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(
            status_code=400,
            detail={"error": {"code": "INVALID_CSV", "message": "Only .csv files are supported"}},
        )
    try:
        loop = asyncio.get_running_loop()
        report = await loop.run_in_executor(
            None, partial(generate_report_from_file, file.file, file.filename)
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail={"error": {"code": "CSV_PARSE_ERROR", "message": str(exc)}},
        )
    return report


@router.post("/pdf")
async def generate_pdf(request: PdfRequest) -> Response:
    raise HTTPException(status_code=501, detail="PDF generation not implemented")


@router.get("/health")
async def health() -> JSONResponse:
    return JSONResponse({"status": "ok"})
