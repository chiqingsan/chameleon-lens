#!/usr/bin/env python3
"""渲染顶部 Tab 与统一色系的 V4 UI 概念稿。"""
from pathlib import Path

from PyQt5.QtCore import QPointF, QRectF, Qt
from PyQt5.QtGui import (
    QColor,
    QFont,
    QGuiApplication,
    QImage,
    QLinearGradient,
    QPainter,
    QPen,
)


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "ui_concept_v4.png"


C = {
    "page_a": QColor("#070a12"),
    "page_b": QColor("#0e1726"),
    "shell": QColor("#0c1220"),
    "header": QColor("#101827"),
    "panel": QColor("#111c2e"),
    "panel_soft": QColor("#142238"),
    "panel_deep": QColor("#0b1322"),
    "line": QColor(148, 163, 184, 34),
    "line_bright": QColor(45, 212, 191, 96),
    "text": QColor("#f8fafc"),
    "muted": QColor("#a7b4c8"),
    "subtle": QColor("#69778d"),
    "accent": QColor("#2dd4bf"),
    "accent_hi": QColor("#67e8f9"),
    "accent_soft": QColor(45, 212, 191, 34),
    "white_soft": QColor(255, 255, 255, 20),
}


def font(size: int, weight: int = QFont.Normal) -> QFont:
    f = QFont("Microsoft YaHei UI", size)
    f.setWeight(weight)
    return f


def text(p: QPainter, x: float, y: float, value: str, size=12, color=None, weight=QFont.Normal):
    p.setFont(font(size, weight))
    p.setPen(color or C["text"])
    p.drawText(QPointF(x, y), value)


def rounded(p: QPainter, x: float, y: float, w: float, h: float, r: float, fill, stroke=None, width=1):
    p.setBrush(fill)
    p.setPen(QPen(stroke, width) if stroke else Qt.NoPen)
    p.drawRoundedRect(QRectF(x, y, w, h), r, r)


def chip(p: QPainter, x, y, w, label, active=False):
    fill = C["accent_soft"] if active else QColor(255, 255, 255, 14)
    stroke = C["line_bright"] if active else C["line"]
    rounded(p, x, y, w, 28, 14, fill, stroke)
    p.setFont(font(10, QFont.DemiBold))
    p.setPen(C["accent_hi"] if active else C["muted"])
    p.drawText(QRectF(x, y, w, 28), Qt.AlignCenter, label)


def tab(p: QPainter, x, y, w, label, active=False):
    fill = C["accent_soft"] if active else QColor(255, 255, 255, 10)
    stroke = C["line_bright"] if active else QColor(148, 163, 184, 22)
    rounded(p, x, y, w, 38, 10, fill, stroke)
    if active:
        rounded(p, x + 14, y + 30, w - 28, 3, 2, C["accent"])
    p.setFont(font(11, QFont.Bold if active else QFont.Normal))
    p.setPen(C["text"] if active else C["muted"])
    p.drawText(QRectF(x, y, w, 35), Qt.AlignCenter, label)


def icon_box(p: QPainter, x, y, label, active=True):
    fill = C["accent_soft"] if active else QColor(255, 255, 255, 16)
    stroke = C["line_bright"] if active else C["line"]
    rounded(p, x, y, 34, 34, 9, fill, stroke)
    p.setFont(font(13, QFont.Bold))
    p.setPen(C["accent_hi"] if active else C["muted"])
    p.drawText(QRectF(x, y, 34, 34), Qt.AlignCenter, label)


def toggle(p: QPainter, x, y, checked=True):
    fill = C["accent_soft"] if checked else QColor(255, 255, 255, 26)
    stroke = C["line_bright"] if checked else C["line"]
    rounded(p, x, y, 44, 24, 12, fill, stroke)
    p.setBrush(C["accent_hi"] if checked else QColor("#94a3b8"))
    p.setPen(Qt.NoPen)
    p.drawEllipse(QPointF(x + (32 if checked else 12), y + 12), 7, 7)


