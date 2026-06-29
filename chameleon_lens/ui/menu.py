"""主控制菜单。"""
from PyQt5.QtWidgets import (
    QApplication, QDialog, QFrame, QGridLayout, QHBoxLayout, QLabel,
    QListView, QSpinBox, QStackedWidget, QVBoxLayout, QWidget,
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QColor

from ..config import Config, UI_OPACITY_MAX, UI_OPACITY_MIN, save_config
from ..logging import LOG_DIR
from ..runtime import ESPRuntime
from .widgets import (
    AppearancePreview, ClickableSlider, CloseButton, ColorPickerDialog,
    ColorSwatchButton, EspPreview, LogoBadge, MenuComboBox, RadarPreview,
    SmoothButton, SmoothFrame, StatusPill, TabButton, ToggleSwitch,
)


class Menu(QWidget):
    def __init__(self, config: Config, runtime: ESPRuntime):
        super().__init__()
        self.config = config
        self.runtime = runtime
        self.setWindowTitle("Chameleon Lens")
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self._drag_pos = None
        self.tab_buttons = []
        self.esp_previews = []
        self.radar_previews = []
        self.appearance_previews = []
        self.local_ray_switch = None
        self.slider_controls = {}
        self._config_save_timer = QTimer(self)
        self._config_save_timer.setSingleShot(True)
        self._config_save_timer.setInterval(500)
        self._config_save_timer.timeout.connect(self._save_config_now)

        self._build_ui()
        self.setFixedSize(900, 520)

    def _build_ui(self):
        self.container = SmoothFrame(QColor(13, 17, 23, 242), QColor(94, 234, 212, 34), 14, 1.4, self)
        self._apply_panel_style()

        root = QVBoxLayout(self.container)
        root.setContentsMargins(18, 18, 18, 18)
        root.setSpacing(12)

        root.addWidget(self._build_header())
        root.addLayout(self._build_tabs())

        self.stack = QStackedWidget()
        self.stack.setObjectName("pageStack")
        self.stack.addWidget(self._build_esp_page())
        self.stack.addWidget(self._build_radar_page())
        self.stack.addWidget(self._build_appearance_page())
        self.stack.addWidget(self._build_debug_page())
        root.addWidget(self.stack, 1)

        outer = QVBoxLayout(self)
        outer.addWidget(self.container)
        outer.setContentsMargins(0, 0, 0, 0)
        self.setLayout(outer)
        self._select_tab(0)
        self.refresh_status()

    def _apply_panel_style(self):
        self.setWindowOpacity(max(UI_OPACITY_MIN / 100.0, min(UI_OPACITY_MAX / 100.0, self.config.ui_opacity / 100.0)))
        self.container.setStyleSheet("""
            QFrame#settingRow {
                border-bottom: 1px solid rgba(148, 163, 184, 18);
            }
            QStackedWidget#pageStack {
                border: none;
                background: transparent;
            }
            QLabel {
                color: #f4f7fb;
                font-family: "Microsoft YaHei UI";
                font-size: 13px;
            }
            QSpinBox, QComboBox {
                background-color: rgba(255, 255, 255, 12);
                color: #f4f7fb;
                border: 2px solid rgba(148, 163, 184, 20);
                border-radius: 8px;
                padding: 5px 10px;
                min-height: 30px;
                font-family: "Microsoft YaHei UI";
                font-size: 12px;
            }
            QComboBox QAbstractItemView {
                background-color: #111821;
                color: #f4f7fb;
                border: 1px solid rgba(94, 234, 212, 80);
                border-radius: 8px;
                padding: 6px;
                outline: 0;
                selection-background-color: rgba(94, 234, 212, 38);
                selection-color: #5eead4;
                font-family: "Microsoft YaHei UI";
                font-size: 12px;
            }
        """)

    def _build_header(self):
        header_frame = SmoothFrame(QColor(18, 24, 33, 235), QColor(148, 163, 184, 22), 11, 1.2)
        self.header_frame = header_frame
        header_frame.setFixedHeight(52)
        header = QHBoxLayout(header_frame)
        header.setContentsMargins(14, 0, 14, 0)
        header.setSpacing(12)
        header.addWidget(LogoBadge())
        title = QLabel("Chameleon Lens")
        title.setStyleSheet("font-size: 16px; font-weight: 700; color: #f4f7fb;")
        header.addWidget(title)
        header.addStretch()
        self.lbl_status = StatusPill()
        header.addWidget(self.lbl_status)
        close_btn = CloseButton(size=32)
        close_btn.clicked.connect(QApplication.instance().quit)
        header.addWidget(close_btn)
        return header_frame

    def _build_tabs(self):
        tabs = QHBoxLayout()
        tabs.setSpacing(8)
        for index, name in enumerate(["ESP", "雷达", "外观", "调试"]):
            btn = self._tab(name)
            btn.clicked.connect(lambda _checked=False, i=index: self._select_tab(i))
            self.tab_buttons.append(btn)
            tabs.addWidget(btn)
        tabs.addStretch()
        return tabs

    def _build_esp_page(self):
        page = QWidget()
        body = QHBoxLayout(page)
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(24)

        panel, layout = self._panel("ESP 显示", "目标点、标签和射线控制", 548)
        grid = QGridLayout()
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(18)
        grid.setVerticalSpacing(2)

        controls = [
            ("覆盖层", "启用透明窗口绘制", "enabled", None),
            ("ESP 绘制", "控制目标点、标签和射线", "esp_enabled", self._refresh_ray_dependencies),
            ("猎人 ESP", "显示猎人的点、标签和雷达点", "show_hunter_esp", None),
            ("目标圆点", "以低干扰点位标记目标", "box_esp", None),
            ("名称标签", "显示目标名称", "show_names", None),
            ("距离标签", "显示目标距离", "show_distance", None),
            ("本地标记", "显示自己的点位", "show_local", self._refresh_ray_dependencies),
            ("ESP 射线", "从底部绘制目标指向线", "snap_lines", self._refresh_ray_dependencies),
            ("自身射线", "需开启本地标记与 ESP 射线", "show_local_snap_line", None),
            ("边缘提示", "屏幕外目标钳到边缘显示", "show_edge_indicators", None),
        ]
        for index, (label, desc, attr, after_change) in enumerate(controls):
            switch = self._switch_control(attr, after_change)
            if attr == "show_local_snap_line":
                self.local_ray_switch = switch
            grid.addWidget(self._control_row(label, desc, switch, height=56), index // 2, index % 2)

        layout.addLayout(grid)
        layout.addStretch()
        self._refresh_ray_dependencies()
        body.addWidget(panel)
        body.addWidget(self._esp_preview_panel())
        return page

    def _build_radar_page(self):
        page = QWidget()
        body = QHBoxLayout(page)
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(24)

        panel, layout = self._panel("雷达设置", "按相机朝向显示目标相对位置", 548)
        layout.addWidget(self._toggle_row("雷达面板", "在覆盖层角落显示雷达", "radar_enabled"))
        layout.addWidget(self._spin_row("显示范围", "换算到雷达盘面的目标范围", "radar_range", 20, 300, "m"))
        layout.addWidget(self._spin_row("面板尺寸", "覆盖层中的雷达直径", "radar_size", 120, 280, "px"))
        layout.addWidget(self._combo_row("位置", "雷达在覆盖层中的停靠角落", "radar_position", ["右上角", "左上角", "右下角", "左下角"]))
        layout.addWidget(self._slider_row("盘面亮度", "radar_opacity", 20, 100, "%"))
        layout.addStretch()
        body.addWidget(panel)
        body.addWidget(self._radar_preview_panel())
        return page

    def _build_appearance_page(self):
        page = QWidget()
        body = QHBoxLayout(page)
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(24)

        panel, layout = self._panel("外观", "覆盖层的透明度、点位和颜色", 548)
        layout.addWidget(self._section_label("绘制参数"))
        param_grid = QGridLayout()
        param_grid.setContentsMargins(0, 8, 0, 0)
        param_grid.setHorizontalSpacing(18)
        param_grid.setVerticalSpacing(0)
        param_grid.addWidget(self._slider_row("菜单透明度", "ui_opacity", UI_OPACITY_MIN, UI_OPACITY_MAX, "%", compact=True), 0, 0)
        param_grid.addWidget(self._slider_row("圆点半径", "dot_radius", 2, 32, "px", compact=True), 0, 1)
        layout.addLayout(param_grid)
        layout.addSpacing(18)

        layout.addWidget(self._section_label("颜色方案"))
        self.btn_hunter_color = self._color_button("猎人颜色", self.config.hunter_color, self._pick_hunter_color)
        self.btn_survivor_color = self._color_button("躲藏者颜色", self.config.survivor_color, self._pick_survivor_color)
        self.btn_enemy_color = self._color_button("默认目标", self.config.enemy_color, self._pick_enemy_color)
        self.btn_local_color = self._color_button("本地颜色", self.config.local_color, self._pick_local_color)
        color_row = QHBoxLayout()
        color_row.setContentsMargins(0, 8, 0, 0)
        color_row.setSpacing(8)
        for button in (
            self.btn_hunter_color,
            self.btn_survivor_color,
            self.btn_enemy_color,
            self.btn_local_color,
        ):
            color_row.addWidget(button)
        layout.addLayout(color_row)
        layout.addSpacing(18)
        reset_row = QHBoxLayout()
        reset_row.setContentsMargins(0, 0, 0, 0)
        reset_btn = SmoothButton("恢复默认外观")
        reset_btn.setFixedSize(128, 34)
        reset_btn.clicked.connect(self._reset_appearance_defaults)
        reset_row.addWidget(reset_btn)
        reset_row.addStretch()
        layout.addLayout(reset_row)
        layout.addStretch()

        body.addWidget(panel)
        body.addWidget(self._appearance_preview_panel())
        return page

    def _build_debug_page(self):
        page = QWidget()
        body = QHBoxLayout(page)
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(24)

        panel, layout = self._panel("调试", "排查连接和覆盖层数据，不占用主界面", 548)
        layout.addWidget(self._toggle_row("调试信息", "在覆盖层左上角显示数据计数", "show_debug"))
        layout.addWidget(self._toggle_row("数据记录", "每秒写入一次覆盖层诊断 JSONL", "record_debug_data"))
        self.lbl_debug_status = self._body_text("")
        self.lbl_debug_error = self._body_text("")
        self.lbl_debug_error.setWordWrap(True)
        layout.addWidget(self._control_row("运行状态", "当前连接与重试状态", self.lbl_debug_status))
        layout.addWidget(self._control_row("最近错误", "仅用于排查目标进程读取问题", self.lbl_debug_error))
        retry_btn = SmoothButton("立即重试", primary=True)
        retry_btn.setFixedSize(128, 36)
        retry_btn.clicked.connect(self._manual_retry)
        layout.addWidget(self._control_row("连接", "手动触发一次目标进程连接", retry_btn))
        layout.addStretch()

        body.addWidget(panel)
        body.addWidget(self._debug_target_panel())
        return page

    def _radar_preview_panel(self):
        panel, layout = self._panel("雷达", "实时方位预览", 280)
        preview = RadarPreview(self.config)
        self.radar_previews.append(preview)
        layout.addWidget(preview, alignment=Qt.AlignCenter)
        layout.addStretch()
        return panel

    def _esp_preview_panel(self):
        panel, layout = self._panel("ESP 预览", "当前开关的实际效果", 280)
        preview = EspPreview(self.config)
        self.esp_previews.append(preview)
        layout.addWidget(preview, alignment=Qt.AlignCenter)
        layout.addStretch()
        return panel

    def _appearance_preview_panel(self):
        panel, layout = self._panel("外观预览", "颜色、圆点和连线效果", 280)
        preview = AppearancePreview(self.config)
        self.appearance_previews.append(preview)
        layout.addWidget(preview, alignment=Qt.AlignCenter)
        layout.addStretch()
        return panel

    def _debug_target_panel(self):
        panel, layout = self._panel("目标信息", "当前连接目标", 280)
        layout.addWidget(self._info_row("进程", self.runtime.process_name))
        layout.addWidget(self._info_row("模块", self.runtime.module_name))
        layout.addWidget(self._info_row("重试", "每 2 秒自动连接"))
        layout.addWidget(self._info_row("热键", "Insert / F1"))
        layout.addWidget(self._info_row("日志", str(LOG_DIR)))
        layout.addStretch()
        return panel

    def _panel(self, title, subtitle, width):
        frame = SmoothFrame(QColor(17, 24, 33, 232), QColor(148, 163, 184, 20), 10, 1.2)
        frame.setFixedWidth(width)
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(0)
        layout.addWidget(self._label(title, 15, "#f4f7fb", 700))
        layout.addWidget(self._label(subtitle, 10, "#687486", 500))
        layout.addSpacing(14)
        return frame, layout

    def _section_label(self, text):
        label = self._label(text, 11, "#a5b1c2", 700)
        label.setStyleSheet(
            "color: #a5b1c2; font-size: 11px; font-weight: 700; "
            "letter-spacing: 0px;"
        )
        return label

    def _toggle_row(self, label, desc, attr):
        switch = self._switch_control(attr)
        return self._control_row(label, desc, switch)

    def _switch_control(self, attr, after_change=None):
        switch = ToggleSwitch(getattr(self.config, attr))

        def on_changed(state, a=attr):
            setattr(self.config, a, bool(state))
            if after_change:
                after_change()
            self._refresh_preview()
            self._schedule_config_save()

        switch.stateChanged.connect(on_changed)
        return switch

    def _control_row(self, label, desc, control, height=48):
        frame = QFrame()
        frame.setObjectName("settingRow")
        frame.setFixedHeight(height)
        row = QHBoxLayout(frame)
        row.setContentsMargins(0, 0, 0, 0)
        text_col = QVBoxLayout()
        text_col.setContentsMargins(0, 5, 0, 5)
        text_col.setSpacing(1)
        title_label = self._label(label, 13, "#f4f7fb", 600)
        desc_label = self._label(desc, 10, "#687486")
        title_label.setFixedHeight(17)
        desc_label.setFixedHeight(15)
        text_col.addWidget(title_label)
        text_col.addWidget(desc_label)
        text_col.addStretch()
        row.addLayout(text_col, 1)
        row.addWidget(control)
        return frame

    def _info_row(self, label, value):
        frame = QFrame()
        frame.setObjectName("settingRow")
        frame.setFixedHeight(50)
        row = QVBoxLayout(frame)
        row.setContentsMargins(0, 4, 0, 4)
        row.setSpacing(1)
        row.addWidget(self._label(label, 10, "#687486", 600))
        row.addWidget(self._label(value, 11, "#f4f7fb", 600))
        return frame

    def _spin_row(self, label, desc, attr, min_value, max_value, suffix):
        spin = QSpinBox()
        spin.setRange(min_value, max_value)
        spin.setSuffix(f" {suffix}")
        spin.setValue(int(getattr(self.config, attr)))
        spin.setFixedWidth(96)
        spin.setButtonSymbols(QSpinBox.NoButtons)
        spin.valueChanged.connect(lambda value, a=attr: setattr(self.config, a, value))
        spin.valueChanged.connect(lambda _value: self._after_value_changed(attr))
        return self._control_row(label, desc, spin)

    def _slider_row(self, label, attr, min_value, max_value, suffix, compact=False):
        frame = QFrame()
        frame.setObjectName("settingRow")
        frame.setFixedHeight(56)
        if compact:
            frame.setFixedWidth(246)
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(0, 5, 0, 7)
        label_row = QHBoxLayout()
        value = QLabel(f"{getattr(self.config, attr)}{suffix}")
        value.setStyleSheet("color: #f4f7fb; font-size: 12px; font-weight: 700;")
        label_row.addWidget(self._label(label, 12, "#a5b1c2", 600))
        label_row.addStretch()
        label_row.addWidget(value)
        slider = ClickableSlider(Qt.Horizontal)
        slider.setRange(min_value, max_value)
        slider.setValue(int(getattr(self.config, attr)))
        slider.valueChanged.connect(lambda v, a=attr: setattr(self.config, a, v))
        slider.valueChanged.connect(lambda v: value.setText(f"{v}{suffix}"))
        slider.valueChanged.connect(lambda _v, a=attr: self._after_value_changed(a))
        self.slider_controls[attr] = (slider, value, suffix)
        layout.addLayout(label_row)
        layout.addWidget(slider)
        return frame

    def _combo_row(self, label, desc, attr, values):
        combo = MenuComboBox()
        combo.setView(QListView())
        combo.addItems(values)
        combo.setCurrentText(getattr(self.config, attr))
        combo.currentTextChanged.connect(lambda text, a=attr: setattr(self.config, a, text))
        combo.currentTextChanged.connect(lambda _text: self._after_value_changed(attr))
        combo.setFixedWidth(132)
        return self._control_row(label, desc, combo)

    def _tab(self, text):
        return TabButton(text)

    def _select_tab(self, index):
        self.stack.setCurrentIndex(index)
        for i, btn in enumerate(self.tab_buttons):
            btn.set_active(i == index)

    def _chip(self, text, active=False, width=120):
        label = QLabel(text)
        label.setAlignment(Qt.AlignCenter)
        label.setFixedWidth(width)
        label.setFixedHeight(32)
        self._style_chip(label, active)
        return label

    def _style_chip(self, label, active=False):
        border = "rgba(94,234,212,84)" if active else "rgba(148,163,184,32)"
        bg = "rgba(94,234,212,30)" if active else "rgba(255,255,255,14)"
        color = "#5eead4" if active else "#a5b1c2"
        label.setStyleSheet(
            f"background-color: {bg}; color: {color}; border: 1px solid {border}; "
            "border-radius: 16px; padding: 0 14px; font-size: 11px; font-weight: 700;"
        )

    def _label(self, text, size=12, color="#f4f4f5", weight=400):
        label = QLabel(text)
        label.setStyleSheet(f"color: {color}; font-size: {size}px; font-weight: {weight};")
        return label

    def _body_text(self, text):
        label = self._label(text, 12, "#a5b1c2")
        label.setWordWrap(True)
        return label

    def _muted(self, text):
        return self._label(text, 11, "#a5b1c2")

    def _color_button(self, text, color, callback):
        btn = ColorSwatchButton(text, color)
        btn.clicked.connect(callback)
        return btn

    def _apply_color_button(self, button, color):
        button.set_color(color)

    def _after_value_changed(self, attr):
        if attr == "ui_opacity":
            self._apply_panel_style()
        self._refresh_preview()
        self._schedule_config_save()

    def _set_slider_value(self, attr, value):
        control = self.slider_controls.get(attr)
        if not control:
            return
        slider, label, suffix = control
        slider.blockSignals(True)
        slider.setValue(int(value))
        slider.blockSignals(False)
        label.setText(f"{int(value)}{suffix}")

    def _reset_appearance_defaults(self):
        defaults = Config()
        self.config.ui_opacity = defaults.ui_opacity
        self.config.dot_radius = defaults.dot_radius
        self.config.enemy_color = defaults.enemy_color
        self.config.hunter_color = defaults.hunter_color
        self.config.survivor_color = defaults.survivor_color
        self.config.local_color = defaults.local_color
        self._set_slider_value("ui_opacity", self.config.ui_opacity)
        self._set_slider_value("dot_radius", self.config.dot_radius)
        self._apply_color_button(self.btn_enemy_color, self.config.enemy_color)
        self._apply_color_button(self.btn_hunter_color, self.config.hunter_color)
        self._apply_color_button(self.btn_survivor_color, self.config.survivor_color)
        self._apply_color_button(self.btn_local_color, self.config.local_color)
        self._apply_panel_style()
        self._refresh_preview()
        self._schedule_config_save()

    def _schedule_config_save(self):
        self._config_save_timer.start()

    def _save_config_now(self):
        save_config(self.config)

    def _refresh_ray_dependencies(self):
        if not self.local_ray_switch:
            return
        enabled = self.config.esp_enabled and self.config.snap_lines and self.config.show_local
        self.local_ray_switch.setEnabled(enabled)
        tip = "" if enabled else "需先开启 ESP 绘制、本地标记和 ESP 射线"
        self.local_ray_switch.setToolTip(tip)

    def _refresh_preview(self):
        for preview in self.esp_previews:
            preview.update()
        for preview in self.radar_previews:
            preview.update()
        for preview in self.appearance_previews:
            preview.update()

    def refresh_status(self):
        connected = self.runtime.connected
        self.lbl_status.set_status(
            connected,
            "已连接 · 游戏进程" if connected else "未连接 · 等待进程",
        )
        self.lbl_status.setToolTip(self.runtime.status)
        if hasattr(self, "lbl_debug_status"):
            self.lbl_debug_status.setText(self.runtime.status)
        if hasattr(self, "lbl_debug_error"):
            self.lbl_debug_error.setText(self.runtime.last_error or "无")

    def _manual_retry(self):
        self.runtime.connect_once()
        self.refresh_status()

    def _pick_enemy_color(self):
        dialog = ColorPickerDialog("默认目标", self.config.enemy_color, self)
        if dialog.exec_() == QDialog.Accepted:
            self.config.enemy_color = dialog.selected_color
            self._apply_color_button(self.btn_enemy_color, self.config.enemy_color)
            self._refresh_preview()
            self._schedule_config_save()

    def _pick_hunter_color(self):
        dialog = ColorPickerDialog("猎人颜色", self.config.hunter_color, self)
        if dialog.exec_() == QDialog.Accepted:
            self.config.hunter_color = dialog.selected_color
            self._apply_color_button(self.btn_hunter_color, self.config.hunter_color)
            self._refresh_preview()
            self._schedule_config_save()

    def _pick_survivor_color(self):
        dialog = ColorPickerDialog("躲藏者颜色", self.config.survivor_color, self)
        if dialog.exec_() == QDialog.Accepted:
            self.config.survivor_color = dialog.selected_color
            self._apply_color_button(self.btn_survivor_color, self.config.survivor_color)
            self._refresh_preview()
            self._schedule_config_save()

    def _pick_local_color(self):
        dialog = ColorPickerDialog("本地颜色", self.config.local_color, self)
        if dialog.exec_() == QDialog.Accepted:
            self.config.local_color = dialog.selected_color
            self._apply_color_button(self.btn_local_color, self.config.local_color)
            self._refresh_preview()
            self._schedule_config_save()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and hasattr(self, "header_frame") and self.header_frame.geometry().contains(event.pos()):
            self._drag_pos = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()
            return
        self._drag_pos = None
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._drag_pos is not None and event.buttons() == Qt.LeftButton:
            self.move(event.globalPos() - self._drag_pos)
            event.accept()

    def mouseReleaseEvent(self, event):
        self._drag_pos = None
