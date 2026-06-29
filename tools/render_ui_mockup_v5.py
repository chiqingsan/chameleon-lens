#!/usr/bin/env python3
"""渲染精简仪器面板方向的 V5 UI 概念稿。"""
from pathlib import Path

from PyQt5.QtCore import QPointF, QRectF, Qt
from PyQt5.QtGui import QColor, QFont, QGuiApplication, QImage, QLinearGradient, QPainter, QPen


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "ui_concept_v5.png"


C = {
    "page_a": QColor("#07090d"),
    "page_b": QColor("#0c1118"),
    "shell": QColor("#0d1117"),
    "header": QColor("#121821"),
    "surface": QColor("#111821"),
    "surface_2": QColor("#151e29"),
    "row": QColor("#182230"),
    "line": QColor(148, 163, 184, 32),
    "line_soft": QColor(148, 163, 184, 18),
    "text": QColor("#f4f7fb"),
    "muted": QColor("#a5b1c2"),
    "subtle": QColor("#687486"),
    "accent": QColor("#5eead4"),
    "accent_2": QColor("#38bdf8"),
    "accent_soft": QColor(94, 234, 212, 30),
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
    stroke = QColor(94, 234, 212, 84) if active else C["line"]
    rounded(p, x, y, w, 24, 12, fill, stroke)
    p.setFont(font(9, QFont.DemiBold))
    p.setPen(C["accent"] if active else C["muted"])
    p.drawText(QRectF(x, y, w, 24), Qt.AlignCenter, label)


def status_pill(p: QPainter, x, y, connected=False):
    fill = QColor(94, 234, 212, 24) if connected else QColor(251, 191, 36, 16)
    stroke = QColor(94, 234, 212, 84) if connected else QColor(251, 191, 36, 58)
    dot = C["accent"] if connected else QColor("#fbbf24")
    rounded(p, x, y, 156, 28, 14, fill, stroke, 2)
    p.setPen(Qt.NoPen)
    p.setBrush(QColor(dot.red(), dot.green(), dot.blue(), 44))
    p.drawEllipse(QPointF(x + 17, y + 14), 6, 6)
    p.setBrush(dot)
    p.drawEllipse(QPointF(x + 17, y + 14), 3.2, 3.2)
    text(p, x + 30, y + 19, "等待游戏进程", 10, C["text"], QFont.DemiBold)


def tab(p: QPainter, x, y, w, label, active=False):
    fill = C["surface_2"] if active else QColor(255, 255, 255, 8)
    rounded(p, x, y, w, 32, 8, fill, QColor(94, 234, 212, 78) if active else C["line_soft"])
    p.setFont(font(11, QFont.Bold if active else QFont.Normal))
    p.setPen(C["text"] if active else C["muted"])
    p.drawText(QRectF(x, y, w, 29), Qt.AlignCenter, label)


def toggle(p: QPainter, x, y, checked=True):
    fill = C["accent_soft"] if checked else QColor(255, 255, 255, 22)
    stroke = QColor(94, 234, 212, 86) if checked else C["line"]
    rounded(p, x, y, 40, 22, 11, fill, stroke)
    p.setBrush(C["accent"] if checked else QColor("#8793a4"))
    p.setPen(Qt.NoPen)
    p.drawEllipse(QPointF(x + (29 if checked else 11), y + 11), 6, 6)


def setting_row(p: QPainter, x, y, w, label, desc, checked=True):
    p.setPen(QPen(C["line_soft"], 1))
    p.drawLine(int(x), int(y + 48), int(x + w), int(y + 48))
    text(p, x, y + 20, label, 13, C["text"], QFont.DemiBold)
    text(p, x, y + 40, desc, 10, C["subtle"])
    toggle(p, x + w - 44, y + 13, checked)


def setting_tile(p: QPainter, x, y, w, label, desc, checked=True):
    p.setPen(QPen(C["line_soft"], 1))
    p.drawLine(int(x), int(y + 54), int(x + w), int(y + 54))
    text(p, x, y + 22, label, 13, C["text"], QFont.DemiBold)
    text(p, x, y + 43, desc, 10, C["subtle"])
    toggle(p, x + w - 44, y + 16, checked)


def slider(p: QPainter, x, y, w, label, value, ratio):
    text(p, x, y + 16, label, 12, C["muted"], QFont.DemiBold)
    text(p, x + w - 46, y + 16, value, 12, C["text"], QFont.Bold)
    rounded(p, x, y + 32, w, 6, 3, QColor(255, 255, 255, 24))
    rounded(p, x, y + 32, w * ratio, 6, 3, C["accent"])


def esp_preview(p: QPainter, x, y, w, h):
    rounded(p, x, y, w, h, 10, C["surface"], C["line"])
    text(p, x + 18, y + 28, "ESP 预览", 13, C["text"], QFont.Bold)
    chip(p, x + w - 92, y + 13, 70, "效果", False)

    bx, by, bw, bh = x + 14, y + 64, w - 28, h - 88
    rounded(p, bx, by, bw, bh, 10, QColor(13, 17, 23, 92), QColor(148, 163, 184, 34))
    origin = QPointF(bx + bw / 2, by + bh - 34)
    targets = [
        (QPointF(bx + 58, by + 48), QColor(255, 84, 104), "目标 A", "18m", True),
        (QPointF(bx + 166, by + 84), QColor(255, 84, 104), "目标 B", "31m", True),
        (QPointF(bx + 122, by + 138), C["accent"], "自己", "0m", False),
    ]
    for point, color, name, distance, draw_ray in targets:
        if draw_ray:
            p.setPen(QPen(QColor(color.red(), color.green(), color.blue(), 165), 1))
            p.drawLine(origin, point)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(color.red(), color.green(), color.blue(), 46))
        p.drawEllipse(point, 15, 15)
        p.setBrush(color)
        p.drawEllipse(point, 8, 8)
        label = f"{name} · {distance}"
        p.setFont(font(9, QFont.DemiBold))
        p.setPen(QColor("#dbeafe"))
        label_width = p.fontMetrics().horizontalAdvance(label)
        label_x = point.x() + 16
        if label_x + label_width > bx + bw - 14:
            label_x = point.x() - 16 - label_width
        label_x = max(bx + 14, label_x)
        p.drawText(QPointF(label_x, point.y() + 4), label)

    p.setPen(QPen(C["line_soft"], 1))
    p.drawLine(int(bx + 16), int(by + bh - 54), int(bx + bw - 16), int(by + bh - 54))
    text(p, bx + 18, by + bh - 30, "目标射线开", 10, C["text"], QFont.Bold)
    text(p, bx + 128, by + bh - 30, "自身射线关", 10, C["subtle"], QFont.Bold)


