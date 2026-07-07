"""
tests/test_activity_view.py
The Activity Log shows a user-friendly summary of each change instead of the
raw JSON snapshot stored in audit_log. These cover that humanizing layer.
"""

import json

from views.activity_view import _humanize_details, _friendly_time, ENTITY_LABELS


class TestHumanizeDetails:
    def test_hides_internal_ids_and_json(self):
        raw = json.dumps({
            "account_id": 3, "category_id": 5, "date": "2026-07-07",
            "description": "Groceries", "amount": -52.4, "recurring_id": None,
        })
        out = _humanize_details(raw)
        # Readable content is present…
        assert "Groceries" in out
        assert "Date: 2026-07-07" in out
        # …but the developer plumbing is gone.
        assert "account_id" not in out
        assert "category_id" not in out
        assert "{" not in out and "}" not in out

    def test_money_is_formatted_to_two_decimals(self):
        out = _humanize_details(json.dumps({"name": "Rent", "amount": -1500}))
        assert "Amount: -1,500.00" in out

    def test_none_values_are_skipped(self):
        out = _humanize_details(json.dumps({"name": "Rent", "end_date": None}))
        assert out == "Rent"

    def test_non_json_passthrough(self):
        assert _humanize_details("plain text") == "plain text"

    def test_empty(self):
        assert _humanize_details(None) == ""
        assert _humanize_details("") == ""


class TestFriendlyTime:
    def test_formats_and_keeps_raw_sort_key(self):
        display, sort_key = _friendly_time("2026-07-07T15:59:49")
        assert display == "Jul 7, 2026, 15:59"
        assert sort_key == "2026-07-07T15:59:49"  # sorts on the real timestamp

    def test_two_digit_day_keeps_hour_leading_zero(self):
        # Regression: the day loses its leading zero but the time must not.
        display, _ = _friendly_time("2026-07-15T05:30:00")
        assert display == "Jul 15, 2026, 05:30"

    def test_bad_input_is_returned_verbatim(self):
        assert _friendly_time("not-a-date") == ("not-a-date", "not-a-date")
        assert _friendly_time(None) == ("", "")


def test_entity_labels_cover_every_logged_entity():
    # Guard: every entity written to audit_log has a friendly name so the Item
    # column never falls back to a raw table name.
    logged = {
        "user", "account", "category", "category_rule", "transaction",
        "transfer", "budget", "goal", "recurring", "watchlist",
    }
    assert logged <= set(ENTITY_LABELS)
