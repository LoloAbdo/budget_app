"""
tests/test_pdf_report.py
Tests for PDFReportGenerator — exercises the full monthly-report path,
including the budget-status section (a regression guard: the budget query
was once called with the wrong arguments and crashed every export).
"""

from datetime import datetime
from pathlib import Path


def _now():
    n = datetime.now()
    return n.month, n.year


def _expense_category(db) -> int:
    return next(c["id"] for c in db.get_categories("Expense"))


def test_generate_monthly_report_creates_pdf(db, user_id, account_id, tmp_path):
    from reports.pdf_report import PDFReportGenerator

    month, year = _now()
    today = datetime.now().strftime("%Y-%m-%d")
    cat = _expense_category(db)
    db.create_transaction(account_id, cat, today, "Groceries", -42.50)

    dest = tmp_path / "report.pdf"
    out = PDFReportGenerator(db).generate_monthly_report(user_id, month, year, str(dest))

    assert Path(out).exists()
    assert Path(out).stat().st_size > 0
    # A PDF always starts with the %PDF- magic bytes.
    assert Path(out).read_bytes().startswith(b"%PDF-")


def test_generate_monthly_report_includes_budget_section(db, user_id, account_id, tmp_path):
    """With a budget set, the report must build without raising (regression)."""
    from reports.pdf_report import PDFReportGenerator

    month, year = _now()
    today = datetime.now().strftime("%Y-%m-%d")
    cat = _expense_category(db)
    db.upsert_budget(user_id, cat, month, year, 200.0)
    db.create_transaction(account_id, cat, today, "Groceries", -120.0)

    dest = tmp_path / "report_budget.pdf"
    out = PDFReportGenerator(db).generate_monthly_report(user_id, month, year, str(dest))

    assert Path(out).exists()
    assert Path(out).stat().st_size > 0


def test_generate_monthly_report_empty_period(db, user_id, account_id, tmp_path):
    """No transactions for the period should still produce a valid PDF."""
    from reports.pdf_report import PDFReportGenerator

    dest = tmp_path / "report_empty.pdf"
    out = PDFReportGenerator(db).generate_monthly_report(user_id, 1, 2000, str(dest))

    assert Path(out).exists()
    assert Path(out).read_bytes().startswith(b"%PDF-")
