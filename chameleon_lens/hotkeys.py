"""全局快捷键名称与 Windows VK 映射。"""

KEY_NAME_TO_VK = {
    "BACKSPACE": 0x08,
    "TAB": 0x09,
    "ENTER": 0x0D,
    "ESCAPE": 0x1B,
    "SPACE": 0x20,
    "PAGEUP": 0x21,
    "PAGEDOWN": 0x22,
    "END": 0x23,
    "HOME": 0x24,
    "LEFT": 0x25,
    "UP": 0x26,
    "RIGHT": 0x27,
    "DOWN": 0x28,
    "INSERT": 0x2D,
    "DELETE": 0x2E,
}

for _index in range(1, 13):
    KEY_NAME_TO_VK[f"F{_index}"] = 0x70 + _index - 1
for _code in range(ord("A"), ord("Z") + 1):
    KEY_NAME_TO_VK[chr(_code)] = _code
for _code in range(ord("0"), ord("9") + 1):
    KEY_NAME_TO_VK[chr(_code)] = _code

HOTKEY_ALIASES = {
    "": "",
    "NONE": "",
    "NULL": "",
    "ESC": "ESCAPE",
    "RETURN": "ENTER",
    "INS": "INSERT",
    "DEL": "DELETE",
    "PGUP": "PAGEUP",
    "PGDN": "PAGEDOWN",
}


def normalize_hotkey(value) -> str:
    key = str(value or "").strip().upper().replace(" ", "")
    key = HOTKEY_ALIASES.get(key, key)
    return key if key in KEY_NAME_TO_VK else ""


def hotkey_to_vk(value):
    key = normalize_hotkey(value)
    return KEY_NAME_TO_VK.get(key)


def hotkey_display(value) -> str:
    return normalize_hotkey(value) or "未设置"
