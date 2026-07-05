"""Vector UI icons drawn with QPainter — thin, monochrome line art.

Matches the app's existing glyph vocabulary (× ⇅ ↻ ✎ …, ~1.4px strokes) and
takes an explicit colour so an icon can follow the active palette. State is
shown the conventional way: an OUTLINE when inactive, a solid FILL when active.

Pixmaps are oversampled (rendered at OVERSAMPLE× and tagged with a matching
devicePixelRatio) so Qt always DOWN-scales to the screen — crisp at 1x, 2x or
3x — instead of up-scaling a tiny bitmap (which stair-steps the curves).
"""
from __future__ import annotations

from PyQt6.QtCore import QRectF, Qt
from PyQt6.QtGui import (
    QColor,
    QIcon,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
    QTransform,
)

_OVERSAMPLE = 4

# Upright push-pin silhouette in a 0..100 box, pointing down, symmetric about
# x=50: a round head, a slim collar (no wider than the head, so it doesn't pinch
# the circle), and the needle to a point. Bounding box is ~centred, nudged a hair
# low to optically balance the head-heavy shape.
_PIN_PATH: QPainterPath | None = None


def _pin_path() -> QPainterPath:
    global _PIN_PATH
    if _PIN_PATH is None:
        path = QPainterPath()
        path.addEllipse(QRectF(35, 16, 30, 30))           # round head
        path.addRoundedRect(QRectF(34, 41, 32, 6), 3, 3)  # collar (== head width)
        needle = QPainterPath()
        needle.moveTo(46, 46)
        needle.lineTo(54, 46)
        needle.lineTo(50, 87)                             # sharp tip
        needle.closeSubpath()
        _PIN_PATH = path.united(needle).simplified()
    return _PIN_PATH


def pin_pixmap(size_px: int, color: str, *, pinned: bool) -> QPixmap:
    """A flat push-pin: thin outline when unpinned, solid fill when pinned."""
    size_px = max(8, int(size_px))
    pm = QPixmap(size_px * _OVERSAMPLE, size_px * _OVERSAMPLE)
    pm.setDevicePixelRatio(float(_OVERSAMPLE))
    pm.fill(Qt.GlobalColor.transparent)

    painter = QPainter(pm)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

    # Map the 0..100 silhouette into the padded icon box (device-independent px).
    pad = size_px * 0.12
    scale = (size_px - 2 * pad) / 100.0
    # The head is heavy and sits high, so the geometric centre reads as "too high".
    # Nudge the whole glyph down a hair to optically centre it in the button.
    optical_dy = size_px * 0.06
    transform = QTransform()
    transform.translate(pad, pad + optical_dy)
    transform.scale(scale, scale)
    path = transform.map(_pin_path())

    qcolor = to_qcolor(color)
    if pinned:
        painter.fillPath(path, qcolor)
    else:
        pen = QPen(qcolor, max(1.0, size_px * 0.08))
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.strokePath(path, pen)
    painter.end()
    return pm


def pin_icon(size_px: int, color: str, *, pinned: bool) -> QIcon:
    return QIcon(pin_pixmap(size_px, color, pinned=pinned))


# ── Antialiased rounded surfaces (replace QSS border-radius, which Qt's
# stylesheet engine rasterises with poor corner antialiasing) ──

def rounded_rect_path(rect, radius: float, *, top_only: bool = False,
                      bottom_only: bool = False) -> QPainterPath:
    """A rounded-rect path. top_only/bottom_only round just that PAIR of
    corners (for a header strip / footer area sitting inside a rounded
    container)."""
    path = QPainterPath()
    r = max(0.0, float(radius))
    if (not top_only and not bottom_only) or r == 0.0:
        path.addRoundedRect(rect, r, r)
        return path
    x, y, w, h = rect.x(), rect.y(), rect.width(), rect.height()
    if top_only:
        path.moveTo(x, y + h)
        path.lineTo(x, y + r)
        path.arcTo(x, y, 2 * r, 2 * r, 180.0, -90.0)
        path.lineTo(x + w - r, y)
        path.arcTo(x + w - 2 * r, y, 2 * r, 2 * r, 90.0, -90.0)
        path.lineTo(x + w, y + h)
        path.closeSubpath()
        return path
    path.moveTo(x, y)
    path.lineTo(x, y + h - r)
    path.arcTo(x, y + h - 2 * r, 2 * r, 2 * r, 180.0, 90.0)
    path.lineTo(x + w - r, y + h)
    path.arcTo(x + w - 2 * r, y + h - 2 * r, 2 * r, 2 * r, 270.0, 90.0)
    path.lineTo(x + w, y)
    path.closeSubpath()
    return path


def to_qcolor(value) -> QColor:
    """Parse a palette colour into a QColor. Palette values use CSS syntax —
    'rgba(r, g, b, a)' with a fractional alpha — which QSS understands but
    QColor() does NOT (it silently yields an INVALID colour that paints
    black). Every QPainter path must convert through here."""
    if isinstance(value, QColor):
        return value
    s = str(value).strip()
    if s.startswith(('rgba(', 'rgb(')):
        parts = [p.strip() for p in s[s.index('(') + 1:s.rindex(')')].split(',')]
        r, g, b = (int(float(parts[i])) for i in range(3))
        alpha = 255
        if len(parts) == 4:
            a = float(parts[3])
            alpha = round(a * 255) if a <= 1.0 else round(a)
        return QColor(r, g, b, alpha)
    return QColor(s)


def paint_rounded_surface(painter, rect, radius: float, *, bg=None, border=None,
                          border_w: float = 1.0, dashed: bool = False) -> None:
    """Paint an antialiased rounded rect (fill and/or 1px border) — the shared
    replacement for QSS border-radius on any surface. Call from a widget's
    paintEvent; the widget should have WA_TranslucentBackground so the corners
    show the parent. Colours are palette strings/QColor."""
    from PyQt6.QtCore import QRectF
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    body = rounded_rect_path(QRectF(rect).adjusted(0.5, 0.5, -0.5, -0.5), radius)
    if bg is not None:
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(to_qcolor(bg))
        painter.drawPath(body)
    if border is not None:
        painter.setBrush(Qt.BrushStyle.NoBrush)
        pen = QPen(to_qcolor(border), border_w)
        if dashed:
            pen.setStyle(Qt.PenStyle.DashLine)
        painter.setPen(pen)
        painter.drawPath(body)
