"""Vector UI icons drawn with QPainter — flat, monochrome, theme-recolorable.

Replaces emoji glyphs (which render as OS-specific colour bitmaps) with clean
line art that matches the app's design language and takes an explicit colour so
it can follow the active palette.
"""
from __future__ import annotations

from PyQt6.QtCore import QRectF, Qt
from PyQt6.QtGui import (
    QColor,
    QGuiApplication,
    QIcon,
    QPainter,
    QPainterPath,
    QPixmap,
    QTransform,
)

# Push-pin silhouette in a 0..100 box, pointing straight down, symmetric about
# x=50: a pressable cap, a wider collar, and the needle to a point.
_PIN_PATH: QPainterPath | None = None


def _pin_path() -> QPainterPath:
    global _PIN_PATH
    if _PIN_PATH is None:
        path = QPainterPath()
        path.addRoundedRect(QRectF(33, 6, 34, 26), 8, 8)   # cap you press
        path.addRoundedRect(QRectF(22, 30, 56, 13), 5, 5)  # metal collar
        needle = QPainterPath()
        needle.moveTo(44, 41)
        needle.lineTo(56, 41)
        needle.lineTo(50, 95)                              # sharp tip
        needle.closeSubpath()
        _PIN_PATH = path.united(needle)
    return _PIN_PATH


def _dpr() -> float:
    try:
        screen = QGuiApplication.primaryScreen()
        return screen.devicePixelRatio() if screen is not None else 1.0
    except Exception:
        return 1.0


def pin_pixmap(size_px: int, color: str, *, pinned: bool) -> QPixmap:
    """A flat push-pin: upright + solid colour when pinned, tilted when not."""
    size_px = max(8, int(size_px))
    dpr = _dpr()
    pm = QPixmap(int(round(size_px * dpr)), int(round(size_px * dpr)))
    pm.setDevicePixelRatio(dpr)
    pm.fill(Qt.GlobalColor.transparent)

    painter = QPainter(pm)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

    pad = size_px * 0.16
    scale = (size_px - 2 * pad) / 100.0
    center = size_px / 2.0
    transform = QTransform()
    transform.translate(center, center)
    if not pinned:
        transform.rotate(-32)  # "not stuck in" — leans off-vertical
    transform.translate(-center, -center)
    transform.translate(pad, pad)
    transform.scale(scale, scale)
    painter.setTransform(transform)
    painter.fillPath(_pin_path(), QColor(color))
    painter.end()
    return pm


def pin_icon(size_px: int, color: str, *, pinned: bool) -> QIcon:
    return QIcon(pin_pixmap(size_px, color, pinned=pinned))
