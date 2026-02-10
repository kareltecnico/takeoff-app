from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen.canvas import Canvas

from app.reporting.models import ReportSection, TakeoffReport
from app.reporting.renderers import TakeoffReportRenderer

__all__ = ["PdfStyle", "ReportLabTakeoffPdfRenderer", "render_takeoff_pdf"]


@dataclass(frozen=True)
class PdfStyle:
    page_size = letter
    margin_left: float = 0.65 * inch
    margin_right: float = 0.65 * inch
    margin_top: float = 0.65 * inch
    margin_bottom: float = 0.65 * inch
    font: str = "Helvetica"
    font_bold: str = "Helvetica-Bold"
    font_size: int = 9
    title_size: int = 14
    section_size: int = 11
    line_height: float = 12


@dataclass(frozen=True)
class ReportLabTakeoffPdfRenderer(TakeoffReportRenderer):
    style: PdfStyle | None = None

    def render(self, report: TakeoffReport, output_path: Path) -> Path:
        return render_takeoff_pdf(report, output_path, style=self.style)


def _money(x: Decimal) -> str:
    return f"${x:.2f}"


def _fit_text(text: str, max_width: float, font: str, size: int) -> str:
    """Truncate with ellipsis so it fits in max_width."""
    if stringWidth(text, font, size) <= max_width:
        return text

    ell = "…"
    lo, hi = 0, len(text)
    best = ell

    while lo <= hi:
        mid = (lo + hi) // 2
        candidate = text[:mid].rstrip() + ell
        if stringWidth(candidate, font, size) <= max_width:
            best = candidate
            lo = mid + 1
        else:
            hi = mid - 1

    return best


