#!/usr/bin/env python3
"""从 SVG 生成 Windows ICO 图标。"""
import sys
from pathlib import Path

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QImage, QPainter
from PyQt5.QtSvg import QSvgRenderer


ROOT = Path(__file__).resolve().parents[1]
SVG_PATH = ROOT / "assets" / "chameleon.svg"
ICO_PATH = ROOT / "assets" / "chameleon.ico"


def main():
    renderer = QSvgRenderer(str(SVG_PATH))
    if not renderer.isValid():
        print(f"[错误] SVG 无法渲染：{SVG_PATH}")
        return 1

    image = QImage(256, 256, QImage.Format_ARGB32)
    image.fill(Qt.transparent)
    painter = QPainter(image)
    painter.setRenderHint(QPainter.Antialiasing)
    renderer.render(painter)
    painter.end()

    if not image.save(str(ICO_PATH), "ICO"):
        print(f"[错误] ICO 写入失败：{ICO_PATH}")
        return 1
    print(f"[Chameleon Lens] 已生成图标：{ICO_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
