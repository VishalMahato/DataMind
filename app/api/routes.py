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
    report = generate_report_from_file(file.file)
    return report


@router.post("/pdf")
async def generate_pdf(request: PdfRequest) -> Response:
    raise HTTPException(status_code=501, detail="PDF generation not implemented")


@router.get("/health")
async def health() -> JSONResponse:
    return JSONResponse({"status": "ok"})
