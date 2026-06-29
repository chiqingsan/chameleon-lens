"""自绘 PyQt 控件、预览组件和颜色选择面板。"""
from PyQt5.QtWidgets import (
    QCheckBox, QDialog, QFrame, QGridLayout, QHBoxLayout,
    QLabel, QPushButton, QSlider, QVBoxLayout, QWidget,
)
from PyQt5.QtCore import Qt, QPoint, QPointF, QRectF, QPropertyAnimation, QEasingCurve, pyqtProperty, pyqtSignal
from PyQt5.QtGui import QPainter, QPen, QColor, QFont, QPixmap

from ..config import Config
from ..paths import APP_ICON_PATH, APP_LOGO_PATH


# ---------------------------------------------------------------------------
# Menu window
# ---------------------------------------------------------------------------
class ToggleSwitch(QCheckBox):
    def __init__(self, checked=False, parent=None):
        super().__init__(parent)
        self._thumb_pos = 1.0 if checked else 0.0
        self.setChecked(checked)
        self._anim = QPropertyAnimation(self, b"thumbPos", self)
        self._anim.setDuration(150)
        self._anim.setEasingCurve(QEasingCurve.OutCubic)
        self.stateChanged.connect(self._animate_thumb)
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedSize(48, 28)

    def get_thumb_pos(self):
        return self._thumb_pos

    def set_thumb_pos(self, value):
        self._thumb_pos = max(0.0, min(1.0, float(value)))
        self.update()

    thumbPos = pyqtProperty(float, fget=get_thumb_pos, fset=set_thumb_pos)

    def sync_checked(self, checked, animate=True):
        """外部配置同步时不触发业务信号，但保留开关滑块的视觉反馈。"""
        checked = bool(checked)
        target = 1.0 if checked else 0.0
        if self.isChecked() == checked and abs(self._thumb_pos - target) < 0.001:
            return
        self._anim.stop()
        was_blocked = self.blockSignals(True)
        super().setChecked(checked)
        self.blockSignals(was_blocked)
        if animate:
            self._anim.setStartValue(self._thumb_pos)
            self._anim.setEndValue(target)
            self._anim.start()
        else:
            self.set_thumb_pos(target)

    def _animate_thumb(self, state):
        self._anim.stop()
        self._anim.setStartValue(self._thumb_pos)
        self._anim.setEndValue(1.0 if state else 0.0)
        self._anim.start()

    def hitButton(self, pos):
        # Qt 默认复选框只认很小的 indicator 命中区；这里让整个开关都可点击。
        return self.rect().contains(pos)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self.rect().contains(event.pos()):
            self.setChecked(not self.isChecked())
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        enabled = self.isEnabled()
        track = QColor(94, 234, 212, 40) if self.isChecked() else QColor(255, 255, 255, 24)
        border = QColor(94, 234, 212, 118) if self.isChecked() else QColor(148, 163, 184, 58)
        knob = QColor("#5eead4") if self.isChecked() else QColor("#8793a4")
        if not enabled:
            track = QColor(255, 255, 255, 10)
            border = QColor(148, 163, 184, 24)
            knob = QColor("#4b5563")
        painter.setPen(QPen(border, 1.4))
        painter.setBrush(track)
        painter.drawRoundedRect(QRectF(1, 1, 46, 26), 13, 13)
        painter.setPen(Qt.NoPen)
        painter.setBrush(knob)
        painter.drawEllipse(QPointF(14 + 20 * self._thumb_pos, 14), 8, 8)


class StatusPill(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.connected = False
        self.text = "未连接 · 等待进程"
        self.setFixedSize(166, 26)

    def set_status(self, connected: bool, text: str):
        self.connected = connected
        self.text = text
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        if self.connected:
            border = QColor(94, 234, 212, 84)
            fill = QColor(94, 234, 212, 24)
            dot = QColor("#5eead4")
            main = QColor("#e6fffb")
        else:
            border = QColor(251, 191, 36, 50)
            fill = QColor(251, 191, 36, 13)
            dot = QColor("#fbbf24")
            main = QColor("#fff7d6")

        painter.setPen(QPen(border, 1.2))
        painter.setBrush(fill)
        painter.drawRoundedRect(QRectF(0.8, 0.8, self.width() - 1.6, self.height() - 1.6), 13, 13)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(dot.red(), dot.green(), dot.blue(), 44))
        painter.drawEllipse(QPointF(16, 13), 5.8, 5.8)
        painter.setBrush(dot)
        painter.drawEllipse(QPointF(16, 13), 3.0, 3.0)

        painter.setFont(QFont("Microsoft YaHei UI", 10, QFont.DemiBold))
        painter.setPen(QPen(main))
        text_rect = QRectF(28, 0, self.width() - 38, self.height())
        safe_text = painter.fontMetrics().elidedText(self.text, Qt.ElideRight, int(text_rect.width()))
        painter.drawText(text_rect, Qt.AlignVCenter | Qt.AlignLeft, safe_text)


