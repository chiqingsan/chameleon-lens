# Chameleon Lens 开发文档

## 二开目标

本目录是 `meccha-esp-master` 的二次开发目录，上游参考目录为 `C:\Users\chiqingsan\Downloads\meccha-esp-master\meccha-esp-master`。后续功能修改应优先落在本目录，避免直接污染上游参考代码。

当前阶段目标：

1. 聚焦 `ESP + 雷达`，不再扩展辅助瞄准或其他战斗功能。
2. 提升 PyQt5 菜单和覆盖层状态提示的现代感。
3. 将用户可见文本汉化。
4. 目标游戏进程未启动、退出或暂时不可读时，程序保持运行并给出等待状态。

## 代码结构

- `chameleon_lens/`：主程序包，按内存读取、目标读取、配置、运行时、UI、覆盖层和入口拆分。
- `chameleon_lens/radar.py`：雷达坐标转换，把目标相对相机位置投影到雷达盘面。
- `esp.py`：兼容入口，旧调试脚本仍可从这里导入 `MecchaESP`、`rp`、`read_array` 等对象；新业务不要继续写入该文件。
- `run.bat`：Windows 一键启动脚本，负责检查 Python、创建 `.venv`、安装依赖并启动主程序。
- `bootstrap.py`：启动器，最终通过 `python -m chameleon_lens` 进入主程序。
- `requirements.txt`：运行依赖清单，由启动脚本自动安装到 `.venv`。
- `config.json`：运行时自动生成的用户配置文件，保存菜单开关、颜色、雷达和外观参数。
- `docs/ARCHITECTURE.md`：当前模块边界和依赖方向。
- `docs/CODEBASE_MAP.md`：项目文件地图。
- `docs/DEVELOPMENT_GUIDE.md`：修改、验证和文档同步规则。
- `docs/UI_CONCEPT.md`：UI 概念稿说明。
- `docs/ui_concept_v2.png`：第二版横向矩形 UI 渲染图。
- `docs/ui_concept_v3.png`：第三版横向深色工具台 UI 渲染图，验证左侧导航和更强卡片层级。
- `docs/ui_concept_v4.png`：第四版顶部 Tab + 统一青绿色系 UI 渲染图，验证统一配色后的整体观感。
- `docs/ui_concept_v5.png`：第五版精简仪器面板 UI 渲染图，当前真实菜单按该方向落地，尺寸为 900 x 520。
- `docs/ui_actual_v2.png`：真实 PyQt 菜单离屏渲染图，用于快速检查布局。
- `docs/ui_actual_v5.png`：V5 真实 PyQt 菜单离屏渲染图，用于检查窗口尺寸和布局。
- `docs/ui_color_picker.png`：自定义深色颜色选择面板截图。
- `tools/analyze_runtime_debug.py`：汇总 `logs/runtime_debug_*.jsonl`，用于快速判断漏绘制发生在死亡过滤、目标过滤、坐标读取还是投影阶段。
- `debug_teams.py`、`diag_fname.py`、`find_prop_offsets.py`：调试和定位工具，暂未改动。
- `debug_life_state.py`：记录 PlayerArray 和 Level Character 在存活/阵亡前后的字段变化，并记录可选 `display_name`，用于定位死亡过滤和玩家名字段。
- `README.md`：面向使用者的中文说明。

## 设计约定

