import io
from decimal import Decimal
from typing import List, Dict

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer


def _register_fonts() -> str:
    try:
        pdfmetrics.getFont("DejaVu")
        return "DejaVu"
    except KeyError:
        pass

    import os
    candidates = [
        ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "DejaVu"),
        ("/usr/share/fonts/dejavu/DejaVuSans.ttf", "DejaVu"),
        ("C:/Windows/Fonts/arial.ttf", "Arial"),
        ("C:/Windows/Fonts/times.ttf", "Times"),
    ]
    for path, name in candidates:
        if os.path.exists(path):
            pdfmetrics.registerFont(TTFont(name, path))
            return name

    return "Helvetica"


def generate_receipt_pdf(
    resident_name: str,
    personal_account: str,
    address: str,
    period: str,
    charges: List[Dict],
    total_charged: Decimal,
    total_paid: Decimal,
    debt: Decimal,
) -> io.BytesIO:
    """Generate a payment receipt (kvitantsiya) as PDF."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=15*mm, bottomMargin=15*mm)

    font_name = _register_fonts()
    styles = getSampleStyleSheet()

    # Override font
    for style in styles.byName.values():
        style.fontName = font_name

    elements = []

    # Header
    elements.append(Paragraph(
        f"<b>КВИТАНЦИЯ НА ОПЛАТУ ЖИЛИЩНО-КОММУНАЛЬНЫХ УСЛУГ</b>",
        styles["Title"],
    ))
    elements.append(Spacer(1, 5*mm))

    # Resident info
    info_data = [
        ["Период:", period],
        ["Плательщик:", resident_name],
        ["Лицевой счёт:", personal_account],
        ["Адрес:", address],
    ]
    info_table = Table(info_data, colWidths=[35*mm, 140*mm])
    info_table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), font_name),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("FONTNAME", (0, 0), (0, -1), font_name),
        ("TEXTCOLOR", (0, 0), (0, -1), colors.grey),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ]))
    elements.append(info_table)
    elements.append(Spacer(1, 8*mm))

    # Charges table
    table_data = [["Услуга", "Ед. изм.", "Потребление", "Тариф", "Сумма"]]
    for c in charges:
        table_data.append([
            c.get("service_name", ""),
            c.get("unit", ""),
            str(c.get("consumption", "")),
            str(c.get("tariff_price", "")),
            f'{c.get("amount", 0):,.2f}'.replace(",", " "),
        ])

    charges_table = Table(table_data, colWidths=[55*mm, 25*mm, 30*mm, 30*mm, 35*mm])
    charges_table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), font_name),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#4472C4")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTSIZE", (0, 0), (-1, 0), 10),
        ("ALIGN", (2, 0), (-1, -1), "RIGHT"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
    ]))
    elements.append(charges_table)
    elements.append(Spacer(1, 5*mm))

    # Totals
    fmt = lambda x: f"{x:,.2f}".replace(",", " ")
    totals_data = [
        ["Итого начислено:", f"{fmt(total_charged)} руб."],
        ["Оплачено:", f"{fmt(total_paid)} руб."],
        ["К оплате:", f"{fmt(debt)} руб."],
    ]
    totals_table = Table(totals_data, colWidths=[140*mm, 35*mm])
    totals_table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), font_name),
        ("FONTSIZE", (0, 0), (-1, -1), 11),
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ("FONTSIZE", (0, 2), (-1, 2), 13),
        ("TEXTCOLOR", (1, 2), (1, 2), colors.HexColor("#C00000")),
        ("LINEABOVE", (0, 2), (-1, 2), 1, colors.black),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    elements.append(totals_table)
    elements.append(Spacer(1, 10*mm))

    # Footer
    elements.append(Paragraph(
        "Оплатите до 15 числа следующего месяца.",
        styles["Normal"],
    ))

    doc.build(elements)
    buffer.seek(0)
    return buffer
