# Chameleon Lens 开发文档

## 维护目标

本项目基于 `meccha-esp-master` 做二次开发，当前仓库只保留整理后的 Chameleon Lens 代码、文档和维护工具。后续功能修改应优先落在 `chameleon_lens/` 包内，避免重新回到单文件入口或散落脚本结构。公开发布前需要确认上游授权，并补充合适的 `LICENSE` 文件。

当前阶段目标：

1. 聚焦 `ESP + 雷达`，不再扩展辅助瞄准或其他战斗功能。
2. 提升 PyQt5 菜单和覆盖层状态提示的现代感。
3. 将用户可见文本汉化。
4. 目标游戏进程未启动、退出或暂时不可读时，程序保持运行并给出等待状态。

## 代码结构

- `chameleon_lens/`：主程序包，按内存读取、目标读取、配置、运行时、UI、覆盖层和入口拆分。
- `chameleon_lens/radar.py`：雷达坐标转换，把目标相对相机位置投影到雷达盘面。
- `main.py`：Nuitka 打包入口，源码开发和日常启动优先使用 `python -m chameleon_lens`。
- `run.bat`：Windows 一键启动脚本，检测到 `.venv` 和依赖 stamp 后直接快速启动；首次运行、缺少 stamp 或手动 `--check-only` 时转交 `bootstrap.py`。
- `bootstrap.py`：启动器，负责创建 `.venv`、按 `requirements.txt` 哈希安装依赖，最终通过 `python -m chameleon_lens` 进入主程序。
- `build_nuitka.bat`：Nuitka 打包脚本，输出 `dist\ChameleonLens_版本号_HHmm.exe`，成功后清理 Nuitka 中间目录。
- `chameleon_lens/_version.py`：应用版本号单一来源。
- `assets/`：应用图标资源；`app.png` 是源图，`chameleon.ico` 和 `chameleon_logo.png` 由工具脚本裁切、透明化并生成。
- `requirements.txt`：运行依赖清单，由启动脚本自动安装到 `.venv`。
- `docs/ARCHITECTURE.md`：当前模块边界和依赖方向。
- `docs/CODEBASE_MAP.md`：项目文件地图。
- `docs/DEVELOPMENT_GUIDE.md`：修改、验证和文档同步规则。
- `docs/UI_CONCEPT.md`：UI 概念方向和当前落地说明，仅保留文字记录。
- `tools/analyze_runtime_debug.py`：汇总 `logs/runtime_debug_*.jsonl`，用于快速判断漏绘制发生在死亡过滤、目标过滤、坐标读取还是投影阶段。
- `tools/generate_app_icon.py`：从 `assets/app.png` 生成 Windows `.ico` 图标和菜单高分辨率 Logo。
- `README.md`：面向使用者的中文说明。

## 运行时生成文件

- `config.json`：源码运行时自动生成的用户配置，不提交到 Git。
- `logs/runtime_debug_*.jsonl`：源码运行时生成的调试日志，不提交到 Git。
- `dist/`：Nuitka 打包输出目录，不提交到 Git。
- `.venv/`：本地虚拟环境，不提交到 Git。

## 设计约定

