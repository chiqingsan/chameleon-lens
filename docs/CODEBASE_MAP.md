# 代码地图

状态：当前参考文档。用途：保存目录结构、主要模块职责和运行入口。

## 根目录

- `README.md`：用户侧项目说明。
- `DEVELOPMENT.md`：当前二开约定和重要设计决策。
- `VERSION`：应用版本号。
- `bootstrap.py`：启动器，创建 `.venv`、按依赖哈希安装依赖并通过 `python -m chameleon_lens` 启动。
- `run.bat`：Windows 双击入口，依赖未变化时直接快速启动，必要时转发到 `bootstrap.py`。
- `main.py`：Nuitka 打包入口，转入 `chameleon_lens.app.main()`。
- `build_nuitka.bat`：Nuitka 打包脚本，使用 `main.py` 生成 `dist\ChameleonLens.exe` 并清理中间目录。
- `assets/`：应用图标 SVG/ICO 和资产说明。
- `requirements.txt`：运行依赖。
- `tools/`：日志分析和图标生成等正式维护工具。
- `docs/`：架构、代码地图、UI 概念和开发说明。
- `chameleon_lens/`：主程序包。

## 运行时生成目录

- `config.json`：源码运行时用户配置，已在 `.gitignore` 忽略。
- `logs/runtime_debug_*.jsonl`：源码运行时调试日志，已在 `.gitignore` 忽略。
- `dist/`：Nuitka 打包输出目录，已在 `.gitignore` 忽略。
- `.venv/`：本地虚拟环境，已在 `.gitignore` 忽略。

## 主程序包

### `chameleon_lens/__main__.py`

允许通过以下方式启动：

```bat
python -m chameleon_lens
```

### `chameleon_lens/app.py`

应用组合根。

负责：

- 设置 DPI 感知。
- 使用 Windows 命名互斥体保证单例运行。
- 创建 `QApplication`。
- 设置应用图标。
- 加载配置。
- 创建 `ESPRuntime`、`Menu` 和 `Overlay`。
- 管理自动重连定时器。
- 管理可配置全局快捷键轮询，默认 `F1` 控制菜单显隐。

### `chameleon_lens/memory.py`

底层内存设施。

负责：

- `OFFSETS` 基础布局。
- `OffsetResolver` 动态偏移解析。
- `rp`、`ru32`、`rvec3`、`read_array`、`read_fstring` 等安全读写原语。
- `PatternScanner`。
- `FNameResolver`。
- `UObjectArray`。

### `chameleon_lens/reader.py`

游戏读取器。

负责：

- 扫描 `GUObjectArray` 和 `FNamePool`。
- 解析世界、相机、本地控制器。
- 枚举目标玩家。
- 对 `SpectatePawn` 先尝试解析真实 Character 链接；命中计入 `pa_linked` 并绘制，未命中才计入 `pa_dead` 作为死亡或观战跳过。
- 按 class 名称推断猎人、躲藏者和变身形态。
- 为目标生成 `short_id`，并用位置大跳变识别回合/地图切换。
- 读取并短时缓存 PlayerState 显示名。
- 提供 `w2s()` 世界到屏幕投影。

### `chameleon_lens/config.py`

配置边界。

负责：

- `Config` dataclass。
- `load_config()`。
- `save_config()`。
- 通过 `chameleon_lens.paths.CONFIG_PATH` 决定配置文件位置。
- 保存快捷键配置字段，启动时归一化为可识别按键名。

### `chameleon_lens/paths.py`

运行路径边界。

负责：

- 区分源码运行和 Nuitka 打包运行。
- 源码运行时把配置和日志放在项目根目录。
- 打包运行时把配置和日志放在 `%LOCALAPPDATA%\Chameleon Lens`。
- 暴露应用图标资源路径。

### `chameleon_lens/hotkeys.py`

全局快捷键名称映射。

负责：

- 归一化菜单录入的按键名称。
- 把按键名称转换为 Windows VK 值。
- 提供快捷键按钮显示文本。

### `chameleon_lens/runtime.py`

运行时连接状态。

负责：

- 保存当前 `MecchaESP` 实例。
- 记录连接状态和最近错误。
- 提供 `connect_once()`。

### `chameleon_lens/logging.py`

运行时诊断记录。

负责：

- 在当前运行日志目录创建 `runtime_debug_*.jsonl`。
- 限频写入覆盖层候选目标、过滤统计、相机、投影原因和最终绘制结果。

### `chameleon_lens/radar.py`

雷达坐标模型。

负责：

- 按相机 yaw 把目标相对位置转换到雷达盘面。
- 计算点位、距离和是否钳到雷达边缘。
- 保持纯计算，不依赖 Qt、配置对象或内存读取。

### `chameleon_lens/ui/widgets.py`

自绘 UI 控件集合。

负责：

- 开关、页签、按钮、关闭按钮、滑条、下拉框。
- 状态胶囊、Logo、SmoothFrame。
- ESP / 雷达 / 外观预览。
- 颜色选择面板。

### `chameleon_lens/ui/menu.py`

主菜单。

负责：

- 组装 `ESP / 雷达 / 外观 / 快捷键 / 调试` 页签。
- 连接配置变更、预览刷新和自动保存。
- 手动重试连接。
- 打开当前日志目录。
- 录入菜单显隐、覆盖层总开关、ESP 绘制和雷达面板快捷键。
- 标题栏拖动。

### `chameleon_lens/overlay.py`

透明覆盖层。

负责：

- 跟随游戏窗口位置和尺寸。
- 分离窗口几何刷新、目标快照采样和覆盖层绘制节奏。
- 绘制目标点、标签、距离、射线和可选边缘提示。
- 绘制真实雷达，按相机 yaw 展示目标相对位置。
- 在调试日志中记录采样耗时、绘制耗时和刷新间隔。
- 连接断开时通知运行时和菜单。

## 维护工具

- `tools/analyze_runtime_debug.py`：汇总运行日志，辅助判断漏绘制、过滤和投影问题。
- `tools/generate_app_icon.py`：从 SVG 生成 Windows ICO 图标。
