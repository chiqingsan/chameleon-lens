#!/usr/bin/env python3
"""从源 PNG 处理并生成多尺寸 Windows ICO 图标。"""
import sys
from pathlib import Path

from PyQt5.QtCore import QByteArray, QBuffer, QIODevice, QRect, Qt
from PyQt5.QtGui import QColor, QImage, QPainter, QPainterPath


ROOT = Path(__file__).resolve().parents[1]
SOURCE_PATH = ROOT / "assets" / "app.png"
ICO_PATH = ROOT / "assets" / "chameleon.ico"
LOGO_PATH = ROOT / "assets" / "chameleon_logo.png"
ICON_SIZES = (16, 20, 24, 32, 40, 48, 64, 128, 256)
ICON_EDGE_TRIM = 18


def main():
    if not SOURCE_PATH.exists():
        print(f"[错误] 找不到图标源图：{SOURCE_PATH}")
        print("[提示] 请把参考图片保存为 assets\\app.png 后重新运行。")
        return 1

    source = QImage(str(SOURCE_PATH)).convertToFormat(QImage.Format_ARGB32)
    if source.isNull():
        print(f"[错误] 图标源图无法读取：{SOURCE_PATH}")
        return 1

    master = _prepare_master_icon(source)
    if not master.save(str(LOGO_PATH), "PNG"):
        print(f"[错误] 菜单 Logo 无法写入：{LOGO_PATH}")
        return 1
    images = [_render_png(master, size) for size in ICON_SIZES]
    _write_ico(ICO_PATH, images)
    print(f"[Chameleon Lens] 已生成图标：{ICO_PATH}")
    print(f"[Chameleon Lens] 已生成菜单 Logo：{LOGO_PATH}")
    return 0


def _prepare_master_icon(source):
    square = _icon_base_rect(source)

    cropped = source.copy(square)
    icon = QImage(1024, 1024, QImage.Format_ARGB32)
    icon.fill(Qt.transparent)
    painter = QPainter(icon)
    painter.setRenderHint(QPainter.Antialiasing)
    painter.setRenderHint(QPainter.SmoothPixmapTransform)
    painter.drawImage(QRect(0, 0, 1024, 1024), cropped)
    painter.end()
    return _apply_icon_mask(_remove_white_background(icon))


def _icon_base_rect(source):
    dark_rect = _dark_background_rect(source)
    if dark_rect.isNull():
        return _square_from_rect(_content_rect(source), source.rect())
    # 深色圆角底比外部白色发光更适合作为 ICO 本体；高度里通常包含底部投影，
    # 因此优先使用宽度作为方形边长，避免把白色背景带进菜单 Logo。
    side = dark_rect.width()
    square = QRect(dark_rect.left(), dark_rect.top(), side, side).intersected(source.rect())
    # 源图边缘带有浅色发光，缩到标题栏后会像一圈白边；内收少量像素保留底板主体。
    return square.adjusted(ICON_EDGE_TRIM, ICON_EDGE_TRIM, -ICON_EDGE_TRIM, -ICON_EDGE_TRIM)


def _dark_background_rect(image):
    left, top = image.width(), image.height()
    right, bottom = 0, 0
    count = 0
    for y in range(image.height()):
        for x in range(image.width()):
            color = image.pixelColor(x, y)
            if color.alpha() <= 0:
                continue
            luma = 0.2126 * color.red() + 0.7152 * color.green() + 0.0722 * color.blue()
            is_greenish = color.green() >= color.red() and color.green() >= color.blue()
            if luma < 185 and is_greenish:
                left = min(left, x)
                top = min(top, y)
                right = max(right, x)
                bottom = max(bottom, y)
                count += 1
    if count <= 0 or right <= left or bottom <= top:
        return QRect()
    return QRect(left, top, right - left + 1, bottom - top + 1)


