"""
tests/test_import_export.py
Covers ImportExportService export, especially that the filter kwargs forwarded
from the Transactions toolbar narrow the export the same way the on-screen list
is narrowed.
"""

import csv

import pytest

from services.import_export_service import ImportExportService


@pytest.fixture
def ie(db):
    return ImportExportService(db)


@pytest.fixture
def sample_txns(db, user_id, account_id):
    """Two transactions in different months and categories."""
    cats = {c["name"]: c["id"] for c in db.get_categories()}
    cid = next(iter(cats.values()))
    other_cid = list(cats.values())[1]
    db.create_transaction(account_id, cid, "2026-06-01", "Coffee", -5.0, "")
    db.create_transaction(account_id, other_cid, "2026-01-01", "OldThing", -9.0, "")
    return {"cid": cid, "other_cid": other_cid}


def _read_csv(path):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def test_export_csv_all(ie, user_id, sample_txns, tmp_path):
    out = tmp_path / "all.csv"
    n = ie.export_csv(user_id, str(out))
    rows = _read_csv(out)
    assert n == 2
    assert {r["description"] for r in rows} == {"Coffee", "OldThing"}


def test_export_csv_date_filter(ie, user_id, sample_txns, tmp_path):
    out = tmp_path / "june.csv"
    n = ie.export_csv(user_id, str(out), start_date="2026-05-01", end_date="2026-06-30")
    rows = _read_csv(out)
    assert n == 1
    assert rows[0]["description"] == "Coffee"


def test_export_csv_category_filter(ie, db, user_id, sample_txns, tmp_path):
    out = tmp_path / "cat.csv"
    n = ie.export_csv(user_id, str(out), category_id=sample_txns["other_cid"])
    rows = _read_csv(out)
    assert n == 1
    assert rows[0]["description"] == "OldThing"


def test_export_excel_row_count(ie, user_id, sample_txns, tmp_path):
    out = tmp_path / "all.xlsx"
    n = ie.export_excel(user_id, str(out))
    assert n == 2
    assert out.exists()
