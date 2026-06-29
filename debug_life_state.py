#!/usr/bin/env python3
"""记录玩家存活/阵亡前后的内存状态，用于定位可靠的死亡判定字段。"""
import argparse
import json
import math
import time
from datetime import datetime
from pathlib import Path

from esp import (
    MecchaESP, OFFSETS, read_array, read_fstring, read_ftext,
    rp, rfloat, rvec3, ru16, ru32,
)


INTERESTING_KEYWORDS = (
    "alive", "dead", "death", "die", "health", "hp", "life", "down", "knock",
    "state", "status", "spect", "hidden", "visible", "collision", "damage",
    "movement", "controller", "player", "pawn", "team", "name", "display",
    "nick", "user", "account",
)


def safe_hex(value):
    return f"0x{value:X}" if value else "0x0"


def safe_class_name(esp, obj):
    if not obj:
        return ""
    cls = rp(esp.pm, obj + OFFSETS["UObjectBase::ClassPrivate"])
    return esp.objects._obj_name(cls) if cls else ""


def safe_obj_name(esp, obj):
    return esp.objects._obj_name(obj) if obj else ""


def safe_vec3(pm, addr):
    try:
        value = rvec3(pm, addr)
        if all(math.isfinite(v) for v in value):
            return [round(v, 3) for v in value]
    except Exception:
        pass
    return None


def safe_float(pm, addr):
    try:
        value = rfloat(pm, addr)
        if math.isfinite(value) and -1_000_000.0 < value < 1_000_000.0:
            return round(value, 5)
    except Exception:
        pass
    return None


def iter_class_properties(esp, cls):
    """遍历类和父类属性，记录名称和偏移；用于发现 Health/Dead 一类字段。"""
    seen_classes = set()
    while cls and cls not in seen_classes:
        seen_classes.add(cls)
        owner_name = safe_obj_name(esp, cls)
        prop = rp(esp.pm, cls + OFFSETS["UStruct::ChildProperties"])
        depth = 0
        while prop and depth < 1024:
            name = esp.objects.fnames.resolve(ru32(esp.pm, prop + OFFSETS["FField::NamePrivate"]))
            offset = ru32(esp.pm, prop + OFFSETS["FProperty::Offset_Internal"])
            if name:
                yield {
                    "owner": owner_name,
                    "name": name,
                    "offset": offset,
                }
            prop = rp(esp.pm, prop + OFFSETS["FField::Next"])
            depth += 1
        cls = rp(esp.pm, cls + OFFSETS["UStruct::SuperStruct"])


def interesting_properties(esp, obj, limit=80):
    if not obj:
        return []
    cls = rp(esp.pm, obj + OFFSETS["UObjectBase::ClassPrivate"])
    out = []
    for prop in iter_class_properties(esp, cls):
        lname = prop["name"].lower()
        if any(keyword in lname for keyword in INTERESTING_KEYWORDS):
            out.append(prop)
            if len(out) >= limit:
                break
    return out


def read_property_values(esp, obj, props):
    values = {}
    for prop in props:
        off = prop["offset"]
        addr = obj + off
        ptr = rp(esp.pm, addr)
        values[prop["name"]] = {
            "offset": off,
            "u8": ru32(esp.pm, addr) & 0xFF,
            "u16": ru16(esp.pm, addr),
            "u32": ru32(esp.pm, addr),
            "f32": safe_float(esp.pm, addr),
            "ptr": safe_hex(ptr),
            "ptr_class": safe_class_name(esp, ptr),
        }
    return values


