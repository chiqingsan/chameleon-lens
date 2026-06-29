#!/usr/bin/env python3
"""汇总 runtime_debug 日志，快速定位 ESP 漏绘制卡在哪一层。"""
import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")


def load_rows(path):
    rows = []
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def pick_latest(log_dir):
    files = sorted(Path(log_dir).glob("runtime_debug_*.jsonl"), key=lambda p: p.stat().st_mtime)
    if not files:
        raise SystemExit(f"没有找到 runtime_debug 日志：{log_dir}")
    return files[-1]


def print_counter(title, counter, total=None, limit=12):
    print(f"\n{title}")
    if not counter:
        print("  无")
        return
    for key, count in counter.most_common(limit):
        ratio = f" ({count / total:.1%})" if total else ""
        print(f"  {key}: {count}{ratio}")


def summarize(path):
    rows = load_rows(path)
    print(f"日志：{path}")
    print(f"帧数：{len(rows)}")
    if rows:
        print(f"时间：{rows[0].get('time')} -> {rows[-1].get('time')}")

    candidate_drawn = Counter()
    stats_counter = Counter()
    projection_reasons = Counter()
    edge_reasons = Counter()
    target_reasons = Counter()
    pa_reasons = Counter()
    level_reasons = Counter()
    position_sources = Counter()
    emitted_sources = Counter()
    emitted_results = Counter()
    display_sources = Counter()
    name_candidate_results = Counter()
    accepted_names = Counter()
    roles = Counter()
    stable_roles = Counter()
    filter_roles = Counter()
    role_pairs = Counter()
    role_pending = Counter()
    forms = Counter()
    role_timeline = defaultdict(list)
    edge_frames = 0
    position_jump_frames = 0
    position_jump_count = 0
    pa_dead_frames = 0
    pa_linked_frames = 0
    pa_orphan_frames = 0
    pa_suspect_frames = 0

    for row in rows:
        stats = row.get("stats") or {}
        candidate_drawn[(row.get("player_candidates"), row.get("drawn"), len(row.get("radar_targets") or []))] += 1
        stats_counter[(
            stats.get("pa_total"),
            stats.get("pa_valid"),
            stats.get("pa_dead"),
            stats.get("pa_linked", 0),
            stats.get("pa_orphan"),
            stats.get("pa_suspect"),
            stats.get("level_valid"),
            stats.get("level_orphan"),
            stats.get("rendered"),
        )] += 1
        if stats.get("pa_dead", 0):
            pa_dead_frames += 1
        if stats.get("pa_linked", 0):
            pa_linked_frames += 1
        if stats.get("pa_orphan", 0):
            pa_orphan_frames += 1
        if stats.get("pa_suspect", 0):
            pa_suspect_frames += 1

        projection_reasons.update(row.get("projection_reasons") or {})
        row_edge_reasons = row.get("edge_reasons") or {}
        if row_edge_reasons:
            edge_frames += 1
        edge_reasons.update(row_edge_reasons)
        jumps = row.get("position_jumps") or []
        if jumps:
            position_jump_frames += 1
            position_jump_count += len(jumps)
        for target in row.get("targets") or []:
            role = target.get("role") or "unknown"
            stable_role = target.get("stable_role") or role
            filter_role = target.get("filter_role") or role
            roles[role] += 1
            stable_roles[stable_role] += 1
            filter_roles[filter_role] += 1
            role_pairs[(role, stable_role, filter_role)] += 1
            forms[target.get("form") or "unknown"] += 1
            if not target.get("drawn"):
                target_reasons[target.get("reason") or "unknown"] += 1
        for item in row.get("player_array_debug") or []:
            pa_reasons[item.get("reason") or item.get("result") or "unknown"] += 1
            role = item.get("role") or "unknown"
            stable_role = item.get("stable_role") or role
            filter_role = item.get("filter_role") or role
            roles[role] += 1
            stable_roles[stable_role] += 1
            filter_roles[filter_role] += 1
            role_pairs[(role, stable_role, filter_role)] += 1
            if item.get("role_pending"):
                role_pending[(role, stable_role, filter_role)] += 1
            forms[item.get("form") or "unknown"] += 1
            ps = item.get("player_state") or ""
            if ps and ps != "0x0" and item.get("reason") != "local_player_state":
                state = (
                    row.get("time"),
                    item.get("result") or "skip",
                    item.get("reason") or "",
                    role,
                    stable_role,
                    filter_role,
                    item.get("class") or "",
                )
                timeline = role_timeline[ps]
                if not timeline or timeline[-1][1:] != state[1:]:
                    timeline.append(state)
            source = item.get("display_name_source") or "none"
            display_sources[source] += 1
            for candidate in item.get("name_candidates") or []:
                key = (
                    candidate.get("field") or "unknown",
                    candidate.get("source") or "none",
                    "accepted" if candidate.get("accepted") else candidate.get("reason") or "rejected",
                )
                name_candidate_results[key] += 1
                if candidate.get("accepted") and candidate.get("raw"):
                    accepted_names[candidate.get("raw")] += 1
        for item in row.get("level_actor_debug") or []:
            level_reasons[item.get("reason") or item.get("result") or "unknown"] += 1
        for item in row.get("emitted_targets") or []:
            position_sources[item.get("position_source") or "unknown"] += 1
            emitted_sources[item.get("source") or "unknown"] += 1
            emitted_results[item.get("result") or "unknown"] += 1

    print(f"pa_dead 出现帧：{pa_dead_frames}")
    print(f"pa_linked 出现帧：{pa_linked_frames}")
    print(f"pa_orphan 出现帧：{pa_orphan_frames}")
    print(f"pa_suspect 出现帧：{pa_suspect_frames}")
    print(f"边缘提示出现帧：{edge_frames}")
    print(f"位置大跳变出现帧：{position_jump_frames}，事件数：{position_jump_count}")
    print_counter("候选/绘制/雷达 Top", candidate_drawn, len(rows))
    print_counter("统计 Top: pa_total, pa_valid, pa_dead, pa_linked, pa_orphan, pa_suspect, level_valid, level_orphan, rendered", stats_counter, len(rows))
    print_counter("投影失败原因", projection_reasons or target_reasons)
    print_counter("边缘绘制原因", edge_reasons)
    print_counter("PlayerArray 跳过/候选原因", pa_reasons)
    print_counter("LevelActor 跳过/候选原因", level_reasons)
    print_counter("发射目标来源", emitted_sources)
    print_counter("发射结果", emitted_results)
    print_counter("坐标来源", position_sources)
    print_counter("名称来源", display_sources)
    print_counter("名称候选结果: field, reader, result", name_candidate_results)
    print_counter("已接受名称", accepted_names)
    print_counter("角色分类", roles)
    print_counter("稳定角色分类", stable_roles)
    print_counter("过滤角色分类", filter_roles)
    print_counter("角色/稳定角色/过滤角色组合", role_pairs)
    print_counter("角色防抖中的组合", role_pending)
    print_counter("形态分类", forms)

    changing_players = {
        ps: timeline for ps, timeline in role_timeline.items()
        if len({item[3] for item in timeline if item[3] != "unknown"}) > 1
    }
    if changing_players:
        print("\n身份发生变化的 PlayerState Top")
        for ps, timeline in sorted(changing_players.items(), key=lambda kv: -len(kv[1]))[:8]:
            print(f"  {ps}: {len(timeline)} 次状态段")
            for item in timeline[:8]:
                time, result, reason, role, stable_role, filter_role, cls_name = item
                reason_text = f"/{reason}" if reason else ""
                print(f"    {time} {result}{reason_text} role={role} stable={stable_role} filter={filter_role} class={cls_name}")
            if len(timeline) > 8:
                print(f"    ... 还有 {len(timeline) - 8} 段")

    print("\n判断提示")
    if pa_dead_frames:
        print("  pa_dead 有出现：有 pawn 被按 SpectatePawn 死亡/观战处理，需要看 player_array_debug 的 dead_or_spectator。")
    else:
        print("  pa_dead 没出现：死亡/观战类过滤暂时不是首要嫌疑。")
    if pa_linked_frames:
        print("  pa_linked 有出现：SpectatePawn 指向了真实 Character，覆盖层已改用该 Character 绘制。")
    if projection_reasons or target_reasons:
        print("  有投影失败：若候选和雷达仍存在，优先检查坐标源、相机数据或增加屏幕边缘指示。")
    if edge_reasons:
        print("  有边缘绘制：说明屏幕外/背后目标已被钳到屏幕边缘显示。")
        if rows and edge_frames / len(rows) > 0.4:
            print("  边缘提示帧占比较高：可以考虑在 UI 里关闭“边缘提示”，只保留雷达感知。")
    if pa_reasons:
        print("  有 PlayerArray 明细：重点看 dead_or_spectator/no_pawn/stale_orphan 是否在漏绘制时集中出现。")
    if role_pending:
        print("  角色防抖有触发：身份刚从躲藏者/猎人/观战切换时，会短暂沿用稳定角色参与过滤。")
    if name_candidate_results:
        print("  名称候选里 accepted 表示已读到可显示昵称；internal_prefix/internal_token 多半是资源名或蓝图名。")
    if position_jump_count:
        print("  位置大跳变已出现：通常意味着回合重置、地图切换或目标实例重建，相关缓存会被清理。")


def main():
    parser = argparse.ArgumentParser(description="分析 Chameleon Lens runtime_debug 日志")
    parser.add_argument("path", nargs="?", help="runtime_debug_*.jsonl 路径；不传则使用 logs 下最新文件")
    parser.add_argument("--log-dir", default="logs", help="日志目录，默认 logs")
    args = parser.parse_args()

    path = Path(args.path) if args.path else pick_latest(args.log_dir)
    summarize(path)


if __name__ == "__main__":
    main()
