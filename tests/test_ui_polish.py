"""
tests/test_ui_polish.py
Chart tick formatting, summary-card deltas, EmptyState widget, and toasts.
"""

import os

import pytest


# ── Compact money formatter (pure) ────────────────────────────────────────────

def test_compact_money_formatting():
    from views.chartutil import compact_money
    assert compact_money(0) == "0"
    assert compact_money(950) == "950"
    assert compact_money(1000) == "1k"
    assert compact_money(1500) == "1.5k"
    assert compact_money(30000) == "30k"
    assert compact_money(2_500_000) == "2.5M"
    assert compact_money(-1500) == "-1.5k"


def test_chart_font_matches_ui_font():
    import matplotlib
    import views.chartutil  # noqa: F401 — importing configures rcParams
    families = matplotlib.rcParams["font.sans-serif"]
    assert families[0] == "Inter"          # bundled UI font first
    assert "Segoe UI" in families          # sensible fallback chain


# ── Delta helpers (pure) ──────────────────────────────────────────────────────

def test_delta_text_up_and_down():
    from views.widgets import delta_text, GREEN, RED
    assert delta_text(112, 100) == ("▲ 12%", GREEN)
    assert delta_text(88, 100) == ("▼ 12%", RED)


def test_delta_text_inverted_for_expenses():
    from views.widgets import delta_text, GREEN, RED
    assert delta_text(112, 100, invert=True) == ("▲ 12%", RED)
    assert delta_text(88, 100, invert=True) == ("▼ 12%", GREEN)


def test_delta_text_no_comparison_cases():
    from views.widgets import delta_text
    assert delta_text(50, None) is None      # no previous data
    assert delta_text(50, 0.0) is None       # divide-by-zero guard
    assert delta_text(100.0, 100.0) is None  # flat


def test_delta_points_for_rates():
    from views.widgets import delta_points, GREEN, RED
    assert delta_points(23.2, 20.0) == ("▲ 3.2 pts", GREEN)
    assert delta_points(18.0, 20.0) == ("▼ 2.0 pts", RED)
    assert delta_points(20.0, None) is None
    assert delta_points(20.02, 20.0) is None  # flat


# ── Qt widgets (offscreen) ────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def qapp():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PyQt6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
    yield app


def test_empty_state_text_and_action(qapp):
    from views.widgets import EmptyState
    clicks = []
    es = EmptyState("Nothing here", icon="🏦",
                    action_text="+ Add", on_action=lambda: clicks.append(1))
    assert es._text_lbl.text() == "Nothing here"
    es.setText("Still nothing")
    assert es._text_lbl.text() == "Still nothing"
    es._action_btn.click()
    assert clicks == [1]
    es.set_action_visible(False)
    assert not es._action_btn.isVisibleTo(es)


def test_empty_state_without_action(qapp):
    from views.widgets import EmptyState
    es = EmptyState("Empty")
    assert es._action_btn is None
    es.set_action_visible(True)   # must be a safe no-op


def test_summary_card_with_delta(qapp):
    from views.widgets import SummaryCard, delta_text
    card = SummaryCard("Income", "CAD 3,000.00",
                       delta=delta_text(3000, 2500), delta_label="vs last month")
    labels = [l.text() for l in card.findChildren(type(card._lbl_value))]
    assert any("▲ 20%" in t for t in labels)
    assert any("vs last month" in t for t in labels)


def test_toast_shows_on_window(qapp):
    from PyQt6.QtWidgets import QMainWindow
    from views.toast import show_toast
    win = QMainWindow()
    win.resize(800, 600)
    win.show()
    show_toast(win, "Transfer created")
    toast1 = win._active_toast
    assert toast1 is not None and toast1.isVisible()
    # A second toast replaces the first rather than stacking.
    show_toast(win, "Rates updated", kind="info")
    assert win._active_toast is not toast1
    win.close()
