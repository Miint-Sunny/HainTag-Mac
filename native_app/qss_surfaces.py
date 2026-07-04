"""Pre-rendered antialiased 9-patch surfaces for Qt style sheets.

Qt's stylesheet engine rasterises border-radius corners WITHOUT antialiasing,
so every QSS-rounded control shows stair-stepped corners. Controls (buttons,
inputs, menus) have hundreds of creation sites and rely on QSS state selectors,
which makes per-widget custom painting impractical. Instead, each rounded
surface (fill + border + radius) is pre-rendered here into a tiny PNG pair
(1x and @2x — Qt picks the @2x automatically on retina) and applied by QSS as
a 9-patch via border-image: the corners come from the antialiased pre-render
while the middle stretches, and the whole :hover/:pressed/:focus machinery
keeps working by swapping images per state.

The generated declarations set border-width == slice (radius + 1), which eats
into the content box — callers compensate padding/min-sizes in their rules
(see theme.control_surfaces_qss()).
"""
from __future__ import annotations

import hashlib
import tempfile
from pathlib import Path

from PyQt6.QtCore import QRectF, Qt
from PyQt6.QtGui import QImage, QPainter, QPainterPath, QPen

from .icons import to_qcolor

_CACHE_DIR = Path(tempfile.gettempdir()) / 'haintag-qss-surfaces'
# Bump when the render logic changes so stale cached PNGs are never reused.
_RENDER_VERSION = 2


def _render(path: Path, radius: int, fill: str, border: str | None,
            border_w: float, scale: int) -> None:
    size = (2 * radius + 3) * scale
    img = QImage(size, size, QImage.Format.Format_ARGB32_Premultiplied)
    img.fill(Qt.GlobalColor.transparent)
    painter = QPainter(img)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    inset = (border_w * scale) / 2.0 if border else 0.0
    rect = QRectF(inset, inset, size - 2 * inset, size - 2 * inset)
    r = max(1.0, radius * scale - inset)
    shape = QPainterPath()
    shape.addRoundedRect(rect, r, r)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(to_qcolor(fill))
    painter.drawPath(shape)
    if border:
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(QPen(to_qcolor(border), border_w * scale))
        painter.drawPath(shape)
    painter.end()
    img.save(str(path))


def surface_decl(radius: int, fill: str, border: str | None = None,
                 border_w: float = 1.0) -> str:
    """QSS declarations rendering an AA rounded surface as a 9-patch.

    Returns 'border-width: ...; border-image: ...; background: transparent;'
    ready to drop into a rule. radius is in (UI-scale-adjusted) logical px.
    """
    _CACHE_DIR.mkdir(parents=True, exist_ok=True)
    key = hashlib.sha1(
        f"v{_RENDER_VERSION}|{radius}|{fill}|{border}|{border_w}".encode()
    ).hexdigest()[:12]
    base = _CACHE_DIR / f"s{key}.png"
    hi = _CACHE_DIR / f"s{key}@2x.png"
    if not base.exists():
        _render(base, radius, fill, border, border_w, 1)
    if not hi.exists():
        _render(hi, radius, fill, border, border_w, 2)
    s = radius + 1
    return (
        f'border-width: {s}px; '
        f'border-image: url("{base.as_posix()}") {s} {s} {s} {s} stretch stretch; '
        f'background: transparent;'
    )