- 用户可见文本使用中文；UE 类名、偏移键、进程名、窗口标题等技术标识保持原文。
- 关键运行时状态不通过异常弹窗暴露给用户，菜单和覆盖层只展示简短状态。
- 目标进程未出现时，状态只显示在菜单标题栏右上角；覆盖层保持透明，不绘制等待提示卡。
- 进程连接失败属于正常状态：`ESPRuntime.connect_once()` 捕获异常、更新状态，并由入口定时器重试。
- 应用入口通过 Windows 命名互斥体 `Global\ChameleonLensMecchaEsp` 做单例保护，重复启动会直接退出。
- 运行依赖统一通过项目内 `.venv` 管理，用户入口优先使用 `run.bat`。`run.bat` 只检查 `.venv\.requirements.stamp` 是否存在，存在时直接启动主程序，避免每次启动都拉起 PowerShell 算哈希或进入 pip 检查；修改 `requirements.txt` 后用 `run.bat --check-only` 刷新依赖 stamp。
- 配置持久化使用 JSON。源码运行时写入项目根目录 `config.json`，便于开发排查；Nuitka 打包版写入 `%LOCALAPPDATA%\Chameleon Lens\config.json`，日志写入 `%LOCALAPPDATA%\Chameleon Lens\logs`，避免 onefile 临时目录或程序目录权限导致数据丢失。保存采用临时文件替换，避免写入中断导致配置损坏。
- UI 信息架构按 `ESP / 雷达 / 外观 / 快捷键 / 调试` 五个顶部页签组织：ESP 页只放目标点、标签和射线控制，雷达页只放雷达与参数，外观页只放透明度、点半径和颜色，快捷键页只放全局开关按键。
- ESP 页使用两列开关布局和 ESP 效果预览；雷达预览只出现在雷达页，避免一个页签同时承载两个主题。
- 运行状态放在标题栏右上角；标题栏只保留品牌、连接状态和窗口控制，不再显示透明度胶囊或副标题。
- 连接状态使用自绘状态胶囊，标题栏只显示单行主状态：“未连接 · 等待进程”或“已连接 · 游戏进程”；详细错误和重试信息放在调试页。
- 滑条使用可点击轨道控件并通过 `QPainter` 自绘，避免 QSS 滑条在圆角和 handle 上出现毛刺；开关需要让整个控件区域都可点击。紧凑数值输入使用自绘显示态并在点击后进入原生编辑态；下拉框只自绘闭合态，弹层、焦点和键盘选择交给原生 `QComboBox`，避免自制弹层交互不稳。
- 开关使用 `QPropertyAnimation` 做短距离滑动动画，动画时间保持在 150ms 左右，避免影响工具响应感。
- 主要容器、标题栏和内容面板使用 `SmoothFrame` 自绘，避免 QSS 的半透明圆角边框毛刺。
- 顶部页签使用 `TabButton` 自绘，不再使用底部横条。Qt StyleSheet 的 `border + border-radius + 半透明背景` 在 Windows 上容易出现圆角毛刺，Logo、关闭按钮、关键按钮、调色板候选色、颜色预览和主要操作按钮优先用 `QPainter` 抗锯齿绘制。雷达预览使用开放 HUD 画布，仅保留角标、雷达环和目标点，不再额外绘制横竖底线、底部基线或内层卡片边框。
- 自绘按钮、页签、关闭按钮和调色板候选色使用轻量 hover 过渡；滑条在 hover/拖动时改变轨道与滑块状态，提升可操作感但不做夸张动效。
- `enabled` 是覆盖层总开关；`esp_enabled` 只控制屏幕 ESP 绘制，关闭后目标点、标签、射线和边缘提示都不画，但雷达仍由 `radar_enabled` 独立控制。
- 全局快捷键由 `hotkey_menu_toggle`、`hotkey_overlay_toggle`、`hotkey_esp_toggle`、`hotkey_radar_toggle` 四个配置字段控制；菜单显隐默认 `F1`，其余默认为空。快捷键录入期间入口轮询会暂停，避免按下当前热键时误触发菜单隐藏或开关切换。
- 覆盖层分离三个刷新节奏：绘制约 90 FPS，目标快照采样约 90 FPS，窗口位置和尺寸约每 250ms 更新一次。高刷新使用 `Qt.PreciseTimer`，不要盲目继续拉高 timer；先看调试日志里的 `performance.sample_ms` 和 `performance.paint_ms`，若采样 p95 接近 11ms，应优先降低采样频率或减少读取开销。
- `show_hunter_esp` 控制猎人是否参与显示；关闭后稳定判定为猎人的屏幕 ESP 与雷达点都不绘制，但底层 PlayerArray 调试日志仍会记录猎人候选。猎人过滤使用 `filter_role`，不会直接吃瞬时 `role`；颜色显示优先使用当前明确的 `role`，避免身份防抖期间猎人/躲藏者短暂沿用旧颜色。
- `show_names` 和 `show_distance` 是两个独立开关，不再用一个“名称与距离”控件同时表达两件事；`show_edge_indicators` 独立控制屏幕外/背后目标边缘提示。
- 名称标签优先读取 `APlayerState::CustomPlayerName`，按 FText/FString 都尝试；失败后再读 `APlayerState::PlayerNamePrivate` 的 FString，最后才回退为“玩家 短 ID”、`PlayerId` 或“目标 N”。短 ID 不再用 `#xxxxxx`，避免和颜色 Hex 格式混淆。`CustomPlayerName`、`PlayerNamePrivate`、`PlayerId` 都采用动态属性解析优先，失败时使用历史日志确认过的 `0x388`、`0x340`、`0x2AC` 兜底。PlayerState 显示名会短时缓存，只有开启数据记录时才写入完整 `name_candidates`。
- 名称候选只允许中文、英文、数字和少量昵称符号；`BP_`、`MI_`、`Default__`、`Character`、`Material` 等蓝图/资源/对象标识会被过滤，避免覆盖层显示乱码或内部对象名。
- `snap_lines` 控制普通 ESP 射线；`show_local_snap_line` 只控制本地玩家是否绘制自身 ESP 射线。
- `show_local_snap_line` 依赖 `show_local` 与 `snap_lines`，两者任一关闭时自身射线开关置灰但保留用户选择。
- 覆盖层默认只使用 PlayerArray，不再使用 Level Actor fallback 参与实际绘制，避免场景残留、尸体和旧实例混进覆盖层。`reader.iter_players()` 返回 `TargetSnapshot`，旧五元组迭代仍保留兼容。
- 目标枚举采用极简策略：PlayerArray 里除本地玩家和死亡/观战 pawn 外全部进入绘制流程，不再用 Character 白名单或反向绑定延迟过滤。`SpectatePawn` 不直接等价死亡，会检查 `SpectatePawn + 0x1A0` 是否指向真实 Character；只要该 Character 的 `LastMyPlayerState` 或 `APawn::PlayerState` 匹配当前 PlayerState、坐标有效，并且未被 GameState 阵营数组判为旧 survivor 链接，就使用真实 Character 绘制并计入 `pa_linked`。`Dead` 字段只写入日志，不再作为临时过滤条件。感染模式中仍在 `LiveSurvivors` 的 Spectate 链接会继续绘制；非感染/基础模式里不在 `LiveSurvivors` 的旧 survivor 链接会跳过并计入 `pa_suppressed`，避免击杀后继续显示旧躲藏模型。
- `GameState` 阵营数组有效时，Reader 会用 `LiveSurvivors_PlayerState` / `HuntersPlayerState` 辅助修正角色身份和隐藏旧链接：`PlayerState` 在 LiveSurvivors 中按躲藏方处理，在 Hunters 中按猎人处理；`SpectatePawn` 链接到 survivor 旧模型但 PlayerState 不在 LiveSurvivors 时，会跳过并计入 `pa_suppressed` / `suppressed_not_live_survivor`。该规则只在 `game_mode_raw` 为已观察到的 `0/1`、`MainGamePhase` 为 `1/2/3` 且阵营数组非空时生效；大厅、结算切换或数组为空时不会用空数组隐藏目标。
- 玩法模式语义：普通模式开局有若干猎人寻找若干躲藏方，躲藏方被击杀后进入观战视角；感染模式开局有若干猎人寻找若干躲藏方，躲藏方被击杀后会变为猎人，出现猎人角色建模、视角切换为猎人、并操控猎人角色，身份只会从躲藏方切到猎人一次；双重模式房间内若干玩家先全部开始躲藏，随后这些玩家变为猎人开始寻找。后续做模式化过滤时，不能把这三类身份切换按同一死亡/观战规则处理。双重模式当前不做专门优化；如果用户关闭“猎人 ESP”，双重后半段全员变猎人时可能看起来像没有 ESP，这是配置和模式语义共同导致的结果。
- 类名用于角色和形态分类：`Hunter` 记为猎人，`Survivor` 记为躲藏者，`Spectate` 记为观战；形态从类名中的 `Cube`、`Base` 等 token 推断。普通、感染、双重模式都会让同一 PlayerState 在躲藏者、猎人、观战之间合法切换，因此不能把“曾经是躲藏者”当永久身份。
- Reader 会维护 PlayerState 级别的短时身份状态，输出 `stable_role`、`filter_role`、`role_pending`、`converted_to_hunter` 和 `converted_hunter_age` 到 `TargetSnapshot` 与调试日志。`filter_role` 用于猎人 ESP 过滤和颜色选择，避免身份刚切换 1 秒内的瞬时抖动造成漏绘制；持续稳定后才按新身份处理。`converted_to_hunter` 只表示同一 PlayerState 已观察到躲藏者到猎人的转换，用于感染模式抑制旧躲藏者链接，不代表永久阵营。
- `APawn::PlayerState` 反向绑定异常只计入 `pa_suspect`，不再作为覆盖层跳过依据。躲猫猫玩法里静止属于正常状态，不能作为死亡依据。
- Level Actor fallback 保留在 `reader.iter_players(players_only=False)` 里用于调试和对比，但覆盖层调用 `players_only=True`。
- `APawn::PlayerState` 与 `APawn::Controller` 采用可选懒解析，解析失败时 fallback 宁可少画，也不把无绑定残留模型当作目标。
- 雷达使用相机 yaw 作为朝向，把目标相对相机位置旋转到雷达盘面；超出 `radar_range` 的目标钳在雷达边缘，用于补足屏幕外和背后目标感知。雷达坐标转换放在 `chameleon_lens.radar`，覆盖层只负责绘制。
- 屏幕 ESP 对 `behind_camera` / `outside_view*` 的目标不再直接丢弃；开启边缘提示时会把目标钳到屏幕边缘绘制一个边缘标记，避免“候选已读到但视觉上像漏绘制”。日志中的 `edge_reasons` 记录这些边缘绘制来源，若占比过高可在 ESP 页关闭“边缘提示”。
- 菜单只允许通过标题栏拖动，避免用户调节控件时误拖窗口。
- 控制项标题和说明使用紧凑两行布局，避免标题与说明之间出现松散空隙。
- 调试页“数据记录”会每秒写入 `logs/runtime_debug_*.jsonl`，并提供“打开日志”按钮用于打开当前运行日志目录。日志用于分析候选目标、过滤统计、投影原因、名称候选、角色形态、边缘提示和最终绘制结果。日志包含 `performance`、`projection_reasons`、`edge_reasons`、`player_array_debug`、`level_actor_debug`、`emitted_targets` 和 `reader_context`：先看采样/绘制耗时是否异常，再看目标是否进入 PlayerArray、是否被过滤、位置来源和投影失败原因。`reader_context` 会记录 `GameState`、关卡和本地 Pawn 的类名/对象名，用于区分不同对局模式并决定是否需要模式化的 `SpectatePawn` 链接策略；开启数据记录时还会额外记录 `game_state_fields`，包含 `GameMode` 原始值、`MainGamePhase`、`CurrentGamePhase`、计时器、`MapIndex`、`LiveSurvivors_PlayerState` 和 `HuntersPlayerState` 等 SDK 偏移字段。`context_event` 会记录 world/GameState/Level 上下文变化，变化时 Reader 会清理跨局身份、名称、pawn 生命周期和位置缓存。`spectate_link` 会记录链接角色的类名、角色/形态、`LastMyPlayerState`、`APawn::PlayerState`、Controller、Dead、坐标来源、root 和 mesh，并附带 `SpectateTarget`、`MyMainBody`、`CanBackBody` 等 `BP_SpectatePawn_cLeon_C` 命名字段。`player_array_debug`、`level_actor_debug` 和 `emitted_targets` 在数据记录帧会记录 `character_flags`，包含 `IsHunter`、`IsLiveSelf`、`BodyVisibility`、`HideBlock`、`CurrentNamePlateVisibility`、物理混合 bit 和 `PhysicsBlendWeight`。这些 SDK 字段当前只用于日志诊断，不参与绘制过滤；正常游玩时仍建议关闭“数据记录”。若出现“候选/绘制/雷达数量相同但游戏内感觉少人”，重点看 `dead_or_spectator`、`spectate_link`、`pa_linked`、`pa_suppressed`、`role/stable_role/filter_role` 是否解释了被过滤对象。
- 名称定位优先看 `player_array_debug[].name_candidates`、`display_name_source` 和 `display_name_reader`。如果局内仍读不到昵称，先保留开启数据记录后的最新 JSONL 日志，再按日志补充专门的 `tools/` 诊断脚本。
- 位置大跳变超过阈值时会记录到 `position_jumps` 并清理旧 pawn/目标位置缓存，用于识别回合重置、地图切换或目标实例重建。
- `player_array_debug[].reason` 记录 `no_pawn`、`local_pawn`、`duplicate_pawn`、`dead_or_spectator` 等跳过原因；`emitted_targets[].position_source` 记录当前使用的坐标来源。后续定位“突然不绘制”时，先确认 `pa_dead` 是否异常增加，以及未绘制帧里的 `position_source`、`projection_reasons` 和 `edge_reasons` 是否异常。
- 菜单透明度使用窗口级 `setWindowOpacity()` 生效，外观页只开放 70%-96% 的可读区间，避免过低看不清、100% 过实。
- 配置包含 `config_version`；升级默认配色时只迁移精确等于旧默认值的颜色，避免覆盖用户自定义颜色。
- 右上角关闭按钮用于退出程序，并需要保留 hover 反馈。
- 颜色选择使用项目内自定义深色面板，避免调用系统默认 `QColorDialog`。
- 外观页按“绘制参数 / 颜色方案”分区，透明度和圆点半径并排使用滑条，颜色用横向自绘色板列表，并提供“恢复默认外观”。
- 新 UI 可以参考深色工具台风格，但当前更适合顶部 Tab 和精简仪器面板；功能边界保持 `ESP + 雷达`，不引入无关自动化模块。
- PyQt5 菜单保持轻量单文件实现，避免在当前小项目中过早引入额外 UI 框架。
- 含中文文件统一按 UTF-8 读写；PowerShell 读取时先切换 `chcp 65001` 并使用 `Get-Content -Encoding UTF8`。

## 后续维护建议

- 若要修复阵亡后仍绘制的问题，先开启调试页“数据记录”，分别保存存活和阵亡场景的 `runtime_debug_*.jsonl`，用 `tools/analyze_runtime_debug.py` 汇总后再判断是否需要新增专门诊断脚本；确认稳定字段后再接入 `MecchaESP.iter_players()` 的过滤逻辑。
- 若后续配置项变成多套预设、历史记录或复杂用户档案，再考虑 SQLite；当前单配置文件继续使用 JSON。
- 若继续扩展 UI，优先抽取菜单控件工厂或样式常量，避免 `_build_ui()` 继续膨胀；`ui.menu` 不直接 import `reader`，目标进程信息经 `runtime` 暴露。
- 若要提高 ESP 刷新率，先对比 `performance.sample_ms` 和 `performance.paint_ms`；采样开销偏高时优先降低内存读取频率或增加缓存，绘制开销偏高时再优化 QPainter 绘制。
- 若要发布给普通用户，建议增加日志文件、配置导入导出和错误上报，把调试错误写入日志而不是只显示在控制台。
- 游戏更新后，优先验证 `PROCESS_NAME`、`MODULE_NAME`、窗口标题、`GUObjectArray` 和 `FNamePool` 定位逻辑。
