"""用户配置读写边界。"""
import json
from dataclasses import asdict, dataclass, fields
from pathlib import Path
from typing import Tuple


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
CONFIG_PATH = Path(__file__).resolve().parents[1] / "config.json"
CONFIG_VERSION = 2
UI_OPACITY_MIN = 70
UI_OPACITY_MAX = 96
LEGACY_DEFAULT_COLORS = {
    "enemy_color": (255, 0, 0),
    "hunter_color": (255, 84, 84),
    "local_color": (0, 255, 0),
}


@dataclass
class Config:
    config_version: int = CONFIG_VERSION
    enabled: bool = True
    esp_enabled: bool = True
    show_hunter_esp: bool = True
    box_esp: bool = True  # 当前绘制圆点，不再绘制旧版方框。
    show_local: bool = True
    show_names: bool = True
    show_distance: bool = True
    snap_lines: bool = True
    show_local_snap_line: bool = False
    show_edge_indicators: bool = True
    enemy_color: Tuple[int, int, int] = (248, 113, 113)
    hunter_color: Tuple[int, int, int] = (251, 113, 133)
    survivor_color: Tuple[int, int, int] = (94, 234, 212)
    local_color: Tuple[int, int, int] = (52, 211, 153)
    dot_radius: int = 8
    show_debug: bool = False
    record_debug_data: bool = False
    ui_opacity: int = 94

    # 雷达根据相机朝向绘制目标相对位置。
    radar_enabled: bool = True
    radar_range: int = 80
    radar_size: int = 180
    radar_opacity: int = 68
    radar_position: str = "右上角"


def _coerce_color(value, default):
    if not isinstance(value, (list, tuple)) or len(value) != 3:
        return default
    try:
        return tuple(max(0, min(255, int(v))) for v in value)
    except Exception:
        return default


def load_config(path: Path = CONFIG_PATH) -> Config:
    config = Config()
    if not path.exists():
        return config
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return config
    if not isinstance(data, dict):
        return config

    try:
        file_version = int(data.get("config_version", 1))
    except Exception:
        file_version = 1

    known_fields = {field.name for field in fields(Config)}
    for key, value in data.items():
        if key not in known_fields:
            continue
        default = getattr(config, key)
        try:
            if key.endswith("_color"):
                setattr(config, key, _coerce_color(value, default))
            elif isinstance(default, bool):
                setattr(config, key, bool(value))
            elif isinstance(default, int):
                setattr(config, key, int(value))
            elif isinstance(default, float):
                setattr(config, key, float(value))
            elif isinstance(default, str):
                setattr(config, key, str(value))
        except Exception:
            # 配置文件允许用户手动编辑，单个字段坏了就回退默认值。
            continue
    if file_version < CONFIG_VERSION:
        _migrate_config(config, file_version)
    config.ui_opacity = max(UI_OPACITY_MIN, min(UI_OPACITY_MAX, int(config.ui_opacity)))
    config.config_version = CONFIG_VERSION
    return config


def _migrate_config(config: Config, file_version: int):
    if file_version < 2:
        defaults = Config()
        # 只迁移精确等于旧默认值的颜色，避免覆盖用户手动挑过的配色。
        for attr, legacy_color in LEGACY_DEFAULT_COLORS.items():
            if getattr(config, attr) == legacy_color:
                setattr(config, attr, getattr(defaults, attr))


def save_config(config: Config, path: Path = CONFIG_PATH) -> bool:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = path.with_suffix(path.suffix + ".tmp")
        tmp_path.write_text(
            json.dumps(asdict(config), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        tmp_path.replace(path)
        return True
    except Exception:
        return False
