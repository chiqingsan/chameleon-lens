# 开发指南

状态：当前入口文档。用途：约束代码修改、验证和文档同步。

## 基本规则

- 所有文件读写使用 UTF-8。
- PowerShell 读取含中文文件时先执行 `chcp 65001`，并使用 `Get-Content -Encoding UTF8`。
- 代码注释使用中文，关键业务分支要写清楚原因。
- 重要代码改动后同步 `README.md`、`DEVELOPMENT.md` 或 `docs/`。
- 不要新增根目录兼容入口或临时转发脚本；新业务按职责写入 `chameleon_lens` 包内模块。

## 代码组织原则

- 内存读写和 UE 基础结构放在 `chameleon_lens.memory`。
- 游戏对象、目标枚举、死亡过滤和坐标投影放在 `chameleon_lens.reader`。
- 配置读写放在 `chameleon_lens.config`。
- 连接状态放在 `chameleon_lens.runtime`。
- 自绘控件和预览放在 `chameleon_lens.ui.widgets`。
- 菜单页面组装放在 `chameleon_lens.ui.menu`。
- 透明覆盖层绘制放在 `chameleon_lens.overlay`。
- 雷达坐标转换放在 `chameleon_lens.radar`，覆盖层只负责画出来。
- Qt 应用启动和定时器放在 `chameleon_lens.app`。

## 修改前判断

动手前先问：

- 这是 UI 展示、内存读取、配置、覆盖层绘制还是启动流程？
- 是否必须依赖 Qt？不依赖 Qt 的逻辑不要放到 UI 模块。
- 是否影响 `reader.iter_players()`？如果影响，先开启运行日志并用 `tools/analyze_runtime_debug.py` 汇总现象。
- 是否改变用户可见配置、快捷键、日志或启动方式？如果改变，需要同步文档。

## 测试分级

文档或纯 UI 文案改动：

```bat
.\.venv\Scripts\python.exe -m compileall -q main.py chameleon_lens
```

涉及配置、入口或模块拆分：

```bat
.\.venv\Scripts\python.exe -m compileall -q main.py bootstrap.py chameleon_lens tools
```

涉及打包或启动脚本：

```bat
run.bat --check-only
build_nuitka.bat
```

- Nuitka 打包版配置和日志应写入 `%LOCALAPPDATA%\Chameleon Lens`，不要写入 onefile 临时目录。

涉及 UI 布局：

- 本仓库不再保存 UI 截图资产；修改后直接运行菜单检查主窗口、ESP 两列布局、雷达页、外观页横向色板和调色板交互。
- 如需临时截图用于讨论，保存在本地临时目录，不提交到仓库。

涉及目标过滤：

- 开启调试页“数据记录”，分别保存存活和阵亡场景的运行日志。
- 用 `tools/analyze_runtime_debug.py` 汇总最新日志，必要时再补充专门诊断脚本。
- 对比 PlayerArray、Level Actor、`player_state`、`controller`、`display_name` 和位置变化。
- 如果是“漏绘制”或卡顿，优先开启调试页“数据记录”，检查 `logs/runtime_debug_*.jsonl` 中的 `performance`、`stats`、`projection_reasons`、`player_array_debug`、`level_actor_debug`、`emitted_targets` 和 `targets[].projection`。
- 定位顺序：先看 `performance.sample_ms` 和 `performance.paint_ms`，确认压力来自采样还是绘制；再看 `pa_dead` 是否异常增加，它表示 PlayerArray pawn 类名包含 `Spectate` 且没有找到可用真实 Character。再看 `pa_linked` 与 `player_array_debug[].spectate_link`，它表示 `SpectatePawn` 指向了仍可绘制的真实 Character。接着看 `player_array_debug[].reason` 是否大量出现 `no_pawn`、`dead_or_spectator`；然后看 `role/stable_role/filter_role` 是否发生身份切换或防抖；最后看 `emitted_targets[].position_source`、`targets[].reason` 和 `edge_reasons`。`behind_camera` / `outside_view*` 代表目标已读到但不在当前屏幕内；开启“边缘提示”时覆盖层会把这些目标钳到屏幕边缘绘制，若仍异常再检查坐标源或相机数据。
- 可以用 `tools/analyze_runtime_debug.py` 汇总最新日志：`.\.venv\Scripts\python.exe tools\analyze_runtime_debug.py`。
- 当前覆盖层只使用 PlayerArray；`SpectatePawn` 会先尝试解析真实 Character 链接，未命中时才作为死亡/观战跳过依据。`pa_suspect` 只表示 PlayerArray pawn 反向绑定异常，不再作为跳过依据。
- `SpectatePawn` 可能是观战壳，也可能仍链接一个真实躲藏者 Character；当前已用 `SpectatePawn + 0x1A0` 做保守兜底，只有真实 Character 的 `LastMyPlayerState` 或 `APawn::PlayerState` 匹配当前 PlayerState 且 `Dead=0` 时才绘制。
- 不要用“目标静止不动”作为死亡判定依据；本游戏是躲猫猫类玩法，静止是正常行为。
- 角色/形态只来自 class 名称：`Hunter`、`Survivor`、`Spectate` 和 `Cube`、`Base` 等 token 会进入 `role/form`。同一局不同模式下身份会合法切换，不能永久锁定“曾经是躲藏者”的身份。
- `stable_role` 和 `filter_role` 是 PlayerState 级短时身份防抖结果；关闭“猎人 ESP”时覆盖层按 `filter_role` 过滤，而不是直接用瞬时 `role`。
- `player_state` 或 `pawn` 指针会生成 `short_id`，比 PlayerArray 的 `idx` 更适合作为临时目标标识；UI 显示为“玩家 短 ID”，不使用 `#xxxxxx` 格式。
- `position_jumps` 表示同一目标位置大跳变，通常是回合重置、地图切换或目标实例重建；出现时相关缓存会被清理。

涉及玩家昵称：

- 覆盖层名称读取顺序为 `CustomPlayerName` FText/FString、`PlayerNamePrivate` FString、“玩家 短 ID”、`PlayerId`，最后回退为“目标 N”。
- 名称必须通过自然昵称过滤：中文、英文、数字和少量昵称符号可显示；蓝图名、材质名、对象名和乱码候选必须过滤。
- 日常绘制会短时缓存 PlayerState 名称；只有开启“数据记录”时才写入完整 `name_candidates`。
- 开启调试页“数据记录”后，先看 `player_array_debug[].name_candidates`、`display_name_source` 和 `display_name_reader`。
- 如果日志里没有 accepted 名称，先保留最新 `runtime_debug_*.jsonl`，再根据日志补充 `tools/` 下的专项昵称扫描脚本。

## 后续拆分原则

- 先拆高变化、高风险模块，不为单行转发制造抽象。
- `ui.widgets` 超过当前体量后，优先拆成 `controls.py`、`previews.py`、`dialogs.py`。
- `TargetSnapshot` 已作为 `reader.iter_players()` 输出结构；后续新增目标字段优先扩展 dataclass，不再扩展裸元组。
- 雷达坐标转换已经拆出 `overlay`；后续若继续扩展，保持 `radar.py` 只做纯计算，`overlay.py` 只做绘制。
