#!/usr/bin/env python3
"""渲染 Chameleon Lens 的 UI 概念稿。"""
from pathlib import Path

from PyQt5.QtCore import Qt, QRectF, QPointF
from PyQt5.QtGui import (
    QColor,
    QFont,
    QGuiApplication,
    QImage,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
)


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "ui_concept_v1.png"


COLORS = {
    "bg": QColor("#09090b"),
    "surface": QColor("#18181b"),
    "surface_2": QColor("#202024"),
    "surface_3": QColor("#27272a"),
    "line": QColor("#3f3f46"),
    "line_soft": QColor(255, 255, 255, 24),
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


def rounded(p, x, y, w, h, r, fill, stroke=None, width=1):
    p.setBrush(fill)
    if stroke is None:
        p.setPen(Qt.NoPen)
    else:
        p.setPen(QPen(stroke, width))
    p.drawRoundedRect(QRectF(x, y, w, h), r, r)


def text(p, x, y, value, size=13, color=None, weight=QFont.Normal):
    p.setFont(font(size, weight))
    p.setPen(color or COLORS["text"])
    p.drawText(QPointF(x, y), value)


def toggle(p, x, y, checked=True):
    fill = COLORS["green"] if checked else COLORS["surface_3"]
    knob = QColor("#ecfdf5") if checked else COLORS["subtle"]
    rounded(p, x, y, 42, 22, 11, fill, None)
    cx = x + 30 if checked else x + 12
    p.setBrush(knob)
    p.setPen(Qt.NoPen)
    p.drawEllipse(QPointF(cx, y + 11), 7, 7)


def section_header(p, x, y, title, subtitle=None):
    text(p, x, y, title, 13, COLORS["text"], QFont.DemiBold)
    if subtitle:
        text(p, x, y + 20, subtitle, 10, COLORS["muted"])


def control_row(p, x, y, label, value=None, checked=None):
    text(p, x, y + 17, label, 12, COLORS["text"])
    if value is not None:
        text(p, x + 220, y + 17, value, 12, COLORS["muted"])
    if checked is not None:
        toggle(p, x + 250, y + 1, checked)
    p.setPen(QPen(COLORS["line_soft"], 1))
    p.drawLine(x, y + 34, x + 292, y + 34)


def pill(p, x, y, w, label, active=False):
    fill = COLORS["green_soft"] if active else COLORS["surface_2"]
    stroke = QColor(16, 185, 129, 120) if active else COLORS["line"]
    color = COLORS["text"] if active else COLORS["muted"]
    rounded(p, x, y, w, 32, 8, fill, stroke)
    p.setFont(font(12, QFont.DemiBold if active else QFont.Normal))
    p.setPen(color)
    p.drawText(QRectF(x, y, w, 32), Qt.AlignCenter, label)


def draw_panel(p):
    x, y, w, h = 92, 82, 376, 720
    rounded(p, x, y, w, h, 10, COLORS["surface"], COLORS["line"])

    text(p, x + 24, y + 42, "Chameleon Lens", 20, COLORS["text"], QFont.Bold)
    text(p, x + 24, y + 66, "ESP + 雷达控制台", 11, COLORS["muted"])

    rounded(p, x + 232, y + 24, 104, 28, 14, COLORS["green_soft"], QColor(16, 185, 129, 110))
    p.setBrush(COLORS["green"])
    p.setPen(Qt.NoPen)
    p.drawEllipse(QPointF(x + 250, y + 38), 4, 4)
    text(p, x + 263, y + 43, "已连接", 11, QColor("#d1fae5"), QFont.DemiBold)

    pill(p, x + 24, y + 96, 92, "ESP", True)
    pill(p, x + 124, y + 96, 92, "雷达", False)
    pill(p, x + 224, y + 96, 92, "外观", False)

    section_header(p, x + 24, y + 162, "ESP", "只保留目标感知相关功能")
    control_row(p, x + 24, y + 204, "覆盖层", checked=True)
    control_row(p, x + 24, y + 244, "目标圆点", value="8 px", checked=True)
    control_row(p, x + 24, y + 284, "名称与距离", checked=True)
    control_row(p, x + 24, y + 324, "底部连线", checked=False)
    control_row(p, x + 24, y + 364, "本地玩家", checked=True)

    section_header(p, x + 24, y + 436, "雷达", "先占位，后续接入玩家坐标")
    control_row(p, x + 24, y + 478, "雷达面板", checked=True)
    control_row(p, x + 24, y + 518, "显示范围", value="80 m")
    control_row(p, x + 24, y + 558, "面板尺寸", value="180 px")
    control_row(p, x + 24, y + 598, "位置", value="右上角")

    rounded(p, x + 24, y + 656, 292, 42, 8, COLORS["surface_2"], COLORS["line"])
    text(p, x + 40, y + 682, "Insert / F1 显示或隐藏", 12, COLORS["muted"])
    text(p, x + 243, y + 682, "调试关闭", 11, COLORS["subtle"])


def draw_radar(p, cx, cy, r):
    p.setRenderHint(QPainter.Antialiasing)
    p.setBrush(QColor(9, 9, 11, 170))
    p.setPen(QPen(QColor(45, 212, 191, 110), 1))
    p.drawEllipse(QPointF(cx, cy), r, r)
    p.setBrush(Qt.NoBrush)
    p.setPen(QPen(QColor(255, 255, 255, 22), 1))
    for rr in (r * 0.33, r * 0.66):
        p.drawEllipse(QPointF(cx, cy), rr, rr)
    p.drawLine(int(cx - r), cy, int(cx + r), cy)
    p.drawLine(cx, int(cy - r), cx, int(cy + r))

    p.setBrush(COLORS["green"])
    p.setPen(Qt.NoPen)
    p.drawEllipse(QPointF(cx, cy), 5, 5)
    for dx, dy, color in [(-38, -22, COLORS["red"]), (44, 18, COLORS["red"]), (18, -52, COLORS["amber"])]:
        p.setBrush(color)
        p.drawEllipse(QPointF(cx + dx, cy + dy), 4, 4)

    text(p, cx - 36, cy + r + 24, "雷达占位", 11, COLORS["muted"], QFont.DemiBold)


def draw_overlay_preview(p):
    x, y, w, h = 510, 82, 838, 720
    rounded(p, x, y, w, h, 10, QColor("#111113"), COLORS["line"])

    text(p, x + 24, y + 42, "覆盖层预览", 16, COLORS["text"], QFont.DemiBold)
    text(p, x + 24, y + 66, "最少干扰，只显示目标感知信息", 11, COLORS["muted"])

    game_x, game_y, game_w, game_h = x + 24, y + 92, w - 48, h - 124
    grad = QLinearGradient(game_x, game_y, game_x + game_w, game_y + game_h)
    grad.setColorAt(0.0, QColor("#18181b"))
    grad.setColorAt(1.0, QColor("#0f172a"))
    rounded(p, game_x, game_y, game_w, game_h, 8, grad, QColor(255, 255, 255, 18))

    p.setPen(QPen(QColor(255, 255, 255, 10), 1))
    for i in range(1, 9):
        xx = game_x + i * game_w / 9
        p.drawLine(int(xx), game_y, int(xx), game_y + game_h)
    for i in range(1, 6):
        yy = game_y + i * game_h / 6
        p.drawLine(game_x, int(yy), game_x + game_w, int(yy))

    # 预览目标点和标签，突出“少但准”的覆盖层风格。
    targets = [
        (game_x + 258, game_y + 240, "目标 2 | 31m", COLORS["red"]),
        (game_x + 452, game_y + 186, "目标 5 | 44m", COLORS["red"]),
        (game_x + 612, game_y + 318, "目标 7 | 57m", COLORS["amber"]),
    ]
    for tx, ty, label, color in targets:
        p.setBrush(color)
        p.setPen(Qt.NoPen)
        p.drawEllipse(QPointF(tx, ty), 7, 7)
        p.setPen(QPen(color, 1))
        p.drawLine(int(game_x + game_w / 2), game_y + game_h, int(tx), int(ty))
        text(p, tx + 16, ty + 5, label, 11, color)

    p.setPen(QPen(QColor(255, 255, 255, 70), 1))
    p.drawLine(int(game_x + game_w / 2 - 8), int(game_y + game_h / 2), int(game_x + game_w / 2 + 8), int(game_y + game_h / 2))
    p.drawLine(int(game_x + game_w / 2), int(game_y + game_h / 2 - 8), int(game_x + game_w / 2), int(game_y + game_h / 2 + 8))

    draw_radar(p, game_x + game_w - 112, game_y + 112, 74)


def render():
    OUT.parent.mkdir(parents=True, exist_ok=True)
    app = QGuiApplication.instance() or QGuiApplication([])
    image = QImage(1440, 900, QImage.Format_ARGB32_Premultiplied)
    image.fill(COLORS["bg"])
    painter = QPainter(image)
    painter.setRenderHint(QPainter.Antialiasing)

    bg_grad = QLinearGradient(0, 0, 1440, 900)
    bg_grad.setColorAt(0.0, QColor("#09090b"))
    bg_grad.setColorAt(1.0, QColor("#131316"))
    painter.fillRect(0, 0, 1440, 900, bg_grad)

    text(painter, 92, 46, "UI Concept V1 / ESP + Radar", 14, COLORS["muted"], QFont.DemiBold)
    draw_panel(painter)
    draw_overlay_preview(painter)

    painter.end()
    image.save(str(OUT))
    print(OUT)
    app.quit()


if __name__ == "__main__":
    render()
