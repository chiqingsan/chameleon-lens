#!/usr/bin/env python3
"""渲染横向矩形版 UI 概念稿。"""
from pathlib import Path

from PyQt5.QtCore import Qt, QRectF, QPointF
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
OUT = ROOT / "docs" / "ui_concept_v2.png"


C = {
    "bg": QColor("#09090b"),
    "panel": QColor("#18181b"),
    "panel_2": QColor("#202024"),
    "panel_3": QColor("#27272a"),
    "line": QColor("#3f3f46"),
    "line_soft": QColor(255, 255, 255, 22),
    "text": QColor("#f4f4f5"),
    "muted": QColor("#a1a1aa"),
    "subtle": QColor("#71717a"),
    "green": QColor("#10b981"),
    "green_soft": QColor(16, 185, 129, 42),
    "teal": QColor("#2dd4bf"),
    "amber": QColor("#f59e0b"),
    "red": QColor("#f43f5e"),
}


def font(size, weight=QFont.Normal):
    f = QFont("Microsoft YaHei UI", size)
    f.setWeight(weight)
    return f


def text(p, x, y, value, size=12, color=None, weight=QFont.Normal):
    p.setFont(font(size, weight))
    p.setPen(color or C["text"])
    p.drawText(QPointF(x, y), value)


def rounded(p, x, y, w, h, r, fill, stroke=None):
    p.setBrush(fill)
    p.setPen(QPen(stroke, 1) if stroke else Qt.NoPen)
    p.drawRoundedRect(QRectF(x, y, w, h), r, r)


def toggle(p, x, y, checked=True):
    rounded(p, x, y, 38, 20, 10, C["green"] if checked else C["panel_3"])
    p.setBrush(QColor("#ecfdf5") if checked else C["subtle"])
    p.setPen(Qt.NoPen)
    p.drawEllipse(QPointF(x + (27 if checked else 11), y + 10), 6, 6)


def row(p, x, y, label, value=None, checked=None):
    text(p, x, y + 16, label, 12, C["text"])
    if value:
        text(p, x + 214, y + 16, value, 12, C["muted"])
    if checked is not None:
        toggle(p, x + 254, y, checked)
    p.setPen(QPen(C["line_soft"], 1))
    p.drawLine(x, y + 33, x + 292, y + 33)


def tab(p, x, y, w, label, active=False):
    fill = C["green_soft"] if active else C["panel_2"]
    stroke = QColor(16, 185, 129, 120) if active else C["line"]
    rounded(p, x, y, w, 34, 8, fill, stroke)
    p.setPen(C["text"] if active else C["muted"])
    p.setFont(font(12, QFont.DemiBold if active else QFont.Normal))
    p.drawText(QRectF(x, y, w, 34), Qt.AlignCenter, label)


def slider(p, x, y, label, value, ratio):
    text(p, x, y + 15, label, 12, C["text"])
    text(p, x + 222, y + 15, value, 12, C["muted"])
    track_x, track_y, track_w = x, y + 30, 292
    rounded(p, track_x, track_y, track_w, 6, 3, C["panel_3"])
    rounded(p, track_x, track_y, track_w * ratio, 6, 3, C["green"])


def radar(p, cx, cy, r):
    p.setBrush(QColor(9, 9, 11, 168))
    p.setPen(QPen(QColor(45, 212, 191, 120), 1))
    p.drawEllipse(QPointF(cx, cy), r, r)
    p.setBrush(Qt.NoBrush)
    p.setPen(QPen(QColor(255, 255, 255, 26), 1))
    for rr in (r * 0.35, r * 0.7):
        p.drawEllipse(QPointF(cx, cy), rr, rr)
    p.drawLine(int(cx - r), cy, int(cx + r), cy)
    p.drawLine(cx, int(cy - r), cx, int(cy + r))
    p.setBrush(C["green"])
    p.setPen(Qt.NoPen)
    p.drawEllipse(QPointF(cx, cy), 5, 5)
    for dx, dy, color in [(-45, -18, C["red"]), (54, 22, C["red"]), (16, -58, C["amber"]), (-22, 48, C["red"])]:
        p.setBrush(color)
        p.drawEllipse(QPointF(cx + dx, cy + dy), 4, 4)


def render():
    OUT.parent.mkdir(parents=True, exist_ok=True)
    app = QGuiApplication.instance() or QGuiApplication([])

    image = QImage(1440, 900, QImage.Format_ARGB32_Premultiplied)
    image.fill(C["bg"])
    p = QPainter(image)
    p.setRenderHint(QPainter.Antialiasing)

    bg = QLinearGradient(0, 0, 1440, 900)
    bg.setColorAt(0.0, QColor("#09090b"))
    bg.setColorAt(1.0, QColor("#121216"))
    p.fillRect(0, 0, 1440, 900, bg)

    # 主面板使用 960 x 594，比例约 1.62，接近黄金比例，适合横向悬浮工具。
    x, y, w, h = 240, 153, 960, 594
    rounded(p, x, y, w, h, 10, C["panel"], C["line"])

    text(p, x + 28, y + 40, "Chameleon Lens", 21, C["text"], QFont.Bold)
    text(p, x + 28, y + 64, "ESP + 雷达 · 简约控制台", 11, C["muted"])

    rounded(p, x + w - 218, y + 24, 92, 28, 14, C["green_soft"], QColor(16, 185, 129, 110))
    p.setBrush(C["green"])
    p.setPen(Qt.NoPen)
    p.drawEllipse(QPointF(x + w - 198, y + 38), 4, 4)
    text(p, x + w - 185, y + 43, "已连接", 11, QColor("#d1fae5"), QFont.DemiBold)
    rounded(p, x + w - 116, y + 24, 76, 28, 14, C["panel_2"], C["line"])
    text(p, x + w - 96, y + 43, "62 FPS", 11, C["muted"], QFont.DemiBold)

    p.setPen(QPen(C["line_soft"], 1))
    p.drawLine(x, y + 84, x + w, y + 84)

    tab(p, x + 28, y + 108, 104, "ESP", True)
    tab(p, x + 140, y + 108, 104, "雷达", False)
    tab(p, x + 252, y + 108, 104, "外观", False)

    content_y = y + 170
    left_x = x + 36
    mid_x = x + 354
    right_x = x + 684

    text(p, left_x, content_y, "ESP 显示", 14, C["text"], QFont.DemiBold)
    text(p, left_x, content_y + 22, "只保留目标感知相关开关", 10, C["muted"])
    row(p, left_x, content_y + 52, "覆盖层", checked=True)
    row(p, left_x, content_y + 92, "目标圆点", "8 px", True)
    row(p, left_x, content_y + 132, "名称与距离", checked=True)
    row(p, left_x, content_y + 172, "底部连线", checked=False)
    row(p, left_x, content_y + 212, "本地玩家", checked=True)
    slider(p, left_x, content_y + 266, "透明度", "92%", 0.92)

    p.setPen(QPen(C["line_soft"], 1))
    p.drawLine(mid_x - 28, content_y - 12, mid_x - 28, y + h - 82)

    text(p, mid_x, content_y, "雷达", 14, C["text"], QFont.DemiBold)
    text(p, mid_x, content_y + 22, "当前先做占位，后续接入坐标", 10, C["muted"])
    row(p, mid_x, content_y + 52, "雷达面板", checked=True)
    row(p, mid_x, content_y + 92, "显示范围", "80 m")
    row(p, mid_x, content_y + 132, "面板尺寸", "180 px")
    row(p, mid_x, content_y + 172, "位置", "右上角")
    slider(p, mid_x, content_y + 226, "盘面亮度", "68%", 0.68)

    p.setPen(QPen(C["line_soft"], 1))
    p.drawLine(right_x - 28, content_y - 12, right_x - 28, y + h - 82)

    text(p, right_x, content_y, "雷达预览", 14, C["text"], QFont.DemiBold)
    text(p, right_x, content_y + 22, "悬浮在覆盖层右上角", 10, C["muted"])
    radar(p, right_x + 122, content_y + 172, 96)
    rounded(p, right_x, content_y + 308, 244, 54, 8, C["panel_2"], C["line"])
    text(p, right_x + 18, content_y + 332, "目标点", 11, C["muted"])
    text(p, right_x + 18, content_y + 352, "红色敌方 · 绿色自身 · 琥珀提示", 10, C["subtle"])

    rounded(p, x + 28, y + h - 58, w - 56, 34, 8, C["panel_2"], C["line"])
    text(p, x + 44, y + h - 36, "Insert / F1 显示或隐藏", 11, C["muted"])
    text(p, x + 300, y + h - 36, "方向：ESP + 雷达", 11, C["subtle"])
    text(p, x + w - 174, y + h - 36, "调试信息关闭", 11, C["subtle"])

    p.end()
    image.save(str(OUT))
    print(OUT)
    app.quit()


if __name__ == "__main__":
    render()
