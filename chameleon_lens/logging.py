"""运行时诊断数据记录。"""
import json
import time
from datetime import datetime
from pathlib import Path


LOG_DIR = Path(__file__).resolve().parents[1] / "logs"


class DebugDataRecorder:
    """按 JSONL 记录覆盖层诊断数据，避免 UI 和读取逻辑互相污染。"""

    def __init__(self, interval_seconds=1.0):
        self.interval_seconds = interval_seconds
        self._path = None
        self._last_write = 0.0

    @property
    def path(self):
        if self._path is None:
            stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            self._path = LOG_DIR / f"runtime_debug_{stamp}.jsonl"
        return self._path

    def write(self, payload):
        now = time.monotonic()
        if now - self._last_write < self.interval_seconds:
            return False
        self._last_write = now
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        item = {
            "time": datetime.now().isoformat(timespec="milliseconds"),
            **payload,
        }
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(item, ensure_ascii=False, separators=(",", ":")) + "\n")
        return True
