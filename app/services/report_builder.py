from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from typing import Iterable

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


@dataclass
class ReportTransaction:
    date: str
    description: str
    amount: float
    direction: str
    category: str
    bucket: str


def _format_money(value: float, currency: str) -> str:
    return f"{currency} {value:,.2f}"


def _month_label(month: str) -> str:
    year, month_part = month.split("-")
    month_names = [
        "January",
        "February",
        "March",
        "April",
        "May",
        "June",
        "July",
        "August",
        "September",
        "October",
        "November",
        "December",
    ]
    month_number = int(month_part)
    return f"{month_names[month_number - 1]} {year}"


def build_monthly_spend_pdf(month: str, transactions: Iterable[ReportTransaction], currency: str = "INR") -> bytes:
    spending = [item for item in transactions if item.direction == "out" and item.amount > 0]

    total_spend = sum(item.amount for item in spending)
    avg_spend = total_spend / len(spending) if spending else 0.0

    by_category: dict[str, float] = {}
    for item in spending:
        category = item.category or "Other"
        by_category[category] = by_category.get(category, 0.0) + item.amount

    top_categories = sorted(by_category.items(), key=lambda kv: kv[1], reverse=True)[:6]
    top_transactions = sorted(spending, key=lambda item: item.amount, reverse=True)[:10]

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        # Standard document margins for formal A4 reports.
        leftMargin=22 * mm,
        rightMargin=22 * mm,
        topMargin=24 * mm,
        bottomMargin=22 * mm,
        title=f"Monthly Spend Report {month}",
        author="Finance App",
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "ReportTitle",
        parent=styles["Title"],
        fontSize=20,
        leading=24,
        textColor=colors.HexColor("#1D2A3A"),
        spaceAfter=2,
    )
    subtitle_style = ParagraphStyle(
        "Subtitle",
        parent=styles["Normal"],
        fontSize=9,
        leading=12,
        textColor=colors.HexColor("#5F6B78"),
    )
    meta_style = ParagraphStyle(
        "Meta",
        parent=styles["Normal"],
        fontSize=9,
        leading=12,
        textColor=colors.HexColor("#2E3B4E"),
    )
    section_style = ParagraphStyle(
        "SectionHeader",
        parent=styles["Heading2"],
        fontSize=12,
        leading=16,
        textColor=colors.HexColor("#1D2A3A"),
        spaceBefore=12,
        spaceAfter=6,
    )

    report_month_label = _month_label(month)

    story = [
        Paragraph("Monthly Spend Report", title_style),
        Paragraph(
            f"Period: {report_month_label}",
            subtitle_style,
        ),
        Paragraph("Prepared by: Finance App Analytics", meta_style),
        Paragraph("Document type: Monthly Expenditure Statement", meta_style),
        Spacer(1, 8),
    ]

    rule = Table([[""]], colWidths=[166 * mm], rowHeights=[0.7 * mm])
    rule.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, 0), colors.HexColor("#D3DAE3")),
                ("LINEBELOW", (0, 0), (0, 0), 0, colors.white),
            ]
        )
    )
    story.extend([rule, Spacer(1, 10)])

    stat_table = Table(
        [
            ["Total Spend", "Transactions", "Average Spend", "Top Category"],
            [
                _format_money(total_spend, currency),
                str(len(spending)),
                _format_money(avg_spend, currency),
                top_categories[0][0] if top_categories else "n/a",
            ],
        ],
        colWidths=[40 * mm, 30 * mm, 40 * mm, 56 * mm],
    )
    stat_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E6EBF2")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#1F2D3D")),
                ("BACKGROUND", (0, 1), (-1, 1), colors.HexColor("#FAFBFC")),
                ("TEXTCOLOR", (0, 1), (-1, 1), colors.HexColor("#1D2A3A")),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTNAME", (0, 1), (-1, 1), "Helvetica-Bold"),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CFD6E0")),
                ("LEFTPADDING", (0, 0), (-1, -1), 7),
                ("RIGHTPADDING", (0, 0), (-1, -1), 7),
                ("TOPPADDING", (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
            ]
        )
    )

    story.extend([stat_table, Spacer(1, 10)])

    story.append(Paragraph("Category Breakdown", section_style))
    category_rows = [["Category", "Amount", "Share"]]
    for category, amount in top_categories:
        share = (amount / total_spend * 100) if total_spend > 0 else 0
        category_rows.append([category, _format_money(amount, currency), f"{share:.1f}%"])

    if len(category_rows) == 1:
        category_rows.append(["No spending records", _format_money(0, currency), "0.0%"])

    category_table = Table(category_rows, colWidths=[78 * mm, 46 * mm, 26 * mm])
    category_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2F3A47")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("ALIGN", (1, 1), (-1, -1), "RIGHT"),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#F8FAFC"), colors.white]),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#D2D9E2")),
                ("LEFTPADDING", (0, 0), (-1, -1), 7),
                ("RIGHTPADDING", (0, 0), (-1, -1), 7),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    story.extend([category_table, Spacer(1, 10)])

    story.append(Paragraph("Largest Transactions", section_style))
    transaction_rows = [["Date", "Description", "Bucket", "Amount"]]
    for item in top_transactions:
        transaction_rows.append(
            [
                item.date,
                (item.description[:44] + "...") if len(item.description) > 47 else item.description,
                item.bucket or "Misc",
                _format_money(item.amount, currency),
            ]
        )

    if len(transaction_rows) == 1:
        transaction_rows.append([month + "-01", "No transactions in this month", "-", _format_money(0, currency)])

    transaction_table = Table(transaction_rows, colWidths=[26 * mm, 82 * mm, 30 * mm, 22 * mm])
    transaction_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2F3A47")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("ALIGN", (-1, 1), (-1, -1), "RIGHT"),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8FAFC")]),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#D2D9E2")),
                ("LEFTPADDING", (0, 0), (-1, -1), 7),
                ("RIGHTPADDING", (0, 0), (-1, -1), 7),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    story.extend([transaction_table, Spacer(1, 8)])

    story.append(
        Paragraph(
            "Tip: Focus on the top two categories first. Small weekly cuts there create the fastest monthly savings impact.",
            subtitle_style,
        )
    )

    doc.build(story)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes