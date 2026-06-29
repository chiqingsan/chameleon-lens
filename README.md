# Chameleon Lens

`Chameleon Lens` 是基于 `meccha-esp-master` 的二次开发版本，用于 MECCHA CHAMELEON 的外部覆盖层实验。项目保持纯外部读取方式：不注入 DLL，不依赖 UE4SS，通过 `pymem` 读取游戏进程内存并用 PyQt5 绘制透明覆盖层。

> 本项目仅用于学习、研究和 UI/外部覆盖层技术实验。使用第三方工具可能违反游戏服务条款，请自行承担风险。

## 当前功能

- 现代化深色浮动菜单，支持拖动和置顶。
- 菜单、覆盖层状态和目标标签已汉化。
- 游戏进程未启动时不再报错退出，菜单显示等待状态并每 2 秒自动重试连接，覆盖层保持透明。
- 应用使用单例运行，重复启动时会直接退出，不会叠加多个覆盖层。
- 覆盖层绘制、目标采样和窗口位置更新分离，减少每帧重复读内存和查找窗口带来的卡顿。
- 提供一键启动批处理，会自动创建 `.venv` 并安装依赖；依赖未变化时会直接快速启动。
- 横向精简仪器面板，顶部页签按 ESP、雷达、外观、快捷键、调试组织，运行状态显示在标题栏右上角。
- 雷达预览使用开放 HUD 画布，仅保留角标、雷达环和目标点，不再绘制横竖底线或堆叠内层卡片。
- 菜单仅标题栏可拖动，右上角关闭按钮会退出程序。
- 自绘连接状态胶囊、动画开关、hover 按钮和可点击滑条，避免系统默认控件破坏整体质感。
- 自定义深色颜色选择面板，不调用系统默认颜色对话框。
- 支持独立 ESP 绘制、猎人 ESP 过滤、目标圆点、边缘提示、名称标签、距离标签、本地标记、ESP 射线、自身射线、真实雷达和调试计数开关。
- 名称标签会优先尝试读取 PlayerState 玩家昵称；读取不到昵称时自动回退为“玩家 短 ID”、玩家 ID 或“目标 N”，避免 `#xxxxxx` 看起来像颜色值。
- 阵亡/观战过滤以 PlayerArray 中的 `SpectatePawn` 类名为主，调试统计中计入 `pa_dead`；如果 `SpectatePawn` 仍指向一个 `Dead=0` 且 `LastMyPlayerState` 匹配的真实 Character，会改用该 Character 绘制并计入 `pa_linked`。猎人 ESP 过滤会做短时身份防抖，避免瞬时 `Hunter` 抖动立刻隐藏目标。
- 可按类名区分猎人、躲藏者和变身形态，外观页支持用横向色板分别配置猎人、躲藏者、本地和默认目标颜色。
- 菜单设置会自动保存，源码运行时写入项目根目录 `config.json`，打包版写入 `%LOCALAPPDATA%\Chameleon Lens\config.json`。
- 快捷键页支持配置菜单显隐、覆盖层总开关、ESP 绘制和雷达面板开关；菜单显隐默认 `F1`，其余默认不启用。
- 外观页支持恢复默认外观，方便快速回退颜色、圆点半径和菜单透明度。
- 调试页支持开启“数据记录”，并可一键打开日志目录；日志会在 `logs/runtime_debug_*.jsonl` 中记录采样/绘制耗时、候选目标、过滤统计、投影原因、边缘提示原因、角色形态和位置大跳变。

## 环境要求

- Windows 10/11
- Python 3.11+
- 游戏使用窗口化或无边框窗口模式

## 快速开始

```bash
run.bat
```

1. 双击 `run.bat`。
2. 如果游戏尚未启动，程序会保持运行并在标题栏显示“未连接 · 等待进程”。
3. 启动 MECCHA CHAMELEON 后，覆盖层会自动尝试连接目标进程。
4. 默认按 **F1** 显示/隐藏菜单，也可以在“快捷键”页修改。
5. 在菜单中调整 ESP 显示、雷达、外观颜色、快捷键和调试信息。

ESP 页只负责屏幕 ESP、目标点、标签和射线开关；雷达设置统一放在“雷达”页。关闭“ESP 绘制”只会隐藏屏幕 ESP，雷达仍由“雷达面板”独立控制。

首次运行时，批处理会自动检查 Python 3.11+、创建 `.venv`、安装 `requirements.txt` 中的依赖，然后通过 `python -m chameleon_lens` 启动主程序。根目录不再保留旧版 `esp.py` 兼容入口；Nuitka 打包使用 `main.py` 作为干净入口。

后续运行时，如果 `.venv` 已存在且 `requirements.txt` 未变化，`run.bat` 会跳过启动器和 pip 检查，直接进入主程序。需要生成可执行文件时运行 `build_nuitka.bat`，输出位于 `dist\ChameleonLens.exe`。

## 开发与打包

```bash
run.bat --check-only
python -m chameleon_lens --version
build_nuitka.bat
```

- 源码运行配置写入项目根目录 `config.json`，该文件不提交到 Git。
- 源码运行日志写入 `logs/runtime_debug_*.jsonl`，日志文件不提交到 Git。
- 打包版配置和日志写入 `%LOCALAPPDATA%\Chameleon Lens`。

## 目录结构

- `chameleon_lens/`：主程序包。
- `assets/`：应用图标资源和来源说明。
- `docs/`：架构、开发指南、代码地图和 UI 设计记录。
- `tools/`：日志分析、图标生成等维护工具。
- `run.bat`：日常启动入口。
- `bootstrap.py`：启动前置脚本，负责虚拟环境和依赖检查。
- `main.py`：Nuitka 打包入口。
- `build_nuitka.bat`：打包脚本。

## 注意事项

- 目标进程名当前为 `PenguinHotel-Win64-Shipping.exe`。
- 游戏窗口标题当前按 `Chameleon  ` 查找；如果后续版本标题变化，需要更新 `Overlay._find_game_window()`。
- 偏移和特征码来自当前 UE5.6 构建，游戏更新后可能需要重新定位。
- 上传公开仓库前请确认上游项目授权，并补充合适的 `LICENSE` 文件。
