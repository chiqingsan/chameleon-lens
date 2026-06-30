"""MECCHA CHAMELEON 外部读取器和世界到屏幕投影。"""
import math
import struct
import time
import unicodedata
from dataclasses import dataclass

import pymem

from .memory import (
    OFFSETS, FNameResolver, OffsetResolver, PatternScanner, UObjectArray,
    dist, read_array, read_fstring, read_ftext, rfloat, rp, rvec3, ru32,
)


@dataclass(frozen=True)
class TargetSnapshot:
    """覆盖层消费的目标快照；保留迭代兼容旧的五元组调用。"""
    is_local: bool
    pos: tuple
    idx: int
    display_name: str = ""
    player_id: int = 0
    short_id: str = ""
    player_state: int = 0
    pawn: int = 0
    class_name: str = ""
    role: str = "unknown"
    stable_role: str = "unknown"
    filter_role: str = "unknown"
    form: str = "unknown"
    source: str = "unknown"
    position_jump: bool = False
    converted_to_hunter: bool = False
    converted_hunter_age: float = 0.0

    def __iter__(self):
        yield self.is_local
        yield self.pos
        yield self.idx
        yield self.display_name
        yield self.player_id

    def __len__(self):
        return 5


INTERNAL_NAME_PREFIXES = (
    "bp_", "abp_", "wbp_", "mi_", "m_", "t_", "sk_", "sm_", "ns_", "dt_",
    "da_", "default__", "skel_", "reinst_",
)

INTERNAL_NAME_TOKENS = (
    "cleon", "c_leon", "firstperson", "character", "sculpture", "baloon",
    "balloon", "material", "texture", "curve", "vector", "object", "script",
    "component", "controller", "session", "pawn", "spectate", "linearcolor",
    "gradient", "datatable", "rowhandle", "uint", "intvector",
)

FORM_NAME_MAP = {
    "cube": "立方体",
    "base": "基础",
    "hunter": "猎人",
    "survivor": "躲藏者",
    "default": "默认",
    "spectator": "观战",
    "spectatepawn": "观战",
}


def _normalize_display_name(name):
    if not name:
        return "", "empty"
    name = unicodedata.normalize("NFKC", str(name)).strip().strip("\x00").strip()
    if not name:
        return "", "empty"
    if len(name) > 32:
        return "", "too_long"
    if any(sep in name for sep in ("/", "\\", ":", "\r", "\n", "\t")):
        return "", "bad_separator"

    lower = name.lower()
    if lower in ("none", "null", "player", "name", "unknown"):
        return "", "placeholder"
    if lower.startswith(INTERNAL_NAME_PREFIXES):
        return "", "internal_prefix"
    if any(token in lower for token in INTERNAL_NAME_TOKENS):
        return "", "internal_token"

    allowed_symbols = set(" _-[]().#")
    meaningful = 0
    for ch in name:
        code = ord(ch)
        if ch in allowed_symbols:
            continue
        if "0" <= ch <= "9" or "A" <= ch <= "Z" or "a" <= ch <= "z":
            meaningful += 1
            continue
        if "\u4e00" <= ch <= "\u9fff":
            meaningful += 1
            continue
        category = unicodedata.category(ch)
        if category.startswith("C") or category.startswith("M"):
            return "", "bad_unicode"
        # 非 ASCII 拉丁扩展经常来自错误解码的 FString，先保守过滤。
        return "", "unsupported_char"
    if meaningful <= 0:
        return "", "no_meaningful_char"
    return name, ""


