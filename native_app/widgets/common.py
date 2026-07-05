from __future__ import annotations

from PyQt6.QtCore import QPoint, QRect, QRectF, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QMouseEvent, QPainter
from PyQt6.QtWidgets import (
    QCheckBox,
    QLabel,
    QPushButton,
    QSlider,
    QStyle,
    QStyleOptionSlider,
    QWidget,
)

from ..icons import paint_rounded_surface, to_qcolor
from ..theme import current_palette, is_theme_light
from ..ui_tokens import RAD_SM, _dp, _rad


def compute_resized_rect(
    origin: QRect,
    direction: str,
    delta: QPoint,
    bounds: QRect,
    min_width: int,
    min_height: int,
) -> QRect:
    """Compute a new rectangle after a directional resize, clamped to bounds and minimum size."""
    left = origin.left()
    top = origin.top()
    right = origin.right()
    bottom = origin.bottom()

    if 'left' in direction:
        left += delta.x()
    if 'right' in direction:
        right += delta.x()
    if 'top' in direction:
        top += delta.y()
    if 'bottom' in direction:
        bottom += delta.y()

    if 'left' in direction:
        left = min(left, right - min_width + 1)
    elif 'right' in direction:
        right = max(right, left + min_width - 1)

    if 'top' in direction:
        top = min(top, bottom - min_height + 1)
    elif 'bottom' in direction:
        bottom = max(bottom, top + min_height - 1)

    if bounds.isValid():
        if 'left' in direction:
            left = max(bounds.left(), left)
            if right - left + 1 < min_width:
                left = max(bounds.left(), right - min_width + 1)
        elif 'right' in direction:
            right = min(bounds.right(), right)
            if right - left + 1 < min_width:
                right = min(bounds.right(), left + min_width - 1)

        if 'top' in direction:
            top = max(bounds.top(), top)
            if bottom - top + 1 < min_height:
                top = max(bounds.top(), bottom - min_height + 1)
        elif 'bottom' in direction:
            bottom = min(bounds.bottom(), bottom)
            if bottom - top + 1 < min_height:
                bottom = min(bounds.bottom(), top + min_height - 1)

    return QRect(left, top, right - left + 1, bottom - top + 1)


class ToggleSwitch(QCheckBox):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedSize(_dp(36), _dp(18))

    def paintEvent(self, _event: object) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        light = is_theme_light()
        if self.isChecked():
            track_color = QColor(80, 100, 180, 50) if light else QColor(100, 120, 220, 70)
            knob_color = QColor(80, 90, 160) if light else QColor(122, 122, 204)
        else:
            track_color = QColor(0, 0, 0, 18) if light else QColor(255, 255, 255, 18)
            knob_color = QColor(160, 160, 165) if light else QColor(74, 74, 106)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(track_color)
        painter.drawRoundedRect(self.rect(), 9, 9)
        x = 20 if self.isChecked() else 2
        painter.setBrush(knob_color)
        painter.drawEllipse(x, 2, 14, 14)
        painter.end()

    def hitButton(self, pos) -> bool:
        return self.rect().contains(pos)