class LogoBadge(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        # Logo 本身已经带圆角底板，控件背景必须透明，避免标题栏里出现额外白边。
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_NoSystemBackground)
        self.setAutoFillBackground(False)
        logo_path = APP_LOGO_PATH if APP_LOGO_PATH.exists() else APP_ICON_PATH
        self._pixmap = QPixmap(str(logo_path)) if logo_path.exists() else QPixmap()
        self.setFixedSize(32, 32)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        if not self._pixmap.isNull():
            painter.setRenderHint(QPainter.SmoothPixmapTransform)
            painter.drawPixmap(QRectF(0, 0, 32, 32), self._pixmap, QRectF(self._pixmap.rect()))
            return
        painter.setPen(QPen(QColor(94, 234, 212, 70), 1.1))
        painter.setBrush(QColor(255, 255, 255, 10))
        painter.drawRoundedRect(QRectF(0.8, 0.8, self.width() - 1.6, self.height() - 1.6), 8, 8)
        painter.setFont(QFont("Microsoft YaHei UI", 9, QFont.Bold))
        painter.setPen(QPen(QColor("#5eead4")))
        painter.drawText(self.rect(), Qt.AlignCenter, "CL")


def _ease_mix(start, end, progress):
    return int(round(start + (end - start) * max(0.0, min(1.0, progress))))


def _draw_hud_canvas(painter, scene, active=True, grid=True, scan=True):
    painter.save()
    grid_alpha = 18 if active else 9
    accent_alpha = 34 if active else 14
    painter.setBrush(Qt.NoBrush)
    if grid:
        painter.setPen(QPen(QColor(148, 163, 184, grid_alpha), 1))

        x = scene.left() + 24
        while x < scene.right() - 8:
            painter.drawLine(QPointF(x, scene.top() + 10), QPointF(x, scene.bottom() - 10))
            x += 24

        y = scene.top() + 24
        while y < scene.bottom() - 8:
            painter.drawLine(QPointF(scene.left() + 10, y), QPointF(scene.right() - 10, y))
            y += 24

    if scan:
        painter.setPen(QPen(QColor(94, 234, 212, accent_alpha), 1))
        scan_y = scene.top() + 58
        painter.drawLine(QPointF(scene.left() + 12, scan_y), QPointF(scene.right() - 12, scan_y))

    corner_len = 20
    painter.setPen(QPen(QColor(94, 234, 212, accent_alpha + 10), 1.2))
    for x1, y1, x2, y2 in [
        (scene.left() + corner_len, scene.top(), scene.left(), scene.top() + corner_len),
        (scene.right() - corner_len, scene.top(), scene.right(), scene.top() + corner_len),
        (scene.left(), scene.bottom() - corner_len, scene.left() + corner_len, scene.bottom()),
        (scene.right(), scene.bottom() - corner_len, scene.right() - corner_len, scene.bottom()),
    ]:
        painter.drawLine(QPointF(x1, y1), QPointF(x2, y2))
    painter.restore()