# ---------------------------------------------------------------------------
# Game reader
# ---------------------------------------------------------------------------
class MecchaESP:
    PROCESS_NAME = "PenguinHotel-Win64-Shipping.exe"
    MODULE_NAME = "PenguinHotel-Win64-Shipping.exe"

    GUOBJECT_SIG = bytes([
        0x48, 0x8D, 0x05, 0x00, 0x00, 0x00, 0x00,
        0x48, 0x89, 0x01, 0x45, 0x8B, 0xD1
    ])
    GUOBJECT_MASK = bytes([1, 1, 1, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1])

    # Multiple FNamePool references can appear; we verify by trying to read names.
    FNAMEPOOL_PATTERNS = (
        # lea rcx,[FNamePool]; call FName::FName; mov r8,rax
        (bytes([0x48, 0x8D, 0x0D, 0x00, 0x00, 0x00, 0x00,
                0xE8, 0x00, 0x00, 0x00, 0x00,
                0x4C, 0x8B, 0xC0]),
         bytes([1, 1, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 1, 1])),
        # lea rcx,[FNamePool]; call FName::FName; mov rax,[rbx+...]
        (bytes([0x48, 0x8D, 0x0D, 0x00, 0x00, 0x00, 0x00,
                0xE8, 0x00, 0x00, 0x00, 0x00,
                0x48, 0x8B]),
         bytes([1, 1, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 1])),
        # lea rsi,[FNamePool]
        (bytes([0x48, 0x8D, 0x35, 0x00, 0x00, 0x00, 0x00]),
         bytes([1, 1, 1, 0, 0, 0, 0])),
        # lea rdi,[FNamePool]
        (bytes([0x48, 0x8D, 0x3D, 0x00, 0x00, 0x00, 0x00]),
         bytes([1, 1, 1, 0, 0, 0, 0])),
    )
    FNAMEPOOL_DELTA = 0xE3B40
    STALE_PAWN_SECONDS = 1.5
    POSITION_JUMP_UNITS = 30000.0
    ROLE_SWITCH_GRACE_SECONDS = 1.2
    PLAYER_TRACKER_TTL_SECONDS = 20.0
    LIVE_SURVIVOR_CACHE_SECONDS = 8.0
    NAME_CACHE_SECONDS = 1.0
    SPECTATE_LINKED_CHARACTER_OFFSET = 0x1A0
    GAMESTATE_DIAGNOSTIC_OFFSETS = {
        "current_game_phase": 0x0318,
        "live_survivors_player_state": 0x0348,
        "live_survivors_controller": 0x0358,
        "timer_number": 0x0390,
        "timer_text_index": 0x0394,
        "max_timer_time": 0x0398,
        "game_mode_raw": 0x039C,
        "hunters_player_state": 0x03A0,
        "force_provocation_interval": 0x03C0,
        "map_index": 0x03D8,
        "main_game_phase": 0x0418,
    }
    CHARACTER_DIAGNOSTIC_OFFSETS = {
        "mesh": 0x0328,
        "is_hunter_flag": 0x0C3A,
        "is_live_self": 0x0C3C,
        "game_state_ptr": 0x0C40,
        "last_my_player_state_sdk": 0x0C48,
        "body_visibility": 0x0C50,
        "hide_block": 0x0C60,
        "nameplate_visibility": 0x0C61,
    }
    SPECTATE_DIAGNOSTIC_OFFSETS = {
        "spectate_target": 0x0368,
        "self_controller": 0x0378,
        "is_free_camera": 0x0388,
        "my_main_body": 0x03A0,
        "can_back_body": 0x03A8,
    }
    MESH_BLEND_PHYSICS_BYTE_OFFSET = 0x0A71
    MESH_BLEND_PHYSICS_BIT_MASK = 0x20
    MESH_BODY_PHYSICS_BLEND_WEIGHT_OFFSET = 0x04AC
    PLAYERSTATE_FALLBACK_OFFSETS = {
        "CustomPlayerName": 0x388,
        "PlayerNamePrivate": 0x340,
        "PlayerId": 0x2AC,
    }

    OFFSET_MAP = {
        "UWorld::GameState": ("World", "GameState"),
        "UWorld::OwningGameInstance": ("World", "OwningGameInstance"),
        "UGameInstance::LocalPlayers": ("GameInstance", "LocalPlayers"),
        "UPlayer::PlayerController": ("Player", "PlayerController"),
        "UEngine::GameViewport": ("Engine", "GameViewport"),
        "UGameViewportClient::World": ("GameViewportClient", "World"),
        "AGameStateBase::PlayerArray": ("GameStateBase", "PlayerArray"),
        "APlayerState::PawnPrivate": ("PlayerState", "PawnPrivate"),
        "AController::PlayerState": ("Controller", "PlayerState"),
        "AController::ControlRotation": ("Controller", "ControlRotation"),
        "APlayerController::AcknowledgedPawn": ("PlayerController", "AcknowledgedPawn"),
        "APlayerController::PlayerCameraManager": ("PlayerController", "PlayerCameraManager"),
        "APlayerCameraManager::CameraCachePrivate": ("PlayerCameraManager", "CameraCachePrivate"),
        "AActor::RootComponent": ("Actor", "RootComponent"),
        "USceneComponent::RelativeLocation": ("SceneComponent", "RelativeLocation"),
        # Note: UWorld::PersistentLevel and ULevel::Actors are only used in the
        # level-actors fallback; they are resolved lazily with hardcoded defaults.
    }

    def __init__(self):
        self.pm = pymem.Pymem(self.PROCESS_NAME)
        self.guobject_array = self._scan_guobject_array()
        if not self.guobject_array:
            raise RuntimeError("Could not find GUObjectArray via pattern scan")
        self.fname_pool = self._scan_fname_pool()
        if not self.fname_pool:
            raise RuntimeError("Could not find FNamePool via pattern scan or delta fallback")
        self.objects = UObjectArray(self.pm, self.guobject_array, self.fname_pool)
        # Sanity-check globals; on failure we still open, but warn in overlay.
        self._globals_ok = self._verify_globals()
        self.resolver = OffsetResolver(self.pm, self.objects)
        self.offsets = self.resolver.resolve_map(self.OFFSET_MAP)
        self.offsets["APlayerState::CustomPlayerName"] = (
            self.resolver.resolve("PlayerState", "CustomPlayerName")
            or self.PLAYERSTATE_FALLBACK_OFFSETS["CustomPlayerName"]
        )
        self.offsets["APlayerState::PlayerNamePrivate"] = (
            self.resolver.resolve("PlayerState", "PlayerNamePrivate")
            or self.PLAYERSTATE_FALLBACK_OFFSETS["PlayerNamePrivate"]
        )
        self.offsets["APlayerState::PlayerId"] = (
            self.resolver.resolve("PlayerState", "PlayerId")
            or self.PLAYERSTATE_FALLBACK_OFFSETS["PlayerId"]
        )
        # Fill in the stable nested struct offsets from the bootstrap dict.
        for key in ("FCameraCacheEntry::POV", "FMinimalViewInfo::Location",
                    "FMinimalViewInfo::Rotation", "FMinimalViewInfo::FOV"):
            self.offsets[key] = OFFSETS[key]
        self.gengine = self.objects.find_first_instance("GameEngine")
        if not self.gengine:
            raise RuntimeError("Could not find GEngine instance")
        self._pawn_life_tracker = {}
        self._last_iter_stats = {}
        self._last_iter_context = {}
        self._last_playerarray_debug = []
        self._last_level_debug = []
        self._last_emit_debug = []
        self._target_position_cache = {}
        self._last_position_jumps = []
        self._player_state_tracker = {}
        self._player_name_cache = {}
        self._last_world_signature = None

    def _scan_guobject_array(self):
        scanner = PatternScanner(self.pm, self.MODULE_NAME)
        addr = scanner.scan(self.GUOBJECT_SIG, self.GUOBJECT_MASK)
        if not addr:
            return 0
        rel = struct.unpack("<i", self.pm.read_bytes(addr + 3, 4))[0]
        return addr + 7 + rel

    def _scan_fname_pool(self):
        # The delta has been stable for this build; use it as the default.
        delta_candidate = self.guobject_array - self.FNAMEPOOL_DELTA
        if self._verify_fname_pool(delta_candidate):
            return delta_candidate
        # Try a few common FNamePool signatures as backups.
        scanner = PatternScanner(self.pm, self.MODULE_NAME)
        for sig, mask in self.FNAMEPOOL_PATTERNS:
            for addr in scanner.scan_all(sig, mask):
                rel = struct.unpack("<i", self.pm.read_bytes(addr + 3, 4))[0]
                candidate = addr + 7 + rel
                if self._verify_fname_pool(candidate):
                    return candidate
        # Even if unverified, fall back to the delta so the ESP can still open.
        # Name resolution may self-correct via the resolver's lazy offset probe.
        return delta_candidate

    def _verify_fname_pool(self, pool_addr):
        resolver = FNameResolver(self.pm, pool_addr)
        if resolver.resolve(0) == "None":
            return True
        # Some builds don't keep "None" at id 0; settle for any printable name.
        for probe in (0, 1, 2, 3, 4, 5):
            name = resolver.resolve(probe)
            if name and 0 < len(name) <= 128 and name.isprintable():
                return True
        return False

    def _verify_globals(self):
        # GUObjectArray + 0x10 is TUObjectArray::Objects; read its header.
        obj_array = self.guobject_array + 0x10
        num = ru32(self.pm, obj_array + 0x14)
        max_chunks = ru32(self.pm, obj_array + 0x18)
        if num == 0 or num > 10_000_000 or max_chunks == 0 or max_chunks > 64:
            return False
        # We should be able to find the meta Class object.
        return self.objects.find_class("Class") != 0

    def _get_world(self):
        viewport = rp(self.pm, self.gengine + self.offsets["UEngine::GameViewport"])
        if not viewport:
            return 0
        return rp(self.pm, viewport + self.offsets["UGameViewportClient::World"])

    def _get_local_controller(self, world):
        if not world:
            return 0
        gi = rp(self.pm, world + self.offsets["UWorld::OwningGameInstance"])
        if not gi:
            return 0
        lp_data, lp_count, _ = read_array(self.pm, gi + self.offsets["UGameInstance::LocalPlayers"])
        if not lp_data or lp_count == 0:
            return 0
        local_player = rp(self.pm, lp_data)
        if not local_player:
            return 0
        return rp(self.pm, local_player + self.offsets["UPlayer::PlayerController"])

    def _read_pov(self, pov_addr):
        """Read a minimal view POV from the given address."""
        return {
            "loc": rvec3(self.pm, pov_addr + self.offsets["FMinimalViewInfo::Location"]),
            "rot": rvec3(self.pm, pov_addr + self.offsets["FMinimalViewInfo::Rotation"]),
            "fov": rfloat(self.pm, pov_addr + self.offsets["FMinimalViewInfo::FOV"]),
        }

    def get_camera(self):
        world = self._get_world()
        if not world:
            return None
        pc = self._get_local_controller(world)
        if not pc:
            return None
        cam = rp(self.pm, pc + self.offsets["APlayerController::PlayerCameraManager"])
        if not cam:
            return None

        # Primary: CameraCachePrivate (always reflects the current camera).
        cc = cam + self.offsets["APlayerCameraManager::CameraCachePrivate"]
        pov = cc + self.offsets["FCameraCacheEntry::POV"]
        try:
            camera = self._read_pov(pov)
        except Exception:
            camera = None

        # Fallback: PlayerCameraManager->ViewTarget.POV (some spectate/free-look modes).
        if (camera is None or
            (abs(camera["loc"][0]) < 0.01 and abs(camera["loc"][1]) < 0.01 and abs(camera["loc"][2]) < 0.01) or
            camera["fov"] <= 0.0):
            vt_off = self.offsets.get("APlayerCameraManager::ViewTarget")
            vt_pov_off = self.offsets.get("FTViewTarget::POV")
            if vt_off is not None and vt_pov_off is not None:
                try:
                    fallback = self._read_pov(cam + vt_off + vt_pov_off)
                    if fallback["fov"] > 0.0:
                        camera = fallback
                except Exception:
                    pass

        if camera is None or camera["fov"] <= 0.0:
            return None
        return camera

    def _class_name(self, obj):
        if not obj:
            return ""
        cls = rp(self.pm, obj + OFFSETS["UObjectBase::ClassPrivate"])
        return self.objects._obj_name(cls) if cls else ""

    def _object_name(self, obj):
        """读取 UObject 名称，用于日志里识别地图、GameState 和模式指纹。"""
        if not obj:
            return ""
        try:
            return self.objects._obj_name(obj) or ""
        except Exception:
            return ""

    def _safe_class_name(self, obj):
        """调试上下文读取不能影响目标枚举，失败时只返回空字符串。"""
        try:
            return self._class_name(obj)
        except Exception:
            return ""

    def _pawn_controller(self, pawn):
        if not pawn:
            return 0
        off = self.offsets.get("APawn::Controller")
        if off is None:
            off = self.resolver.resolve("Pawn", "Controller") or 0
            self.offsets["APawn::Controller"] = off
        return rp(self.pm, pawn + off)

    def _pawn_playerstate(self, pawn):
        if not pawn:
            return 0
        off = self.offsets.get("APawn::PlayerState")
        if off is None:
            off = self.resolver.resolve("Pawn", "PlayerState") or 0
            self.offsets["APawn::PlayerState"] = off
        return rp(self.pm, pawn + off)

    def _resolve_object_property_offset(self, obj, prop_name, fallback=0):
        """按对象实际类链解析属性偏移；蓝图子类字段不会出现在基础 PlayerState 上。"""
        if not obj:
            return fallback
        cache_key = f"ObjectProperty::{self._class_name(obj)}::{prop_name}"
        if cache_key in self.offsets:
            return self.offsets[cache_key]
        cls = rp(self.pm, obj + OFFSETS["UObjectBase::ClassPrivate"])
        seen = set()
        while cls and cls not in seen:
            seen.add(cls)
            try:
                offset = self.resolver._resolve_on_class(cls, prop_name)
            except Exception:
                offset = None
            if offset is not None:
                self.offsets[cache_key] = offset
                return offset
            cls = rp(self.pm, cls + OFFSETS["UStruct::SuperStruct"])
        self.offsets[cache_key] = fallback
        return fallback

    def _read_name_candidate(self, player_state, prop_name, offset, readers):
        out = {
            "field": prop_name,
            "offset": offset,
            "raw": "",
            "source": "",
            "accepted": False,
            "reason": "missing_offset",
        }
        if not player_state or not offset:
            return out
        first_rejected = None
        for reader_name, reader in readers:
            try:
                raw = reader(self.pm, player_state + offset)
            except Exception:
                raw = ""
            name, reason = _normalize_display_name(raw)
            if name:
                out["raw"] = raw
                out["name"] = name
                out["source"] = reader_name
                out["accepted"] = True
                out["reason"] = ""
                return out
            if raw:
                first_rejected = first_rejected or {
                    "raw": raw,
                    "source": reader_name,
                    "reason": reason or "rejected",
                }
        if first_rejected:
            out.update(first_rejected)
        else:
            out["reason"] = "empty"
        return out

    def _player_name_candidates(self, player_state):
        if not player_state:
            return []
        custom_off = self._resolve_object_property_offset(
            player_state,
            "CustomPlayerName",
            self.offsets.get("APlayerState::CustomPlayerName", 0),
        )
        private_off = self._resolve_object_property_offset(
            player_state,
            "PlayerNamePrivate",
            self.offsets.get("APlayerState::PlayerNamePrivate", 0),
        )
        # CustomPlayerName 在历史日志里最像真实昵称字段；它可能是 FString，也可能是 FText。
        return [
            self._read_name_candidate(
                player_state,
                "CustomPlayerName",
                custom_off,
                (("FText", read_ftext), ("FString", read_fstring)),
            ),
            self._read_name_candidate(
                player_state,
                "PlayerNamePrivate",
                private_off,
                (("FString", read_fstring),),
            ),
        ]

    def _player_display_name_info(self, player_state, include_candidates=False):
        now = time.monotonic()
        cached = self._player_name_cache.get(player_state)
        if cached and now - cached.get("seen_at", 0.0) < self.NAME_CACHE_SECONDS:
            if include_candidates and "candidates" not in cached:
                cached["candidates"] = self._debug_name_candidates(player_state)
            return {
                "name": cached.get("name", ""),
                "source": cached.get("source", ""),
                "reader": cached.get("reader", ""),
                "candidates": cached.get("candidates", []) if include_candidates else [],
            }

        scanned_candidates = self._player_name_candidates(player_state)
        for candidate in scanned_candidates:
            if candidate.get("accepted"):
                info = {
                    "name": candidate.get("name", ""),
                    "source": candidate.get("field", ""),
                    "reader": candidate.get("source", ""),
                }
                if include_candidates:
                    info["candidates"] = self._format_name_candidates(scanned_candidates)
                self._player_name_cache[player_state] = {"seen_at": now, **info}
                return {**info, "candidates": info.get("candidates", [])}

        info = {
            "name": "",
            "source": "",
            "reader": "",
        }
        if include_candidates:
            info["candidates"] = self._format_name_candidates(scanned_candidates)
        self._player_name_cache[player_state] = {"seen_at": now, **info}
        return {**info, "candidates": info.get("candidates", [])}

    @staticmethod
    def _format_name_candidates(items):
        candidates = []
        for item in items:
            raw = item.get("raw") or ""
            candidates.append({
                "field": item.get("field", ""),
                "offset": item.get("offset", 0),
                "source": item.get("source", ""),
                "raw": raw[:48],
                "accepted": bool(item.get("accepted")),
                "reason": item.get("reason", ""),
            })
        return candidates

    def _debug_name_candidates(self, player_state):
        """记录候选名称的过滤结果；只用于日志，不直接显示到覆盖层。"""
        return self._format_name_candidates(self._player_name_candidates(player_state))

    def _player_display_name(self, player_state):
        if not player_state:
            return ""
        return self._player_display_name_info(player_state)["name"]

    def _player_id(self, player_state):
        """读取 APlayerState::PlayerId，作为比 PlayerArray idx 更稳定的短 ID。"""
        if not player_state:
            return 0
        off = self.offsets.get("APlayerState::PlayerId", 0)
        if not off:
            return 0
        player_id = ru32(self.pm, player_state + off)
        if player_id <= 0 or player_id > 1_000_000:
            return 0
        return player_id

    def _player_display_label(self, player_state):
        name = self._player_display_name(player_state)
        if name:
            return name
        player_id = self._player_id(player_state)
        return f"ID {player_id}" if player_id else ""

    def _player_debug_identity(self, player_state, collect_debug=False):
        """整理 PlayerState 身份信息；本地玩家即使不绘制也要进调试日志。"""
        player_id = self._player_id(player_state)
        name_info = self._player_display_name_info(player_state, include_candidates=collect_debug)
        return {
            "player_id": player_id,
            "short_id": self._short_pointer_id(player_state),
            "display_name": name_info.get("name", ""),
            "display_name_source": name_info.get("source", ""),
            "display_name_reader": name_info.get("reader", ""),
            "name_candidates": name_info.get("candidates", []) if collect_debug else [],
        }

    def _actor_owner(self, actor):
        if not actor:
            return 0
        off = self.offsets.get("AActor::Owner")
        if off is None:
            return 0
        return rp(self.pm, actor + off)

    def _component_world_pos(self, component):
        """Read a USceneComponent's world translation from ComponentToWorld."""
        if not component:
            return None
        ctw_off = self.offsets.get("USceneComponent::ComponentToWorld")
        trans_off = self.offsets.get("FTransform::Translation")
        if ctw_off is None or trans_off is None:
            return None
        try:
            return rvec3(self.pm, component + ctw_off + trans_off)
        except Exception:
            return None

    def _actor_position_info(self, actor):
        """返回 Actor 坐标和来源，方便定位漏绘制时到底读到了哪一种位置。"""
        info = {
            "position": None,
            "source": "missing_actor",
            "root": 0,
            "mesh": 0,
        }

        if not actor:
            return info
        root = rp(self.pm, actor + self.offsets["AActor::RootComponent"])
        info["root"] = root
        if root:
            rel_off = self.offsets.get("USceneComponent::RelativeLocation")
            if rel_off is not None:
                try:
                    pos = rvec3(self.pm, root + rel_off)
                    # Only fall through to ComponentToWorld if RelativeLocation
                    # is clearly uninitialized (origin-only).
                    if not (abs(pos[0]) < 0.01 and abs(pos[1]) < 0.01 and abs(pos[2]) < 0.01):
                        info["position"] = pos
                        info["source"] = "root_relative_location"
                        return info
                except Exception:
                    pass
            # Fallback: world-space transform.
            pos = self._component_world_pos(root)
            if pos is not None:
                info["position"] = pos
                info["source"] = "root_component_to_world"
                return info
        # Last resort: mesh world transform.
        mesh_off = self.offsets.get("ACharacter::Mesh")
        if mesh_off is not None:
            mesh = rp(self.pm, actor + mesh_off)
            info["mesh"] = mesh
            if mesh:
                pos = self._component_world_pos(mesh)
                if pos is not None:
                    info["position"] = pos
                    info["source"] = "mesh_component_to_world"
                    return info
        info["source"] = "missing_position"
        return info

    def _actor_position(self, actor):
        """Return the best available world position for an actor."""
        return self._actor_position_info(actor)["position"]

    @staticmethod
    def _debug_hex(value):
        return f"0x{int(value):X}" if value else "0x0"

    @staticmethod
    def _short_pointer_id(*values):
        for value in values:
            if value:
                return f"{int(value) & 0xFFFFFF:06X}"
        return ""

    @staticmethod
    def _debug_pos(pos):
        if pos is None:
            return None
        return [round(float(v), 3) for v in pos]

    @staticmethod
    def _is_origin_position(pos):
        return pos is not None and abs(pos[0]) < 0.01 and abs(pos[1]) < 0.01 and abs(pos[2]) < 0.01

    def _class_role_info(self, cls_name):
        lower = (cls_name or "").lower()
        if "spectate" in lower:
            role = "spectator"
        elif "hunter" in lower:
            role = "hunter"
        elif "survivor" in lower:
            role = "survivor"
        elif "character" in lower:
            role = "character"
        else:
            role = "unknown"

        form = "unknown"
        for token, label in FORM_NAME_MAP.items():
            if token in lower:
                form = label
        if role == "survivor":
            # 形态通常藏在类名末尾，例如 Default_Cube_1point7。
            for token in ("cube", "base"):
                if token in lower:
                    form = FORM_NAME_MAP[token]
                    break
        elif role in ("hunter", "spectator"):
            form = FORM_NAME_MAP.get(role, role)

        return role, form

    def _update_player_state_tracker(self, player_state, role, form, cls_name, pawn, pos, now):
        """跟踪同一 PlayerState 的身份切换，给 UI 过滤提供短时防抖依据。"""
        role = role or "unknown"
        key = int(player_state or 0)
        if not key:
            return {
                "stable_role": role,
                "filter_role": role,
                "role_age": 0.0,
                "role_pending": False,
                "role_previous": "",
            }

        item = self._player_state_tracker.setdefault(key, {
            "current_role": role,
            "stable_role": role,
            "role_since": now,
            "last_seen": now,
            "last_non_spectator_role": "",
            "last_non_spectator_pawn": 0,
            "last_non_spectator_pos": None,
            "converted_to_hunter": False,
            "converted_hunter_since": 0.0,
        })
        item["last_seen"] = now

        if item.get("current_role") != role:
            item["previous_role"] = item.get("current_role", "")
            if role == "hunter" and (
                item.get("current_role") == "survivor"
                or item.get("stable_role") == "survivor"
                or item.get("last_non_spectator_role") == "survivor"
            ):
                item["converted_to_hunter"] = True
                item["converted_hunter_since"] = now
            elif role == "survivor" and item.get("current_role") != "spectator":
                item["converted_to_hunter"] = False
                item["converted_hunter_since"] = 0.0
            item["current_role"] = role
            item["role_since"] = now

        role_age = max(0.0, now - item.get("role_since", now))
        if role_age >= self.ROLE_SWITCH_GRACE_SECONDS:
            item["stable_role"] = role

        if role not in ("spectator", "unknown"):
            item["last_non_spectator_role"] = role
            if pawn:
                item["last_non_spectator_pawn"] = pawn
            if pos is not None:
                item["last_non_spectator_pos"] = pos

        stable_role = item.get("stable_role") or role
        role_pending = role != stable_role and role_age < self.ROLE_SWITCH_GRACE_SECONDS
        filter_role = stable_role if role_pending else role
        return {
            "stable_role": stable_role,
            "filter_role": filter_role,
            "role_age": round(float(role_age), 3),
            "role_pending": bool(role_pending),
            "role_previous": item.get("previous_role", ""),
            "last_non_spectator_role": item.get("last_non_spectator_role", ""),
            "last_non_spectator_pawn": self._debug_hex(item.get("last_non_spectator_pawn", 0)),
            "last_non_spectator_pos": self._debug_pos(item.get("last_non_spectator_pos")),
            "converted_to_hunter": bool(item.get("converted_to_hunter", False)),
            "converted_hunter_age": round(float(now - item.get("converted_hunter_since", now)), 3)
            if item.get("converted_hunter_since") else 0.0,
        }

    def _reset_match_trackers(self):
        """地图/对局上下文变化时清理跨局缓存，避免旧身份污染新局。"""
        self._pawn_life_tracker.clear()
        self._target_position_cache.clear()
        self._player_state_tracker.clear()
        self._player_name_cache.clear()

    def _cached_live_survivor_actor(self, player_state, game_membership, now):
        """GameState 仍确认存活时，用最近的非观战角色实例兜底 PlayerArray 短暂空 Pawn。"""
        if not player_state or not game_membership.get("valid"):
            return 0, {}
        if player_state not in game_membership.get("live_survivors", set()):
            return 0, {}
        item = self._player_state_tracker.get(player_state) or {}
        age = now - item.get("last_seen", now)
        actor = item.get("last_non_spectator_pawn", 0)
        if (
            not actor
            or age > self.LIVE_SURVIVOR_CACHE_SECONDS
            or item.get("last_non_spectator_role") != "survivor"
        ):
            return 0, {}
        cls_name = self._class_name(actor)
        if not self._is_character_class(cls_name):
            return 0, {}
        pos = self._actor_position(actor)
        if pos is None or self._is_origin_position(pos):
            return 0, {}
        return actor, {
            "age": round(float(age), 3),
            "class": cls_name,
            "position": self._debug_pos(pos),
            "last_position": self._debug_pos(item.get("last_non_spectator_pos")),
        }

    def _update_world_signature(self, world, world_name, game_state, game_state_name, level_name):
        signature = (
            self._debug_hex(world),
            world_name or "",
            self._debug_hex(game_state),
            game_state_name or "",
            level_name or "",
        )
        previous = self._last_world_signature
        if previous is None:
            self._last_world_signature = signature
            return {"type": "initial", "from": [], "to": list(signature)}
        if previous != signature:
            self._reset_match_trackers()
            self._last_world_signature = signature
            return {"type": "world_context_changed", "from": list(previous), "to": list(signature)}
        return {}

    def _cleanup_player_state_tracker(self, active_player_states, now):
        stale = [
            key for key, item in self._player_state_tracker.items()
            if key not in active_player_states and now - item.get("last_seen", now) > self.PLAYER_TRACKER_TTL_SECONDS
        ]
        for key in stale:
            del self._player_state_tracker[key]

    def _cleanup_player_name_cache(self, active_player_states, now):
        stale = [
            key for key, item in self._player_name_cache.items()
            if key not in active_player_states and now - item.get("seen_at", now) > self.PLAYER_TRACKER_TTL_SECONDS
        ]
        for key in stale:
            del self._player_name_cache[key]

    def _read_object_property_u8(self, obj, prop_name):
        off = self._resolve_object_property_offset(obj, prop_name, 0)
        if not off:
            return None
        try:
            return ru32(self.pm, obj + off) & 0xFF
        except Exception:
            return None

    def _read_object_property_ptr(self, obj, prop_name):
        off = self._resolve_object_property_offset(obj, prop_name, 0)
        if not off:
            return 0
        try:
            return rp(self.pm, obj + off)
        except Exception:
            return 0

    def _read_u8_at(self, addr):
        try:
            return struct.unpack("<B", self.pm.read_bytes(addr, 1))[0]
        except Exception:
            return None

    def _read_i32_at(self, addr):
        try:
            return struct.unpack("<i", self.pm.read_bytes(addr, 4))[0]
        except Exception:
            return None

    def _debug_ptr_array_at(self, base, offset, limit=16):
        out = {
            "offset": offset,
            "data": "0x0",
            "count": 0,
            "max": 0,
            "max_legacy_10": 0,
            "items": [],
        }
        if not base:
            return out
        array_addr = base + offset
        data = rp(self.pm, array_addr)
        count = ru32(self.pm, array_addr + 0x08)
        # 标准 TArray 的 Max 在 +0x0C；旧 read_array helper 读取 +0x10，这里两者都记录便于对照。
        cap = ru32(self.pm, array_addr + 0x0C)
        legacy_cap = ru32(self.pm, array_addr + 0x10)
        out["data"] = self._debug_hex(data)
        out["count"] = int(count or 0)
        out["max"] = int(cap or 0)
        out["max_legacy_10"] = int(legacy_cap or 0)
        if not data or count <= 0 or count > 256:
            return out
        for i in range(min(count, limit)):
            ptr = rp(self.pm, data + i * 8)
            out["items"].append({
                "idx": i,
                "ptr": self._debug_hex(ptr),
                "class": self._safe_class_name(ptr),
                "name": self._object_name(ptr),
            })
        return out

    def _ptr_set_at(self, base, offset, limit=64):
        if not base:
            return set(), 0
        data = rp(self.pm, base + offset)
        count = ru32(self.pm, base + offset + 0x08)
        if not data or count <= 0 or count > limit:
            return set(), int(count or 0)
        return {rp(self.pm, data + i * 8) for i in range(count)}, int(count)

    def _game_state_membership(self, gamestate):
        """读取 GameState 阵营数组；只在数组看起来稳定时参与过滤。"""
        if not gamestate:
            return {
                "valid": False,
                "mode_raw": None,
                "main_phase": None,
                "current_phase": None,
                "live_survivors": set(),
                "hunters": set(),
                "live_count": 0,
                "hunter_count": 0,
            }
        off = self.GAMESTATE_DIAGNOSTIC_OFFSETS
        live, live_count = self._ptr_set_at(gamestate, off["live_survivors_player_state"])
        hunters, hunter_count = self._ptr_set_at(gamestate, off["hunters_player_state"])
        mode_raw = self._read_u8_at(gamestate + off["game_mode_raw"])
        main_phase = self._read_u8_at(gamestate + off["main_game_phase"])
        current_phase = self._read_u8_at(gamestate + off["current_game_phase"])
        # phase 0 且数组为空时通常是大厅/结算切换，不能用空数组隐藏目标。
        valid = (
            mode_raw in (0, 1)
            and main_phase in (1, 2, 3)
            and (live_count > 0 or hunter_count > 0)
            and live_count <= 64
            and hunter_count <= 64
        )
        return {
            "valid": bool(valid),
            "mode_raw": mode_raw,
            "main_phase": main_phase,
            "current_phase": current_phase,
            "live_survivors": live,
            "hunters": hunters,
            "live_count": live_count,
            "hunter_count": hunter_count,
        }

    def _player_membership_debug(self, player_state, membership):
        state = "unknown"
        if membership.get("valid"):
            if player_state in membership.get("live_survivors", set()):
                state = "live_survivor"
            elif player_state in membership.get("hunters", set()):
                state = "hunter"
            else:
                state = "neither"
        return {
            "valid": bool(membership.get("valid")),
            "state": state,
            "mode_raw": membership.get("mode_raw"),
            "mode_label": self._game_mode_label(membership.get("mode_raw")),
            "main_phase": membership.get("main_phase"),
            "main_phase_label": self._main_phase_label(membership.get("main_phase")),
            "current_phase": membership.get("current_phase"),
            "live_count": membership.get("live_count", 0),
            "hunter_count": membership.get("hunter_count", 0),
        }

    def _array_role_for_player(self, player_state, membership):
        if not player_state or not membership.get("valid"):
            return ""
        if player_state in membership.get("live_survivors", set()):
            return "survivor"
        if player_state in membership.get("hunters", set()):
            return "hunter"
        return ""

    def _form_for_array_role(self, array_role, current_form):
        if array_role == "hunter":
            return FORM_NAME_MAP.get("hunter", current_form)
        if array_role == "survivor" and current_form == "unknown":
            return FORM_NAME_MAP.get("survivor", current_form)
        return current_form

    @staticmethod
    def _game_mode_label(mode_raw):
        if mode_raw == 0:
            return "infection"
        if mode_raw == 1:
            return "non_infection"
        return "unknown"

    @staticmethod
    def _main_phase_label(main_phase):
        return {
            0: "idle_or_transition",
            1: "pre_round",
            2: "in_round",
            3: "round_end",
        }.get(main_phase, "unknown")

    @staticmethod
    def _is_character_class(cls_name):
        return bool(cls_name) and "Character" in cls_name and "Spectate" not in cls_name

    def _game_state_debug_fields(self, gamestate):
        """记录 SDK 里已知的 GameState 原始字段，只用于后续模式指纹分析。"""
        if not gamestate:
            return {}
        off = self.GAMESTATE_DIAGNOSTIC_OFFSETS
        return {
            "current_game_phase": self._read_u8_at(gamestate + off["current_game_phase"]),
            "main_game_phase": self._read_u8_at(gamestate + off["main_game_phase"]),
            "game_mode_raw": self._read_u8_at(gamestate + off["game_mode_raw"]),
            "timer_number": self._read_i32_at(gamestate + off["timer_number"]),
            "timer_text_index": self._read_i32_at(gamestate + off["timer_text_index"]),
            "max_timer_time": self._read_i32_at(gamestate + off["max_timer_time"]),
            "force_provocation_interval": self._read_i32_at(gamestate + off["force_provocation_interval"]),
            "map_index": self._read_i32_at(gamestate + off["map_index"]),
            "live_survivors_player_state": self._debug_ptr_array_at(
                gamestate, off["live_survivors_player_state"]
            ),
            "live_survivors_controller": self._debug_ptr_array_at(
                gamestate, off["live_survivors_controller"]
            ),
            "hunters_player_state": self._debug_ptr_array_at(
                gamestate, off["hunters_player_state"]
            ),
        }

    def _character_debug_fields(self, actor):
        """记录 Character 蓝图字段和物理混合状态；这些字段暂不参与过滤。"""
        if not actor:
            return {}
        off = self.CHARACTER_DIAGNOSTIC_OFFSETS
        mesh = rp(self.pm, actor + off["mesh"])
        blend_raw = self._read_u8_at(mesh + self.MESH_BLEND_PHYSICS_BYTE_OFFSET) if mesh else None
        return {
            "is_hunter_flag": self._read_u8_at(actor + off["is_hunter_flag"]),
            "is_live_self": self._read_u8_at(actor + off["is_live_self"]),
            "body_visibility": self._read_u8_at(actor + off["body_visibility"]),
            "hide_block": self._read_u8_at(actor + off["hide_block"]),
            "nameplate_visibility": self._read_u8_at(actor + off["nameplate_visibility"]),
            "game_state_ptr": self._debug_hex(rp(self.pm, actor + off["game_state_ptr"])),
            "last_my_player_state_sdk": self._debug_hex(rp(self.pm, actor + off["last_my_player_state_sdk"])),
            "mesh": self._debug_hex(mesh),
            "mesh_blend_physics_raw": blend_raw,
            "mesh_blend_physics_bit": bool(blend_raw & self.MESH_BLEND_PHYSICS_BIT_MASK)
            if blend_raw is not None else None,
            "body_physics_blend_weight": round(
                float(rfloat(self.pm, mesh + self.MESH_BODY_PHYSICS_BLEND_WEIGHT_OFFSET)), 4
            ) if mesh else None,
        }

    def _debug_actor_brief(self, actor):
        if not actor:
            return {"ptr": "0x0"}
        pos_info = self._actor_position_info(actor)
        return {
            "ptr": self._debug_hex(actor),
            "class": self._safe_class_name(actor),
            "name": self._object_name(actor),
            "position": self._debug_pos(pos_info.get("position")),
            "position_source": pos_info.get("source", ""),
        }

    def _spectate_debug_fields(self, spectate_pawn):
        """记录 BP_SpectatePawn_cLeon_C 命名字段，用来和旧 0x1A0 链接做对比。"""
        if not spectate_pawn:
            return {}
        off = self.SPECTATE_DIAGNOSTIC_OFFSETS
        spectate_target = rp(self.pm, spectate_pawn + off["spectate_target"])
        self_controller = rp(self.pm, spectate_pawn + off["self_controller"])
        my_main_body = rp(self.pm, spectate_pawn + off["my_main_body"])
        return {
            "spectate_target": self._debug_actor_brief(spectate_target),
            "self_controller": self._debug_hex(self_controller),
            "self_controller_class": self._safe_class_name(self_controller),
            "is_free_camera": self._read_u8_at(spectate_pawn + off["is_free_camera"]),
            "my_main_body": self._debug_actor_brief(my_main_body),
            "can_back_body": self._read_u8_at(spectate_pawn + off["can_back_body"]),
        }

    def _spectate_linked_character_info(self, spectate_pawn, player_state, collect_debug=False):
        """SpectatePawn 可能只是观战壳；若它指向真实角色，就用真实角色绘制。"""
        info = {
            "actor": 0,
            "reason": "no_linked_actor",
            "spectate_class": self._safe_class_name(spectate_pawn),
            "spectate_position": self._debug_pos(self._actor_position(spectate_pawn)),
        }
        if collect_debug:
            info["spectate_fields"] = self._spectate_debug_fields(spectate_pawn)
        if not spectate_pawn:
            return info
        try:
            linked = rp(self.pm, spectate_pawn + self.SPECTATE_LINKED_CHARACTER_OFFSET)
        except Exception:
            info["reason"] = "read_failed"
            return info

        info["actor"] = linked
        info["offset"] = self.SPECTATE_LINKED_CHARACTER_OFFSET
        info["actor_hex"] = self._debug_hex(linked)
        if not linked or linked == spectate_pawn:
            info["reason"] = "empty_or_self"
            return info

        cls_name = self._class_name(linked)
        info["class"] = cls_name
        role, form = self._class_role_info(cls_name)
        info["role"] = role
        info["form"] = form
        if collect_debug and self._is_character_class(cls_name):
            info["character_flags"] = self._character_debug_fields(linked)
        if not cls_name or "Character" not in cls_name or "Spectate" in cls_name:
            info["reason"] = "not_character"
            return info

        actor_ps = self._pawn_playerstate(linked)
        last_ps = self._read_object_property_ptr(linked, "LastMyPlayerState")
        controller = self._pawn_controller(linked)
        info["last_player_state"] = self._debug_hex(last_ps)
        info["actor_player_state"] = self._debug_hex(actor_ps)
        info["controller"] = self._debug_hex(controller)
        # 当前先优先保证躲藏方不漏绘制：普通模式死亡后可能会继续显示旧 Character。
        # 后续拿到稳定模式指纹后，再把普通模式和特殊模式拆成不同策略。
        if player_state and last_ps != player_state and actor_ps != player_state:
            info["reason"] = "player_state_mismatch"
            return info

        dead = self._read_object_property_u8(linked, "Dead")
        info["dead"] = dead

        pos_info = self._actor_position_info(linked)
        pos = pos_info["position"]
        info["position"] = self._debug_pos(pos)
        info["position_source"] = pos_info["source"]
        info["root"] = self._debug_hex(pos_info.get("root", 0))
        info["mesh"] = self._debug_hex(pos_info.get("mesh", 0))
        if pos is None or self._is_origin_position(pos):
            info["reason"] = "invalid_position"
            return info

        info["reason"] = "linked_character"
        return info

    def _track_position_jump(self, key, pos, now):
        """用位置大跳变识别回合/地图切换，并清理依赖旧位置的缓存。"""
        if not key or pos is None:
            return False, 0.0
        previous = self._target_position_cache.get(key)
        self._target_position_cache[key] = (pos, now)
        if not previous:
            return False, 0.0
        distance = dist(previous[0], pos)
        if distance < self.POSITION_JUMP_UNITS:
            return False, distance

        self._pawn_life_tracker.clear()
        self._player_state_tracker.clear()
        self._last_position_jumps.append({
            "key": key,
            "distance": round(float(distance), 3),
            "from": self._debug_pos(previous[0]),
            "to": self._debug_pos(pos),
        })
        self._last_position_jumps = self._last_position_jumps[-24:]
        return True, distance

    def _cleanup_target_position_cache(self, active_keys, now):
        stale = [
            key for key, (_, seen_at) in self._target_position_cache.items()
            if key not in active_keys and now - seen_at > 10.0
        ]
        for key in stale:
            del self._target_position_cache[key]

    def _should_skip_stale_playerarray_pawn(self, player_state, pawn, pos, now):
        """延迟判定 PlayerArray 里的旧 pawn，避免开局字段暂不同步导致漏绘制。"""
        reverse_off = self.offsets.get("APawn::PlayerState", 0)
        if not reverse_off:
            return False

        reverse_ps = self._pawn_playerstate(pawn)
        item = self._pawn_life_tracker.setdefault(pawn, {
            "first_seen": now,
            "last_seen": now,
            "seen_bound": False,
            "invalid_since": None,
        })
        item["last_seen"] = now

        if reverse_ps == player_state:
            item["seen_bound"] = True
            item["invalid_since"] = None
            return False

        if item["invalid_since"] is None:
            item["invalid_since"] = now

        invalid_seconds = now - item["invalid_since"]

        # 躲猫猫类游戏里“静止不动”是正常玩法，不能作为死亡依据。
        # 这里只在同一个 pawn 曾经绑定正常、随后反向 PlayerState 断开并持续一段时间后跳过。
        if item["seen_bound"] and invalid_seconds >= self.STALE_PAWN_SECONDS:
            return True

        return False

    def _cleanup_pawn_life_tracker(self, seen_pawns, now):
        stale = [
            pawn for pawn, item in self._pawn_life_tracker.items()
            if pawn not in seen_pawns and now - item.get("last_seen", now) > 10.0
        ]
        for pawn in stale:
            del self._pawn_life_tracker[pawn]

    def iter_players(self, include_local=False, players_only=False, collect_debug=True):
        now = time.monotonic()
        world = self._get_world()
        if not world:
            self._last_iter_stats = {"pa_total": 0, "pa_valid": 0, "pa_dead": 0,
                                     "pa_orphan": 0, "pa_suspect": 0,
                                     "pa_linked": 0,
                                     "pa_cached": 0,
                                     "pa_suppressed": 0,
                                     "level_total": 0, "level_valid": 0,
                                     "level_orphan": 0,
                                     "rendered": 0}
            self._last_iter_context = {"world": "0x0"}
            self._last_playerarray_debug = []
            self._last_level_debug = []
            self._last_emit_debug = []
            self._last_position_jumps = []
            return
        gamestate = rp(self.pm, world + self.offsets["UWorld::GameState"])
        pc = self._get_local_controller(world)
        local_pawn = rp(self.pm, pc + self.offsets["APlayerController::AcknowledgedPawn"]) if pc else 0
        local_ps = rp(self.pm, pc + self.offsets["AController::PlayerState"]) if pc else 0
        persistent_level_off = self.offsets.get("UWorld::PersistentLevel", 0x30)
        persistent_level = rp(self.pm, world + persistent_level_off) if world else 0
        world_name = self._object_name(world)
        world_class = self._safe_class_name(world)
        game_state_name = self._object_name(gamestate)
        game_state_class = self._safe_class_name(gamestate)
        persistent_level_name = self._object_name(persistent_level)
        persistent_level_class = self._safe_class_name(persistent_level)
        context_event = self._update_world_signature(
            world, world_name, gamestate, game_state_name, persistent_level_name
        )
        game_membership = self._game_state_membership(gamestate)

        stats = {"pa_total": 0, "pa_valid": 0, "pa_dead": 0, "pa_orphan": 0, "pa_suspect": 0,
                 "pa_linked": 0,
                 "pa_cached": 0,
                 "pa_suppressed": 0,
                 "level_total": 0, "level_valid": 0,
                 "level_orphan": 0,
                 "rendered": 0}
        seen = set()
        seen_life_pawns = set()
        active_position_keys = set()
        active_player_states = set()
        playerarray_debug = []
        level_debug = []
        emit_debug = []
        self._last_position_jumps = []
        self._last_iter_context = {
            "world": self._debug_hex(world),
            "world_name": world_name,
            "world_class": world_class,
            "game_state": self._debug_hex(gamestate),
            "game_state_name": game_state_name,
            "game_state_class": game_state_class,
            "persistent_level": self._debug_hex(persistent_level),
            "persistent_level_name": persistent_level_name,
            "persistent_level_class": persistent_level_class,
            "context_event": context_event,
            "local_controller": self._debug_hex(pc),
            "local_controller_class": self._safe_class_name(pc),
            "local_player_state": self._debug_hex(local_ps),
            "local_player_state_class": self._safe_class_name(local_ps),
            "local_pawn": self._debug_hex(local_pawn),
            "local_pawn_class": self._safe_class_name(local_pawn),
        }
        if collect_debug:
            self._last_iter_context["game_state_fields"] = self._game_state_debug_fields(gamestate)
            self._last_iter_context["game_state_membership"] = {
                "valid": bool(game_membership.get("valid")),
                "mode_raw": game_membership.get("mode_raw"),
                "mode_label": self._game_mode_label(game_membership.get("mode_raw")),
                "main_phase": game_membership.get("main_phase"),
                "main_phase_label": self._main_phase_label(game_membership.get("main_phase")),
                "current_phase": game_membership.get("current_phase"),
                "live_count": game_membership.get("live_count", 0),
                "hunter_count": game_membership.get("hunter_count", 0),
            }
        self._last_playerarray_debug = playerarray_debug
        self._last_level_debug = level_debug
        self._last_emit_debug = emit_debug

        def _is_dead_or_spectator_class(cls_name):
            # 极简目标策略：PlayerArray 里除观战/死亡 pawn 外全部绘制。
            # 不再用 Character 白名单或反向绑定延迟过滤，避免把特殊形态误判成非目标。
            return bool(cls_name) and "Spectate" in cls_name

        def _emit_actor(
            actor, idx, stat_key, display_name="", source="unknown", player_state=0,
            role_state=None, role_override="", form_override=""
        ):
            pos_info = self._actor_position_info(actor)
            pos = pos_info["position"]
            name_info = (
                self._player_display_name_info(player_state, include_candidates=True)
                if collect_debug else {"source": "", "reader": "", "candidates": []}
            )
            cls_name = self._class_name(actor)
            role, form = self._class_role_info(cls_name)
            if role_override:
                role = role_override
            if form_override:
                form = form_override
            if role_state is None:
                role_state = self._update_player_state_tracker(player_state, role, form, cls_name, actor, pos, now)
            short_id = self._short_pointer_id(player_state, actor)
            jump_key = self._debug_hex(player_state or actor)
            active_position_keys.add(jump_key)
            jumped, jump_distance = self._track_position_jump(jump_key, pos, now)
            item = {
                "source": source,
                "idx": idx,
                "actor": self._debug_hex(actor),
                "player_state": self._debug_hex(player_state),
                "player_id": self._player_id(player_state),
                "short_id": short_id,
                "display_name": display_name,
                "display_name_source": name_info.get("source", ""),
                "display_name_reader": name_info.get("reader", ""),
                "name_candidates": name_info.get("candidates", []) if collect_debug else [],
                "class": cls_name,
                "role": role,
                "stable_role": role_state.get("stable_role", role),
                "filter_role": role_state.get("filter_role", role),
                "role_age": role_state.get("role_age", 0.0),
                "role_pending": role_state.get("role_pending", False),
                "role_previous": role_state.get("role_previous", ""),
                "converted_to_hunter": role_state.get("converted_to_hunter", False),
                "converted_hunter_age": role_state.get("converted_hunter_age", 0.0),
                "form": form,
                "position": self._debug_pos(pos),
                "position_source": pos_info["source"],
                "position_jump": jumped,
                "position_jump_distance": round(float(jump_distance), 3),
            }
            if collect_debug and self._is_character_class(cls_name):
                item["character_flags"] = self._character_debug_fields(actor)
            if pos is None:
                item["result"] = "skip"
                item["reason"] = "no_position"
                if collect_debug:
                    emit_debug.append(item)
                return
            # Drop uninitialized / origin-only positions.
            if self._is_origin_position(pos):
                item["result"] = "skip"
                item["reason"] = "origin_position"
                if collect_debug:
                    emit_debug.append(item)
                return
            stats[stat_key] += 1
            stats["rendered"] += 1
            item["result"] = "emit"
            item["stat_key"] = stat_key
            if collect_debug:
                emit_debug.append(item)
            yield TargetSnapshot(
                is_local=False,
                pos=pos,
                idx=idx,
                display_name=display_name,
                player_id=item["player_id"],
                short_id=short_id,
                player_state=player_state,
                pawn=actor,
                class_name=cls_name,
                role=role,
                stable_role=role_state.get("stable_role", role),
                filter_role=role_state.get("filter_role", role),
                form=form,
                source=source,
                position_jump=jumped,
                converted_to_hunter=bool(role_state.get("converted_to_hunter", False)),
                converted_hunter_age=float(role_state.get("converted_hunter_age", 0.0)),
            )

        # Local marker for calibration.
        if include_local and local_pawn:
            pos = self._actor_position(local_pawn)
            if pos is not None:
                stats["rendered"] += 1
                cls_name = self._class_name(local_pawn)
                role, form = self._class_role_info(cls_name)
                role_state = self._update_player_state_tracker(local_ps, role, form, cls_name, local_pawn, pos, now)
                yield TargetSnapshot(
                    is_local=True,
                    pos=pos,
                    idx=0,
                    display_name="自己",
                    player_id=self._player_id(local_ps),
                    short_id=self._short_pointer_id(local_ps, local_pawn),
                    player_state=local_ps,
                    pawn=local_pawn,
                    class_name=cls_name,
                    role=role,
                    stable_role=role_state.get("stable_role", role),
                    filter_role=role_state.get("filter_role", role),
                    form=form,
                    source="local",
                    converted_to_hunter=bool(role_state.get("converted_to_hunter", False)),
                    converted_hunter_age=float(role_state.get("converted_hunter_age", 0.0)),
                )

        # Pass 1: GameState->PlayerArray. This is the stable player source;
        # the level-actor scan can include NPCs/dummies with garbage positions.
        yielded = 0
        if gamestate:
            pa_data, pa_count, _ = read_array(self.pm, gamestate + self.offsets["AGameStateBase::PlayerArray"])
            stats["pa_total"] = pa_count
            if pa_data and pa_count > 0:
                for i in range(pa_count):
                    ps = rp(self.pm, pa_data + i * 8)
                    pa_item = {
                        "idx": i,
                        "player_state": self._debug_hex(ps),
                        "pawn": "0x0",
                    }
                    if not ps:
                        pa_item["result"] = "skip"
                        pa_item["reason"] = "no_player_state"
                        playerarray_debug.append(pa_item)
                        continue
                    active_player_states.add(ps)
                    pa_item.update(self._player_debug_identity(ps, collect_debug=collect_debug))
                    if ps == local_ps:
                        pa_item["result"] = "skip"
                        pa_item["reason"] = "local_player_state"
                        playerarray_debug.append(pa_item)
                        continue
                    pawn = rp(self.pm, ps + self.offsets["APlayerState::PawnPrivate"])
                    pa_item["pawn"] = self._debug_hex(pawn)
                    if not pawn:
                        pa_item["game_state_membership"] = self._player_membership_debug(ps, game_membership)
                        cached_actor, cache_info = self._cached_live_survivor_actor(ps, game_membership, now)
                        if cached_actor and cached_actor != local_pawn and cached_actor not in seen:
                            role = "survivor"
                            cached_cls = cache_info.get("class") or self._class_name(cached_actor)
                            _, cached_form = self._class_role_info(cached_cls)
                            cached_form = self._form_for_array_role(role, cached_form)
                            cached_pos = self._actor_position(cached_actor)
                            role_state = self._update_player_state_tracker(
                                ps, role, cached_form, cached_cls, cached_actor, cached_pos, now
                            )
                            pa_item["cached_actor"] = self._debug_hex(cached_actor)
                            pa_item["cached_actor_info"] = cache_info
                            pa_item["class"] = cached_cls
                            pa_item["position"] = self._debug_pos(cached_pos)
                            pa_item["position_source"] = "cached_live_survivor_actor"
                            pa_item["role"] = role
                            pa_item["form"] = cached_form
                            pa_item.update(role_state)
                            pa_item["result"] = "candidate"
                            pa_item["reason"] = "live_survivor_cached_actor"
                            playerarray_debug.append(pa_item)
                            stats["pa_cached"] += 1
                            seen.add(cached_actor)
                            yield from _emit_actor(
                                cached_actor, i, "pa_valid", pa_item["display_name"],
                                source="player_array_live_survivor_cache", player_state=ps,
                                role_state=role_state, role_override=role, form_override=cached_form
                            )
                            yielded += 1
                            continue
                        pa_item["result"] = "skip"
                        pa_item["reason"] = "no_pawn"
                        playerarray_debug.append(pa_item)
                        continue
                    if pawn == local_pawn:
                        pa_item["result"] = "skip"
                        pa_item["reason"] = "local_pawn"
                        playerarray_debug.append(pa_item)
                        continue
                    if pawn in seen:
                        pa_item["result"] = "skip"
                        pa_item["reason"] = "duplicate_pawn"
                        playerarray_debug.append(pa_item)
                        continue
                    pawn_cls = self._class_name(pawn)
                    pa_item["class"] = pawn_cls
                    if not pawn_cls:
                        pa_item["result"] = "skip"
                        pa_item["reason"] = "no_class"
                        playerarray_debug.append(pa_item)
                        continue
                    pos_info = self._actor_position_info(pawn)
                    pos = pos_info["position"]
                    pa_item["position"] = self._debug_pos(pos)
                    pa_item["position_source"] = pos_info["source"]
                    pa_item["reverse_player_state"] = self._debug_hex(self._pawn_playerstate(pawn))
                    pa_item["controller"] = self._debug_hex(self._pawn_controller(pawn))
                    pa_item["short_id"] = self._short_pointer_id(ps, pawn)
                    if collect_debug and self._is_character_class(pawn_cls):
                        pa_item["character_flags"] = self._character_debug_fields(pawn)
                    pa_item["game_state_membership"] = self._player_membership_debug(ps, game_membership)
                    role, form = self._class_role_info(pawn_cls)
                    array_role = self._array_role_for_player(ps, game_membership)
                    if array_role:
                        role = array_role
                        form = self._form_for_array_role(array_role, form)
                    pa_item["role"] = role
                    pa_item["form"] = form
                    if pos is None:
                        pa_item["result"] = "skip"
                        pa_item["reason"] = "no_position"
                        playerarray_debug.append(pa_item)
                        continue
                    seen_life_pawns.add(pawn)
                    role_state = self._update_player_state_tracker(ps, role, form, pawn_cls, pawn, pos, now)
                    pa_item.update(role_state)
                    if self.offsets.get("APawn::PlayerState", 0) and self._pawn_playerstate(pawn) != ps:
                        stats["pa_suspect"] += 1
                    seen.add(pawn)
                    if _is_dead_or_spectator_class(pawn_cls):
                        linked_info = self._spectate_linked_character_info(pawn, ps, collect_debug=collect_debug)
                        pa_item["spectate_link"] = linked_info
                        linked_actor = linked_info.get("actor", 0)
                        if linked_info.get("reason") == "linked_character" and linked_actor and linked_actor not in seen:
                            linked_cls = linked_info.get("class") or self._class_name(linked_actor)
                            linked_role, linked_form = self._class_role_info(linked_cls)
                            linked_array_role = self._array_role_for_player(ps, game_membership)
                            if linked_array_role == "hunter" and linked_role == "survivor":
                                stats["pa_suppressed"] += 1
                                linked_info["reason"] = "suppressed_not_live_survivor"
                                linked_info["suppressed_by"] = "game_state_hunter"
                                pa_item["result"] = "skip"
                                pa_item["reason"] = "suppressed_not_live_survivor"
                                playerarray_debug.append(pa_item)
                                continue
                            if (
                                linked_role == "survivor"
                                and game_membership.get("valid")
                                and linked_array_role != "survivor"
                            ):
                                stats["pa_suppressed"] += 1
                                linked_info["reason"] = "suppressed_not_live_survivor"
                                linked_info["suppressed_by"] = "game_state_neither"
                                pa_item["result"] = "skip"
                                pa_item["reason"] = "suppressed_not_live_survivor"
                                playerarray_debug.append(pa_item)
                                continue
                            if linked_array_role:
                                linked_role = linked_array_role
                                linked_form = self._form_for_array_role(linked_array_role, linked_form)
                            if role_state.get("converted_to_hunter") and linked_role == "survivor":
                                stats["pa_suppressed"] += 1
                                linked_info["reason"] = "suppressed_after_hunter_conversion"
                                linked_info["suppressed_by"] = "converted_to_hunter"
                                pa_item["result"] = "skip"
                                pa_item["reason"] = "suppressed_after_hunter_conversion"
                                playerarray_debug.append(pa_item)
                                continue
                            linked_pos = self._actor_position(linked_actor)
                            role_state = self._update_player_state_tracker(
                                ps, linked_role, linked_form, linked_cls, linked_actor, linked_pos, now
                            )
                            stats["pa_linked"] += 1
                            pa_item["pawn_class"] = pawn_cls
                            pa_item["linked_actor"] = self._debug_hex(linked_actor)
                            pa_item["linked_class"] = linked_cls
                            pa_item["linked_position"] = self._debug_pos(linked_pos)
                            pa_item["class"] = linked_cls
                            pa_item["role"] = linked_role
                            pa_item["form"] = linked_form
                            pa_item.update(role_state)
                            pa_item["result"] = "candidate"
                            pa_item["reason"] = "spectate_linked_character"
                            playerarray_debug.append(pa_item)
                            seen.add(linked_actor)
                            yield from _emit_actor(
                                linked_actor, i, "pa_valid", pa_item["display_name"],
                                source="player_array_spectate_link", player_state=ps, role_state=role_state,
                                role_override=linked_role, form_override=linked_form
                            )
                            yielded += 1
                            continue
                        stats["pa_dead"] += 1
                        jump_key = self._debug_hex(ps or pawn)
                        active_position_keys.add(jump_key)
                        jumped, jump_distance = self._track_position_jump(jump_key, pos, now)
                        pa_item["position_jump"] = jumped
                        pa_item["position_jump_distance"] = round(float(jump_distance), 3)
                        pa_item["result"] = "skip"
                        pa_item["reason"] = "dead_or_spectator"
                        playerarray_debug.append(pa_item)
                        continue
                    pa_item["result"] = "candidate"
                    pa_item["reason"] = ""
                    playerarray_debug.append(pa_item)
                    yield from _emit_actor(
                        pawn, i, "pa_valid", pa_item["display_name"],
                        source="player_array", player_state=ps, role_state=role_state,
                        role_override=role, form_override=form
                    )
                    yielded += 1

        # Pass 2: Persistent level actors (fallback / merge).
        # ESP uses this to catch players PlayerArray hasn't updated yet.
        if not players_only:
            level = persistent_level
            if level:
                actors_off = self.offsets.get("ULevel::Actors", 0xA0)
                actors_data, actors_count, _ = read_array(self.pm, level + actors_off)
                stats["level_total"] = actors_count
                if actors_data and actors_count > 0 and actors_count < 10000:
                    for i in range(actors_count):
                        actor = rp(self.pm, actors_data + i * 8)
                        level_item = {
                            "idx": i,
                            "actor": self._debug_hex(actor),
                        }
                        if not actor:
                            continue
                        if actor == local_pawn:
                            level_item["result"] = "skip"
                            level_item["reason"] = "local_pawn"
                            level_debug.append(level_item)
                            continue
                        if actor in seen:
                            level_item["result"] = "skip"
                            level_item["reason"] = "duplicate_actor"
                            level_debug.append(level_item)
                            continue
                        cls_name = self._class_name(actor)
                        level_item["class"] = cls_name
                        if not cls_name or "Character" not in cls_name:
                            level_item["result"] = "skip"
                            level_item["reason"] = "non_character"
                            # 只记录和目标相关的条目，避免日志被普通场景 Actor 淹没。
                            continue
                        # Level Actor 扫描会捞到尸体、残留模型或未绑定玩家的旧 Character。
                        # 只有仍然挂着 PlayerState/Controller 的 Character 才作为 fallback 目标。
                        actor_ps = self._pawn_playerstate(actor)
                        controller = self._pawn_controller(actor)
                        if actor_ps:
                            active_player_states.add(actor_ps)
                        level_item["player_state"] = self._debug_hex(actor_ps)
                        level_item["controller"] = self._debug_hex(controller)
                        pos_info = self._actor_position_info(actor)
                        level_item["position"] = self._debug_pos(pos_info["position"])
                        level_item["position_source"] = pos_info["source"]
                        if collect_debug and self._is_character_class(cls_name):
                            level_item["character_flags"] = self._character_debug_fields(actor)
                        if not actor_ps and not controller:
                            stats["level_orphan"] += 1
                            level_item["result"] = "skip"
                            level_item["reason"] = "unbound_orphan"
                            level_debug.append(level_item)
                            continue
                        seen.add(actor)
                        if _is_dead_or_spectator_class(cls_name):
                            level_item["result"] = "skip"
                            level_item["reason"] = "dead_or_spectator"
                            level_debug.append(level_item)
                            continue
                        level_item["result"] = "candidate"
                        level_item["reason"] = ""
                        level_item["player_id"] = self._player_id(actor_ps)
                        name_info = self._player_display_name_info(actor_ps, include_candidates=collect_debug)
                        level_item["display_name"] = name_info.get("name") or self._player_display_label(actor_ps)
                        level_item["display_name_source"] = name_info.get("source", "")
                        level_item["display_name_reader"] = name_info.get("reader", "")
                        level_item["name_candidates"] = name_info.get("candidates", []) if collect_debug else []
                        level_item["short_id"] = self._short_pointer_id(actor_ps, actor)
                        role, form = self._class_role_info(cls_name)
                        role_state = self._update_player_state_tracker(actor_ps, role, form, cls_name, actor, pos_info["position"], now)
                        level_item["role"] = role
                        level_item.update(role_state)
                        level_item["form"] = form
                        level_debug.append(level_item)
                        yield from _emit_actor(
                            actor, i, "level_valid", level_item["display_name"],
                            source="level_actor", player_state=actor_ps, role_state=role_state,
                            role_override=role, form_override=form
                        )

        self._last_iter_stats = stats
        self._cleanup_pawn_life_tracker(seen_life_pawns, now)
        self._cleanup_target_position_cache(active_position_keys, now)
        self._cleanup_player_state_tracker(active_player_states, now)
        self._cleanup_player_name_cache(active_player_states, now)


