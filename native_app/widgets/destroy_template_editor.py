"""Destroy Template Editor — dialog for managing metadata destroy text presets."""
from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QTextEdit,
    QVBoxLayout,
)

from ..i18n import Translator
from ..qss_surfaces import surface_decl
from ..theme import _fs, current_palette
from ..ui_tokens import RAD_SM, _dp, _rad
from .common import HoverPillButton
from .text_context_menu import install_localized_context_menus


class DestroyTemplateEditor(QDialog):
    """Dialog for editing destroy text presets, similar to prompt manager style."""

    def __init__(self, templates: list[dict], active_index: int,
                 translator: Translator, parent=None, tag_dictionary=None):
        super().__init__(parent)
        self._t = translator
        self._templates = [dict(t) for t in templates]  # deep copy
        self._tag_dictionary = tag_dictionary or getattr(parent, "_tag_dictionary", None)

        p = current_palette()
        self.setWindowTitle(translator.t("metadata_edit_preset"))
        self.setMinimumSize(_dp(500), _dp(400))
        # System-titlebar QDialog: no radius on the dialog itself. Inner
        # controls below use AA 9-patch surfaces / self-painted pills instead
        # of QSS border-radius (Qt rasterises those corners without
        # antialiasing). The 9-patch border-width is radius+1 (s) and eats the
        # content box, so paddings compensate: new = old padding + old border
        # - s, floored at 0.
        self.setStyleSheet(f"background: {p['bg']}; color: {p['text']};")
        r = _rad(RAD_SM)
        s = r + 1

        root = QHBoxLayout(self)
        root.setSpacing(_dp(12))
        root.setContentsMargins(_dp(16), _dp(16), _dp(16), _dp(16))

        # ── Left: template list ──
        left = QVBoxLayout()
        left.setSpacing(_dp(6))

        left_header = QHBoxLayout()
        left_label = QLabel(translator.t("metadata_edit_preset"), self)
        left_label.setStyleSheet(f"font-size: {_fs('fs_12')}; font-weight: bold;")
        left_header.addWidget(left_label)
        left_header.addStretch()

        # Accent pill self-painted with AA (palette keys, live on theme swap);
        # QSS keeps only glyph colour/font. Border was already none.
        add_btn = HoverPillButton("+", self)
        add_btn.setFixedSize(_dp(24), _dp(24))
        add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        add_btn.set_pill_colors(normal='accent', hover='accent_hover')
        add_btn.setStyleSheet(
            f"color: {p['accent_text']}; background: transparent; border: none; "
            f"font-size: {_fs('fs_12')}; font-weight: bold;"
        )
        add_btn.clicked.connect(self._add_template)
        left_header.addWidget(add_btn)

        left.addLayout(left_header)

        # List body + item highlight as AA 9-patch surfaces (same pattern as
        # theme.control_surfaces_qss QMenu::item): the normal item carries a
        # transparent surface so its border-width matches the selected state
        # and the text doesn't shift on selection.
        self._list = QListWidget(self)
        self._list.setStyleSheet(
            f"QListWidget {{ {surface_decl(r, p['bg_input'], p['line'])} "
            f"font-size: {_fs('fs_10')}; padding: {max(0, 1 - s)}px; }}"
            f"QListWidget::item {{ {surface_decl(r, 'rgba(0, 0, 0, 0)')} "
            f"padding: {max(0, 6 - s)}px {max(0, 8 - s)}px; }}"
            f"QListWidget::item:selected {{ {surface_decl(r, p['accent'])} "
            f"color: {p['accent_text']}; }}"
        )
        self._list.currentRowChanged.connect(self._on_select)
        left.addWidget(self._list, 1)

        # Static fill: hover repeats the normal key (no hover rule existed).
        del_btn = HoverPillButton(translator.t("delete"), self)
        del_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        del_btn.set_pill_colors(normal='delete_hover', hover='delete_hover')
        del_btn.setStyleSheet(
            f"color: {p['text']}; background: transparent; border: none; "
            f"padding: 4px 12px; font-size: {_fs('fs_10')};"
        )
        del_btn.clicked.connect(self._delete_template)
        left.addWidget(del_btn)

        root.addLayout(left, 1)

        # ── Right: edit fields ──
        right = QVBoxLayout()
        right.setSpacing(_dp(8))

        name_label = QLabel(translator.t("metadata_template_name"), self)
        name_label.setStyleSheet(f"font-size: {_fs('fs_10')}; color: {p['text_dim']};")
        right.addWidget(name_label)

        self._name_edit = QLineEdit(self)
        self._name_edit.setStyleSheet(
            f"QLineEdit {{ {surface_decl(r, p['bg_input'], p['line'])} "
            f"color: {p['text']}; padding: {max(0, 4 + 1 - s)}px {max(0, 8 + 1 - s)}px; "
            f"font-size: {_fs('fs_11')}; }}"
        )
        self._name_edit.textChanged.connect(self._on_name_changed)
        right.addWidget(self._name_edit)

        text_label = QLabel(translator.t("metadata_destroy_fill_text"), self)
        text_label.setStyleSheet(f"font-size: {_fs('fs_10')}; color: {p['text_dim']};")
        right.addWidget(text_label)

        # QTextEdit-scoped so the editor's scrollbars keep global styling.
        self._text_edit = QTextEdit(self)
        self._text_edit.setStyleSheet(
            f"QTextEdit {{ {surface_decl(r, p['bg_input'], p['line'])} "
            f"color: {p['text']}; padding: {max(0, 6 + 1 - s)}px {max(0, 8 + 1 - s)}px; "
            f"font-size: {_fs('fs_10')}; }}"
        )
        self._text_edit.textChanged.connect(self._on_text_changed)
        right.addWidget(self._text_edit, 1)

        # Save / Cancel buttons
        btn_row = QHBoxLayout()
        btn_row.addStretch()

        # Outline pill: fill-less, palette-key border, static (hover=None keeps
        # the normal look); the dropped 1px QSS border folds into the padding.
        cancel_btn = HoverPillButton(translator.t("cancel"), self)
        cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        cancel_btn.set_pill_colors(normal=None, hover=None, border='line')
        cancel_btn.setStyleSheet(
            f"color: {p['text_dim']}; background: transparent; border: none; "
            f"padding: 7px 17px; font-size: {_fs('fs_10')};"
        )
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)

        save_btn = HoverPillButton(translator.t("ok"), self)
        save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        save_btn.set_pill_colors(normal='accent', hover='accent_hover')
        save_btn.setStyleSheet(
            f"color: {p['accent_text']}; background: transparent; border: none; "
            f"padding: 6px 20px; font-size: {_fs('fs_11')}; font-weight: bold;"
        )
        save_btn.clicked.connect(self.accept)
        btn_row.addWidget(save_btn)

        right.addLayout(btn_row)
        root.addLayout(right, 2)

        # Populate
        self._populating = False
        self._populate_list()
        if 0 <= active_index < len(self._templates):
            self._list.setCurrentRow(active_index)
        install_localized_context_menus(self, translator)
        if self._tag_dictionary is not None:
            from .tag_completer import install_completer_recursive
            install_completer_recursive(self, self._tag_dictionary)

    def _populate_list(self):
        self._populating = True
        self._list.clear()
        for t in self._templates:
            self._list.addItem(t["name"])
        self._populating = False

    def _on_select(self, row: int):
        if row < 0 or row >= len(self._templates):
            self._name_edit.clear()
            self._text_edit.clear()
            return
        t = self._templates[row]
        self._populating = True
        self._name_edit.setText(t["name"])
        self._text_edit.setPlainText(t["text"])
        self._populating = False

    def _on_name_changed(self, text: str):
        if self._populating:
            return
        row = self._list.currentRow()
        if 0 <= row < len(self._templates):
            self._templates[row]["name"] = text
            self._list.item(row).setText(text)

    def _on_text_changed(self):
        if self._populating:
            return
        row = self._list.currentRow()
        if 0 <= row < len(self._templates):
            self._templates[row]["text"] = self._text_edit.toPlainText()

    def _add_template(self):
        new = {"name": f"新预设 {len(self._templates) + 1}", "text": ""}
        self._templates.append(new)
        self._list.addItem(new["name"])
        self._list.setCurrentRow(len(self._templates) - 1)

    def _delete_template(self):
        row = self._list.currentRow()
        if row < 0 or len(self._templates) <= 1:
            return
        self._templates.pop(row)
        self._populate_list()
        self._list.setCurrentRow(min(row, len(self._templates) - 1))

    def templates(self) -> list[dict]:
        return self._templates