class HoverPillButton(QPushButton):
    """Titlebar-style pill button (grip ⠿ / pin / × / resize ◢): the pill
    background is painted here with QPainter antialiasing — QSS border-radius
    corners are not antialiased. QSS for these buttons must keep
    `background: transparent`; the style pass then draws only text/icon on top
    of the self-painted pill."""

    def __init__(self, text: str = "", parent=None, *, radius_token: int = RAD_SM) -> None:
        super().__init__(text, parent)
        self._radius_token = radius_token
        self._pill_normal: str | None = None
        self._pill_hover: str | None = 'hover_bg_strong'
        self._pill_disabled: str | None = None
        self._pill_active: str | None = None
        self._pill_border: str | None = None
        self._pill_border_hover: str | None = None
        self._pill_border_disabled: str | None = None
        self._pill_border_active: str | None = None

    def set_pill_colors(self, *, normal: str | None = None,
                        hover: str | None = 'hover_bg_strong',
                        disabled: str | None = None,
                        active: str | None = None,
                        border: str | None = None,
                        border_hover: str | None = None,
                        border_disabled: str | None = None,
                        border_active: str | None = None) -> None:
        """Pill fills/borders as palette KEYS (resolved at paint time so theme
        swaps stay live). The `active` fill is used when the button's
        property('active') == 'true' (toolbar toggle state). Unset borders fall
        back to `border`."""
        self._pill_normal = normal
        self._pill_hover = hover
        self._pill_disabled = disabled
        self._pill_active = active
        self._pill_border = border
        self._pill_border_hover = border_hover or border
        self._pill_border_disabled = border_disabled or border
        self._pill_border_active = border_active or border
        self.update()

    def enterEvent(self, event) -> None:
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        self.update()
        super().leaveEvent(event)

    def paintEvent(self, event) -> None:
        active = self.property('active')
        is_active = (active is True or active == 'true'
                     or (self.isCheckable() and self.isChecked()))
        if not self.isEnabled():
            bg_key, border_key = self._pill_disabled, self._pill_border_disabled
        elif self._pill_active is not None and is_active:
            bg_key, border_key = self._pill_active, self._pill_border_active
        elif self.underMouse():
            bg_key, border_key = self._pill_hover, self._pill_border_hover
        else:
            bg_key, border_key = self._pill_normal, self._pill_border
        if bg_key or border_key:
            pal = current_palette()
            painter = QPainter(self)
            paint_rounded_surface(painter, self.rect(), _rad(self._radius_token),
                                  bg=pal[bg_key] if bg_key else None,
                                  border=pal[border_key] if border_key else None)
            painter.end()
        super().paintEvent(event)


class DashedCircleButton(QPushButton):
    """Small circular “add” chip with an antialiased dashed outline — a QSS
    `border: dashed` + full border-radius circle rasterises with heavy
    stair-stepping. QSS keeps `background: transparent; border: none` and only
    styles the glyph colour."""

    def __init__(self, text: str = "+", parent=None) -> None:
        super().__init__(text, parent)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def enterEvent(self, event) -> None:
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        self.update()
        super().leaveEvent(event)

    def paintEvent(self, event) -> None:
        pal = current_palette()
        hovered = self.isEnabled() and self.underMouse()
        painter = QPainter(self)
        paint_rounded_surface(
            painter, self.rect(), (min(self.width(), self.height()) - 1) / 2.0,
            bg=pal['accent_sub'] if hovered else None,
            border=pal['accent_hover'] if hovered else pal['line_strong'],
            dashed=True,
        )
        painter.end()
        super().paintEvent(event)


class DashedRectButton(QPushButton):
    """Rounded-rect button with an antialiased dashed outline — the shared
    replacement for every QSS `border: 1px dashed …; border-radius: …` control
    (ghost/add buttons, image-select drop pads). Qt's stylesheet engine draws
    those dashed rounded corners with heavy stair-stepping. The fill/border are
    self-painted here; QSS on the widget must keep `background: transparent;
    border: none` and only set glyph colour/padding. Fills/borders are palette
    KEYS resolved at paint time (theme swaps stay live)."""

    def __init__(self, text: str = "", parent=None, *, radius_token: int = RAD_SM,
                 border: str = 'line', border_hover: str = 'line_strong',
                 bg: str | None = None, bg_hover: str | None = None,
                 border_w: float = 1.0) -> None:
        super().__init__(text, parent)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._radius_token = radius_token
        self._border = border
        self._border_hover = border_hover
        self._bg = bg
        self._bg_hover = bg_hover
        self._border_w = border_w

    def set_dashed_colors(self, *, border: str | None = None,
                          border_hover: str | None = None,
                          bg: str | None = None, bg_hover: str | None = None) -> None:
        if border is not None:
            self._border = border
        if border_hover is not None:
            self._border_hover = border_hover
        self._bg = bg
        self._bg_hover = bg_hover
        self.update()

    def enterEvent(self, event) -> None:
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        self.update()
        super().leaveEvent(event)

    def paintEvent(self, event) -> None:
        pal = current_palette()
        hovered = self.isEnabled() and self.underMouse()
        bg_key = (self._bg_hover if hovered else self._bg) or self._bg
        border_key = self._border_hover if hovered else self._border
        painter = QPainter(self)
        paint_rounded_surface(
            painter, self.rect(), _rad(self._radius_token),
            bg=pal[bg_key] if bg_key else None,
            border=pal[border_key],
            border_w=self._border_w, dashed=True,
        )
        painter.end()
        super().paintEvent(event)