def control_row(p: QPainter, x, y, w, icon, title, desc, checked=True):
    rounded(p, x, y, w, 66, 9, QColor(255, 255, 255, 12), C["line"])
    icon_box(p, x + 14, y + 16, icon, checked)
    text(p, x + 60, y + 26, title, 12, C["text"], QFont.Bold)
    text(p, x + 60, y + 47, desc, 9, C["subtle"])
    toggle(p, x + w - 62, y + 21, checked)


def metric(p: QPainter, x, y, w, label, value):
    rounded(p, x, y, w, 74, 9, QColor(255, 255, 255, 12), C["line"])
    text(p, x + 16, y + 26, label, 10, C["muted"], QFont.DemiBold)
    text(p, x + 16, y + 56, value, 22, C["text"], QFont.Bold)


def slider(p: QPainter, x, y, w, label, value, ratio):
    text(p, x, y + 12, label, 10, C["muted"], QFont.DemiBold)
    text(p, x + w - 42, y + 12, value, 10, C["text"], QFont.Bold)
    rounded(p, x, y + 28, w, 6, 3, QColor(255, 255, 255, 28))
    rounded(p, x, y + 28, w * ratio, 6, 3, C["accent"])


def radar(p: QPainter, x, y, w, h):
    rounded(p, x, y, w, h, 12, C["panel_deep"], C["line"])
    text(p, x + 22, y + 32, "雷达预览", 15, C["text"], QFont.Bold)
    text(p, x + 22, y + 54, "统一青绿色目标层，后续接入真实坐标", 9, C["subtle"])
    chip(p, x + w - 118, y + 20, 92, "80m", True)

    cx, cy, r = x + w / 2, y + 202, 124
    glow = QLinearGradient(cx - r, cy - r, cx + r, cy + r)
    glow.setColorAt(0.0, QColor(45, 212, 191, 48))
    glow.setColorAt(1.0, QColor(103, 232, 249, 24))
    p.setBrush(glow)
    p.setPen(QPen(QColor(45, 212, 191, 118), 1))
    p.drawEllipse(QPointF(cx, cy), r, r)

    p.setBrush(Qt.NoBrush)
    p.setPen(QPen(QColor(226, 232, 240, 30), 1))
    for rr in (r * 0.28, r * 0.55, r * 0.82):
        p.drawEllipse(QPointF(cx, cy), rr, rr)
    p.drawLine(int(cx - r), int(cy), int(cx + r), int(cy))
    p.drawLine(int(cx), int(cy - r), int(cx), int(cy + r))

    p.setPen(QPen(QColor(103, 232, 249, 118), 2))
    p.drawLine(int(cx), int(cy), int(cx + 78), int(cy - 44))
    p.setPen(Qt.NoPen)
    p.setBrush(C["accent_hi"])
    p.drawEllipse(QPointF(cx, cy), 7, 7)

    for dx, dy, size, alpha in [
        (-70, -34, 5, 230),
        (64, 40, 5, 210),
        (28, -82, 4, 180),
        (-34, 74, 4, 190),
        (92, -12, 4, 160),
    ]:
        p.setBrush(QColor(103, 232, 249, alpha))
        p.drawEllipse(QPointF(cx + dx, cy + dy), size, size)

    rounded(p, x + 24, y + h - 58, w - 48, 36, 8, QColor(255, 255, 255, 16), C["line"])
    text(p, x + 42, y + h - 35, "自身：实心高亮", 10, C["accent_hi"], QFont.DemiBold)
    text(p, x + 174, y + h - 35, "目标：同色弱化", 10, C["muted"])
    text(p, x + w - 114, y + h - 35, "右上角", 10, C["subtle"])