def _draw_target_view(painter, config: Config, width, footer_text):
    painter.setPen(QPen(QColor("#f4f7fb")))
    painter.setFont(QFont("Microsoft YaHei UI", 11, QFont.Bold))
    painter.drawText(2, 20, "目标视图")

    scene = QRectF(2, 36, width - 4, 204)
    origin = QPointF(scene.center().x(), scene.bottom() - 8)
    hunter = QColor(*config.hunter_color)
    survivor = QColor(*config.survivor_color)
    local = QColor(*config.local_color)
    dot_r = max(5, min(config.dot_radius, 16))
    targets = []
    if config.show_hunter_esp:
        targets.append((QPointF(scene.left() + 46, scene.top() + 58), hunter, "猎人", "18m", False))
    targets.append((QPointF(scene.right() - 70, scene.top() + 92), survivor, "躲藏者", "31m", False))
    if config.show_local:
        targets.append((QPointF(scene.center().x() - 16, scene.top() + 144), local, "自己", "0m", True))

    if config.esp_enabled:
        for point, color, name, distance_text, is_local in targets:
            draw_ray = config.snap_lines and (not is_local or config.show_local_snap_line)
            if draw_ray:
                painter.setPen(QPen(QColor(color.red(), color.green(), color.blue(), 165), 1))
                painter.drawLine(origin, point)

            if config.box_esp:
                painter.setPen(Qt.NoPen)
                painter.setBrush(QColor(color.red(), color.green(), color.blue(), 46))
                painter.drawEllipse(point, dot_r + 7, dot_r + 7)
                painter.setBrush(color)
                painter.drawEllipse(point, dot_r, dot_r)

            label_parts = []
            if config.show_names:
                label_parts.append(name)
            if config.show_distance:
                label_parts.append(distance_text)
            if label_parts:
                label_text = " · ".join(label_parts)
                painter.setPen(QPen(QColor("#dbeafe")))
                painter.setFont(QFont("Microsoft YaHei UI", 9, QFont.DemiBold))
                # 预览面板宽度固定，标签靠近右边缘时自动改到点位左侧，避免被裁切。
                label_width = painter.fontMetrics().horizontalAdvance(label_text)
                label_x = point.x() + dot_r + 8
                if label_x + label_width > scene.right() - 6:
                    label_x = point.x() - dot_r - 8 - label_width
                label_x = max(scene.left() + 6, label_x)
                painter.drawText(int(label_x), int(point.y() + 4), label_text)

    painter.setPen(QPen(QColor(148, 163, 184, 28), 1))
    painter.drawLine(QPointF(scene.left() + 18, scene.bottom()), QPointF(scene.right() - 18, scene.bottom()))
    painter.setPen(QPen(QColor("#a5b1c2")))
    painter.setFont(QFont("Microsoft YaHei UI", 10))
    painter.drawText(2, 266, footer_text)


