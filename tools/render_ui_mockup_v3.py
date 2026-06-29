#!/usr/bin/env python3
"""渲染参考紫色工具台风格的 V3 UI 概念稿。"""
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
OUT = ROOT / "docs" / "ui_concept_v3.png"


C = {
    "page_a": QColor("#070812"),
    "page_b": QColor("#111827"),
    "shell": QColor("#111024"),
    "title": QColor("#17132d"),
    "side": QColor("#17122c"),
    "side_active": QColor("#3b256f"),
    "card": QColor("#1d1937"),
    "card_alt": QColor("#172542"),
    "card_deep": QColor("#12192f"),
    "line": QColor(255, 255, 255, 28),
    "line_strong": QColor(168, 85, 247, 92),
    "text": QColor("#f8fafc"),
    "muted": QColor("#b8b3d4"),
    "subtle": QColor("#817b9f"),
    "purple": QColor("#a855f7"),
    "purple_soft": QColor(168, 85, 247, 42),
    "cyan": QColor("#22f3d1"),
    "cyan_soft": QColor(34, 243, 209, 36),
    "amber": QColor("#fbbf24"),
    "red": QColor("#fb7185"),
    "green": QColor("#34d399"),
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


def pill(p: QPainter, x, y, w, label, fill, stroke, color=None):
    rounded(p, x, y, w, 28, 14, fill, stroke)
    p.setFont(font(10, QFont.DemiBold))
    p.setPen(color or C["text"])
    p.drawText(QRectF(x, y, w, 28), Qt.AlignCenter, label)


def icon_badge(p: QPainter, x, y, label, fill=None, color=None):
    rounded(p, x, y, 34, 34, 9, fill or C["purple_soft"], C["line"])
    p.setFont(font(14, QFont.Bold))
    p.setPen(color or C["purple"])
    p.drawText(QRectF(x, y, 34, 34), Qt.AlignCenter, label)


def toggle(p: QPainter, x, y, checked=True):
    fill = QColor(34, 243, 209, 60) if checked else QColor(255, 255, 255, 38)
    stroke = QColor(34, 243, 209, 135) if checked else C["line"]
    rounded(p, x, y, 46, 24, 12, fill, stroke)
    p.setBrush(C["cyan"] if checked else QColor("#cbd5e1"))
    p.setPen(Qt.NoPen)
    p.drawEllipse(QPointF(x + (34 if checked else 12), y + 12), 7, 7)


def nav_item(p: QPainter, x, y, label, icon, active=False):
    fill = C["side_active"] if active else QColor(0, 0, 0, 0)
    if active:
        rounded(p, x, y, 140, 44, 8, fill, C["line_strong"])
        rounded(p, x, y + 10, 4, 24, 2, C["cyan"])
    p.setFont(font(15, QFont.Bold))
    p.setPen(C["cyan"] if active else C["muted"])
    p.drawText(QRectF(x + 18, y, 24, 44), Qt.AlignCenter, icon)
    text(p, x + 50, y + 28, label, 11, C["text"] if active else C["muted"], QFont.DemiBold if active else QFont.Normal)


def control_card(p: QPainter, x, y, w, icon, title, desc, checked=True):
    rounded(p, x, y, w, 74, 9, C["card"], C["line"])
    icon_badge(p, x + 16, y + 20, icon)
    text(p, x + 62, y + 29, title, 13, C["text"], QFont.Bold)
    text(p, x + 62, y + 51, desc, 9, C["subtle"])
    toggle(p, x + w - 66, y + 25, checked)


def slider(p: QPainter, x, y, w, label, value, ratio, accent=None):
    accent = accent or C["cyan"]
    text(p, x, y + 14, label, 10, C["muted"], QFont.DemiBold)
    text(p, x + w - 48, y + 14, value, 10, C["text"], QFont.Bold)
    rounded(p, x, y + 28, w, 7, 4, QColor(255, 255, 255, 34))
    rounded(p, x, y + 28, w * ratio, 7, 4, accent)


def metric_card(p: QPainter, x, y, w, title, value, desc, icon, accent):
    rounded(p, x, y, w, 96, 9, C["card_alt"], C["line"])
    icon_badge(p, x + 18, y + 18, icon, QColor(accent.red(), accent.green(), accent.blue(), 38), accent)
    text(p, x + 64, y + 32, title, 10, accent, QFont.DemiBold)
    text(p, x + 18, y + 68, value, 23, C["text"], QFont.Bold)
    text(p, x + 82, y + 69, desc, 9, C["subtle"])


def radar(p: QPainter, x, y, w, h):
    rounded(p, x, y, w, h, 10, C["card_deep"], C["line"])
    text(p, x + 22, y + 30, "雷达预览", 15, C["text"], QFont.Bold)
    text(p, x + 22, y + 52, "占位视图 · 后续接入目标坐标", 9, C["subtle"])
    pill(p, x + w - 130, y + 18, 104, "范围 80m", C["cyan_soft"], QColor(34, 243, 209, 90), C["cyan"])

    cx, cy, r = x + w / 2, y + 182, 120
    halo = QLinearGradient(cx - r, cy - r, cx + r, cy + r)
    halo.setColorAt(0.0, QColor(168, 85, 247, 56))
    halo.setColorAt(1.0, QColor(34, 243, 209, 46))
    p.setBrush(halo)
    p.setPen(QPen(QColor(34, 243, 209, 110), 1))
    p.drawEllipse(QPointF(cx, cy), r, r)

    p.setBrush(Qt.NoBrush)
    p.setPen(QPen(QColor(255, 255, 255, 34), 1))
    for rr in (r * 0.28, r * 0.55, r * 0.82):
        p.drawEllipse(QPointF(cx, cy), rr, rr)
    p.drawLine(int(cx - r), int(cy), int(cx + r), int(cy))
    p.drawLine(int(cx), int(cy - r), int(cx), int(cy + r))

    p.setPen(QPen(QColor(34, 243, 209, 95), 2))
    p.drawLine(int(cx), int(cy), int(cx + 74), int(cy - 48))
    p.setPen(Qt.NoPen)
    p.setBrush(C["green"])
    p.drawEllipse(QPointF(cx, cy), 7, 7)
    for dx, dy, color, size in [
        (-70, -30, C["red"], 5),
        (62, 38, C["red"], 5),
        (30, -78, C["amber"], 4),
        (-32, 72, C["red"], 4),
        (88, -8, C["purple"], 4),
    ]:
        p.setBrush(color)
        p.drawEllipse(QPointF(cx + dx, cy + dy), size, size)

    rounded(p, x + 22, y + h - 76, w - 44, 44, 8, QColor(255, 255, 255, 18), C["line"])
    text(p, x + 40, y + h - 49, "自身", 10, C["green"], QFont.DemiBold)
    text(p, x + 102, y + h - 49, "敌方", 10, C["red"], QFont.DemiBold)
    text(p, x + 166, y + h - 49, "提示", 10, C["amber"], QFont.DemiBold)
    text(p, x + w - 124, y + h - 49, "右上角显示", 10, C["subtle"])


def render():
    OUT.parent.mkdir(parents=True, exist_ok=True)
    app = QGuiApplication.instance() or QGuiApplication([])

    image = QImage(1500, 900, QImage.Format_ARGB32_Premultiplied)
    image.fill(C["page_a"])
    p = QPainter(image)
    p.setRenderHint(QPainter.Antialiasing)

    bg = QLinearGradient(0, 0, 1500, 900)
    bg.setColorAt(0.0, C["page_a"])
    bg.setColorAt(0.48, QColor("#10102a"))
    bg.setColorAt(1.0, C["page_b"])
    p.fillRect(0, 0, 1500, 900, bg)

    # V3 仍保持横向矩形，1088 x 672 的比例约 1.62，接近黄金比例。
    x, y, w, h = 206, 114, 1088, 672
    rounded(p, x, y, w, h, 14, C["shell"], QColor(168, 85, 247, 70), 1)
    rounded(p, x + 8, y + 8, w - 16, 52, 12, C["title"], C["line"])

    icon_badge(p, x + 24, y + 17, "CL", QColor(34, 243, 209, 28), C["cyan"])
    text(p, x + 68, y + 37, "Chameleon Lens", 15, C["text"], QFont.Bold)
    text(p, x + 68, y + 54, "ESP + RADAR", 9, C["subtle"], QFont.DemiBold)
    pill(p, x + w - 382, y + 20, 192, "待机 · 目标进程未出现", QColor(251, 191, 36, 28), QColor(251, 191, 36, 92), C["amber"])
    pill(p, x + w - 180, y + 20, 104, "Overlay 92%", C["cyan_soft"], QColor(34, 243, 209, 90), C["cyan"])
    text(p, x + w - 48, y + 40, "_", 15, C["muted"], QFont.Bold)
    text(p, x + w - 24, y + 40, "×", 15, C["muted"], QFont.Bold)

    side_x, side_y, side_w = x + 16, y + 72, 164
    rounded(p, side_x, side_y, side_w, h - 88, 12, C["side"], C["line"])
    nav_item(p, side_x + 12, side_y + 18, "总览", "⌾", True)
    nav_item(p, side_x + 12, side_y + 74, "ESP", "◇", False)
    nav_item(p, side_x + 12, side_y + 130, "雷达", "◎", False)
    nav_item(p, side_x + 12, side_y + 186, "外观", "◐", False)
    nav_item(p, side_x + 12, side_y + 242, "诊断", "≡", False)
    rounded(p, side_x + 18, side_y + h - 186, side_w - 36, 86, 9, QColor(255, 255, 255, 16), C["line"])
    text(p, side_x + 34, side_y + h - 154, "方向", 10, C["subtle"])
    text(p, side_x + 34, side_y + h - 130, "只做 ESP", 12, C["text"], QFont.Bold)
    text(p, side_x + 34, side_y + h - 108, "+ 雷达", 12, C["cyan"], QFont.Bold)

    content_x, content_y = x + 196, y + 72
    metric_card(p, content_x, content_y, 214, "可见目标", "0", "等待进程", "◇", C["purple"])
    metric_card(p, content_x + 230, content_y, 214, "雷达状态", "ON", "占位预览", "◎", C["cyan"])
    metric_card(p, content_x + 460, content_y, 214, "覆盖层", "92%", "低干扰", "◐", C["green"])
    metric_card(p, content_x + 690, content_y, 182, "FPS", "62", "渲染预算", "↯", C["amber"])

    left_x, top_y = content_x, content_y + 114
    rounded(p, left_x, top_y, 424, 356, 12, C["card_deep"], C["line"])
    text(p, left_x + 22, top_y + 32, "ESP 控制", 15, C["text"], QFont.Bold)
    text(p, left_x + 22, top_y + 54, "保留目标感知，不加入瞄准类功能", 9, C["subtle"])
    control_card(p, left_x + 20, top_y + 78, 384, "●", "目标圆点", "用于快速定位敌方目标", True)
    control_card(p, left_x + 20, top_y + 160, 384, "Aa", "名称与距离", "显示玩家名称和距离标签", True)
    control_card(p, left_x + 20, top_y + 242, 384, "╱", "底部连线", "需要时显示目标指向线", False)

    radar(p, left_x + 444, top_y, 428, 356)

    bottom_y = top_y + 372
    rounded(p, left_x, bottom_y, 424, 98, 12, C["card"], C["line"])
    text(p, left_x + 22, bottom_y + 31, "覆盖层外观", 13, C["text"], QFont.Bold)
    slider(p, left_x + 22, bottom_y + 52, 166, "透明度", "92%", 0.92)
    slider(p, left_x + 228, bottom_y + 52, 166, "圆点半径", "8px", 0.64, C["purple"])

    rounded(p, left_x + 444, bottom_y, 428, 98, 12, C["card_alt"], C["line"])
    text(p, left_x + 466, bottom_y + 31, "运行日志", 13, C["text"], QFont.Bold)
    pill(p, left_x + 772, bottom_y + 18, 78, "清空", QColor(168, 85, 247, 32), QColor(168, 85, 247, 92), C["purple"])
    text(p, left_x + 466, bottom_y + 62, "INFO", 10, C["cyan"], QFont.Bold)
    text(p, left_x + 512, bottom_y + 62, "目标进程未出现，覆盖层保持待机，不弹出错误。", 10, C["muted"])

    p.end()
    image.save(str(OUT))
    print(OUT)
    app.quit()


if __name__ == "__main__":
    render()
