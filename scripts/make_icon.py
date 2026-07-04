"""
scripts/make_icon.py
Generate assets/icon.ico — the Budget Manager app icon.

A rounded square filled with the app's violet->indigo accent gradient and a
white dollar glyph, rendered at 256px and downscaled into a multi-size .ico.
Rerun after tweaking colors; the .ico is committed so builds don't need PIL.

Usage:  python scripts/make_icon.py
"""

import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "assets" / "icon.ico"

SIZE = 256
RADIUS = 58                       # corner radius at 256px
GRAD_A = (139, 92, 246)           # #8B5CF6 violet (theme accent_a)
GRAD_B = (99, 102, 241)           # #6366F1 indigo (theme accent_b)
ICO_SIZES = [(s, s) for s in (16, 24, 32, 48, 64, 128, 256)]


def _find_font() -> ImageFont.FreeTypeFont:
    """Bold Segoe UI if available (Windows), else any bundled bold sans."""
    candidates = [
        r"C:\Windows\Fonts\segoeuib.ttf",   # Segoe UI Bold
        r"C:\Windows\Fonts\arialbd.ttf",    # Arial Bold
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    ]
    for path in candidates:
        if Path(path).exists():
            return ImageFont.truetype(path, 168)
    print("No bold font found; using PIL default (glyph will look worse).")
    return ImageFont.load_default()


def main() -> int:
    img = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))

    # Diagonal gradient: interpolate per-pixel on (x + y).
    grad = Image.new("RGBA", (SIZE, SIZE))
    px = grad.load()
    span = 2 * (SIZE - 1)
    for y in range(SIZE):
        for x in range(SIZE):
            t = (x + y) / span
            px[x, y] = tuple(
                round(a + (b - a) * t) for a, b in zip(GRAD_A, GRAD_B)
            ) + (255,)

    # Clip the gradient to a rounded square.
    mask = Image.new("L", (SIZE, SIZE), 0)
    ImageDraw.Draw(mask).rounded_rectangle(
        [0, 0, SIZE - 1, SIZE - 1], radius=RADIUS, fill=255
    )
    img.paste(grad, (0, 0), mask)

    # White "$" glyph, optically centered.
    draw = ImageDraw.Draw(img)
    font = _find_font()
    left, top, right, bottom = draw.textbbox((0, 0), "$", font=font)
    gw, gh = right - left, bottom - top
    pos = ((SIZE - gw) / 2 - left, (SIZE - gh) / 2 - top)
    # Soft shadow for depth, then the glyph.
    draw.text((pos[0] + 3, pos[1] + 4), "$", font=font, fill=(0, 0, 0, 70))
    draw.text(pos, "$", font=font, fill=(255, 255, 255, 255))

    OUT.parent.mkdir(parents=True, exist_ok=True)
    img.save(OUT, format="ICO", sizes=ICO_SIZES)
    print(f"Wrote {OUT} ({OUT.stat().st_size:,} bytes, sizes: "
          + ", ".join(f"{w}px" for w, _ in ICO_SIZES) + ")")
    return 0


if __name__ == "__main__":
    sys.exit(main())