def radar(p: QPainter, x, y, w, h):
    rounded(p, x, y, w, h, 10, C["surface"], C["line"])
    text(p, x + 18, y + 28, "雷达", 13, C["text"], QFont.Bold)
    chip(p, x + w - 92, y + 13, 70, "占位", False)

    cx, cy, r = x + w / 2, y + 154, 92
    glow = QLinearGradient(cx - r, cy - r, cx + r, cy + r)
    glow.setColorAt(0.0, QColor(94, 234, 212, 42))
    glow.setColorAt(1.0, QColor(56, 189, 248, 22))
    p.setBrush(glow)
    p.setPen(QPen(QColor(94, 234, 212, 96), 1))
    p.drawEllipse(QPointF(cx, cy), r, r)
    p.setBrush(Qt.NoBrush)
    p.setPen(QPen(QColor(226, 232, 240, 26), 1))
    for rr in (r * 0.34, r * 0.66):
        p.drawEllipse(QPointF(cx, cy), rr, rr)
    p.drawLine(int(cx - r), int(cy), int(cx + r), int(cy))
    p.drawLine(int(cx), int(cy - r), int(cx), int(cy + r))
    p.setPen(QPen(QColor(94, 234, 212, 110), 2))
    p.drawLine(int(cx), int(cy), int(cx + 52), int(cy - 32))

    p.setPen(Qt.NoPen)
    p.setBrush(C["accent"])
    p.drawEllipse(QPointF(cx, cy), 6, 6)
    for dx, dy, size, alpha in [(-48, -20, 4, 210), (42, 26, 4, 190), (18, -54, 3, 165), (-22, 52, 3, 165)]:
        p.setBrush(QColor(94, 234, 212, alpha))
        p.drawEllipse(QPointF(cx + dx, cy + dy), size, size)

    p.setPen(QPen(C["line_soft"], 1))
    p.drawLine(int(x + 18), int(y + h - 62), int(x + w - 18), int(y + h - 62))
    text(p, x + 18, y + h - 38, "范围", 9, C["subtle"])
    text(p, x + 62, y + h - 38, "80m", 10, C["text"], QFont.Bold)
    text(p, x + 132, y + h - 38, "位置", 9, C["subtle"])
    text(p, x + 176, y + h - 38, "右上角", 10, C["text"], QFont.Bold)


