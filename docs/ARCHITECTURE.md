# 架构方向

状态：当前入口文档。用途：说明模块边界、依赖方向和后续拆分优先级。

## 当前总体结构

项目已经从单文件结构拆为 `chameleon_lens` 包。根目录不再保留旧版 `esp.py` 兼容入口；源码运行使用 `python -m chameleon_lens`，Nuitka 打包使用 `main.py` 进入同一个应用组合根。

- `chameleon_lens.memory`：UE 基础内存读取、偏移解析、FName、UObjectArray 和安全读写原语。
- `chameleon_lens.reader`：MECCHA CHAMELEON 读取器、玩家枚举、`TargetSnapshot`、死亡/观战过滤、角色形态分类、位置跳变检测和世界到屏幕投影。
- `chameleon_lens.config`：JSON 配置模型、读取和保存。
- `chameleon_lens.runtime`：目标进程连接状态。
- `chameleon_lens.ui.widgets`：自绘 PyQt 控件、预览组件和颜色选择面板。
- `chameleon_lens.ui.menu`：主控制菜单和页面组装。
- `chameleon_lens.overlay`：透明覆盖层绘制、目标标签、射线和雷达。
- `chameleon_lens.radar`：雷达坐标转换，把世界坐标投影到以相机朝向为正上方的雷达盘面。
- `chameleon_lens.app`：Qt 应用组合根、单例互斥、定时器、热键轮询和启动流程。
- `chameleon_lens.logging`：运行时 JSONL 诊断记录，当前用于覆盖层候选目标和投影排错。

## 目标依赖方向

```text
app -> ui.menu -> ui.widgets
app -> overlay -> reader -> memory
overlay -> radar
app -> runtime -> reader
ui.menu -> config/runtime
overlay -> config/runtime/reader
config -> 标准库
memory -> pymem/标准库
radar -> 标准库
```

约束：

- `memory` 不依赖 PyQt，不读写配置。
- `reader` 不创建 QWidget，不直接操作菜单。
- `config` 不依赖 PyQt、pymem 或 Windows API。
- `ui.widgets` 只负责展示和控件交互，不直接连接游戏进程。
- `ui.menu` 可以读写配置、刷新预览，但不做内存扫描。
- `overlay` 只消费 `Config`、`ESPRuntime` 和 `reader` 输出，不直接构建菜单页面。
- `radar` 只做坐标转换，不依赖 Qt、配置对象或内存读取。
- 根目录不新增兼容导出脚本；需要复用能力时从 `chameleon_lens` 包内明确导入。

## 当前风险点

- `chameleon_lens.ui.widgets` 和 `chameleon_lens.ui.menu` 仍然偏大，这是第一阶段拆分后的自然过渡状态。
- `reader.iter_players()` 是目标过滤核心，改动前应优先开启运行日志并用 `tools/analyze_runtime_debug.py` 汇总现象。
- 覆盖层仍负责雷达绘制，但雷达坐标转换已经拆到 `chameleon_lens.radar`。
- 启动器和打包脚本都已指向新入口，旧脚本依赖不再作为兼容目标。

## 演进路线

短期：

- 新功能不写进根目录入口文件，按职责落到 `chameleon_lens` 包内模块。
- 真实雷达优先新增到 `reader` 的目标数据模型、`radar` 的坐标转换和 `overlay` 的雷达绘制，不直接塞进菜单。
- UI 小控件继续放在 `ui.widgets`，页面级布局放在 `ui.menu`。

中期：

- 将 `ui.widgets` 继续拆成 `controls.py`、`previews.py`、`dialogs.py`。
- 继续收敛 `TargetSnapshot` 的字段语义，避免 UI 和覆盖层重新依赖裸元组。
- 增加 `logs` 模块，把连接错误、过滤统计和采样摘要写入运行日志。

长期：

- `reader` 和死亡过滤逻辑可以脱离 Qt 做回放测试。
- 雷达成为独立功能层：目标转换、缩放、旋转和绘制分开。
- 入口、配置、调试、UI 和覆盖层都有清晰边界，方便后续打包发布。