def render():
    OUT.parent.mkdir(parents=True, exist_ok=True)
    app = QGuiApplication.instance() or QGuiApplication([])

    image = QImage(1500, 900, QImage.Format_ARGB32_Premultiplied)
    image.fill(C["page_a"])
    p = QPainter(image)
    p.setRenderHint(QPainter.Antialiasing)

    bg = QLinearGradient(0, 0, 1500, 900)
    bg.setColorAt(0.0, C["page_a"])
    bg.setColorAt(0.55, QColor("#0a1020"))
    bg.setColorAt(1.0, C["page_b"])
    p.fillRect(0, 0, 1500, 900, bg)

    # V4 回到顶部 Tab，色彩统一收敛到深蓝黑与青绿色。
    x, y, w, h = 206, 118, 1088, 664
    rounded(p, x, y, w, h, 14, C["shell"], QColor(45, 212, 191, 70))
    rounded(p, x + 8, y + 8, w - 16, 54, 12, C["header"], C["line"])

    icon_box(p, x + 24, y + 18, "CL", True)
    text(p, x + 68, y + 38, "Chameleon Lens", 15, C["text"], QFont.Bold)
    text(p, x + 68, y + 55, "ESP + 雷达 · 顶部标签控制台", 9, C["subtle"], QFont.DemiBold)
    chip(p, x + w - 386, y + 21, 174, "待机 · 等待目标进程", False)
    chip(p, x + w - 200, y + 21, 110, "Overlay 92%", True)
    text(p, x + w - 56, y + 42, "_", 15, C["muted"], QFont.Bold)
    text(p, x + w - 28, y + 42, "×", 15, C["muted"], QFont.Bold)

    tabs_y = y + 78
    tab(p, x + 28, tabs_y, 118, "总览", True)
    tab(p, x + 158, tabs_y, 118, "ESP", False)
    tab(p, x + 288, tabs_y, 118, "雷达", False)
    tab(p, x + 418, tabs_y, 118, "外观", False)
    chip(p, x + w - 160, tabs_y + 5, 118, "62 FPS", False)

    content_x, content_y = x + 28, y + 134
    left_w, mid_w, right_w = 396, 404, 200
    gap = 18

    rounded(p, content_x, content_y, left_w, 356, 12, C["panel"], C["line"])
    text(p, content_x + 22, content_y + 32, "ESP 控制", 15, C["text"], QFont.Bold)
    text(p, content_x + 22, content_y + 54, "只保留目标感知相关显示", 9, C["subtle"])
    control_row(p, content_x + 20, content_y + 78, left_w - 40, "●", "目标圆点", "快速定位敌方目标", True)
    control_row(p, content_x + 20, content_y + 152, left_w - 40, "Aa", "名称与距离", "显示标签与距离", True)
    control_row(p, content_x + 20, content_y + 226, left_w - 40, "╱", "底部连线", "需要时显示指向线", False)

    radar_x = content_x + left_w + gap
    radar(p, radar_x, content_y, mid_w, 356)

    right_x = radar_x + mid_w + gap
    rounded(p, right_x, content_y, right_w, 356, 12, C["panel_soft"], C["line"])
    text(p, right_x + 18, content_y + 32, "状态", 15, C["text"], QFont.Bold)
    metric(p, right_x + 18, content_y + 58, right_w - 36, "可见目标", "0")
    metric(p, right_x + 18, content_y + 144, right_w - 36, "雷达范围", "80m")
    metric(p, right_x + 18, content_y + 230, right_w - 36, "连接状态", "待机")

    bottom_y = content_y + 374
    rounded(p, content_x, bottom_y, 502, 112, 12, C["panel"], C["line"])
    text(p, content_x + 22, bottom_y + 32, "外观", 14, C["text"], QFont.Bold)
    slider(p, content_x + 22, bottom_y + 56, 198, "透明度", "92%", 0.92)
    slider(p, content_x + 274, bottom_y + 56, 190, "圆点半径", "8px", 0.64)

    log_x = content_x + 520
    rounded(p, log_x, bottom_y, 512, 112, 12, C["panel_soft"], C["line"])
    text(p, log_x + 22, bottom_y + 32, "运行日志", 14, C["text"], QFont.Bold)
    chip(p, log_x + 410, bottom_y + 17, 76, "清空", False)
    text(p, log_x + 22, bottom_y + 68, "INFO", 10, C["accent_hi"], QFont.Bold)
    text(p, log_x + 70, bottom_y + 68, "目标进程未出现，覆盖层保持待机，不弹出错误。", 10, C["muted"])

    p.end()
    image.save(str(OUT))
    print(OUT)
    app.quit()


if __name__ == "__main__":
    render()
