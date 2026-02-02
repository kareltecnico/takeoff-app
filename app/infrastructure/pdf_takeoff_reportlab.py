from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from pathlib import Path

from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen.canvas import Canvas

from app.domain.stage import Stage
from app.domain.takeoff import Takeoff
from app.domain.takeoff_line import TakeoffLine


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


def _stage_label(stage: Stage) -> str:
    return {
        Stage.GROUND: "GROUND",
        Stage.TOPOUT: "TOPOUT",
        Stage.FINAL: "FINAL",
    }[stage]


def render_takeoff_pdf(
    takeoff: Takeoff,
    output_path: Path,
    *,
    company_name: str = "LEZA'S PLUMBING",
    created_at: datetime | None = None,
    style: PdfStyle | None = None,
) -> Path:
    """Generate an MVP Take-Off PDF."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    created_at = created_at or datetime.now()
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
    draw_text(company_name, font=style.font_bold, size=style.title_size, x=x0, y=y)
    y -= style.line_height * 1.2

    header = takeoff.header
    draw_text(
        f"PROJECT: {header.project_name}    CONTRACTOR: {header.contractor_name}",
        font=style.font_bold,
        size=style.section_size,
        x=x0,
        y=y,
    )
    y -= style.line_height

    draw_text(
        f"MODEL GROUP: {header.model_group_display}    STORIES: {header.stories}",
        font=style.font,
        size=style.font_size,
        x=x0,
        y=y,
    )
    y -= style.line_height

    draw_text(
        f"CREATED AT: {created_at.strftime('%Y-%m-%d %H:%M')}",
        font=style.font,
        size=style.font_size,
        x=x0,
        y=y,
    )
    y -= style.line_height * 1.2

    # ---------- Column layout ----------
    col_item = 0.12 * (x1 - x0)
    col_desc = 0.36 * (x1 - x0)
    col_price = 0.10 * (x1 - x0)
    col_qty = 0.07 * (x1 - x0)
    col_factor = 0.07 * (x1 - x0)
    col_sub = 0.10 * (x1 - x0)
    col_tax = 0.09 * (x1 - x0)
    col_total = 0.09 * (x1 - x0)

    cols = [
        ("ITEM#", col_item),
        ("DESCRIPTION", col_desc),
        ("PRICE", col_price),
        ("QTY", col_qty),
        ("FACTOR", col_factor),
        ("SUBTOTAL", col_sub),
        ("TAX", col_tax),
        ("TOTAL", col_total),
    ]

    def draw_row(values: list[str], ypos: float, *, bold: bool = False) -> None:
        font = style.font_bold if bold else style.font
        c.setFont(font, style.font_size)

        x = x0
        for (hdr, w), val in zip(cols, values, strict=True):
            if hdr == "DESCRIPTION":
                val = _fit_text(val, w - 6, font, style.font_size)
            c.drawString(x, ypos, val)
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

    def render_stage(stage: Stage, lines: Iterable[TakeoffLine]) -> None:
        nonlocal y
        ensure_space(6)

        draw_text(
            _stage_label(stage),
            font=style.font_bold,
            size=style.section_size,
            x=x0,
            y=y,
        )
        y -= style.line_height

        y = draw_table_header(y)

        for ln in lines:
            ensure_space(2)
            t = ln.totals(tax_rate=takeoff.tax_rate)

            values = [
                ln.item.item_number or "",
                ln.item.description,
                _money(ln.item.unit_price),
                f"{ln.qty}",
                f"{ln.factor}",
                _money(t.subtotal),
                _money(t.tax),
                _money(t.total),
            ]
            draw_row(values, y)
            y -= style.line_height

        ensure_space(3)
        sub, tax, total = takeoff.stage_totals(stage)

        c.setFont(style.font_bold, style.font_size)
        c.line(x0, y + 4, x1, y + 4)
        y -= style.line_height * 0.2

        draw_text(
            f"{_stage_label(stage)} SUBTOTAL: {_money(sub)}",
            font=style.font_bold,
            size=style.font_size,
            x=x0,
            y=y,
        )
        y -= style.line_height

        draw_text(
            f"{_stage_label(stage)} TAX: {_money(tax)}",
            font=style.font_bold,
            size=style.font_size,
            x=x0,
            y=y,
        )
        y -= style.line_height

        draw_text(
            f"{_stage_label(stage)} TOTAL: {_money(total)}",
            font=style.font_bold,
            size=style.font_size,
            x=x0,
            y=y,
        )
        y -= style.line_height * 1.2

    render_stage(Stage.GROUND, takeoff.lines_for_stage(Stage.GROUND))
    render_stage(Stage.TOPOUT, takeoff.lines_for_stage(Stage.TOPOUT))
    render_stage(Stage.FINAL, takeoff.lines_for_stage(Stage.FINAL))

    ensure_space(6)
    gt = takeoff.grand_totals()

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
        f"GRAND TOTAL: {_money(gt.total)}",
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
        f"GRAND TOTAL AFTER DISCOUNT: {_money(gt.total_after_discount)}",
        font=style.font_bold,
        size=style.font_size,
        x=x0,
        y=y,
    )

    c.save()
    return output_path