def _square_from_rect(rect, bounds):
    side = max(rect.width(), rect.height())
    square = QRect(
        rect.center().x() - side // 2,
        rect.center().y() - side // 2,
        side,
        side,
    )
    return square.intersected(bounds)


def _content_rect(image):
    left, top = image.width(), image.height()
    right, bottom = 0, 0
    for y in range(image.height()):
        for x in range(image.width()):
            color = image.pixelColor(x, y)
            if color.alpha() > 0 and not _is_background_white(color):
                left = min(left, x)
                top = min(top, y)
                right = max(right, x)
                bottom = max(bottom, y)
    if right <= left or bottom <= top:
        return image.rect()
    return QRect(left, top, right - left + 1, bottom - top + 1)


def _is_background_white(color):
    return color.red() > 246 and color.green() > 246 and color.blue() > 246


def _remove_white_background(image):
    processed = QImage(image.size(), QImage.Format_ARGB32)
    processed.fill(Qt.transparent)
    for y in range(image.height()):
        for x in range(image.width()):
            color = image.pixelColor(x, y)
            if color.alpha() == 0:
                continue
            luma = 0.2126 * color.red() + 0.7152 * color.green() + 0.0722 * color.blue()
            chroma = max(color.red(), color.green(), color.blue()) - min(color.red(), color.green(), color.blue())
            if luma > 250 and chroma < 8:
                continue
            if luma > 225 and chroma < 14:
                alpha = int(max(0, min(255, (255 - luma) * 5.0)))
                if alpha < 8:
                    continue
                color.setAlpha(alpha)
            processed.setPixelColor(x, y, color)
    return processed


def _apply_icon_mask(image):
    masked = QImage(image.size(), QImage.Format_ARGB32)
    masked.fill(Qt.transparent)
    painter = QPainter(masked)
    painter.setRenderHint(QPainter.Antialiasing)
    path = QPainterPath()
    path.addRoundedRect(0, 0, image.width(), image.height(), image.width() * 0.215, image.height() * 0.215)
    painter.setClipPath(path)
    painter.drawImage(0, 0, image)
    painter.end()
    return masked


def _render_png(master, size):
    image = QImage(size, size, QImage.Format_ARGB32)
    image.fill(Qt.transparent)
    painter = QPainter(image)
    painter.setRenderHint(QPainter.Antialiasing)
    painter.setRenderHint(QPainter.SmoothPixmapTransform)
    radius = max(4.0, size * 0.21)
    path = QPainterPath()
    path.addRoundedRect(0, 0, size, size, radius, radius)
    painter.setClipPath(path)
    inset = 0 if size <= 24 else max(1, round(size * 0.015))
    painter.drawImage(QRect(inset, inset, size - inset * 2, size - inset * 2), master)
    painter.end()

    data = QByteArray()
    buffer = QBuffer(data)
    buffer.open(QIODevice.WriteOnly)
    image.save(buffer, "PNG")
    buffer.close()
    return size, bytes(data)


def _write_ico(path, images):
    # ICO 目录项使用 PNG 载荷，能保留 256px 图标和透明通道。
    header_size = 6 + len(images) * 16
    offset = header_size
    directory = bytearray()
    payload = bytearray()
    for size, data in images:
        size_byte = 0 if size >= 256 else size
        directory.extend(bytes([size_byte, size_byte, 0, 0]))
        directory.extend((1).to_bytes(2, "little"))
        directory.extend((32).to_bytes(2, "little"))
        directory.extend(len(data).to_bytes(4, "little"))
        directory.extend(offset.to_bytes(4, "little"))
        payload.extend(data)
        offset += len(data)

    with path.open("wb") as fh:
        fh.write((0).to_bytes(2, "little"))
        fh.write((1).to_bytes(2, "little"))
        fh.write(len(images).to_bytes(2, "little"))
        fh.write(directory)
        fh.write(payload)


if __name__ == "__main__":
    raise SystemExit(main())
