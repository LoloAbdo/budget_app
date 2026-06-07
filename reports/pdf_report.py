"""
reports/pdf_report.py
Generates PDF financial reports using ReportLab.
"""

from datetime import datetime
from typing import Optional
from pathlib import Path

from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
)
from reportlab.lib.enums import TA_CENTER, TA_RIGHT

from database import DatabaseManager


# ── Colour palette ────────────────────────────────────────────────────────────
NAVY   = colors.HexColor("#1A237E")
TEAL   = colors.HexColor("#00796B")
GREEN  = colors.HexColor("#2E7D32")
RED    = colors.HexColor("#C62828")
LIGHT  = colors.HexColor("#F5F5F5")
WHITE  = colors.white
BLACK  = colors.black


class PDFReportGenerator:
    """Builds and saves a monthly financial PDF report."""

    def __init__(self, db: DatabaseManager) -> None:
        self._db = db

    def generate_monthly_report(
        self,
        user_id: int,
        month: int,
        year: int,
        dest_path: str,
    ) -> str:
        """Generate a monthly summary PDF; return the saved path."""
        user = self._db.get_user(user_id)
        summary = self._db.get_monthly_summary(user_id, month, year)
        spending = self._db.get_spending_by_category(user_id, month, year)
        budgets = self._db.get_budgets(month, year)
        transactions = self._db.get_transactions(
            user_id,
            start_date=f"{year}-{month:02d}-01",
            end_date=f"{year}-{month:02d}-31",
        )

        styles = getSampleStyleSheet()
        title_style = ParagraphStyle("title", parent=styles["Title"],
                                     textColor=NAVY, fontSize=22, spaceAfter=6)
        h2_style = ParagraphStyle("h2", parent=styles["Heading2"],
                                  textColor=TEAL, fontSize=13, spaceBefore=14, spaceAfter=4)
        body_style = styles["BodyText"]
        right_style = ParagraphStyle("right", parent=body_style, alignment=TA_RIGHT)

        story: list = []
        month_name = datetime(year, month, 1).strftime("%B %Y")
        currency = user["currency"] if user else "CAD"

        # ── Title ─────────────────────────────────────────────────────────────
        story.append(Paragraph(f"Financial Report — {month_name}", title_style))
        story.append(Paragraph(f"Prepared for: {user['name'] if user else 'User'}", body_style))
        story.append(Paragraph(
            f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            body_style,
        ))
        story.append(HRFlowable(width="100%", thickness=1, color=NAVY, spaceAfter=10))

        # ── Summary Cards ─────────────────────────────────────────────────────
        story.append(Paragraph("Summary", h2_style))
        summary_data = [
            ["Metric", "Amount"],
            ["Total Income",   f"{currency} {summary['income']:,.2f}"],
            ["Total Expenses", f"{currency} {summary['expenses']:,.2f}"],
            ["Net Savings",    f"{currency} {summary['savings']:,.2f}"],
            ["Savings Rate",   f"{summary['savings_rate']:.1f}%"],
        ]
        t = Table(summary_data, colWidths=[3 * inch, 2 * inch])
        t.setStyle(TableStyle([
            ("BACKGROUND",   (0, 0), (-1, 0), NAVY),
            ("TEXTCOLOR",    (0, 0), (-1, 0), WHITE),
            ("FONTNAME",     (0, 0), (-1, 0), "Helvetica-Bold"),
            ("BACKGROUND",   (0, 1), (-1, -1), LIGHT),
            ("ROWBACKGROUNDS",(0, 1), (-1, -1), [WHITE, LIGHT]),
            ("GRID",         (0, 0), (-1, -1), 0.5, colors.grey),
            ("ALIGN",        (1, 0), (1, -1), "RIGHT"),
            ("FONTNAME",     (0, 1), (-1, -1), "Helvetica"),
            ("TOPPADDING",   (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING",(0, 0), (-1, -1), 5),
        ]))
        story.append(t)
        story.append(Spacer(1, 0.15 * inch))

        # ── Spending by Category ──────────────────────────────────────────────
        if spending:
            story.append(Paragraph("Spending by Category", h2_style))
            cat_data = [["Category", "Amount", "% of Expenses"]]
            total_exp = summary["expenses"] or 1
            for row in spending:
                pct = row["total"] / total_exp * 100
                cat_data.append([
                    row["name"],
                    f"{currency} {row['total']:,.2f}",
                    f"{pct:.1f}%",
                ])
            ct = Table(cat_data, colWidths=[3 * inch, 1.5 * inch, 1.5 * inch])
            ct.setStyle(TableStyle([
                ("BACKGROUND",   (0, 0), (-1, 0), TEAL),
                ("TEXTCOLOR",    (0, 0), (-1, 0), WHITE),
                ("FONTNAME",     (0, 0), (-1, 0), "Helvetica-Bold"),
                ("ROWBACKGROUNDS",(0, 1), (-1, -1), [WHITE, LIGHT]),
                ("GRID",         (0, 0), (-1, -1), 0.5, colors.grey),
                ("ALIGN",        (1, 0), (-1, -1), "RIGHT"),
                ("TOPPADDING",   (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING",(0, 0), (-1, -1), 4),
            ]))
            story.append(ct)
            story.append(Spacer(1, 0.15 * inch))

        # ── Budget Status ─────────────────────────────────────────────────────
        if budgets:
            story.append(Paragraph("Budget Status", h2_style))
            bud_data = [["Category", "Budget", "Actual", "Remaining", "Status"]]
            for b in budgets:
                remaining = b["budget_amount"] - b["actual_spending"]
                status = "✓ OK" if remaining >= 0 else "✗ OVER"
                bud_data.append([
                    b["category_name"],
                    f"{currency} {b['budget_amount']:,.2f}",
                    f"{currency} {b['actual_spending']:,.2f}",
                    f"{currency} {remaining:,.2f}",
                    status,
                ])
            bt = Table(bud_data, colWidths=[2*inch, 1.2*inch, 1.2*inch, 1.2*inch, 0.8*inch])
            bt.setStyle(TableStyle([
                ("BACKGROUND",   (0, 0), (-1, 0), NAVY),
                ("TEXTCOLOR",    (0, 0), (-1, 0), WHITE),
                ("FONTNAME",     (0, 0), (-1, 0), "Helvetica-Bold"),
                ("ROWBACKGROUNDS",(0, 1), (-1, -1), [WHITE, LIGHT]),
                ("GRID",         (0, 0), (-1, -1), 0.5, colors.grey),
                ("ALIGN",        (1, 0), (-1, -1), "RIGHT"),
                ("TOPPADDING",   (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING",(0, 0), (-1, -1), 4),
            ]))
            story.append(bt)
            story.append(Spacer(1, 0.15 * inch))

        # ── Transaction List ──────────────────────────────────────────────────
        story.append(Paragraph("Transactions", h2_style))
        if transactions:
            txn_data = [["Date", "Description", "Category", "Amount"]]
            for txn in transactions[:50]:  # cap at 50 for readability
                txn_data.append([
                    txn["date"],
                    txn["description"][:35],
                    txn.get("category_name", "—"),
                    f"{currency} {txn['amount']:,.2f}",
                ])
            tt = Table(txn_data, colWidths=[1.1*inch, 2.8*inch, 1.5*inch, 1.2*inch])
            tt.setStyle(TableStyle([
                ("BACKGROUND",    (0, 0), (-1, 0), TEAL),
                ("TEXTCOLOR",     (0, 0), (-1, 0), WHITE),
                ("FONTNAME",      (0, 0), (-1, 0), "Helvetica-Bold"),
                ("ROWBACKGROUNDS",(0, 1), (-1, -1), [WHITE, LIGHT]),
                ("GRID",          (0, 0), (-1, -1), 0.3, colors.lightgrey),
                ("ALIGN",         (3, 0), (3, -1), "RIGHT"),
                ("FONTSIZE",      (0, 0), (-1, -1), 8),
                ("TOPPADDING",    (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]))
            story.append(tt)
        else:
            story.append(Paragraph("No transactions recorded for this period.", body_style))

        # ── Footer ────────────────────────────────────────────────────────────
        story.append(Spacer(1, 0.3 * inch))
        story.append(HRFlowable(width="100%", thickness=0.5, color=colors.grey))
        story.append(Paragraph("Budget Manager — Confidential", body_style))

        Path(dest_path).parent.mkdir(parents=True, exist_ok=True)
        doc = SimpleDocTemplate(dest_path, pagesize=letter,
                                leftMargin=0.75*inch, rightMargin=0.75*inch,
                                topMargin=0.75*inch, bottomMargin=0.75*inch)
        doc.build(story)
        return dest_path
