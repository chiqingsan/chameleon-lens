#!/usr/bin/env python3
"""兼容入口：旧脚本仍可从 esp 导入，实际实现已拆到 chameleon_lens 包。"""

from chameleon_lens.app import main
from chameleon_lens.config import CONFIG_PATH, Config, load_config, save_config
from chameleon_lens.memory import (
    OFFSETS, FNameResolver, OffsetResolver, PatternScanner, UObjectArray,
    dist, read_array, read_fstring, read_ftext, rfloat, rp, rrot, ru16, ru32,
    rvec3, wfloat,
)
from chameleon_lens.overlay import Overlay
from chameleon_lens.reader import MecchaESP, rotation_to_axes, w2s
from chameleon_lens.runtime import ESPRuntime
from chameleon_lens.ui.menu import Menu

__all__ = [
    "CONFIG_PATH", "Config", "ESPRuntime", "FNameResolver", "MecchaESP",
    "Menu", "OFFSETS", "OffsetResolver", "Overlay", "PatternScanner",
    "UObjectArray", "dist", "load_config", "main", "read_array",
    "read_fstring", "read_ftext", "rfloat", "rp", "rrot", "ru16", "ru32", "rvec3",
    "rotation_to_axes", "save_config", "w2s", "wfloat",
]


if __name__ == "__main__":
    main()
