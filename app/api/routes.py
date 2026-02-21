import asyncio
from functools import partial
from typing import Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, JSONResponse

from app.api.schemas import PdfRequest, ReportResponse
from app.core.data_processor import generate_report_from_file
from app.core.pdf_generator import generate_report_pdf


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
async def generate_pdf(request: PdfRequest) -> FileResponse:
    if request.report is None:
        raise HTTPException(
            status_code=400, detail="report must be provided in PdfRequest"
        )
    pdf_path = generate_report_pdf(request.report)
    return FileResponse(
        path=str(pdf_path),
        media_type="application/pdf",
        filename=f"{request.report.report_id}.pdf",
    )


@router.get("/health")
async def health() -> JSONResponse:
    return JSONResponse({"status": "ok"})