def render_takeoff_pdf(
    report: TakeoffReport,
    output_path: Path,
    *,
    style: PdfStyle | None = None,
) -> Path:
    """Render a Take-Off PDF using a prepared report DTO (no domain logic)."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    style = style or PdfStyle()

    c = Canvas(str(output_path), pagesize=style.page_size)
    width, height = style.page_size

    x0 = style.margin_left
    x1 = width - style.margin_right
    y = height - style.margin_top

    def draw_text(text: str, *, font: str, size: int, x: float, y: float) -> None:
        c.setFont(font, size)
        c.drawString(x, y, text)

    # ---------- Header ----------
    draw_text(report.company_name, font=style.font_bold, size=style.title_size, x=x0, y=y)
    y -= style.line_height * 1.2

    draw_text(
        f"PROJECT: {report.project_name}    CONTRACTOR: {report.contractor_name}",
        font=style.font_bold,
        size=style.section_size,
        x=x0,
        y=y,
    )
    y -= style.line_height

    draw_text(
        f"MODEL GROUP: {report.model_group_display}    STORIES: {report.stories}",
        font=style.font,
        size=style.font_size,
        x=x0,
        y=y,
    )
    y -= style.line_height

    draw_text(
        f"CREATED AT: {report.created_at.strftime('%Y-%m-%d %H:%M')}",
        font=style.font,
        size=style.font_size,
        x=x0,
        y=y,
    )
    y -= style.line_height * 1.2

    # ---------- Column layout ----------
    table_width = x1 - x0
    col_item = 0.12 * table_width
    col_desc = 0.34 * table_width
    col_price = 0.10 * table_width
    col_qty = 0.07 * table_width
    col_factor = 0.07 * table_width
    col_sub = 0.10 * table_width
    col_tax = 0.09 * table_width
    col_total = 0.09 * table_width

    cols: list[tuple[str, float]] = [
        ("ITEM#", col_item),
        ("DESCRIPTION", col_desc),
        ("PRICE", col_price),
        ("QTY", col_qty),
        ("FACTOR", col_factor),
        ("SUBTOTAL", col_sub),
        ("TAX", col_tax),
        ("TOTAL", col_total),
    ]
    numeric_headers = {"PRICE", "QTY", "FACTOR", "SUBTOTAL", "TAX", "TOTAL"}

    def draw_row(values: list[str], ypos: float, *, bold: bool = False) -> None:
        font = style.font_bold if bold else style.font
        c.setFont(font, style.font_size)

        x = x0
        pad = 2

        for (hdr, w), val in zip(cols, values, strict=True):
            if hdr == "DESCRIPTION":
                val = _fit_text(val, w - 2 * pad, font, style.font_size)
                c.drawString(x + pad, ypos, val)
            elif hdr in numeric_headers:
                c.drawRightString(x + w - pad, ypos, val)
            else:
                c.drawString(x + pad, ypos, val)

            x += w

    def draw_table_header(ypos: float) -> float:
        draw_row([h for h, _ in cols], ypos, bold=True)
        ypos -= style.line_height * 0.9
        c.line(x0, ypos + 3, x1, ypos + 3)
        return ypos - style.line_height * 0.3

    def ensure_space(lines_needed: int) -> None:
        nonlocal y
        min_y = style.margin_bottom + (lines_needed * style.line_height)
        if y < min_y:
            c.showPage()
            y = height - style.margin_top

    def render_section(section: ReportSection) -> None:
        nonlocal y
        ensure_space(6)

        draw_text(section.title, font=style.font_bold, size=style.section_size, x=x0, y=y)
        y -= style.line_height

        if not section.lines:
            draw_text("(no items)", font=style.font, size=style.font_size, x=x0, y=y)
            y -= style.line_height
        else:
            y = draw_table_header(y)
            for ln in section.lines:
                ensure_space(2)
                values = [
                    ln.item_number,
                    ln.description,
                    _money(ln.unit_price),
                    f"{ln.qty}",
                    f"{ln.factor}",
                    _money(ln.subtotal),
                    _money(ln.tax),
                    _money(ln.total),
                ]
                draw_row(values, y)
                y -= style.line_height

        ensure_space(3)
        c.setFont(style.font_bold, style.font_size)
        c.line(x0, y + 4, x1, y + 4)
        y -= style.line_height * 0.2

        draw_text(
            f"{section.title} SUBTOTAL: {_money(section.subtotal)}",
            font=style.font_bold,
            size=style.font_size,
            x=x0,
            y=y,
        )
        y -= style.line_height

        draw_text(
            f"{section.title} TAX: {_money(section.tax)}",
            font=style.font_bold,
            size=style.font_size,
            x=x0,
            y=y,
        )
        y -= style.line_height

        draw_text(
            f"{section.title} TOTAL: {_money(section.total)}",
            font=style.font_bold,
            size=style.font_size,
            x=x0,
            y=y,
        )
        y -= style.line_height * 1.2

    # ---------- Sections ----------
    for section in report.sections:
        render_section(section)

    # ---------- Grand totals ----------
    ensure_space(6)
    gt = report.grand_totals

    c.setFont(style.font_bold, style.section_size)
    c.line(x0, y + 6, x1, y + 6)
    draw_text("TOTALS", font=style.font_bold, size=style.section_size, x=x0, y=y)
    y -= style.line_height * 1.2

    draw_text(
        f"GRAND SUBTOTAL: {_money(gt.subtotal)}",
        font=style.font_bold,
        size=style.font_size,
        x=x0,
        y=y,
    )
    y -= style.line_height

    draw_text(
        f"GRAND TAX: {_money(gt.tax)}",
        font=style.font_bold,
        size=style.font_size,
        x=x0,
        y=y,
    )
    y -= style.line_height

    draw_text(
        f"VALVE DISCOUNT: {_money(gt.valve_discount)}",
        font=style.font_bold,
        size=style.font_size,
        x=x0,
        y=y,
    )
    y -= style.line_height

    draw_text(
        f"GRAND TOTAL: {_money(gt.total)}",
        font=style.font_bold,
        size=style.font_size,
        x=x0,
        y=y,
    )
    y -= style.line_height

    draw_text(
        f"GRAND TOTAL AFTER DISCOUNT: {_money(gt.total_after_discount)}",
        font=style.font_bold,
        size=style.font_size,
        x=x0,
        y=y,
    )

    c.save()
    return output_path