class RoundedPanel(QWidget):
    """Plain rounded surface (fill + 1px border) self-painted with
    antialiasing — for overlay panels whose QSS border-radius would alias
    (e.g. the dock drop-preview band). Colours are palette KEYS resolved at
    paint time."""

    def __init__(self, parent=None, *, bg: str, border: str,
                 radius_token: int = RAD_SM) -> None:
        super().__init__(parent)
        self._panel_bg = bg
        self._panel_border = border
        self._radius_token = radius_token

    def paintEvent(self, event) -> None:
        pal = current_palette()
        painter = QPainter(self)
        paint_rounded_surface(painter, self.rect(), _rad(self._radius_token),
                              bg=pal[self._panel_bg], border=pal[self._panel_border])
        painter.end()


class PillLabel(QLabel):
    """Capsule-shaped status label (radius == half height): the fill and
    border are self-painted with antialiasing — a QSS border-radius capsule
    rasterises with stair-stepped arcs. QSS on the label keeps
    `background: transparent; border: none` and only sets text colour,
    padding and font. Colours are palette KEYS resolved at paint time."""

    def __init__(self, text: str = "", parent=None, *,
                 bg: str = 'bg_menu', border: str = 'line_hover') -> None:
        super().__init__(text, parent)
        self._pill_bg = bg
        self._pill_border = border

    def paintEvent(self, event) -> None:
        pal = current_palette()
        painter = QPainter(self)
        paint_rounded_surface(painter, self.rect(), (self.height() - 1) / 2.0,
                              bg=pal[self._pill_bg], border=pal[self._pill_border])
        painter.end()
        super().paintEvent(event)


class RoundHandleSlider(QSlider):
    """QSlider whose knob is a self-painted antialiased circle — QSS
    border-radius handles rasterise the circle with visible stair-stepping.
    The groove/sub-page stay QSS (2px, no visible aliasing); the widget's QSS
    must set the handle `background: transparent` while KEEPING its
    width/height/margin so subControlRect still lays the knob out — only this
    crisp circle then shows. Colours are palette KEYS resolved at paint time."""

    def __init__(self, orientation, parent: QWidget | None = None, *,
                 handle_key: str = 'accent_handle',
                 handle_hover_key: str = 'accent_text') -> None:
        super().__init__(orientation, parent)
        self._handle_key = handle_key
        self._handle_hover_key = handle_hover_key

    def paintEvent(self, event) -> None:
        super().paintEvent(event)  # groove + sub-page (QSS); handle transparent
        opt = QStyleOptionSlider()
        self.initStyleOption(opt)
        rect = self.style().subControlRect(
            QStyle.ComplexControl.CC_Slider, opt,
            QStyle.SubControl.SC_SliderHandle, self,
        )
        if rect.isEmpty():
            return
        pal = current_palette()
        key = self._handle_hover_key if (self.isEnabled() and self.underMouse()) else self._handle_key
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(to_qcolor(pal[key]))
        d = float(min(rect.width(), rect.height()))
        c = rect.center()
        painter.drawEllipse(QRectF(c.x() + 0.5 - d / 2.0, c.y() + 0.5 - d / 2.0, d, d))
        painter.end()

    def enterEvent(self, event) -> None:
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        self.update()
        super().leaveEvent(event)


class DragHandleLabel(QLabel):
    drag_started = pyqtSignal()

    def __init__(self, text: str = "≡", parent=None) -> None:
        super().__init__(text, parent)
        self.setCursor(Qt.CursorShape.OpenHandCursor)
        self._press_pos = QPoint()

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._press_pos = event.pos()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if event.buttons() & Qt.MouseButton.LeftButton:
            if (event.pos() - self._press_pos).manhattanLength() >= 6:
                self.drag_started.emit()
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        self.setCursor(Qt.CursorShape.OpenHandCursor)
        super().mouseReleaseEvent(event)