def raw_window(esp, obj, size=0x280):
    """记录一段紧凑原始窗口，后续 alive/dead 对比时能发现未知偏移变化。"""
    if not obj:
        return {}
    out = {}
    for off in range(0, size, 4):
        addr = obj + off
        u32 = ru32(esp.pm, addr)
        f32 = safe_float(esp.pm, addr)
        item = {"u32": u32}
        if f32 is not None:
            item["f32"] = f32
        if off % 8 == 0:
            ptr = rp(esp.pm, addr)
            ptr_class = safe_class_name(esp, ptr)
            if ptr_class:
                item["ptr"] = safe_hex(ptr)
                item["ptr_class"] = ptr_class
        if u32 != 0 or "ptr_class" in item:
            out[f"0x{off:X}"] = item
    return out


def actor_position(esp, actor):
    try:
        pos = esp._actor_position(actor)
        return [round(v, 3) for v in pos] if pos else None
    except Exception:
        return None


def component_snapshot(esp, component):
    if not component:
        return {}
    rel_off = esp.offsets.get("USceneComponent::RelativeLocation")
    return {
        "addr": safe_hex(component),
        "class": safe_class_name(esp, component),
        "name": safe_obj_name(esp, component),
        "relative_location": safe_vec3(esp.pm, component + rel_off) if rel_off is not None else None,
        "interesting": read_property_values(esp, component, interesting_properties(esp, component, 40)),
        "raw": raw_window(esp, component, 0x180),
    }


def pawn_snapshot(esp, pawn):
    if not pawn:
        return {}
    root = rp(esp.pm, pawn + esp.offsets["AActor::RootComponent"])
    mesh_off = esp.offsets.get("ACharacter::Mesh")
    mesh = rp(esp.pm, pawn + mesh_off) if mesh_off is not None else 0
    movement_off = esp.resolver.resolve("Character", "CharacterMovement")
    movement = rp(esp.pm, pawn + movement_off) if movement_off is not None else 0
    return {
        "addr": safe_hex(pawn),
        "class": safe_class_name(esp, pawn),
        "name": safe_obj_name(esp, pawn),
        "position": actor_position(esp, pawn),
        "controller": safe_hex(esp._pawn_controller(pawn)),
        "player_state": safe_hex(esp._pawn_playerstate(pawn)),
        "owner": safe_hex(esp._actor_owner(pawn)),
        "root": component_snapshot(esp, root),
        "mesh": component_snapshot(esp, mesh),
        "movement": component_snapshot(esp, movement),
        "interesting": read_property_values(esp, pawn, interesting_properties(esp, pawn)),
        "raw": raw_window(esp, pawn),
    }


def player_state_snapshot(esp, ps):
    if not ps:
        return {}
    pawn = rp(esp.pm, ps + esp.offsets["APlayerState::PawnPrivate"])
    return {
        "addr": safe_hex(ps),
        "class": safe_class_name(esp, ps),
        "name": safe_obj_name(esp, ps),
        "display_name": esp._player_display_name(ps),
        "display_name_info": esp._player_display_name_info(ps),
        "name_candidates": esp._debug_name_candidates(ps),
        "pawn": safe_hex(pawn),
        "interesting": read_property_values(esp, ps, interesting_properties(esp, ps)),
        "raw": raw_window(esp, ps),
        "pawn_snapshot": pawn_snapshot(esp, pawn),
    }


