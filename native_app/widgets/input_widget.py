from __future__ import annotations

from PyQt6.QtCore import QEvent, Qt, pyqtSignal
from PyQt6.QtGui import QKeyEvent, QPainter, QTextCursor
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QTextEdit, QVBoxLayout, QWidget

from ..i18n import Translator
from ..icons import paint_rounded_surface
from ..models import SEND_MODE_CTRL_ENTER, SEND_MODE_ENTER
from ..theme import _fs, current_palette
from ..ui_tokens import CLS_FIELD_LABEL, CLS_INPUT_EDITOR, RAD_SM, WB_INSET, _dp, _rad
from .common import HoverPillButton


class _RoundedInputFrame(QWidget):
    """Workbench input container: fill + border + rounded corners are
    self-painted with antialiasing (QSS border-radius corners are not). Twin of
    output_widget._RoundedOutputFrame. The editor sits inside on layout margins
    that replace its old QSS padding, so it never covers the border."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.focused = False

    def paintEvent(self, event) -> None:
        pal = current_palette()
        painter = QPainter(self)
        paint_rounded_surface(
            painter, self.rect(), _rad(RAD_SM), bg=pal['bg_input'],
            border=pal['accent_hover'] if self.focused else pal['line'],
        )
        painter.end()


class InputWidget(QWidget):
    send_requested = pyqtSignal()

    def __init__(self, translator: Translator, parent=None) -> None:
        super().__init__(parent)
        self._translator = translator
        self._sending = False
        self._send_mode = SEND_MODE_ENTER
        self._tag_dictionary = None

        root = QVBoxLayout(self)
        # Side inset matches the workbench output frame (output_widget.py's
        # _RoundedOutputFrame insets itself by the same 16), so the editor box
        # and the TAG box line up instead of the editor running edge to edge.
        root.setContentsMargins(_dp(WB_INSET), 0, _dp(WB_INSET), 0)
        root.setSpacing(0)

        self.editor_frame = _RoundedInputFrame(self)
        frame_layout = QVBoxLayout(self.editor_frame)
        frame_layout.setContentsMargins(_dp(12), _dp(10), _dp(12), _dp(10))
        frame_layout.setSpacing(0)
        self.editor = QTextEdit(self.editor_frame)
        self.editor.setProperty('class', CLS_INPUT_EDITOR)
        self.editor.setObjectName("WorkbenchInputEditor")
        self.editor.installEventFilter(self)
        frame_layout.addWidget(self.editor, 1)
        root.addWidget(self.editor_frame, 1)

        self.action_bar = QWidget(self)
        self.action_bar.setObjectName('WorkbenchFooter')
        footer = QHBoxLayout(self.action_bar)
        # Horizontal inset already supplied by root's margins.
        footer.setContentsMargins(0, _dp(10), 0, _dp(12))
        footer.setSpacing(_dp(8))

        self.token_label = QLabel(self.action_bar)
        self.token_label.setObjectName('TokenLabel')
        self.token_label.setProperty('class', CLS_FIELD_LABEL)
        footer.addWidget(self.token_label)
        footer.addStretch(1)

        # Surfaces self-painted by HoverPillButton (QSS border-radius corners
        # alias); the QSS below only colours the glyphs.
        self.summary_button = HoverPillButton("", self.action_bar)
        self.summary_button.setObjectName('WorkbenchFooterButton')
        self.summary_button.setFixedSize(_dp(30), _dp(28))
        self.summary_button.set_pill_colors(
            normal='bg_surface', hover='hover_bg_strong', disabled='disabled_bg',
            border='line_hover',
        )
        footer.addWidget(self.summary_button)

        self.send_button = HoverPillButton("", self.action_bar)
        self.send_button.setObjectName('WorkbenchPrimaryButton')
        self.send_button.setFixedSize(_dp(30), _dp(28))
        self.send_button.set_pill_colors(
            normal='accent', hover='accent_hover', border='accent_hover',
        )
        footer.addWidget(self.send_button)

        root.addWidget(self.action_bar, 0)
        self.retranslate_ui()
        self.apply_workbench_style()

    def retranslate_ui(self) -> None:
        self.editor.setPlaceholderText(self._translator.t('input_placeholder'))
        self.summary_button.setText('Σ')
        self.summary_button.setToolTip(self._translator.t('summary'))
        self.send_button.setText('■' if self._sending else '➤')
        send_tooltip = self._translator.t('stop') if self._sending else self._translator.t('send')
        self.send_button.setToolTip(f"{send_tooltip} ({self.send_shortcut_label()})" if not self._sending else send_tooltip)
        if not self.token_label.text():
            self.token_label.setText(f"~0 / 2048 {self._translator.t('token_count')}")
        self.apply_workbench_style()

    def set_sending(self, sending: bool) -> None:
        self._sending = sending
        self.summary_button.setEnabled(not sending)
        self.retranslate_ui()

    def set_send_mode(self, mode: str) -> None:
        self._send_mode = mode if mode in {SEND_MODE_ENTER, SEND_MODE_CTRL_ENTER} else SEND_MODE_ENTER
        self.retranslate_ui()

    def send_shortcut_label(self) -> str:
        return "Enter" if self._send_mode == SEND_MODE_ENTER else "Ctrl+Enter"

    def install_send_key_handler(self) -> None:
        original_key_press = self.editor.keyPressEvent

        def _key_press(event: QKeyEvent) -> None:
            if self._sending:
                if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
                    self.send_requested.emit()
                    return
                original_key_press(event)
                return

            popup = getattr(self.editor, "_tag_completer_popup", None)
            if popup is not None and popup.isVisible():
                original_key_press(event)
                return

            if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
                wants_ctrl = bool(event.modifiers() & Qt.KeyboardModifier.ControlModifier)
                wants_shift = bool(event.modifiers() & Qt.KeyboardModifier.ShiftModifier)
                if self._send_mode == SEND_MODE_ENTER:
                    if wants_shift:
                        original_key_press(event)
                    else:
                        self.send_requested.emit()
                    return
                if wants_ctrl:
                    self.send_requested.emit()
                    return
            original_key_press(event)

        self.editor.keyPressEvent = _key_press

    def set_tag_dictionary(self, dictionary) -> None:
        from .tag_completer import install_completer_recursive
        self._tag_dictionary = dictionary
        install_completer_recursive(self, dictionary)

    def set_text(self, value: str) -> None:
        self.editor.blockSignals(True)
        self.editor.setPlainText(value)
        self.editor.blockSignals(False)

    def text(self) -> str:
        return self.editor.toPlainText()

    def clear_text(self) -> None:
        self.editor.clear()

    def append_separator(self) -> None:
        current = self.editor.toPlainText()
        suffix = '\n\n---\n'
        if current and not current.endswith(suffix):
            self.editor.moveCursor(QTextCursor.MoveOperation.End)
            self.editor.insertPlainText(suffix)
        elif not current:
            self.editor.setPlainText('---\n')

    def append_text(self, value: str) -> None:
        self.editor.moveCursor(QTextCursor.MoveOperation.End)
        self.editor.insertPlainText(value)
        self.editor.ensureCursorVisible()

    def append_status_line(self, value: str) -> None:
        text = self.editor.toPlainText()
        suffix = value if text.endswith('\n') or not text else f'\n{value}'
        self.append_text(suffix)

    def set_token_estimate(self, estimated_tokens: int, max_tokens: int) -> None:
        self.token_label.setText(f"~{estimated_tokens} / {max_tokens} {self._translator.t('token_count')}")
        ratio = (estimated_tokens / max_tokens) if max_tokens else 0.0
        if ratio > 0.95:
            color = current_palette()["close_hover"]
        elif ratio > 0.8:
            color = current_palette()["accent_handle"]
        else:
            color = None
        p = current_palette()
        self.token_label.setStyleSheet(
            f"color: {color or p['text_muted']}; font-size: {_fs('fs_12')};"
        )

    def eventFilter(self, watched, event) -> bool:
        if watched is self.editor and event.type() in (
                QEvent.Type.FocusIn, QEvent.Type.FocusOut):
            # Repaint the self-drawn surface for its focus border.
            self.editor_frame.focused = event.type() == QEvent.Type.FocusIn
            self.editor_frame.update()
        return super().eventFilter(watched, event)

    def apply_workbench_style(self) -> None:
        p = current_palette()
        self.setStyleSheet(
            # Transparent: the workbench surface below already fills this area,
            # and an opaque box here would square off its rounded bottom corners.
            f"InputWidget {{ background: transparent; }}"
            # Surface self-painted by _RoundedInputFrame; the old padding is now
            # that frame's layout margins, so the editor itself stays bare.
            f"QTextEdit#WorkbenchInputEditor {{ background: transparent; border: none; padding: 0px; "
            f"color: {p['text']}; "
            f"selection-background-color: {p['selection_bg']}; "
            f"font-size: {_fs('fs_12')}; }}"
            f"QWidget#WorkbenchFooter {{ background: transparent; }}"
            f"QLabel#TokenLabel {{ color: {p['text_muted']}; font-size: {_fs('fs_12')}; }}"
            f"QPushButton#WorkbenchFooterButton {{ background: transparent; color: {p['text']}; border: none; }}"
            f"QPushButton#WorkbenchFooterButton:disabled {{ color: {p['disabled_text']}; }}"
            f"QPushButton#WorkbenchPrimaryButton {{ background: transparent; color: {p['accent_text']}; border: none; }}"
        )
