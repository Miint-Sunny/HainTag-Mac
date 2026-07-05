"""Library panel widgets for artist and OC references."""
from __future__ import annotations

import os

from PyQt6.QtCore import Qt, pyqtSignal, QRectF, QSize
from PyQt6.QtGui import QPainter, QPainterPath, QPen, QPixmap
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from ..i18n import Translator
from ..icons import paint_rounded_surface, to_qcolor
from ..models import ArtistEntry, OCEntry
from ..storage import AppStorage
from ..theme import _fs, current_palette
from ..ui_tokens import _dp, _rad, RAD_XS, RAD_SM
from .common import DashedRectButton, HoverPillButton, ToggleSwitch

SECTION_ARTIST = "artist"
SECTION_OC = "oc"


def _p() -> dict[str, str]:
    return current_palette()


# ── Shared style helpers (DRY) ──

def _pad(v: int, h: int) -> str:
    return f"{_dp(v)}px {_dp(h)}px"


def _input_style(p: dict, fs: str = 'fs_10', padding: str | None = None) -> str:
    padding = padding or _pad(3, 6)
    return (f"background: {p['bg']}; color: {p['text']}; border: 1px solid {p['line']}; "
            f"border-radius: {_rad(RAD_XS)}px; padding: {padding}; font-size: {_fs(fs)};")


def _del_btn_style(p: dict, fs: str = 'fs_11') -> str:
    return f"color: {p['text_dim']}; background: transparent; border: none; font-size: {_fs(fs)};"


def _arrow_style(p: dict) -> str:
    return f"color: {p['accent_text']}; font-size: {_fs('fs_9')}; background: transparent; border: none;"


def _dim_label_style(p: dict) -> str:
    return f"color: {p['text_dim']}; font-size: {_fs('fs_9')}; border: none; letter-spacing: 1px;"


# ── Self-painted banner surfaces ──
# QSS border-radius corners are rasterised WITHOUT antialiasing, so the banner
# header/body surfaces are painted with QPainter instead. The widgets keep a
# `background: transparent; border: none` stylesheet; QSS only styles children.

