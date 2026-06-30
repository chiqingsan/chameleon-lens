"""应用组合根和 Qt 入口。"""
import ctypes
import sys

from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QTimer
from PyQt5.QtGui import QIcon

from .config import load_config, save_config
from .hotkeys import hotkey_to_vk, normalize_hotkey
from . import __version__
from .paths import APP_ICON_PATH
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
    if "--version" in sys.argv:
        print(__version__)
        return 0

    mutex_handle, is_first_instance = _acquire_single_instance()
    if not is_first_instance:
        print("[Chameleon Lens] 已有实例正在运行。")
        return 0

    _set_dpi_aware()
    app = QApplication(sys.argv)
    if APP_ICON_PATH.exists():
        app.setWindowIcon(QIcon(str(APP_ICON_PATH)))
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

    _key_states = {}

    def _toggle_config_attr(attr, source):
        setattr(config, attr, not bool(getattr(config, attr)))
        config._last_change_source = {"field": attr, "source": source}

    def poll_keys():
        if menu.is_capturing_hotkey():
            _key_states.clear()
            return
        actions = [
            ("menu", config.hotkey_menu_toggle, lambda: menu.setVisible(not menu.isVisible())),
            ("overlay", config.hotkey_overlay_toggle, lambda: _toggle_config_attr("enabled", "hotkey:overlay")),
            ("esp", config.hotkey_esp_toggle, lambda: _toggle_config_attr("esp_enabled", "hotkey:esp")),
            ("radar", config.hotkey_radar_toggle, lambda: _toggle_config_attr("radar_enabled", "hotkey:radar")),
        ]
        for name, key, action in actions:
            key = normalize_hotkey(key)
            vk = hotkey_to_vk(key)
            if not vk:
                _key_states.pop(name, None)
                continue
            state = ctypes.windll.user32.GetAsyncKeyState(vk) & 0x8000
            if state and not _key_states.get(name, False):
                action()
                menu.sync_controls_from_config()
                save_config(config)
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
