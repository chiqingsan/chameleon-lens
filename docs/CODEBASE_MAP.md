# 代码地图

状态：当前参考文档。用途：保存目录结构、主要模块职责和运行入口。

## 根目录

- `README.md`：用户侧项目说明。
- `DEVELOPMENT.md`：当前二开约定和重要设计决策。
- `bootstrap.py`：启动器，创建 `.venv`、安装依赖并通过 `python -m chameleon_lens` 启动。
- `run.bat`：Windows 双击入口，转发到 `bootstrap.py`。
- `esp.py`：兼容入口，旧脚本仍可 `from esp import MecchaESP`。
- `requirements.txt`：运行依赖。
- `config.json`：用户配置，运行时自动生成和保存。
- `logs/`：调试采样日志。
- `tools/`：UI 概念稿渲染脚本。
- `docs/`：架构、代码地图、UI 概念和开发说明。
- `chameleon_lens/`：主程序包。

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
- 加载配置。
- 创建 `ESPRuntime`、`Menu` 和 `Overlay`。
- 管理自动重连定时器。
- 管理 Insert / F1 菜单显示热键轮询。

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
- 读取 PlayerState 显示名。
- 提供 `w2s()` 世界到屏幕投影。

### `chameleon_lens/config.py`

配置边界。

负责：

- `Config` dataclass。
- `load_config()`。
- `save_config()`。
- 保持配置文件在项目根目录 `config.json`。

### `chameleon_lens/runtime.py`

运行时连接状态。

负责：

- 保存当前 `MecchaESP` 实例。
- 记录连接状态和最近错误。
- 提供 `connect_once()`。

### `chameleon_lens/logging.py`

运行时诊断记录。

负责：

- 创建 `logs/runtime_debug_*.jsonl`。
- 限频写入覆盖层候选目标、过滤统计、相机、投影原因和最终绘制结果。

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

- 组装 `ESP / 雷达 / 外观 / 调试` 页签。
- 连接配置变更、预览刷新和自动保存。
- 手动重试连接。
- 标题栏拖动。

### `chameleon_lens/overlay.py`

透明覆盖层。

负责：

- 跟随游戏窗口位置和尺寸。
- 绘制目标点、标签、距离、射线和可选边缘提示。
- 绘制真实雷达，按相机 yaw 展示目标相对位置。
- 连接断开时通知运行时和菜单。

## 调试脚本

- `debug_life_state.py`：采集 PlayerArray、Level Character、display_name、名称候选和原始字段窗口，用于对比存活/阵亡；`names` 子命令用于扫描昵称候选字段。
- `debug_teams.py`：查看 PlayerArray 与 Level Actor 的基础结构。
- `diag_fname.py`、`find_prop_offsets.py`：定位 FName 和属性偏移。
