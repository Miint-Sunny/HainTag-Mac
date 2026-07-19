"""Force every QComboBox onto a predictable drop-down popup (macOS fix).

With the app stylesheet's 9-patch border-image on combos, macOS' native
overlay popup geometry (menu-style, width-of-content, aligned over the
control) miscalculates its height and opens clipped — and the QSS
`combobox-popup: 0` hint is not honoured on the real interaction path.

The reliable switch is the widget's BASE style: give each combo a Fusion
base, whose popup is the standard below-the-control drop-down list. The
application stylesheet still wraps a per-widget style, so the themed 9-patch
rendering is unchanged. An application-level Polish hook covers every combo,
including ones created later (prompt entries, dialogs).
"""
from __future__ import annotations

from PyQt6.QtCore import QEvent, QObject
from PyQt6.QtWidgets import QApplication, QComboBox, QStyleFactory

_fusion = None


def _fusion_style():
    global _fusion
    if _fusion is None:
        _fusion = QStyleFactory.create("Fusion")
    return _fusion


class _ComboPopupFixer(QObject):
    def eventFilter(self, obj: QObject, event: QEvent) -> bool:
        if event.type() == QEvent.Type.Polish and isinstance(obj, QComboBox):
            style = _fusion_style()
            if style is not None and obj.style() is not style:
                obj.setStyle(style)
        return False


_fixer = _ComboPopupFixer()


def install(app: QApplication) -> None:
    """Install the fixer on the application (idempotent)."""
    app.removeEventFilter(_fixer)
    app.installEventFilter(_fixer)
