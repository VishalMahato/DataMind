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
    c.setFont("Helvetica-Bold", 12)
    c.drawString(20 * mm, y, "Executive Summary")
    y -= 8 * mm
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
    if report.wow_findings:
        y -= 4 * mm
        if y < 30 * mm:
            c.showPage()
            y = height - 20 * mm
        c.setFont("Helvetica-Bold", 12)
        c.drawString(20 * mm, y, "Wow Findings")
        y -= 8 * mm
        c.setFont("Helvetica", 10)
        for finding in report.wow_findings[:5]:
            text = f"[{finding.severity.upper()}] {finding.title}"
            c.drawString(25 * mm, y, text)
            y -= 6 * mm
            if y < 20 * mm:
                c.showPage()
                y = height - 20 * mm
    c.showPage()
    c.setFont("Helvetica-Bold", 14)
    c.drawString(20 * mm, height - 20 * mm, "Charts")
    y = height - 32 * mm
    c.setFont("Helvetica", 10)
    for chart in report.charts:
        image_path = STATIC_DIR / report.report_id / f"{chart.id}.png"
        if not image_path.exists():
            continue
        if y < 60 * mm:
            c.showPage()
            c.setFont("Helvetica-Bold", 14)
            c.drawString(20 * mm, height - 20 * mm, "Charts")
            y = height - 32 * mm
            c.setFont("Helvetica", 10)
        c.drawString(20 * mm, y, chart.title)
        y -= 6 * mm
        img_width = width - 40 * mm
        img_height = img_width / 2
        c.drawImage(
            str(image_path),
            20 * mm,
            y - img_height,
            width=img_width,
            height=img_height,
            preserveAspectRatio=True,
            mask="auto",
        )
        y -= img_height + 10 * mm
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
