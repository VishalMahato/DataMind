from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from app.api.schemas import ReportResponse


BASE_DIR = Path(__file__).resolve().parents[2]
TEMPLATES_DIR = BASE_DIR / "app" / "templates"


_env = Environment(
    loader=FileSystemLoader(str(TEMPLATES_DIR)),
    autoescape=select_autoescape(["html", "xml"]),
)


def render_report_html(report: ReportResponse) -> str:
    template = _env.get_template("report_template.html")
    html = template.render(report=report)
    return html
