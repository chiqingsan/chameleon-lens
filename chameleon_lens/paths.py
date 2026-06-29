"""运行路径与资源路径边界。"""
import os
import sys
from pathlib import Path


APP_NAME = "Chameleon Lens"
PACKAGE_ROOT = Path(__file__).resolve().parent
SOURCE_ROOT = PACKAGE_ROOT.parent
DATA_DIR_ENV = "CHAMELEON_LENS_DATA_DIR"


def is_packaged() -> bool:
    try:
        __compiled__  # type: ignore[name-defined]
        return True
    except NameError:
        return bool(getattr(sys, "frozen", False))


def _local_app_data_dir() -> Path:
    base = os.environ.get("LOCALAPPDATA")
    if base:
        return Path(base) / APP_NAME
    return Path.home() / "AppData" / "Local" / APP_NAME


def app_data_dir() -> Path:
    override = os.environ.get(DATA_DIR_ENV)
    if override:
        return Path(override).expanduser()
    if is_packaged():
        return _local_app_data_dir()
    return SOURCE_ROOT


def resource_root() -> Path:
    return SOURCE_ROOT


DATA_DIR = app_data_dir()
CONFIG_PATH = DATA_DIR / "config.json"
LOG_DIR = DATA_DIR / "logs"
ASSET_DIR = resource_root() / "assets"
APP_ICON_PATH = ASSET_DIR / "chameleon.ico"
APP_LOGO_PATH = ASSET_DIR / "chameleon_logo.png"
