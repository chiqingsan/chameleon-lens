"""ESP 连接运行时状态。"""
from typing import Optional

from .reader import MecchaESP


# ---------------------------------------------------------------------------
# 运行状态
# ---------------------------------------------------------------------------
class ESPRuntime:
    def __init__(self):
        self.esp: Optional[MecchaESP] = None
        self.status = "等待游戏进程启动..."
        self.last_error = ""

    @property
    def connected(self):
        return self.esp is not None

    def connect_once(self):
        """尝试连接目标进程；失败只更新状态，避免启动阶段直接崩溃。"""
        try:
            self.esp = MecchaESP()
            self.status = "已连接到游戏"
            self.last_error = ""
            return True
        except Exception as exc:
            self.esp = None
            self.status = f"等待游戏进程启动：{MecchaESP.PROCESS_NAME}"
            self.last_error = str(exc)
            return False