def collect_snapshot(label):
    esp = MecchaESP()
    world = esp._get_world()
    gamestate = rp(esp.pm, world + esp.offsets["UWorld::GameState"]) if world else 0
    pc = esp._get_local_controller(world)
    local_pawn = rp(esp.pm, pc + esp.offsets["APlayerController::AcknowledgedPawn"]) if pc else 0
    local_ps = rp(esp.pm, pc + esp.offsets["AController::PlayerState"]) if pc else 0

    players = []
    if gamestate:
        pa_data, pa_count, _ = read_array(esp.pm, gamestate + esp.offsets["AGameStateBase::PlayerArray"])
        if pa_data and 0 < pa_count < 128:
            for i in range(pa_count):
                ps = rp(esp.pm, pa_data + i * 8)
                if ps:
                    item = player_state_snapshot(esp, ps)
                    item["index"] = i
                    item["is_local"] = ps == local_ps
                    players.append(item)

    level_characters = []
    persistent_level_off = esp.offsets.get("UWorld::PersistentLevel", 0x30)
    actors_off = esp.offsets.get("ULevel::Actors", 0xA0)
    level = rp(esp.pm, world + persistent_level_off) if world else 0
    if level:
        actors_data, actors_count, _ = read_array(esp.pm, level + actors_off)
        if actors_data and 0 < actors_count < 10000:
            for i in range(actors_count):
                actor = rp(esp.pm, actors_data + i * 8)
                cls_name = safe_class_name(esp, actor)
                if not actor or "Character" not in cls_name:
                    continue
                item = pawn_snapshot(esp, actor)
                item["index"] = i
                item["is_local"] = actor == local_pawn
                level_characters.append(item)

    return {
        "time": datetime.now().isoformat(timespec="seconds"),
        "label": label,
        "world": safe_hex(world),
        "game_state": safe_hex(gamestate),
        "local_controller": safe_hex(pc),
        "local_player_state": safe_hex(local_ps),
        "local_pawn": safe_hex(local_pawn),
        "players": players,
        "level_characters": level_characters,
    }


def write_samples(args):
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = out_dir / f"life_state_{stamp}_{args.label}.jsonl"
    with out_path.open("w", encoding="utf-8") as fh:
        for sample_index in range(args.samples):
            snapshot = collect_snapshot(args.label)
            snapshot["sample_index"] = sample_index
            fh.write(json.dumps(snapshot, ensure_ascii=False) + "\n")
            fh.flush()
            print(f"[{sample_index + 1}/{args.samples}] 写入 {out_path}")
            if sample_index + 1 < args.samples:
                time.sleep(args.interval)
    return out_path


def load_last_snapshot(path):
    last = None
    with Path(path).open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                last = json.loads(line)
    if last is None:
        raise RuntimeError(f"日志为空：{path}")
    return last


def flatten_values(prefix, value, out):
    if isinstance(value, dict):
        for key, child in value.items():
            flatten_values(f"{prefix}.{key}" if prefix else str(key), child, out)
    elif isinstance(value, list):
        out[prefix] = json.dumps(value, ensure_ascii=False, sort_keys=True)
    else:
        out[prefix] = value


def compare_snapshots(args):
    before = load_last_snapshot(args.before)
    after = load_last_snapshot(args.after)
    compare_group("PlayerArray", before.get("players", []), after.get("players", []), args.limit)
    compare_group("LevelCharacters", before.get("level_characters", []), after.get("level_characters", []), args.limit)


def compare_group(title, before_items, after_items, limit):
    before_players = {p.get("addr"): p for p in before_items}
    after_players = {p.get("addr"): p for p in after_items}
    shared = [addr for addr in before_players if addr in after_players]
    if not shared:
        print(f"\n{title}: 没有找到相同地址，可能对象已重建或来源不同。")
        return

    print(f"\n=== {title} ===")
    for addr in shared:
        left_flat = {}
        right_flat = {}
        flatten_values("", before_players[addr], left_flat)
        flatten_values("", after_players[addr], right_flat)
        changes = []
        for key in sorted(set(left_flat) | set(right_flat)):
            if left_flat.get(key) != right_flat.get(key):
                changes.append((key, left_flat.get(key), right_flat.get(key)))
        print(f"\n{addr} 变化字段：{len(changes)}")
        for key, old, new in changes[:limit]:
            print(f"  {key}: {old} -> {new}")
        if len(changes) > limit:
            print(f"  ... 还有 {len(changes) - limit} 项，调大 --limit 查看")