- 用户可见文本使用中文；UE 类名、偏移键、进程名、窗口标题等技术标识保持原文。
- 关键运行时状态不通过异常弹窗暴露给用户，菜单和覆盖层只展示简短状态。
- 目标进程未出现时，状态只显示在菜单标题栏右上角；覆盖层保持透明，不绘制等待提示卡。
- 进程连接失败属于正常状态：`ESPRuntime.connect_once()` 捕获异常、更新状态，并由入口定时器重试。
- 应用入口通过 Windows 命名互斥体 `Global\ChameleonLensMecchaEsp` 做单例保护，重复启动会直接退出。
- 运行依赖统一通过项目内 `.venv` 管理，用户入口优先使用 `启动 Chameleon Lens.bat`。
- 配置持久化使用项目根目录 `config.json`。当前配置字段数量少、结构固定，JSON 比 SQLite 更轻，便于手动排查和迁移；保存采用临时文件替换，避免写入中断导致配置损坏。
- UI 信息架构按 `ESP / 雷达 / 外观 / 调试` 四个顶部页签组织：ESP 页只放目标点、标签和射线控制，雷达页只放雷达与参数，外观页只放透明度、点半径和颜色。
- ESP 页使用“基础显示 / 标签与射线”两组开关和 ESP 效果预览；雷达预览只出现在雷达页，避免一个页签同时承载两个主题。
- 运行状态放在标题栏右上角；标题栏只保留品牌、连接状态和窗口控制，不再显示透明度胶囊或副标题。
- 连接状态使用自绘状态胶囊，标题栏只显示单行主状态：“未连接 · 等待进程”或“已连接 · 游戏进程”；详细错误和重试信息放在调试页。
- 滑条使用可点击轨道控件并通过 `QPainter` 自绘，避免 QSS 滑条在圆角和 handle 上出现毛刺；开关需要让整个控件区域都可点击。
- 开关使用 `QPropertyAnimation` 做短距离滑动动画，动画时间保持在 150ms 左右，避免影响工具响应感。
- 主要容器、标题栏和内容面板使用 `SmoothFrame` 自绘，避免 QSS 的半透明圆角边框毛刺。
- 顶部页签使用 `TabButton` 自绘，不再使用底部横条。Qt StyleSheet 的 `border + border-radius + 半透明背景` 在 Windows 上容易出现圆角毛刺，Logo、关闭按钮、关键按钮、调色板候选色、颜色预览和主要操作按钮优先用 `QPainter` 抗锯齿绘制。ESP 与雷达预览共享开放 HUD 画布，用低透明网格、扫描线和角标填补空白，但不再增加内层卡片边框。
- 自绘按钮、页签、关闭按钮和调色板候选色使用轻量 hover 过渡；滑条在 hover/拖动时改变轨道与滑块状态，提升可操作感但不做夸张动效。
- `enabled` 是覆盖层总开关；`esp_enabled` 只控制屏幕 ESP 绘制，关闭后目标点、标签、射线和边缘提示都不画，但雷达仍由 `radar_enabled` 独立控制。
- 覆盖层分离三个刷新节奏：绘制约 60 FPS，目标快照采样约 30 FPS，窗口位置和尺寸约每 250ms 更新一次。不要直接把绘制 timer 拉高来解决感知问题，先看调试日志里的 `performance.sample_ms` 和 `performance.paint_ms`。
- `show_hunter_esp` 控制猎人是否参与显示；关闭后稳定判定为猎人的屏幕 ESP 与雷达点都不绘制，但底层 PlayerArray 调试日志仍会记录猎人候选。猎人过滤使用 `filter_role`，不会直接吃瞬时 `role`。
- `show_names` 和 `show_distance` 是两个独立开关，不再用一个“名称与距离”控件同时表达两件事；`show_edge_indicators` 独立控制屏幕外/背后目标边缘提示。
- 名称标签优先读取 `APlayerState::CustomPlayerName`，按 FText/FString 都尝试；失败后再读 `APlayerState::PlayerNamePrivate` 的 FString，最后才回退为“玩家 短 ID”、`PlayerId` 或“目标 N”。短 ID 不再用 `#xxxxxx`，避免和颜色 Hex 格式混淆。`CustomPlayerName`、`PlayerNamePrivate`、`PlayerId` 都采用动态属性解析优先，失败时使用历史日志确认过的 `0x388`、`0x340`、`0x2AC` 兜底。PlayerState 显示名会短时缓存，只有开启数据记录时才写入完整 `name_candidates`。
- 名称候选只允许中文、英文、数字和少量昵称符号；`BP_`、`MI_`、`Default__`、`Character`、`Material` 等蓝图/资源/对象标识会被过滤，避免覆盖层显示乱码或内部对象名。
- `snap_lines` 控制普通 ESP 射线；`show_local_snap_line` 只控制本地玩家是否绘制自身 ESP 射线。
- `show_local_snap_line` 依赖 `esp_enabled`、`show_local` 与 `snap_lines`，任一关闭时自身射线整行降权置灰但保留用户选择。
- 覆盖层默认只使用 PlayerArray，不再使用 Level Actor fallback 参与实际绘制，避免场景残留、尸体和旧实例混进覆盖层。`reader.iter_players()` 返回 `TargetSnapshot`，旧五元组迭代仍保留兼容。
- 目标枚举采用极简策略：PlayerArray 里除本地玩家和死亡/观战 pawn 外全部进入绘制流程，不再用 Character 白名单或反向绑定延迟过滤。`SpectatePawn` 不再直接等价死亡：先检查 `SpectatePawn + 0x1A0` 是否指向真实 Character，且该 Character 的 `LastMyPlayerState` 或 `APawn::PlayerState` 匹配当前 PlayerState、`Dead=0`、坐标有效；命中时使用真实 Character 绘制并计入 `pa_linked`，否则才计入 `pa_dead`。
- 类名用于角色和形态分类：`Hunter` 记为猎人，`Survivor` 记为躲藏者，`Spectate` 记为观战；形态从类名中的 `Cube`、`Base` 等 token 推断。感染、基础、双重模式都会让同一 PlayerState 在躲藏者、猎人、观战之间合法切换，因此不能把“曾经是躲藏者”当永久身份。
- Reader 会维护 PlayerState 级别的短时身份状态，输出 `stable_role`、`filter_role` 和 `role_pending` 到 `TargetSnapshot` 与调试日志。`filter_role` 用于猎人 ESP 过滤和颜色选择，避免身份刚切换 1 秒内的瞬时抖动造成漏绘制；持续稳定后才按新身份处理。
- `APawn::PlayerState` 反向绑定异常只计入 `pa_suspect`，不再作为覆盖层跳过依据。躲猫猫玩法里静止属于正常状态，不能作为死亡依据。
- Level Actor fallback 保留在 `reader.iter_players(players_only=False)` 里用于调试和对比，但覆盖层调用 `players_only=True`。
- `APawn::PlayerState` 与 `APawn::Controller` 采用可选懒解析，解析失败时 fallback 宁可少画，也不把无绑定残留模型当作目标。
- 雷达使用相机 yaw 作为朝向，把目标相对相机位置旋转到雷达盘面；超出 `radar_range` 的目标钳在雷达边缘，用于补足屏幕外和背后目标感知。雷达坐标转换放在 `chameleon_lens.radar`，覆盖层只负责绘制。
- 屏幕 ESP 对 `behind_camera` / `outside_view*` 的目标不再直接丢弃；开启边缘提示时会把目标钳到屏幕边缘绘制一个边缘标记，避免“候选已读到但视觉上像漏绘制”。日志中的 `edge_reasons` 记录这些边缘绘制来源，若占比过高可在 ESP 页关闭“边缘提示”。
- 菜单只允许通过标题栏拖动，避免用户调节控件时误拖窗口。
- 控制项标题和说明使用紧凑两行布局，避免标题与说明之间出现松散空隙。
- 调试页“数据记录”会每秒写入 `logs/runtime_debug_*.jsonl`，用于分析候选目标、过滤统计、投影原因、名称候选、角色形态、边缘提示和最终绘制结果。日志包含 `performance`、`projection_reasons`、`edge_reasons`、`player_array_debug`、`level_actor_debug` 和 `emitted_targets`：先看采样/绘制耗时是否异常，再看目标是否进入 PlayerArray、是否被过滤、位置来源和投影失败原因。若出现“候选/绘制/雷达数量相同但游戏内感觉少人”，重点看 `dead_or_spectator`、`spectate_link`、`pa_linked`、`role/stable_role/filter_role` 是否解释了被过滤对象。
- 名称定位优先看 `player_array_debug[].name_candidates`、`display_name_source` 和 `display_name_reader`。如果局内仍读不到昵称，运行 `debug_life_state.py names` 扫描 PlayerState 附近的 FString/FText 候选，确认中文/英文/数字昵称是否在其他偏移。
- 位置大跳变超过阈值时会记录到 `position_jumps` 并清理旧 pawn/目标位置缓存，用于识别回合重置、地图切换或目标实例重建。
- `player_array_debug[].reason` 记录 `no_pawn`、`local_pawn`、`duplicate_pawn`、`dead_or_spectator` 等跳过原因；`emitted_targets[].position_source` 记录当前使用的坐标来源。后续定位“突然不绘制”时，先确认 `pa_dead` 是否异常增加，以及未绘制帧里的 `position_source`、`projection_reasons` 和 `edge_reasons` 是否异常。
- 菜单透明度使用窗口级 `setWindowOpacity()` 生效，避免只改变背景 alpha 导致 40%-60% 几乎无差异。
- 配置包含 `config_version`；升级默认配色时只迁移精确等于旧默认值的颜色，避免覆盖用户自定义颜色。
- 右上角关闭按钮用于退出程序，并需要保留 hover 反馈。
- 颜色选择使用项目内自定义深色面板，避免调用系统默认 `QColorDialog`。
- 外观页按“绘制参数 / 颜色方案”分区，透明度和圆点半径并排使用滑条，颜色用横向自绘色板列表，并提供“恢复默认外观”。
- 新 UI 可以参考深色工具台风格，但当前更适合顶部 Tab 和精简仪器面板；功能边界保持 `ESP + 雷达`，不引入无关自动化模块。
- PyQt5 菜单保持轻量单文件实现，避免在当前小项目中过早引入额外 UI 框架。
- 含中文文件统一按 UTF-8 读写；PowerShell 读取时先切换 `chcp 65001` 并使用 `Get-Content -Encoding UTF8`。

## 后续维护建议

- 若要修复阵亡后仍绘制的问题，先用 `debug_life_state.py sample --label alive` 和 `debug_life_state.py sample --label dead` 分别采集日志，再用 `debug_life_state.py compare <alive日志> <dead日志>` 对比变化字段；确认稳定字段后再接入 `MecchaESP.iter_players()` 的过滤逻辑。
- 若后续配置项变成多套预设、历史记录或复杂用户档案，再考虑 SQLite；当前单配置文件继续使用 JSON。
- 若继续扩展 UI，优先抽取菜单控件工厂或样式常量，避免 `_build_ui()` 继续膨胀；`ui.menu` 不直接 import `reader`，目标进程信息经 `runtime` 暴露。
- 若要提高 ESP 刷新率，先对比 `performance.sample_ms` 和 `performance.paint_ms`；采样开销偏高时优先降低内存读取频率或增加缓存，绘制开销偏高时再优化 QPainter 绘制。
- 若要发布给普通用户，建议增加日志文件、配置导入导出和错误上报，把调试错误写入日志而不是只显示在控制台。
- 游戏更新后，优先验证 `PROCESS_NAME`、`MODULE_NAME`、窗口标题、`GUObjectArray` 和 `FNamePool` 定位逻辑。