def render():
    OUT.parent.mkdir(parents=True, exist_ok=True)
    app = QGuiApplication.instance() or QGuiApplication([])

    image = QImage(1500, 900, QImage.Format_ARGB32_Premultiplied)
    image.fill(C["page_a"])
    p = QPainter(image)
    p.setRenderHint(QPainter.Antialiasing)

    bg = QLinearGradient(0, 0, 1500, 900)
    bg.setColorAt(0.0, C["page_a"])
    bg.setColorAt(1.0, C["page_b"])
    p.fillRect(0, 0, 1500, 900, bg)

    # V5 收回成真正的悬浮工具尺寸，并提高字号与行高。
    x, y, w, h = 300, 190, 900, 520
    rounded(p, x, y, w, h, 14, C["shell"], QColor(94, 234, 212, 34), 2)
    rounded(p, x + 8, y + 8, w - 16, 52, 11, C["header"], QColor(148, 163, 184, 22), 2)

    rounded(p, x + 24, y + 16, 32, 32, 8, C["accent_soft"], QColor(94, 234, 212, 80))
    text(p, x + 32, y + 38, "CL", 12, C["accent"], QFont.Bold)
    text(p, x + 70, y + 38, "Chameleon Lens", 16, C["text"], QFont.Bold)
    status_pill(p, x + w - 204, y + 20, False)
    text(p, x + w - 28, y + 38, "×", 14, C["muted"], QFont.Bold)

    tabs_y = y + 72
    tab(p, x + 24, tabs_y, 96, "ESP", True)
    tab(p, x + 130, tabs_y, 96, "雷达", False)
    tab(p, x + 236, tabs_y, 96, "外观", False)
    tab(p, x + 342, tabs_y, 96, "调试", False)

    content_y = y + 118
    left_x, left_w = x + 24, 548
    right_x, right_w = x + 596, 280
    rounded(p, left_x, content_y, left_w, 366, 10, C["surface"], C["line"])
    text(p, left_x + 18, content_y + 33, "ESP 显示", 15, C["text"], QFont.Bold)
    text(p, left_x + 18, content_y + 55, "目标点、标签和射线控制", 10, C["subtle"])

    row_x, row_w = left_x + 18, left_w - 36

    tile_w = (row_w - 18) / 2
    items = [
        ("覆盖层", "启用透明窗口绘制", True),
        ("目标圆点", "以低干扰点位标记目标", True),
        ("名称标签", "显示目标名称", True),
        ("距离标签", "显示目标距离", True),
        ("本地标记", "显示自己的点位", True),
        ("ESP 射线", "从底部绘制目标指向线", True),
        ("自身射线", "需开启本地标记与 ESP 射线", False),
    ]
    for i, item in enumerate(items):
        col = i % 2
        row = i // 2
        setting_tile(p, row_x + col * (tile_w + 18), content_y + 76 + row * 58, tile_w, *item)

    esp_preview(p, right_x, content_y, right_w, 366)

    p.end()
    image.save(str(OUT))
    print(OUT)
    app.quit()


if __name__ == "__main__":
    render()
