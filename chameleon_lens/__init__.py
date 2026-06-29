"""Chameleon Lens 主程序包。"""
from .paths import PACKAGE_ROOT, SOURCE_ROOT


def _load_version() -> str:
    for path in (SOURCE_ROOT / "VERSION", PACKAGE_ROOT / "VERSION"):
        try:
            return path.read_text(encoding="utf-8").strip()
        except Exception:
            continue
    return "0.0.0"


__version__ = _load_version()
