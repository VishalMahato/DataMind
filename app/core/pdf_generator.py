from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

from app.api.schemas import ReportResponse
from app.core.report_renderer import render_report_html


BASE_DIR = Path(__file__).resolve().parents[2]
STATIC_DIR = BASE_DIR / "static"


def _get_weasyprint_html():
    try:
        from weasyprint import HTML
    except OSError:
        return None
    return HTML


def _generate_pdf_with_reportlab(report: ReportResponse, pdf_path: Path) -> None:
    c = canvas.Canvas(str(pdf_path), pagesize=A4)
    width, height = A4
    y = height - 20 * mm
    c.setFont("Helvetica-Bold", 16)
    c.drawString(20 * mm, y, "DataMind Report")
    y -= 10 * mm
    c.setFont("Helvetica", 10)
    c.drawString(20 * mm, y, f"File: {report.dataset_meta.filename}")
    y -= 6 * mm
    c.drawString(20 * mm, y, f"Generated at: {report.generated_at}")
    y -= 6 * mm
    c.drawString(20 * mm, y, f"Mode: {report.mode}")
    y -= 6 * mm
    c.drawString(
        20 * mm,
        y,
        f"Rows: {report.dataset_meta.rows}  Columns: {report.dataset_meta.columns}",
    )
    y -= 12 * mm
    if report.trend and report.trend.summary:
        c.setFont("Helvetica-Bold", 12)
        c.drawString(20 * mm, y, "Trend Summary")
        y -= 8 * mm
        c.setFont("Helvetica", 10)
        for line in report.trend.summary:
            c.drawString(25 * mm, y, str(line))
            y -= 6 * mm
            if y < 20 * mm:
                c.showPage()
                y = height - 20 * mm
    c.showPage()
    c.save()


def generate_report_pdf(report: ReportResponse) -> Path:
    HTML = _get_weasyprint_html()
    report_dir = STATIC_DIR / report.report_id
    report_dir.mkdir(parents=True, exist_ok=True)
    pdf_path = report_dir / "report.pdf"
    if HTML is not None:
        html_str = render_report_html(report)
        HTML(string=html_str, base_url=str(BASE_DIR)).write_pdf(str(pdf_path))
        return pdf_path
    _generate_pdf_with_reportlab(report, pdf_path)
    return pdf_path