def print_name_scan(args):
    """扫描 PlayerState 附近的 FString/FText 候选，专门用于定位玩家昵称字段。"""
    esp = MecchaESP()
    world = esp._get_world()
    gamestate = rp(esp.pm, world + esp.offsets["UWorld::GameState"]) if world else 0
    pc = esp._get_local_controller(world)
    local_ps = rp(esp.pm, pc + esp.offsets["AController::PlayerState"]) if pc else 0

    print(f"world={safe_hex(world)} game_state={safe_hex(gamestate)} local_ps={safe_hex(local_ps)}")
    if not gamestate:
        return

    pa_data, pa_count, _ = read_array(esp.pm, gamestate + esp.offsets["AGameStateBase::PlayerArray"])
    print(f"PlayerArray data={safe_hex(pa_data)} count={pa_count}")
    if not pa_data or pa_count <= 0 or pa_count >= 128:
        return

    for i in range(pa_count):
        ps = rp(esp.pm, pa_data + i * 8)
        if not ps:
            continue
        print(f"\n[{i}] ps={safe_hex(ps)} local={ps == local_ps} class={safe_class_name(esp, ps)} id={esp._player_id(ps)}")
        print(f"  display_info={json.dumps(esp._player_display_name_info(ps), ensure_ascii=False)}")

        hits = []
        for off in range(args.start, args.end + 1, args.step):
            for reader_name, reader in (("FString", read_fstring), ("FText", read_ftext)):
                try:
                    raw = reader(esp.pm, ps + off, args.max_chars)
                except Exception:
                    raw = ""
                if not raw:
                    continue
                item = esp._read_name_candidate(
                    ps,
                    f"offset_0x{off:X}",
                    off,
                    ((reader_name, reader),),
                )
                hits.append({
                    "offset": f"0x{off:X}",
                    "reader": reader_name,
                    "raw": raw[:64],
                    "accepted": item.get("accepted", False),
                    "reason": item.get("reason", ""),
                })

        if not hits:
            print("  扫描窗口内没有读到 FString/FText 候选。")
            continue
        for hit in hits[:args.limit]:
            mark = "可用" if hit["accepted"] else "过滤"
            print(f"  {hit['offset']} {hit['reader']} {mark}: {hit['raw']!r} {hit['reason']}")
        if len(hits) > args.limit:
            print(f"  ... 还有 {len(hits) - args.limit} 项，调大 --limit 查看")


def parse_args():
    parser = argparse.ArgumentParser(description="记录并对比玩家存活/阵亡内存状态。")
    sub = parser.add_subparsers(dest="cmd", required=True)

    sample = sub.add_parser("sample", help="采样当前局内玩家状态")
    sample.add_argument("--label", default="alive", help="样本标签，例如 alive/dead")
    sample.add_argument("--samples", type=int, default=1, help="采样次数")
    sample.add_argument("--interval", type=float, default=1.0, help="多次采样间隔秒数")
    sample.add_argument("--out-dir", default="logs", help="日志输出目录")

    compare = sub.add_parser("compare", help="对比两份 JSONL 最后一条样本")
    compare.add_argument("before", help="第一份日志，例如 alive")
    compare.add_argument("after", help="第二份日志，例如 dead")
    compare.add_argument("--limit", type=int, default=120, help="每个玩家最多打印变化项")

    names = sub.add_parser("names", help="扫描 PlayerState 中疑似玩家昵称的 FString/FText 字段")
    names.add_argument("--start", type=lambda v: int(v, 0), default=0x280, help="扫描起始偏移，默认 0x280")
    names.add_argument("--end", type=lambda v: int(v, 0), default=0x480, help="扫描结束偏移，默认 0x480")
    names.add_argument("--step", type=int, default=8, help="扫描步长，默认 8")
    names.add_argument("--max-chars", type=int, default=64, help="最大读取字符数")
    names.add_argument("--limit", type=int, default=80, help="每个 PlayerState 最多打印候选数量")
    return parser.parse_args()


def main():
    args = parse_args()
    if args.cmd == "sample":
        write_samples(args)
    elif args.cmd == "compare":
        compare_snapshots(args)
    elif args.cmd == "names":
        print_name_scan(args)


if __name__ == "__main__":
    main()
