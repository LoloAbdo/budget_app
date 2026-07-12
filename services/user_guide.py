"""
services/user_guide.py
Render the bundled USER_GUIDE.md to a PDF on demand.

No extra dependencies: Qt's own QTextDocument parses the Markdown and QPdfWriter
paints it to an A4 PDF. The guide file lives next to the source in a normal run,
or in the PyInstaller unpack dir (``sys._MEIPASS``) for the frozen build — the
build scripts and release.yml bundle it via ``--add-data`` (mirroring CHANGELOG).
"""

from pathlib import Path
from typing import Optional
import sys


def _guide_path(lang: Optional[str] = None) -> Optional[Path]:
    """Locate the guide file. Prefers ``USER_GUIDE.<lang>.md`` when it exists,
    else the bilingual ``USER_GUIDE.md``. Returns None if nothing is found."""
    base = Path(getattr(sys, "_MEIPASS", "")) or Path(__file__).resolve().parent.parent
    candidates = []
    if lang and lang != "en":
        candidates.append(f"USER_GUIDE.{lang}.md")
    candidates.append("USER_GUIDE.md")
    for name in candidates:
        p = base / name
        if p.is_file():
            return p
    return None


def guide_markdown(lang: Optional[str] = None) -> str:
    """The guide's Markdown text, or "" if the file can't be found/read."""
    p = _guide_path(lang)
    if p is None:
        return ""
    try:
        return p.read_text(encoding="utf-8")
    except OSError:
        return ""


def write_pdf(dest_path: str, lang: Optional[str] = None) -> bool:
    """Render the guide to *dest_path* as a PDF. Returns False if the guide is
    missing. Requires a running QGuiApplication (true inside the app)."""
    from PyQt6.QtGui import QTextDocument, QPdfWriter, QPageSize, QFont
    from PyQt6.QtCore import QMarginsF
    from views import fonts

    md = guide_markdown(lang)
    if not md:
        return False

    doc = QTextDocument()
    # Use the bundled Inter (falls back to Segoe UI) so the PDF renders the same
    # on every machine; QTextDocument ignores the app's QSS font.
    doc.setDefaultFont(QFont(fonts.family(), 11))
    doc.setMarkdown(md)

    writer = QPdfWriter(dest_path)
    writer.setPageSize(QPageSize(QPageSize.PageSizeId.A4))
    writer.setPageMargins(QMarginsF(18, 18, 18, 18))  # millimetres
    writer.setTitle("Budget Manager — User Guide")

    doc.print(writer)
    return True