class AnimatedPaintButton(QPushButton):
    """自绘控件的轻量 hover 动画基类，避免 QSS 边框带来的圆角毛刺。"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._hover_progress = 0.0
        self._hover_anim = QPropertyAnimation(self, b"hoverProgress", self)
        self._hover_anim.setDuration(130)
        self._hover_anim.setEasingCurve(QEasingCurve.OutCubic)
        self.setAttribute(Qt.WA_Hover, True)

    def get_hover_progress(self):
        return self._hover_progress

    def set_hover_progress(self, value):
        self._hover_progress = max(0.0, min(1.0, float(value)))
        self.update()

    hoverProgress = pyqtProperty(float, fget=get_hover_progress, fset=set_hover_progress)

    def _animate_hover(self, value):
        self._hover_anim.stop()
        self._hover_anim.setStartValue(self._hover_progress)
        self._hover_anim.setEndValue(value)
        self._hover_anim.start()

    def enterEvent(self, event):
        self._animate_hover(1.0)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._animate_hover(0.0)
        super().leaveEvent(event)


class TabButton(AnimatedPaintButton):
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self._active = False
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedSize(96, 34)

    def set_active(self, active):
        if self._active != active:
            self._active = active
            self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        hover = self.hoverProgress
        fill = QColor(21, 30, 41, 235) if self._active else QColor(255, 255, 255, _ease_mix(8, 14, hover))
        border = QColor(94, 234, 212, 76) if self._active else QColor(148, 163, 184, _ease_mix(22, 40, hover))
        if not self._active and hover > 0:
            border = QColor(94, 234, 212, _ease_mix(34, 62, hover))

        painter.setPen(QPen(border, 1.2))
        painter.setBrush(fill)
        painter.drawRoundedRect(QRectF(0.8, 0.8, self.width() - 1.6, self.height() - 1.6), 8, 8)

        painter.setFont(QFont("Microsoft YaHei UI", 11, QFont.Bold if self._active else QFont.Normal))
        painter.setPen(QPen(QColor("#f4f7fb") if self._active else QColor("#a5b1c2")))
        painter.drawText(self.rect(), Qt.AlignCenter, self.text())


class SmoothButton(AnimatedPaintButton):
    def __init__(self, text, primary=False, parent=None):
        super().__init__(text, parent)
        self.primary = primary
        self.setCursor(Qt.PointingHandCursor)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        hover = self.hoverProgress
        down_boost = 10 if self.isDown() else 0
        if self.primary:
            fill = QColor(94, 234, 212, _ease_mix(28, 48, hover) + down_boost)
            border = QColor(94, 234, 212, _ease_mix(78, 112, hover))
            text_color = QColor("#5eead4")
        else:
            fill = QColor(255, 255, 255, _ease_mix(8, 16, hover) + down_boost)
            border = QColor(148, 163, 184, _ease_mix(18, 44, hover))
            text_color = QColor("#f4f7fb" if hover > 0.45 else "#a5b1c2")

        painter.setPen(QPen(border, 1.1))
        painter.setBrush(fill)
        painter.drawRoundedRect(QRectF(0.8, 0.8, self.width() - 1.6, self.height() - 1.6), 8, 8)
        painter.setFont(QFont("Microsoft YaHei UI", 11, QFont.DemiBold))
        painter.setPen(QPen(text_color))
        painter.drawText(self.rect(), Qt.AlignCenter, self.text())


class HotkeyButton(AnimatedPaintButton):
    capturingChanged = pyqtSignal(bool)

    def __init__(self, text="", parent=None):
        super().__init__("", parent)
        self._text = text
        self._capturing = False
        self.setCursor(Qt.PointingHandCursor)
        self.setFocusPolicy(Qt.StrongFocus)
        self.setFixedSize(112, 34)

    def set_key(self, text):
        self._text = text
        self._capturing = False
        self.capturingChanged.emit(False)
        self.update()

    def key(self):
        return self._text

    def is_capturing(self):
        return self._capturing

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self.rect().contains(event.pos()):
            self._capturing = True
            self.setFocus(Qt.MouseFocusReason)
            self.capturingChanged.emit(True)
            self.update()
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def keyPressEvent(self, event):
        if not self._capturing:
            super().keyPressEvent(event)
            return
        event.accept()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        hover = self.hoverProgress
        active = self._capturing or self.hasFocus()
        border_alpha = 112 if active else _ease_mix(30, 74, hover)
        fill_alpha = 22 if active else _ease_mix(8, 15, hover)
        painter.setPen(QPen(QColor(94, 234, 212, border_alpha), 1.2))
        painter.setBrush(QColor(94, 234, 212, fill_alpha))
        painter.drawRoundedRect(QRectF(0.8, 0.8, self.width() - 1.6, self.height() - 1.6), 8, 8)
        painter.setFont(QFont("Microsoft YaHei UI", 10, QFont.DemiBold))
        painter.setPen(QPen(QColor("#5eead4" if active else "#f4f7fb")))
        label = "按下按键" if self._capturing else (self._text or "未设置")
        painter.drawText(self.rect(), Qt.AlignCenter, label)


class CloseButton(AnimatedPaintButton):
    def __init__(self, parent=None, size=32):
        super().__init__("", parent)
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedSize(size, size)
        self.setToolTip("关闭")

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        hover = self.hoverProgress
        if hover > 0:
            painter.setPen(QPen(QColor(248, 113, 113, _ease_mix(0, 86, hover)), 1.2))
            painter.setBrush(QColor(248, 113, 113, _ease_mix(0, 32, hover)))
            painter.drawRoundedRect(QRectF(0.8, 0.8, self.width() - 1.6, self.height() - 1.6), 8, 8)

        painter.setFont(QFont("Microsoft YaHei UI", 15, QFont.Bold))
        painter.setPen(QPen(QColor("#fecaca") if hover > 0.35 else QColor("#a5b1c2")))
        painter.drawText(self.rect(), Qt.AlignCenter, "×")


class ColorPresetButton(AnimatedPaintButton):
    def __init__(self, color, parent=None):
        super().__init__("", parent)
        self.color = color
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedSize(30, 30)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        color = QColor(*self.color)
        hover = self.hoverProgress
        border = QColor(94, 234, 212, _ease_mix(44, 150, hover))
        painter.setPen(QPen(border, 1.2))
        painter.setBrush(color)
        radius = 13.0 + hover * 0.8
        painter.drawEllipse(QPointF(15, 15), radius, radius)


class SmoothFrame(QFrame):
    def __init__(self, fill, border, radius=10, border_width=1.2, parent=None):
        super().__init__(parent)
        self.fill = QColor(fill)
        self.border = QColor(border)
        self.radius = radius
        self.border_width = border_width

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        inset = self.border_width / 2
        painter.setPen(QPen(self.border, self.border_width))
        painter.setBrush(self.fill)
        painter.drawRoundedRect(
            QRectF(inset, inset, self.width() - self.border_width, self.height() - self.border_width),
            self.radius,
            self.radius,
        )


class ClickableSlider(QSlider):
    def __init__(self, orientation=Qt.Horizontal, parent=None):
        super().__init__(orientation, parent)
        self._hovered = False
        self._dragging = False
        self.setAttribute(Qt.WA_Hover, True)
        self.setCursor(Qt.PointingHandCursor)
        self.setFocusPolicy(Qt.StrongFocus)
        self.setMinimumHeight(34)

    def enterEvent(self, event):
        self._hovered = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._hovered = False
        self._dragging = False
        self.update()
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._dragging = True
            self._set_value_from_pos(event.pos())
            self.update()
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.LeftButton:
            self._set_value_from_pos(event.pos())
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._dragging = False
            self.update()
        super().mouseReleaseEvent(event)

    def _set_value_from_pos(self, pos):
        if self.orientation() != Qt.Horizontal or self.width() <= 0:
            return
        margin = 10
        usable = max(1, self.width() - margin * 2)
        ratio = max(0.0, min(1.0, (pos.x() - margin) / usable))
        value = self.minimum() + round(ratio * (self.maximum() - self.minimum()))
        self.setValue(value)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        margin = 10
        usable = max(1, self.width() - margin * 2)
        ratio = 0.0 if self.maximum() == self.minimum() else (self.value() - self.minimum()) / (self.maximum() - self.minimum())
        ratio = max(0.0, min(1.0, ratio))
        center_y = self.height() / 2
        active = self._hovered or self._dragging
        track_h = 9 if active else 8
        track_rect = QRectF(margin, center_y - track_h / 2, usable, track_h)
        fill_rect = QRectF(margin, center_y - track_h / 2, usable * ratio, track_h)
        handle_x = margin + usable * ratio

        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(255, 255, 255, 30 if active else 24))
        painter.drawRoundedRect(track_rect, track_h / 2, track_h / 2)
        painter.setBrush(QColor(94, 234, 212, 238 if active else 220))
        painter.drawRoundedRect(fill_rect, track_h / 2, track_h / 2)
        painter.setPen(QPen(QColor(13, 17, 23, 90), 1.2))
        painter.setBrush(QColor("#dffcf8"))
        radius = 10.8 if active else 10
        painter.drawEllipse(QPointF(handle_x, center_y), radius, radius)


class MenuComboBox(QWidget):
    currentTextChanged = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_Hover, True)
        self.setCursor(Qt.PointingHandCursor)
        self.setMinimumHeight(34)
        self._items = []
        self._current_index = -1
        self._popup = None

    def addItems(self, values):
        for value in values:
            self._items.append(str(value))
        if self._current_index < 0 and self._items:
            self._current_index = 0
        self.update()

    def count(self):
        return len(self._items)

    def itemText(self, index):
        if 0 <= index < len(self._items):
            return self._items[index]
        return ""

    def currentIndex(self):
        return self._current_index

    def currentText(self):
        return self.itemText(self._current_index)

    def setCurrentIndex(self, index):
        if not 0 <= index < len(self._items):
            return
        if index == self._current_index:
            return
        self._current_index = index
        self.currentTextChanged.emit(self.currentText())
        self.update()

    def setCurrentText(self, text):
        try:
            index = self._items.index(str(text))
        except ValueError:
            return
        self.setCurrentIndex(index)

    def showPopup(self):
        if self.count() <= 0:
            return
        if self._popup:
            self._popup.close()
        self._popup = _ComboPopup(self)
        popup_size = self._popup.size()
        pos = self.mapToGlobal(QPoint(0, self.height() + 4))
        screen = self.screen()
        if screen and pos.y() + popup_size.height() > screen.availableGeometry().bottom():
            pos = self.mapToGlobal(QPoint(0, -popup_size.height() - 4))
        self._popup.move(pos)
        self._popup.show()
        self._popup.setFocus(Qt.PopupFocusReason)
        self.update()

    def hidePopup(self):
        if self._popup:
            self._popup.close()
            self._popup = None
        self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self.rect().contains(event.pos()):
            self.showPopup()
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key_Return, Qt.Key_Enter, Qt.Key_Space, Qt.Key_Down):
            self.showPopup()
            event.accept()
            return
        super().keyPressEvent(event)

    def enterEvent(self, event):
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.update()
        super().leaveEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        border = QColor(94, 234, 212, 90) if self.underMouse() else QColor(148, 163, 184, 34)
        painter.setPen(QPen(border, 1.2))
        painter.setBrush(QColor(255, 255, 255, 12))
        painter.drawRoundedRect(QRectF(0.8, 0.8, self.width() - 1.6, self.height() - 1.6), 8, 8)

        painter.setPen(QPen(QColor("#f4f7fb")))
        painter.setFont(QFont("Microsoft YaHei UI", 12, QFont.DemiBold))
        painter.drawText(QRectF(12, 0, self.width() - 42, self.height()), Qt.AlignVCenter | Qt.AlignLeft, self.currentText())

        # QSS 在不同 Qt 后端下容易把下拉箭头渲成方块，这里手动绘制 chevron。
        cx, cy = self.width() - 18, self.height() / 2 + 1
        painter.setPen(QPen(QColor("#a5b1c2"), 2, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        painter.drawLine(QPointF(cx - 4, cy - 2), QPointF(cx, cy + 2))
        painter.drawLine(QPointF(cx, cy + 2), QPointF(cx + 4, cy - 2))


class _ComboPopup(QWidget):
    ROW_HEIGHT = 28
    PAD = 6

    def __init__(self, combo):
        super().__init__(combo, Qt.Popup | Qt.FramelessWindowHint)
        self.combo = combo
        self.active_index = combo.currentIndex()
        self.setFocusPolicy(Qt.StrongFocus)
        self.setMouseTracking(True)
        height = self.PAD * 2 + combo.count() * self.ROW_HEIGHT
        self.setFixedSize(combo.width(), height)

    def _index_at(self, pos):
        index = int((pos.y() - self.PAD) // self.ROW_HEIGHT)
        if 0 <= index < self.combo.count():
            return index
        return -1

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.fillRect(self.rect(), QColor(12, 18, 26, 248))
        outer = QRectF(0.8, 0.8, self.width() - 1.6, self.height() - 1.6)
        painter.setPen(QPen(QColor(94, 234, 212, 92), 1.2))
        painter.setBrush(QColor(12, 18, 26, 248))
        painter.drawRoundedRect(outer, 8, 8)

        for index in range(self.combo.count()):
            row = QRectF(self.PAD, self.PAD + index * self.ROW_HEIGHT, self.width() - self.PAD * 2, self.ROW_HEIGHT - 2)
            current = index == self.combo.currentIndex()
            active = index == self.active_index
            if current:
                painter.setPen(Qt.NoPen)
                painter.setBrush(QColor(94, 234, 212, 36))
                painter.drawRoundedRect(row, 6, 6)
                painter.setBrush(QColor("#5eead4"))
                painter.drawRoundedRect(QRectF(row.left() + 6, row.top() + 7, 3, row.height() - 14), 1.5, 1.5)
            elif active:
                painter.setPen(Qt.NoPen)
                painter.setBrush(QColor(255, 255, 255, 14))
                painter.drawRoundedRect(row, 6, 6)

            painter.setFont(QFont("Microsoft YaHei UI", 10, QFont.DemiBold if current else QFont.Medium))
            painter.setPen(QPen(QColor("#e6fffb" if current else "#cbd5e1")))
            painter.drawText(QRectF(row.left() + 14, row.top(), row.width() - 22, row.height()),
                             Qt.AlignVCenter | Qt.AlignLeft, self.combo.itemText(index))

    def mouseMoveEvent(self, event):
        index = self._index_at(event.pos())
        if index >= 0 and index != self.active_index:
            self.active_index = index
            self.update()
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            index = self._index_at(event.pos())
            if index >= 0:
                self.combo.setCurrentIndex(index)
            self.close()
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key_Escape, Qt.Key_Tab):
            self.close()
            event.accept()
            return
        if event.key() in (Qt.Key_Up, Qt.Key_Down):
            step = -1 if event.key() == Qt.Key_Up else 1
            count = self.combo.count()
            start = self.active_index if 0 <= self.active_index < count else self.combo.currentIndex()
            self.active_index = (start + step) % count
            self.update()
            event.accept()
            return
        if event.key() in (Qt.Key_Return, Qt.Key_Enter, Qt.Key_Space):
            if 0 <= self.active_index < self.combo.count():
                self.combo.setCurrentIndex(self.active_index)
            self.close()
            event.accept()
            return
        super().keyPressEvent(event)

    def closeEvent(self, event):
        if self.combo._popup is self:
            self.combo._popup = None
            self.combo.update()
        super().closeEvent(event)


class EspPreview(QWidget):
    def __init__(self, config: Config, parent=None):
        super().__init__(parent)
        self.config = config
        self.setFixedSize(252, 286)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        status = "ESP 绘制开" if self.config.esp_enabled else "ESP 绘制关"
        effective_local_ray = self.config.snap_lines and self.config.show_local and self.config.show_local_snap_line
        local_ray = "自身射线开" if effective_local_ray else "自身射线关"
        _draw_target_view(painter, self.config, self.width(), f"{status} · {local_ray}")


class RadarPreview(QWidget):
    def __init__(self, config: Config, parent=None):
        super().__init__(parent)
        self.config = config
        self.setFixedSize(252, 286)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        enabled = self.config.radar_enabled
        scene = QRectF(2, 36, self.width() - 4, 204)
        center = QPointF(scene.center().x(), scene.center().y() + 5)
        radius = 82

        painter.setPen(QPen(QColor("#f4f7fb")))
        painter.setFont(QFont("Microsoft YaHei UI", 11, QFont.Bold))
        painter.drawText(2, 20, "雷达视图")

        _draw_hud_canvas(painter, scene, enabled, grid=False, scan=False)
        hud_alpha = 58 if enabled else 22
        painter.setBrush(Qt.NoBrush)

        painter.setPen(QPen(QColor(94, 234, 212, hud_alpha), 1))
        for scale in (0.38, 0.68, 1.0):
            range_r = radius * scale
            painter.drawEllipse(center, range_r, range_r)

        painter.setPen(QPen(QColor(94, 234, 212, 126 if enabled else 40), 1.6))
        painter.drawLine(center, QPointF(center.x() + 48, center.y() - 32))

        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(94, 234, 212, 42 if enabled else 16))
        painter.drawEllipse(center, 10, 10)
        painter.setBrush(QColor("#5eead4") if enabled else QColor("#4b5563"))
        painter.drawEllipse(center, 5, 5)

        hunter = QColor(*self.config.hunter_color)
        survivor = QColor(*self.config.survivor_color)
        point_alpha = 196 if enabled else 52
        targets = [(-46, -19, 4, hunter), (42, 25, 4, survivor),
                   (18, -52, 3, survivor), (-22, 50, 3, hunter)]
        for dx, dy, size, color in targets:
            point = QPointF(center.x() + dx, center.y() + dy)
            painter.setBrush(QColor(color.red(), color.green(), color.blue(), 40 if enabled else 12))
            painter.drawEllipse(point, size + 5, size + 5)
            painter.setBrush(QColor(color.red(), color.green(), color.blue(), point_alpha))
            painter.drawEllipse(point, size, size)

        painter.setPen(QPen(QColor("#a5b1c2")))
        painter.setFont(QFont("Microsoft YaHei UI", 10))
        state = "开" if enabled else "关"
        painter.drawText(2, 266, f"雷达{state} · 范围 {self.config.radar_range}m · {self.config.radar_position}")


class AppearancePreview(QWidget):
    def __init__(self, config: Config, parent=None):
        super().__init__(parent)
        self.config = config
        self.setFixedSize(252, 286)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        _draw_target_view(
            painter,
            self.config,
            self.width(),
            f"圆点 {self.config.dot_radius}px · 透明度 {self.config.ui_opacity}%",
        )


class ColorSwatchButton(AnimatedPaintButton):
    def __init__(self, title, color, parent=None):
        super().__init__("", parent)
        self.title = title
        self.color = color
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedSize(122, 70)

    def set_color(self, color):
        self.color = color
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        hover = self.hoverProgress
        border = QColor(94, 234, 212, _ease_mix(32, 92, hover))
        painter.setPen(QPen(border, 1.2))
        painter.setBrush(QColor(255, 255, 255, _ease_mix(8, 14, hover)))
        painter.drawRoundedRect(QRectF(0.8, 0.8, self.width() - 1.6, self.height() - 1.6), 9, 9)

        swatch = QColor(*self.color)
        # 色板用横向色条表达主色，比圆点按钮更接近专业调色面板。
        swatch_rect = QRectF(8, 8, self.width() - 16, 24)
        painter.setPen(QPen(QColor(255, 255, 255, 34), 1))
        painter.setBrush(QColor(swatch.red(), swatch.green(), swatch.blue(), 232))
        painter.drawRoundedRect(swatch_rect, 6, 6)
        painter.setPen(QPen(QColor(swatch.red(), swatch.green(), swatch.blue(), 92), 1))
        painter.drawLine(QPointF(14, 38), QPointF(self.width() - 14, 38))

        painter.setPen(QPen(QColor("#f4f7fb")))
        painter.setFont(QFont("Microsoft YaHei UI", 9, QFont.DemiBold))
        painter.drawText(QRectF(8, 42, self.width() - 16, 14), Qt.AlignCenter, self.title)
        painter.setPen(QPen(QColor("#a5b1c2")))
        painter.setFont(QFont("Microsoft YaHei UI", 8, QFont.Medium))
        painter.drawText(QRectF(8, 57, self.width() - 16, 11), Qt.AlignCenter, "#{:02X}{:02X}{:02X}".format(*self.color))


class ColorPreviewBox(QWidget):
    def __init__(self, color, parent=None):
        super().__init__(parent)
        self.color = color
        self.setFixedSize(58, 58)

    def set_color(self, color):
        self.color = color
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        r, g, b = self.color
        painter.setPen(QPen(QColor(255, 255, 255, 42), 1.2))
        painter.setBrush(QColor(r, g, b))
        painter.drawRoundedRect(QRectF(0.8, 0.8, self.width() - 1.6, self.height() - 1.6), 12, 12)


class ColorPickerDialog(QDialog):
    PRESETS = [
        (94, 234, 212), (56, 189, 248), (129, 140, 248), (192, 132, 252),
        (251, 113, 133), (248, 113, 113), (251, 191, 36), (52, 211, 153),
        (226, 232, 240), (148, 163, 184), (71, 85, 105), (15, 23, 42),
        (255, 0, 0), (0, 255, 0), (255, 255, 255), (0, 0, 0),
    ]

    def __init__(self, title, color, parent=None):
        super().__init__(parent)
        self.selected_color = color
        self.setWindowTitle(title)
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setModal(True)
        self.setMinimumSize(380, 392)
        self.resize(380, 392)
        self.setStyleSheet("""
            QLabel {
                color: #f4f7fb;
                font-family: "Microsoft YaHei UI";
                font-size: 12px;
            }
        """)
        self._build_ui(title)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(QPen(QColor(94, 234, 212, 72), 1.4))
        painter.setBrush(QColor(13, 17, 23, 248))
        painter.drawRoundedRect(QRectF(0.8, 0.8, self.width() - 1.6, self.height() - 1.6), 14, 14)

    def _build_ui(self, title):
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 16, 20, 18)
        root.setSpacing(14)
        self.channel_value_labels = {}

        header = QHBoxLayout()
        header.addWidget(self._label(title, 15, "#f4f7fb", 700))
        header.addStretch()
        close_btn = CloseButton(size=30)
        close_btn.clicked.connect(self.reject)
        header.addWidget(close_btn)
        root.addLayout(header)

        preview_row = QHBoxLayout()
        self.preview = ColorPreviewBox(self.selected_color)
        preview_row.addWidget(self.preview)
        preview_text = QVBoxLayout()
        preview_text.setSpacing(3)
        preview_text.addWidget(self._label("当前颜色", 12, "#a5b1c2", 600))
        self.hex_label = self._label("", 18, "#f4f7fb", 700)
        preview_text.addWidget(self.hex_label)
        preview_text.addStretch()
        preview_row.addLayout(preview_text)
        root.addLayout(preview_row)
        root.addSpacing(10)

        grid = QGridLayout()
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(12)
        for i, preset in enumerate(self.PRESETS):
            btn = ColorPresetButton(preset)
            btn.clicked.connect(lambda _checked=False, c=preset: self._set_color(c))
            grid.addWidget(btn, i // 8, i % 8)
        root.addLayout(grid)

        self.channel_sliders = {}
        for label, key, value in [
            ("R", "r", self.selected_color[0]),
            ("G", "g", self.selected_color[1]),
            ("B", "b", self.selected_color[2]),
        ]:
            root.addLayout(self._channel_row(label, key, value))

        buttons = QHBoxLayout()
        buttons.addStretch()
        cancel_btn = SmoothButton("取消")
        cancel_btn.setFixedSize(64, 34)
        cancel_btn.clicked.connect(self.reject)
        ok_btn = SmoothButton("确定", primary=True)
        ok_btn.setFixedSize(64, 34)
        ok_btn.clicked.connect(self.accept)
        buttons.addWidget(cancel_btn)
        buttons.addWidget(ok_btn)
        root.addLayout(buttons)
        self._update_preview()

    def _label(self, text, size, color, weight=400):
        label = QLabel(text)
        label.setStyleSheet(f"color: {color}; font-size: {size}px; font-weight: {weight};")
        return label

    def _channel_row(self, title, key, value):
        row = QHBoxLayout()
        row.setSpacing(8)
        row.addWidget(self._label(title, 12, "#a5b1c2", 700))
        slider = ClickableSlider(Qt.Horizontal)
        slider.setRange(0, 255)
        slider.setValue(value)
        value_label = self._label(str(value), 12, "#f4f7fb", 700)
        value_label.setFixedWidth(34)
        slider.valueChanged.connect(lambda v, k=key, lbl=value_label: self._set_channel(k, v, lbl))
        self.channel_sliders[key] = slider
        self.channel_value_labels[key] = value_label
        row.addWidget(slider, 1)
        row.addWidget(value_label)
        return row

    def _set_channel(self, key, value, value_label):
        value_label.setText(str(value))
        r, g, b = self.selected_color
        if key == "r":
            r = value
        elif key == "g":
            g = value
        else:
            b = value
        self.selected_color = (r, g, b)
        self._update_preview()

    def _set_color(self, color):
        self.selected_color = color
        for key, value in zip(("r", "g", "b"), color):
            self.channel_sliders[key].blockSignals(True)
            self.channel_sliders[key].setValue(value)
            self.channel_sliders[key].blockSignals(False)
            self.channel_value_labels[key].setText(str(value))
        self._update_preview()

    def _update_preview(self):
        r, g, b = self.selected_color
        self.preview.set_color(self.selected_color)
        self.hex_label.setText("#{:02X}{:02X}{:02X}".format(r, g, b))
