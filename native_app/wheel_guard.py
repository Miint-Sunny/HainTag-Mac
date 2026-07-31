"""Application-wide guard against accidental mouse-wheel value changes.

Spinboxes, sliders and combo boxes adjust their value on a mouse wheel, so
scrolling a settings/prompt list with the pointer over one of them silently
bumps the value — the complaint in upstream issue #3. When wheel-adjust is
disabled (the default), this filter swallows the wheel before the control
sees it and scrolls the nearest scroll area DIRECTLY via its scrollbar —
no synthetic event forwarding (re-dispatching wheel events breaks macOS
trackpad phase/momentum tracking). Enable the settings toggle to restore
native wheel-adjust behaviour.

A single filter on the QApplication covers every current and future control
without touching creation sites.
"""
from __future__ import annotations

from PyQt6.QtCore import QEvent, QObject
from PyQt6.QtGui import QWheelEvent
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QAbstractScrollArea,
    QAbstractSlider,
    QAbstractSpinBox,
    QApplication,
    QComboBox,
    QWidget,
)

_enabled = False
_GUARDED = (QAbstractSpinBox, QComboBox, QAbstractSlider)


def set_wheel_adjust_enabled(enabled: bool) -> None:
    """True = native wheel-adjust; False = wheel scrolls the list instead."""
    global _enabled
    _enabled = bool(enabled)


def wheel_adjust_enabled() -> bool:
    return _enabled


def _scroll_ancestor(widget: QWidget) -> QAbstractScrollArea | None:
    parent = widget.parentWidget()
    while parent is not None:
        if isinstance(parent, QAbstractScrollArea):
            return parent
        parent = parent.parentWidget()
    return None


def _scroll_directly(area: QAbstractScrollArea, event: QWheelEvent) -> None:
    """Apply the wheel delta straight to the area's scrollbars."""
    for bar, pixels, angle in (
        (area.verticalScrollBar(), event.pixelDelta().y(), event.angleDelta().y()),
        (area.horizontalScrollBar(), event.pixelDelta().x(), event.angleDelta().x()),
    ):
        if bar is None:
            continue
        if pixels:  # trackpads: pixel-precise deltas
            bar.setValue(bar.value() - pixels)
        elif angle:  # wheel notches: 120 units == 3 lines
            bar.setValue(bar.value() - round(angle / 120.0 * bar.singleStep() * 3))


class _WheelGuard(QObject):
    def eventFilter(self, obj: QObject, event: QEvent) -> bool:
        if _enabled or event.type() != QEvent.Type.Wheel:
            return False
        widget = obj
        depth = 0
        # Walk up a couple of levels: the wheel may land on a spinbox's inner
        # line edit rather than the spinbox itself.
        while isinstance(widget, QWidget) and depth < 3:
            if isinstance(widget, QAbstractItemView):
                return False  # a real list/table (e.g. an open combo popup) scrolls itself
            if isinstance(widget, _GUARDED):
                area = _scroll_ancestor(widget)
                if area is not None:
                    _scroll_directly(area, event)
                return True  # swallow it so the control's value doesn't change
            widget = widget.parentWidget()
            depth += 1
        return False


_guard = _WheelGuard()


def install(app: QApplication) -> None:
    """Install the guard on the application (idempotent)."""
    app.removeEventFilter(_guard)
    app.installEventFilter(_guard)
