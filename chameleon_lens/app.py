"""应用组合根和 Qt 入口。"""
import ctypes
import sys

from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QTimer

from .config import load_config, save_config
from .runtime import ESPRuntime
from .ui.menu import Menu
from .overlay import Overlay


ERROR_ALREADY_EXISTS = 183
SINGLE_INSTANCE_MUTEX = "Global\\ChameleonLensMecchaEsp"


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
def _set_dpi_aware():
    try:
        ctypes.windll.user32.SetProcessDpiAwarenessContext(-4)  # PerMonitorAwareV2
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass


def _acquire_single_instance():
    """使用 Windows 命名互斥体保证覆盖层只运行一个实例。"""
    try:
        kernel32 = ctypes.windll.kernel32
        kernel32.SetLastError(0)
        handle = kernel32.CreateMutexW(None, False, SINGLE_INSTANCE_MUTEX)
        if not handle:
            return None, False
        already_exists = kernel32.GetLastError() == ERROR_ALREADY_EXISTS
        return handle, not already_exists
    except Exception:
        # 单例保护失败时不要阻塞主程序，避免极端系统环境下无法启动。
        return None, True


def main():
    mutex_handle, is_first_instance = _acquire_single_instance()
    if not is_first_instance:
        print("[Chameleon Lens] 已有实例正在运行。")
        return 0

    _set_dpi_aware()
    app = QApplication(sys.argv)
    config = load_config()
    app.aboutToQuit.connect(lambda: save_config(config))
    runtime = ESPRuntime()
    runtime.connect_once()
    menu = Menu(config, runtime)
    overlay = Overlay(runtime, config, menu.refresh_status)
    overlay.show()
    menu.show()

    def retry_connect():
        if not runtime.connected:
            runtime.connect_once()
            menu.refresh_status()

    connect_timer = QTimer()
    connect_timer.timeout.connect(retry_connect)
    connect_timer.start(2000)

    # 全局轮询 Insert/F1，用于在游戏窗口上方快速显示或隐藏菜单。
    VK_INSERT = 0x2D
    VK_F1 = 0x70
    _key_states = {"insert": False, "f1": False}

    def poll_keys():
        for vk, name in [(VK_INSERT, "insert"), (VK_F1, "f1")]:
            state = ctypes.windll.user32.GetAsyncKeyState(vk) & 0x8000
            if state and not _key_states[name]:
                menu.setVisible(not menu.isVisible())
            _key_states[name] = bool(state)

    key_timer = QTimer()
    key_timer.timeout.connect(poll_keys)
    key_timer.start(50)

    exit_code = app.exec_()
    if mutex_handle:
        ctypes.windll.kernel32.CloseHandle(mutex_handle)
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