# ---------------------------------------------------------------------------
# World-to-screen
# ---------------------------------------------------------------------------
def rotation_to_axes(rot):
    pitch, yaw, roll = [math.radians(x) for x in rot]
    sp, cp = math.sin(pitch), math.cos(pitch)
    sy, cy = math.sin(yaw), math.cos(yaw)
    sr, cr = math.sin(roll), math.cos(roll)

    forward = (cp * cy, cp * sy, sp)
    right = (sr * sp * cy - cr * sy, sr * sp * sy + cr * cy, -sr * cp)
    up = (-(cr * sp * cy + sr * sy), cy * sr - cr * sp * sy, cr * cp)
    return forward, right, up


def w2s(world_pos, camera, screen_w, screen_h):
    info = project_debug(world_pos, camera, screen_w, screen_h)
    if not info["visible"]:
        return None
    return tuple(info["screen"])


def project_debug(world_pos, camera, screen_w, screen_h):
    cam_loc = camera["loc"]
    cam_rot = camera["rot"]
    fov = camera["fov"]

    forward, right, up = rotation_to_axes(cam_rot)

    dx = world_pos[0] - cam_loc[0]
    dy = world_pos[1] - cam_loc[1]
    dz = world_pos[2] - cam_loc[2]

    view_x = dx * forward[0] + dy * forward[1] + dz * forward[2]
    view_y = dx * right[0] + dy * right[1] + dz * right[2]
    view_z = dx * up[0] + dy * up[1] + dz * up[2]

    if view_x <= 0.1:
        return {
            "visible": False,
            "reason": "behind_camera",
            "view": [round(view_x, 3), round(view_y, 3), round(view_z, 3)],
        }

    aspect = screen_w / screen_h
    tan_hfov = math.tan(math.radians(fov) / 2.0)

    ndc_x = view_y / (view_x * tan_hfov)
    ndc_y = view_z / (view_x * tan_hfov / aspect)

    screen_x = (1.0 + ndc_x) * screen_w / 2.0
    screen_y = (1.0 - ndc_y) * screen_h / 2.0

    visible = 0 <= screen_x <= screen_w and 0 <= screen_y <= screen_h
    reason = None if visible else "outside_view"
    if not visible and 0 <= screen_x <= screen_w:
        reason = "outside_view_y"
    elif not visible and 0 <= screen_y <= screen_h:
        reason = "outside_view_x"

    result = {
        "visible": visible,
        "reason": reason,
        "screen": [round(screen_x, 2), round(screen_y, 2)],
        "ndc": [round(ndc_x, 4), round(ndc_y, 4)],
        "view": [round(view_x, 3), round(view_y, 3), round(view_z, 3)],
    }
    if not (0 <= screen_x <= screen_w and 0 <= screen_y <= screen_h):
        return result
    return result