class _BannerHeader(QWidget):
    """Banner header row — AA rounded surface. Collapsed: all four corners
    round. Expanded: top corners only, with an OPEN bottom edge (the QSS
    version used `border-bottom: none`) so the body continues the outline."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._expanded = False

    def set_expanded(self, expanded: bool) -> None:
        if self._expanded != expanded:
            self._expanded = expanded
            self.update()

    def paintEvent(self, event):
        p = _p()
        painter = QPainter(self)
        if not self._expanded:
            paint_rounded_surface(painter, self.rect(), _rad(RAD_SM),
                                  bg=p['bg_surface'], border=p['line'])
            painter.end()
            return
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        r = float(_rad(RAD_SM))
        # Bottom edge runs to the exact widget edge (no 0.5 inset): the body
        # widget continues the same outline right below, so the fills and the
        # left/right border strokes must meet without a half-pixel seam.
        rect = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, 0.0)
        x, y, w, h = rect.x(), rect.y(), rect.width(), rect.height()
        path = QPainterPath()  # left edge ↑, top corners, right edge ↓ — open bottom
        path.moveTo(x, y + h)
        path.lineTo(x, y + r)
        path.arcTo(x, y, 2 * r, 2 * r, 180.0, -90.0)
        path.lineTo(x + w - r, y)
        path.arcTo(x + w - 2 * r, y, 2 * r, 2 * r, 90.0, -90.0)
        path.lineTo(x + w, y + h)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(to_qcolor(p['bg_surface']))
        painter.drawPath(path)  # fill auto-closes across the open bottom
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(QPen(to_qcolor(p['line']), 1.0))
        painter.drawPath(path)
        painter.end()


class _BannerBody(QWidget):
    """Banner expanded body — AA rounded surface: bottom corners only, with an
    OPEN top edge (the QSS version used `border-top: none`; the header above
    owns the shared edge)."""

    def paintEvent(self, event):
        p = _p()
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        r = float(_rad(RAD_SM))
        # Top edge runs to the exact widget edge (see _BannerHeader) — no seam.
        rect = QRectF(self.rect()).adjusted(0.5, 0.0, -0.5, -0.5)
        x, y, w, h = rect.x(), rect.y(), rect.width(), rect.height()
        path = QPainterPath()  # right edge ↓, bottom corners, left edge ↑ — open top
        path.moveTo(x + w, y)
        path.lineTo(x + w, y + h - r)
        path.arcTo(x + w - 2 * r, y + h - 2 * r, 2 * r, 2 * r, 0.0, -90.0)
        path.lineTo(x + r, y + h)
        path.arcTo(x, y + h - 2 * r, 2 * r, 2 * r, 270.0, -90.0)
        path.lineTo(x, y)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(to_qcolor(p['bg_content']))
        painter.drawPath(path)  # fill auto-closes across the open top
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(QPen(to_qcolor(p['line']), 1.0))
        painter.drawPath(path)
        painter.end()


class _ThumbLabel(QLabel):
    """Reference-image thumbnail tile — the rounded surface (fill + border) is
    self-painted with antialiasing beneath the pixmap; QSS border-radius is
    not antialiased."""

    def paintEvent(self, event):
        p = _p()
        painter = QPainter(self)
        paint_rounded_surface(painter, self.rect(), _rad(RAD_SM),
                              bg=p['bg_content'], border=p['line'])
        painter.end()
        super().paintEvent(event)


# ═══════════════════════════════════════════════════════════
#  Reference Image Grid
# ═══════════════════════════════════════════════════════════

class _RefImageGrid(QWidget):
    """Reference image display. Two modes:

    - vertical=True (artist): full-width images stacked vertically, click to remove
    - vertical=False (OC): small horizontal thumbnails
    """

    changed = pyqtSignal()

    def __init__(self, storage: AppStorage, translator: Translator, thumb_size: int = 40,
                 vertical: bool = False, parent=None):
        super().__init__(parent)
        self._storage = storage
        self._t = translator
        self._paths: list[str] = []
        self._thumb_size = thumb_size
        self._vertical = vertical

        if vertical:
            self._layout = QVBoxLayout(self)
            self._layout.setContentsMargins(0, 2, 0, 2)
            self._layout.setSpacing(_dp(6))
        else:
            self._layout = QHBoxLayout(self)
            self._layout.setContentsMargins(0, 2, 0, 2)
            self._layout.setSpacing(_dp(4))

        self._add_btn = DashedRectButton("+", self, border='line', border_hover='line_strong',
                                         bg='bg_content')
        if vertical:
            self._add_btn.setFixedHeight(_dp(28))
        else:
            self._add_btn.setFixedSize(thumb_size, thumb_size)
        self._layout.addWidget(self._add_btn)
        self._add_btn.clicked.connect(self._pick_image)
        if not vertical:
            self._layout.addStretch()
        self._apply_btn_style()

    def _apply_btn_style(self):
        # Dashed rounded surface self-painted (antialiased) in DashedRectButton.
        p = _p()
        self._add_btn.setStyleSheet(
            f"background: transparent; border: none; color: {p['text_dim']}; font-size: {_fs('fs_14')};"
        )

    def set_paths(self, paths: list[str]):
        self._paths = list(paths)
        self._rebuild()

    def paths(self) -> list[str]:
        return list(self._paths)

    def _rebuild(self):
        # Remove all widgets except the add button (last for vertical, has stretch for horizontal)
        while self._layout.count() > (1 if self._vertical else 2):
            item = self._layout.takeAt(0)
            w = item.widget()
            if w and w is not self._add_btn:
                w.deleteLater()
        insert_pos = 0
        for i, path in enumerate(self._paths):
            if self._vertical:
                # Full-width image — rounded tile self-painted (AA) in _ThumbLabel.
                thumb = _ThumbLabel(self)
                thumb.setAlignment(Qt.AlignmentFlag.AlignCenter)
                thumb.setStyleSheet("background: transparent; border: none;")
                thumb.setCursor(Qt.CursorShape.PointingHandCursor)
                if os.path.isfile(path):
                    pm = QPixmap(path).scaledToWidth(
                        max(180, self.width() - 8),
                        Qt.TransformationMode.SmoothTransformation)
                    thumb.setPixmap(pm)
                    thumb.setFixedHeight(pm.height() + _dp(4))
                thumb.setToolTip(self._t.t("click_remove"))
                thumb.mousePressEvent = lambda _, idx=i: self._remove_image(idx)
                self._layout.insertWidget(insert_pos, thumb)
            else:
                # Small thumbnail — rounded tile self-painted (AA) in _ThumbLabel.
                ts = self._thumb_size
                thumb = _ThumbLabel(self)
                thumb.setFixedSize(ts, ts)
                thumb.setAlignment(Qt.AlignmentFlag.AlignCenter)
                thumb.setStyleSheet("background: transparent; border: none;")
                thumb.setCursor(Qt.CursorShape.PointingHandCursor)
                if os.path.isfile(path):
                    pm = QPixmap(path).scaled(QSize(ts - 4, ts - 4),
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation)
                    thumb.setPixmap(pm)
                thumb.setToolTip(self._t.t("click_remove"))
                thumb.mousePressEvent = lambda _, idx=i: self._remove_image(idx)
                self._layout.insertWidget(insert_pos, thumb)
            insert_pos += 1

    def _pick_image(self):
        from ..file_dialogs import pick_image_file
        path = pick_image_file(self, self._t)
        if path:
            saved = self._storage.copy_library_image(path)
            self._paths.append(saved)
            self._rebuild()
            self.changed.emit()

    def _remove_image(self, idx: int):
        if 0 <= idx < len(self._paths):
            self._storage.remove_library_image(self._paths[idx])
            self._paths.pop(idx)
            self._rebuild()
            self.changed.emit()

    def remove_assets(self) -> None:
        for path in self._paths:
            self._storage.remove_library_image(path)
        self._paths.clear()


# ═══════════════════════════════════════════════════════════
#  Artist Banner
# ═══════════════════════════════════════════════════════════

class ArtistBanner(QWidget):
    """Expandable entry card for an artist."""

    changed = pyqtSignal()
    delete_requested = pyqtSignal(object)

    def __init__(self, translator: Translator, storage: AppStorage,
                 entry: ArtistEntry | None = None, parent=None):
        super().__init__(parent)
        self._t = translator
        self._expanded = False
        p = _p()

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Header (always visible) — rounded surface self-painted (AA) ──
        self._header = _BannerHeader(self)
        self._header.setCursor(Qt.CursorShape.PointingHandCursor)
        self._header.setStyleSheet("background: transparent; border: none;")
        hl = QHBoxLayout(self._header)
        hl.setContentsMargins(_dp(10), _dp(6), _dp(6), _dp(6))
        hl.setSpacing(_dp(8))

        self._arrow = QLabel("▸", self._header)
        self._arrow.setStyleSheet(_arrow_style(p))
        self._arrow.setFixedWidth(_dp(10))
        hl.addWidget(self._arrow)

        self._name_label = QLabel(translator.t("artist_name"), self._header)
        self._name_label.setStyleSheet(f"color: {p['text']}; font-size: {_fs('fs_11')}; background: transparent; border: none;")
        hl.addWidget(self._name_label, 1)

        del_btn = QPushButton("×", self._header)
        del_btn.setFixedSize(_dp(16), _dp(16))
        del_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        del_btn.setStyleSheet(_del_btn_style(p))
        del_btn.clicked.connect(lambda: self.delete_requested.emit(self))
        hl.addWidget(del_btn)

        self._header.mousePressEvent = lambda e: self._toggle()
        root.addWidget(self._header)

        # ── Body (expandable) — rounded surface self-painted (AA) ──
        self._body = _BannerBody(self)
        self._body.setStyleSheet("background: transparent; border: none;")
        bl = QVBoxLayout(self._body)
        bl.setContentsMargins(_dp(8), _dp(6), _dp(8), _dp(8))
        bl.setSpacing(_dp(4))

        # Reference images — hero area, full width
        self._ref_grid = _RefImageGrid(storage, translator, vertical=True, parent=self._body)
        self._ref_grid.changed.connect(self.changed.emit)
        bl.addWidget(self._ref_grid)

        # Name — compact
        self._name_edit = QLineEdit(self._body)
        self._name_edit.setPlaceholderText(translator.t("artist_name"))
        self._name_edit.setStyleSheet(_input_style(p))
        self._name_edit.textChanged.connect(self._on_name_changed)
        bl.addWidget(self._name_edit)

        # LoRA / trigger — compact with copy button
        string_row = QHBoxLayout()
        string_row.setSpacing(_dp(4))
        self._string_edit = QLineEdit(self._body)
        self._string_edit.setPlaceholderText(translator.t("artist_string"))
        self._string_edit.setStyleSheet(_input_style(p))
        self._string_edit.textChanged.connect(lambda: self.changed.emit())
        string_row.addWidget(self._string_edit, 1)
        self._copy_btn = QPushButton(self._body)
        self._copy_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._copy_btn.setFixedHeight(_dp(22))
        self._copy_btn.setStyleSheet(
            f"background: {p['accent']}; color: {p['accent_text']}; border: none; "
            f"border-radius: {_rad(RAD_XS)}px; padding: 0 10px; font-size: {_fs('fs_9')}; letter-spacing: 1px;"
        )
        self._copy_btn.clicked.connect(self._copy_string)
        string_row.addWidget(self._copy_btn)
        bl.addLayout(string_row)

        self._body.hide()
        root.addWidget(self._body)

        self.retranslate_ui()
        if entry:
            self.set_entry(entry)

    def apply_theme(self):
        p = _p()
        self._header.update()  # surface colours resolve from the palette at paint time
        self._body.update()
        self._arrow.setStyleSheet(_arrow_style(p))
        self._name_label.setStyleSheet(f"color: {p['text']}; font-size: {_fs('fs_11')}; background: transparent; border: none;")
        self._name_edit.setStyleSheet(_input_style(p))
        self._string_edit.setStyleSheet(_input_style(p))
        self._ref_grid._apply_btn_style()
        self._copy_btn.setStyleSheet(
            f"background: {p['accent']}; color: {p['accent_text']}; border: none; "
            f"border-radius: {_rad(RAD_XS)}px; padding: 0 10px; font-size: {_fs('fs_9')}; letter-spacing: 1px;"
        )

    def _toggle(self):
        self._expanded = not self._expanded
        self._body.setVisible(self._expanded)
        self._arrow.setText("▾" if self._expanded else "▸")
        self._header.set_expanded(self._expanded)

    def set_expanded(self, expanded: bool) -> None:
        if self._expanded == expanded:
            return
        self._toggle()

    def _copy_string(self):
        from PyQt6.QtWidgets import QApplication
        text = self._string_edit.text().strip()
        if text:
            QApplication.clipboard().setText(text)

    def _on_name_changed(self, text: str):
        self._name_label.setText(text or self._t.t("artist_name"))
        self.changed.emit()

    def set_entry(self, entry: ArtistEntry):
        self._name_edit.setText(entry.name)
        self._name_label.setText(entry.name or self._t.t("artist_name"))
        self._string_edit.setText(entry.artist_string)
        self._ref_grid.set_paths(entry.reference_images)

    def retranslate_ui(self) -> None:
        self._name_edit.setPlaceholderText(self._t.t("artist_name"))
        self._string_edit.setPlaceholderText(self._t.t("artist_string"))
        self._copy_btn.setText(self._t.t("copy"))

    def entry(self) -> ArtistEntry:
        return ArtistEntry(
            name=self._name_edit.text().strip(),
            artist_string=self._string_edit.text().strip(),
            reference_images=self._ref_grid.paths(),
            enabled=True,
        )

    def remove_assets(self) -> None:
        self._ref_grid.remove_assets()


# ═══════════════════════════════════════════════════════════
#  OC Banner
# ═══════════════════════════════════════════════════════════

class _OutfitRow(QWidget):
    """A single outfit entry row: toggle + name + tags + delete."""

    changed = pyqtSignal()
    delete_requested = pyqtSignal(object)  # self

    def __init__(self, outfit, translator: Translator, parent=None):
        super().__init__(parent)
        self._t = translator
        p = _p()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(_dp(3))

        # Top row: toggle + name + delete
        top = QHBoxLayout()
        top.setSpacing(_dp(6))
        self._toggle = ToggleSwitch(self)
        self._toggle.setChecked(outfit.active)
        self._toggle.toggled.connect(lambda: self.changed.emit())
        top.addWidget(self._toggle)

        self._name_edit = QLineEdit(self)
        self._name_edit.setPlaceholderText(self._t.t("outfit_name_placeholder"))
        self._name_edit.setText(outfit.name)
        self._name_edit.setStyleSheet(_input_style(p, padding=_pad(2, 6)))
        self._name_edit.setFixedHeight(_dp(22))
        self._name_edit.textChanged.connect(lambda: self.changed.emit())
        top.addWidget(self._name_edit, 1)

        del_btn = QPushButton("×", self)
        del_btn.setFixedSize(_dp(16), _dp(16))
        del_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        del_btn.setStyleSheet(_del_btn_style(p, 'fs_10'))
        del_btn.clicked.connect(lambda: self.delete_requested.emit(self))
        top.addWidget(del_btn)
        layout.addLayout(top)

        # Tags row
        self._tags_edit = QLineEdit(self)
        self._tags_edit.setPlaceholderText(self._t.t("outfit_tags_placeholder"))
        self._tags_edit.setText(outfit.tags)
        self._tags_edit.setStyleSheet(_input_style(p, padding=_pad(2, 6)))
        self._tags_edit.setFixedHeight(_dp(22))
        self._tags_edit.textChanged.connect(lambda: self.changed.emit())
        layout.addWidget(self._tags_edit)

    def apply_theme(self):
        p = _p()
        self._name_edit.setStyleSheet(_input_style(p, padding=_pad(2, 6)))
        self._tags_edit.setStyleSheet(_input_style(p, padding=_pad(2, 6)))

    def retranslate_ui(self):
        self._name_edit.setPlaceholderText(self._t.t("outfit_name_placeholder"))
        self._tags_edit.setPlaceholderText(self._t.t("outfit_tags_placeholder"))

    def outfit(self):
        from ..models import OutfitEntry
        return OutfitEntry(
            name=self._name_edit.text().strip(),
            tags=self._tags_edit.text().strip(),
            active=self._toggle.isChecked(),
        )


class OCBanner(QWidget):
    """Expandable entry card for an OC character."""

    changed = pyqtSignal()
    delete_requested = pyqtSignal(object)

    def __init__(self, translator: Translator, storage: AppStorage,
                 entry: OCEntry | None = None, parent=None):
        super().__init__(parent)
        self._t = translator
        self._expanded = False
        self._tag_dictionary = None
        p = _p()

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Header — rounded surface self-painted (AA) ──
        self._header = _BannerHeader(self)
        self._header.setCursor(Qt.CursorShape.PointingHandCursor)
        self._header.setStyleSheet("background: transparent; border: none;")
        hl = QHBoxLayout(self._header)
        hl.setContentsMargins(_dp(10), _dp(6), _dp(6), _dp(6))
        hl.setSpacing(_dp(8))

        self._arrow = QLabel("▸", self._header)
        self._arrow.setStyleSheet(_arrow_style(p))
        self._arrow.setFixedWidth(_dp(10))
        hl.addWidget(self._arrow)

        self._name_label = QLabel(translator.t("character_name"), self._header)
        self._name_label.setStyleSheet(f"color: {p['text']}; font-size: {_fs('fs_11')}; background: transparent; border: none;")
        hl.addWidget(self._name_label, 1)

        self._enabled = ToggleSwitch(self._header)
        self._enabled.setChecked(True)
        self._enabled.toggled.connect(lambda: self.changed.emit())
        hl.addWidget(self._enabled)

        del_btn = QPushButton("×", self._header)
        del_btn.setFixedSize(_dp(16), _dp(16))
        del_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        del_btn.setStyleSheet(_del_btn_style(p))
        del_btn.clicked.connect(lambda: self.delete_requested.emit(self))
        hl.addWidget(del_btn)

        self._header.mousePressEvent = lambda e: self._toggle()
        root.addWidget(self._header)

        # ── Body — rounded surface self-painted (AA) ──
        self._body = _BannerBody(self)
        self._body.setStyleSheet("background: transparent; border: none;")
        bl = QVBoxLayout(self._body)
        bl.setContentsMargins(_dp(12), _dp(8), _dp(12), _dp(8))
        bl.setSpacing(_dp(6))

        # Order + Depth row
        spin_style = _input_style(p, padding=_pad(2, 4))
        dim_style = _dim_label_style(p)
        od_row = QHBoxLayout()
        od_row.setSpacing(_dp(6))
        self._order_label = QLabel(self._body)
        self._order_label.setStyleSheet(dim_style)
        od_row.addWidget(self._order_label)
        self._order_spin = QSpinBox(self._body)
        self._order_spin.setRange(0, 9999)
        self._order_spin.setValue(100)
        self._order_spin.setFixedWidth(_dp(54))
        self._order_spin.setStyleSheet(spin_style)
        self._order_spin.valueChanged.connect(lambda: self.changed.emit())
        od_row.addWidget(self._order_spin)
        od_row.addSpacing(_dp(8))
        self._depth_label = QLabel(self._body)
        self._depth_label.setStyleSheet(dim_style)
        od_row.addWidget(self._depth_label)
        self._depth_spin = QSpinBox(self._body)
        self._depth_spin.setRange(0, 999)
        self._depth_spin.setValue(4)
        self._depth_spin.setFixedWidth(_dp(54))
        self._depth_spin.setStyleSheet(spin_style)
        self._depth_spin.valueChanged.connect(lambda: self.changed.emit())
        od_row.addWidget(self._depth_spin)
        od_row.addStretch()
        bl.addLayout(od_row)

        self._character_label = QLabel(self._body)
        self._character_label.setStyleSheet(dim_style)
        bl.addWidget(self._character_label)
        self._name_edit = QLineEdit(self._body)
        self._name_edit.setStyleSheet(_input_style(p, 'fs_11', _pad(4, 8)))
        self._name_edit.textChanged.connect(self._on_name_changed)
        bl.addWidget(self._name_edit)

        self._tags_label = QLabel(self._body)
        self._tags_label.setStyleSheet(dim_style)
        bl.addWidget(self._tags_label)
        self._tags_edit = QTextEdit(self._body)
        self._tags_edit.setStyleSheet(_input_style(p, 'fs_11', _pad(4, 8)))
        self._tags_edit.setMaximumHeight(_dp(56))
        self._tags_edit.textChanged.connect(lambda: self.changed.emit())
        bl.addWidget(self._tags_edit)

        self._ref_grid = _RefImageGrid(storage, translator, parent=self._body)
        self._ref_grid.changed.connect(self.changed.emit)
        bl.addWidget(self._ref_grid)

        # ── Outfits section ──
        sep = QLabel("", self._body)
        sep.setFixedHeight(1)
        sep.setStyleSheet(f"background: {p['line']}; border: none;")
        bl.addWidget(sep)

        outfit_header = QHBoxLayout()
        self._outfit_label = QLabel(self._body)
        self._outfit_label.setStyleSheet(dim_style)
        outfit_header.addWidget(self._outfit_label)
        outfit_header.addStretch()
        add_outfit_btn = QPushButton("+", self._body)
        add_outfit_btn.setFixedSize(_dp(20), _dp(20))
        add_outfit_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        add_outfit_btn.setStyleSheet(
            f"background: transparent; color: {p['text_dim']}; border: 1px solid {p['line']}; "
            f"border-radius: {_rad(RAD_XS)}px; font-size: {_fs('fs_12')};"
        )
        add_outfit_btn.clicked.connect(self._add_outfit)
        outfit_header.addWidget(add_outfit_btn)
        bl.addLayout(outfit_header)

        self._outfit_list = QVBoxLayout()
        self._outfit_list.setSpacing(_dp(4))
        bl.addLayout(self._outfit_list)
        self._outfit_rows: list[_OutfitRow] = []

        self._body.hide()
        root.addWidget(self._body)

        self.retranslate_ui()
        if entry:
            self.set_entry(entry)

    def _toggle(self):
        self._expanded = not self._expanded
        self._body.setVisible(self._expanded)
        self._arrow.setText("▾" if self._expanded else "▸")
        self._header.set_expanded(self._expanded)

    def set_expanded(self, expanded: bool) -> None:
        if self._expanded == expanded:
            return
        self._toggle()

    def apply_theme(self):
        p = _p()
        self._header.update()  # surface colours resolve from the palette at paint time
        self._body.update()
        self._arrow.setStyleSheet(_arrow_style(p))
        self._name_label.setStyleSheet(f"color: {p['text']}; font-size: {_fs('fs_11')}; background: transparent; border: none;")
        self._name_edit.setStyleSheet(_input_style(p, 'fs_11', _pad(4, 8)))
        self._tags_edit.setStyleSheet(_input_style(p, 'fs_11', _pad(4, 8)))
        spin_style = _input_style(p, padding=_pad(2, 4))
        dim_style = _dim_label_style(p)
        self._order_label.setStyleSheet(dim_style)
        self._depth_label.setStyleSheet(dim_style)
        self._character_label.setStyleSheet(dim_style)
        self._tags_label.setStyleSheet(dim_style)
        self._outfit_label.setStyleSheet(dim_style)
        self._order_spin.setStyleSheet(spin_style)
        self._depth_spin.setStyleSheet(spin_style)
        self._ref_grid._apply_btn_style()
        for row in self._outfit_rows:
            row.apply_theme()

    def _on_name_changed(self, text: str):
        self._name_label.setText(text or self._t.t("character_name"))
        self.changed.emit()

    def set_tag_dictionary(self, dictionary) -> None:
        from .tag_completer import install_completer_recursive
        self._tag_dictionary = dictionary
        install_completer_recursive(self, dictionary)

    def _add_outfit(self, outfit=None):
        from ..models import OutfitEntry
        if not isinstance(outfit, OutfitEntry):
            outfit = OutfitEntry(name="", tags="")
        row = _OutfitRow(outfit, self._t, self)
        row.changed.connect(self.changed.emit)
        row.delete_requested.connect(self._remove_outfit)
        self._outfit_rows.append(row)
        self._outfit_list.addWidget(row)
        if self._tag_dictionary is not None:
            from .tag_completer import install_completer_recursive
            install_completer_recursive(row, self._tag_dictionary)
        self.changed.emit()

    def retranslate_ui(self) -> None:
        self._order_label.setText(self._t.t("order"))
        self._depth_label.setText(self._t.t("depth"))
        self._character_label.setText(self._t.t("character_name"))
        self._tags_label.setText(self._t.t("tags"))
        self._outfit_label.setText(self._t.t("outfits"))
        self._tags_edit.setPlaceholderText(self._t.t("oc_tags_placeholder"))
        for row in self._outfit_rows:
            row.retranslate_ui()

    def _remove_outfit(self, row):
        if row in self._outfit_rows:
            self._outfit_rows.remove(row)
            self._outfit_list.removeWidget(row)
            row.deleteLater()
            self.changed.emit()

    def set_entry(self, entry: OCEntry):
        self._name_edit.setText(entry.character_name)
        self._name_label.setText(entry.character_name or self._t.t("character_name"))
        self._tags_edit.setPlainText(entry.tags)
        self._ref_grid.set_paths(entry.reference_images)
        self._order_spin.setValue(entry.order)
        self._depth_spin.setValue(entry.depth)
        self._enabled.setChecked(entry.enabled)
        for o in entry.outfits:
            self._add_outfit(o)

    def entry(self) -> OCEntry:
        outfits = [r.outfit() for r in self._outfit_rows]
        return OCEntry(
            character_name=self._name_edit.text().strip(),
            tags=self._tags_edit.toPlainText().strip(),
            reference_images=self._ref_grid.paths(),
            outfits=outfits,
            order=self._order_spin.value(),
            depth=self._depth_spin.value(),
            enabled=self._enabled.isChecked(),
        )

    def remove_assets(self) -> None:
        self._ref_grid.remove_assets()


# ═══════════════════════════════════════════════════════════
#  Library Panel — Two-Step Scroll Drawer
# ═══════════════════════════════════════════════════════════

class LibraryPanel(QWidget):
    """Right sidebar for artist and OC libraries."""

    SIDEBAR_WIDTH = 320

    changed = pyqtSignal()
    width_changed = pyqtSignal(int)
    section_changed = pyqtSignal(str)
    close_requested = pyqtSignal()

    def __init__(self, translator: Translator, storage: AppStorage, parent=None):
        super().__init__(parent)
        self.setObjectName("LibPanel")
        self._t = translator
        self._storage = storage
        self._artist_banners: list[ArtistBanner] = []
        self._oc_banners: list[OCBanner] = []
        self._current_section = SECTION_ARTIST
        self._default_oc_order = 77
        self._default_oc_depth = 4
        self._loading_entries = False
        self._tag_dictionary = None

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self._header = QWidget(self)
        header_layout = QVBoxLayout(self._header)
        header_layout.setContentsMargins(_dp(10), _dp(10), _dp(10), _dp(8))
        header_layout.setSpacing(_dp(8))
        title_row = QHBoxLayout()
        title_row.setContentsMargins(0, 0, 0, 0)
        title_row.setSpacing(_dp(6))
        self._title = QLabel(self._header)
        title_row.addWidget(self._title, 1)
        self._close_btn = QPushButton("×", self._header)
        self._close_btn.setFixedSize(_dp(22), _dp(22))
        self._close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._close_btn.clicked.connect(self.close_requested.emit)
        title_row.addWidget(self._close_btn)
        header_layout.addLayout(title_row)

        tab_row = QHBoxLayout()
        tab_row.setContentsMargins(0, 0, 0, 0)
        tab_row.setSpacing(_dp(6))

        # Segmented tabs — pill surface self-painted (AA) by HoverPillButton;
        # the active fill follows the 'active' property set in _apply_strip_styles.
        self._artist_title_btn = HoverPillButton("", self._header)
        self._artist_title_btn.set_pill_colors(
            normal='bg_surface', hover='bg_surface', active='accent',
            border='line', border_hover='line', border_active='accent')
        self._artist_title_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._artist_title_btn.clicked.connect(lambda: self.set_current_section(SECTION_ARTIST))
        tab_row.addWidget(self._artist_title_btn)

        self._oc_title_btn = HoverPillButton("", self._header)
        self._oc_title_btn.set_pill_colors(
            normal='bg_surface', hover='bg_surface', active='accent',
            border='line', border_hover='line', border_active='accent')
        self._oc_title_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._oc_title_btn.clicked.connect(lambda: self.set_current_section(SECTION_OC))
        tab_row.addWidget(self._oc_title_btn)
        header_layout.addLayout(tab_row)
        root.addWidget(self._header)

        self._scroll = QScrollArea(self)
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(self._scroll.Shape.NoFrame)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._scroll.setStyleSheet("background: transparent; border: none;")

        self._scroll_inner = QWidget()
        self._sections_layout = QVBoxLayout(self._scroll_inner)
        self._sections_layout.setContentsMargins(_dp(10), 0, _dp(10), _dp(12))
        self._sections_layout.setSpacing(0)

        self._artist_body = QWidget(self._scroll_inner)
        al = QVBoxLayout(self._artist_body)
        al.setContentsMargins(0, 0, 0, 0)
        al.setSpacing(_dp(6))
        # Full-width add button — pill surface self-painted (AA) by HoverPillButton.
        self._add_artist_btn = HoverPillButton("", self._artist_body)
        self._add_artist_btn.set_pill_colors(normal='bg_surface', hover='bg_surface',
                                             border='line', border_hover='line')
        self._add_artist_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._add_artist_btn.clicked.connect(self._add_artist)
        al.addWidget(self._add_artist_btn)
        self._artist_list = QVBoxLayout()
        self._artist_list.setSpacing(_dp(6))
        al.addLayout(self._artist_list)
        al.addStretch()

        self._oc_body = QWidget(self._scroll_inner)
        ol = QVBoxLayout(self._oc_body)
        ol.setContentsMargins(0, 0, 0, 0)
        ol.setSpacing(_dp(6))
        # Full-width add button — pill surface self-painted (AA) by HoverPillButton.
        self._add_oc_btn = HoverPillButton("", self._oc_body)
        self._add_oc_btn.set_pill_colors(normal='bg_surface', hover='bg_surface',
                                         border='line', border_hover='line')
        self._add_oc_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._add_oc_btn.clicked.connect(self._add_oc)
        ol.addWidget(self._add_oc_btn)
        self._oc_list = QVBoxLayout()
        self._oc_list.setSpacing(_dp(6))
        ol.addLayout(self._oc_list)
        ol.addStretch()

        self._sections_layout.addWidget(self._artist_body)
        self._sections_layout.addWidget(self._oc_body)
        self._scroll.setWidget(self._scroll_inner)
        root.addWidget(self._scroll, 1)

        self.setFixedWidth(_dp(self.SIDEBAR_WIDTH))
        self.retranslate_ui()
        self.set_current_section(SECTION_ARTIST)
        self.apply_theme()

    def current_section(self) -> str:
        return self._current_section

    def set_current_section(self, section: str):
        self._current_section = SECTION_OC if section == SECTION_OC else SECTION_ARTIST
        self._artist_body.setVisible(self._current_section == SECTION_ARTIST)
        self._oc_body.setVisible(self._current_section == SECTION_OC)
        self._apply_strip_styles()
        self.section_changed.emit(self._current_section)
        self.width_changed.emit(self.width())

    def open_artist_library(self) -> None:
        self.set_current_section(SECTION_ARTIST)

    def open_oc_library(self) -> None:
        self.set_current_section(SECTION_OC)

    def retranslate_ui(self) -> None:
        self._title.setText(self._t.t("library_panel"))
        self._close_btn.setToolTip(self._t.t("close_library"))
        self._artist_title_btn.setText(self._t.t("artist_library"))
        self._oc_title_btn.setText(self._t.t("oc_library"))
        self._add_artist_btn.setText("+ " + self._t.t("add_artist"))
        self._add_oc_btn.setText("+ " + self._t.t("add_oc"))
        for banner in self._artist_banners:
            banner.retranslate_ui()
        for banner in self._oc_banners:
            banner.retranslate_ui()

    def apply_theme(self):
        p = _p()
        self.setFixedWidth(_dp(self.SIDEBAR_WIDTH))
        self._close_btn.setFixedSize(_dp(22), _dp(22))
        self._artist_list.setSpacing(_dp(6))
        self._oc_list.setSpacing(_dp(6))
        self._sections_layout.setContentsMargins(_dp(10), 0, _dp(10), _dp(12))
        self.setStyleSheet(
            f"#LibPanel {{ background: {p['bg']}; border-left: 1px solid {p['line_strong']}; }}"
        )
        self._title.setStyleSheet(
            f"color: {p['text']}; font-size: {_fs('fs_11')}; font-weight: bold;"
        )
        self._close_btn.setStyleSheet(
            f"color: {p['text_dim']}; background: transparent; border: none; "
            f"border-radius: {_rad(RAD_XS)}px; font-size: {_fs('fs_12')};"
        )
        self._apply_strip_styles()
        self._apply_add_btn_styles()
        for banner in self._artist_banners:
            banner.apply_theme()
        for banner in self._oc_banners:
            banner.apply_theme()

    def _apply_strip_styles(self):
        # Pill fill/border are self-painted (AA) by HoverPillButton, keyed off
        # the 'active' property; QSS keeps only the text styling. The removed
        # 1px QSS border is compensated with +1 padding so metrics are stable.
        p = _p()
        pad = f"{_dp(6) + 1}px {_dp(8) + 1}px"
        active = (
            f"background: transparent; border: none; color: {p['accent_text']}; "
            f"padding: {pad}; font-size: {_fs('fs_10')}; font-weight: bold;"
        )
        normal = (
            f"background: transparent; border: none; color: {p['text_dim']}; "
            f"padding: {pad}; font-size: {_fs('fs_10')};"
        )
        for btn, section in ((self._artist_title_btn, SECTION_ARTIST),
                             (self._oc_title_btn, SECTION_OC)):
            is_active = self._current_section == section
            btn.setProperty('active', is_active)
            btn.setStyleSheet(active if is_active else normal)
            btn.update()

    def _apply_add_btn_styles(self):
        # Pill fill/border self-painted (AA) by HoverPillButton; QSS keeps only
        # text styling (removed 1px border compensated with +1 padding).
        p = _p()
        style = (
            f"background: transparent; border: none; color: {p['text']}; "
            f"padding: {_dp(6) + 1}px {_dp(8) + 1}px; font-size: {_fs('fs_10')};"
        )
        self._add_artist_btn.setStyleSheet(style)
        self._add_oc_btn.setStyleSheet(style)

    def set_tag_dictionary(self, dictionary) -> None:
        from .tag_completer import install_completer_recursive
        self._tag_dictionary = dictionary
        install_completer_recursive(self, dictionary)
        for banner in self._oc_banners:
            banner.set_tag_dictionary(dictionary)

    def _install_completer_on(self, widget) -> None:
        if self._tag_dictionary is None:
            return
        from .tag_completer import install_completer_recursive
        install_completer_recursive(widget, self._tag_dictionary)
        if hasattr(widget, "set_tag_dictionary"):
            widget.set_tag_dictionary(self._tag_dictionary)

    def _add_artist(self, entry: ArtistEntry | None = None):
        banner = ArtistBanner(self._t, self._storage, entry, self._scroll_inner)
        banner.changed.connect(self.changed.emit)
        banner.delete_requested.connect(self._remove_artist)
        self._artist_banners.append(banner)
        self._artist_list.addWidget(banner)
        self._install_completer_on(banner)
        if entry is None:
            banner._toggle()
        if not self._loading_entries:
            self.changed.emit()

    def add_artist_entry(self, entry: ArtistEntry | None = None) -> None:
        self.set_current_section(SECTION_ARTIST)
        self._add_artist(entry)

    def _remove_artist(self, banner):
        if banner in self._artist_banners:
            banner.remove_assets()
            self._artist_banners.remove(banner)
            self._artist_list.removeWidget(banner)
            banner.deleteLater()
            self.changed.emit()

    def set_oc_defaults(self, order: int, depth: int):
        self._default_oc_order = order
        self._default_oc_depth = depth

    def _add_oc(self, entry: OCEntry | None = None):
        if not isinstance(entry, OCEntry):
            entry = OCEntry(order=self._default_oc_order, depth=self._default_oc_depth)
        banner = OCBanner(self._t, self._storage, entry, self._scroll_inner)
        banner.changed.connect(self.changed.emit)
        banner.delete_requested.connect(self._remove_oc)
        self._oc_banners.append(banner)
        self._oc_list.addWidget(banner)
        self._install_completer_on(banner)
        if entry is None:
            banner._toggle()
        if not self._loading_entries:
            self.changed.emit()

    def add_oc_entry(self, entry: OCEntry | None = None) -> None:
        self.set_current_section(SECTION_OC)
        self._add_oc(entry)

    def focus_oc_entry(self, index: int, *, expand: bool = True) -> bool:
        if not 0 <= index < len(self._oc_banners):
            return False
        self.set_current_section(SECTION_OC)
        banner = self._oc_banners[index]
        if expand:
            banner.set_expanded(True)
        self._scroll.ensureWidgetVisible(banner, 0, _dp(12))
        return True

    def _remove_oc(self, banner):
        if banner in self._oc_banners:
            banner.remove_assets()
            self._oc_banners.remove(banner)
            self._oc_list.removeWidget(banner)
            banner.deleteLater()
            self.changed.emit()

    def set_entries(self, artists: list[ArtistEntry], ocs: list[OCEntry]):
        self._loading_entries = True
        try:
            for banner in list(self._artist_banners):
                self._artist_list.removeWidget(banner)
                banner.deleteLater()
            for banner in list(self._oc_banners):
                self._oc_list.removeWidget(banner)
                banner.deleteLater()
            self._artist_banners.clear()
            self._oc_banners.clear()
            for a in artists:
                self._add_artist(a)
            for o in ocs:
                self._add_oc(o)
        finally:
            self._loading_entries = False

    def artist_entries(self) -> list[ArtistEntry]:
        return [b.entry() for b in self._artist_banners]

    def oc_entries(self) -> list[OCEntry]:
        return [b.entry() for b in self._oc_banners]

    def update_oc_entry(self, index: int, entry: OCEntry) -> None:
        entries = self.oc_entries()
        if not 0 <= index < len(entries):
            return
        entries[index] = entry
        self.set_entries(self.artist_entries(), entries)
        self.changed.emit()

    def set_oc_enabled(self, index: int, enabled: bool) -> None:
        entries = self.oc_entries()
        if not 0 <= index < len(entries):
            return
        entries[index].enabled = enabled
        self.set_entries(self.artist_entries(), entries)
        self.changed.emit()
