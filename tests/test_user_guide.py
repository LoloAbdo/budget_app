"""tests/test_user_guide.py — user-guide PDF export."""
import os
import tempfile
import pytest

from services import user_guide


@pytest.fixture(scope="module")
def qapp():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PyQt6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


def test_guide_markdown_found_and_nonempty():
    md = user_guide.guide_markdown()
    assert md.strip()
    assert "Budget Manager" in md


def test_guide_markdown_missing_lang_falls_back_to_english():
    # No USER_GUIDE.zz.md exists → falls back to the bundled English file.
    assert user_guide.guide_markdown("zz") == user_guide.guide_markdown()


def test_write_pdf_creates_valid_pdf(qapp):
    fd, path = tempfile.mkstemp(suffix=".pdf")
    os.close(fd)
    try:
        assert user_guide.write_pdf(path) is True
        with open(path, "rb") as fh:
            head = fh.read(5)
        assert head == b"%PDF-"
        assert os.path.getsize(path) > 1000   # real content, not an empty stub
    finally:
        try:
            os.unlink(path)
        except OSError:
            pass
