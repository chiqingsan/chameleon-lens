"""透明覆盖层绘制。"""
import time

from PyQt5.QtWidgets import QWidget
from PyQt5.QtCore import Qt, QTimer, QPointF
from PyQt5.QtGui import QPainter, QPen, QColor, QFont

from .config import Config
from .logging import DebugDataRecorder
from .memory import dist
from .radar import project_radar_point
from .reader import project_debug
from .runtime import ESPRuntime


# ---------------------------------------------------------------------------
# 覆盖层
# ---------------------------------------------------------------------------
class Overlay(QWidget):
    PAINT_INTERVAL_MS = 11
    SNAPSHOT_INTERVAL_MS = 11
    GEOMETRY_INTERVAL_MS = 250
    CAMERA_WAIT_RECONNECT_SECONDS = 3.0

    def __init__(self, runtime: ESPRuntime, config: Config, on_status_changed=None):
        super().__init__()
        self.runtime = runtime
        self.config = config
        self.on_status_changed = on_status_changed
        self.setWindowFlags(
            Qt.FramelessWindowHint
            | Qt.WindowStaysOnTopHint
            | Qt.Tool
            | Qt.WindowTransparentForInput
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.setWindowTitle("MECCHA 变色龙覆盖层")
        self.debug_recorder = DebugDataRecorder()
        self._snapshot_esp = None
        self._snapshot_camera = None
        self._snapshot_players = []
        self._snapshot_collect_debug = False
        self._last_sample_ms = 0.0
        self._last_paint_ms = 0.0
        self._last_debug_config = None
        self._camera_missing_since = None

        self.paint_timer = QTimer(self)
        self.paint_timer.setTimerType(Qt.PreciseTimer)
        self.paint_timer.timeout.connect(self.update)
        self.paint_timer.start(self.PAINT_INTERVAL_MS)

        self.sample_timer = QTimer(self)
        self.sample_timer.setTimerType(Qt.PreciseTimer)
        self.sample_timer.timeout.connect(self.refresh_snapshot)
        self.sample_timer.start(self.SNAPSHOT_INTERVAL_MS)

        self.geometry_timer = QTimer(self)
        self.geometry_timer.timeout.connect(self.update_geometry)
        self.geometry_timer.start(self.GEOMETRY_INTERVAL_MS)

        self.game_hwnd = self._find_game_window()
        self.update_geometry()
        self.refresh_snapshot()

    def _find_game_window(self):
        try:
            import win32gui
            return win32gui.FindWindow(None, "Chameleon  ")
        except Exception:
            return 0

    def _resize_to_game(self):
        try:
            import win32gui
            if self.game_hwnd:
                rect = win32gui.GetClientRect(self.game_hwnd)
                tl = win32gui.ClientToScreen(self.game_hwnd, (rect[0], rect[1]))
                br = win32gui.ClientToScreen(self.game_hwnd, (rect[2], rect[3]))
                self.setGeometry(tl[0], tl[1], br[0] - tl[0], br[1] - tl[1])
            else:
                self.setGeometry(0, 0, 1920, 1080)
        except Exception:
            self.setGeometry(0, 0, 1920, 1080)

    def _ensure_topmost(self):
        """游戏后启动时可能抢到顶层窗口，这里周期性把透明层放回最上方。"""
        try:
            import win32con
            import win32gui
            win32gui.SetWindowPos(
                int(self.winId()),
                win32con.HWND_TOPMOST,
                self.x(),
                self.y(),
                self.width(),
                self.height(),
                win32con.SWP_NOACTIVATE | win32con.SWP_SHOWWINDOW,
            )
        except Exception:
            pass

    def update_geometry(self):
        self.game_hwnd = self._find_game_window()
        self._resize_to_game()
        self._ensure_topmost()

    def refresh_snapshot(self):
        """按固定采样频率读取目标快照，绘制阶段只消费缓存，避免 UI 线程每帧重复读内存。"""
        if not self.config.enabled:
            self._snapshot_esp = None
            self._snapshot_camera = None
            self._snapshot_players = []
            self._snapshot_collect_debug = False
            return

        esp = self.runtime.esp
        if not esp:
            self._snapshot_esp = None
            self._snapshot_camera = None
            self._snapshot_players = []
            self._snapshot_collect_debug = False
            return

        started = time.perf_counter()
        try:
            cam = esp.get_camera()
            if not cam:
                self._handle_missing_camera()
                self._snapshot_camera = None
                self._snapshot_players = []
                self._snapshot_collect_debug = False
                return
            self._camera_missing_since = None
            collect_debug = self.config.record_debug_data and self.debug_recorder.is_due()
            players = list(esp.iter_players(
                include_local=self.config.show_local,
                players_only=True,
                collect_debug=collect_debug,
            ))
        except Exception as exc:
            self._snapshot_esp = None
            self._snapshot_camera = None
            self._snapshot_players = []
            self._snapshot_collect_debug = False
            self._mark_disconnected(exc)
            return

        self._snapshot_esp = esp
        self._snapshot_camera = cam
        self._snapshot_players = players
        self._snapshot_collect_debug = collect_debug
        self._last_sample_ms = (time.perf_counter() - started) * 1000.0
        self.update()

    def _handle_missing_camera(self):
        now = time.monotonic()
        if self._camera_missing_since is None:
            self._camera_missing_since = now
            return
        if now - self._camera_missing_since < self.CAMERA_WAIT_RECONNECT_SECONDS:
            return
        self._camera_missing_since = None
        self.runtime.disconnect(
            "已找到进程，等待游戏画面初始化...",
            "连续读取不到相机，已重建连接等待游戏窗口和 UE World 就绪",
        )
        if self.on_status_changed:
            self.on_status_changed()

    def paintEvent(self, event):
        started = time.perf_counter()
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        font = QFont("Microsoft YaHei UI", 10)
        painter.setFont(font)

        w = self.width()
        h = self.height()

        try:
            if not self.config.enabled:
                return

            esp = self._snapshot_esp
            cam = self._snapshot_camera
            if not esp or not cam:
                return

            count = 0
            debug_targets = []
            players = self._snapshot_players
            collect_frame_debug = (
                self.config.record_debug_data
                and self._snapshot_collect_debug
                and self.debug_recorder.is_due()
            )

            if self.config.esp_enabled:
                for player in players:
                    target = self._target_info(player)
                    if self._target_hidden_by_role(target):
                        continue
                    is_local = target["is_local"]
                    pos = target["pos"]
                    idx = target["idx"]
                    label = self._target_label(target)
                    color = self._target_color(target)
                    projection = project_debug(pos, cam, w, h)
                    screen_info = tuple(projection["screen"]) if projection["visible"] else None
                    if not screen_info:
                        edge_info = self._edge_point_for_projection(projection, w, h) if self.config.show_edge_indicators else None
                        if edge_info:
                            sx, sy = edge_info
                            self._draw_offscreen_target(painter, sx, sy, color)

                            should_draw_ray = self.config.snap_lines and (not is_local or self.config.show_local_snap_line)
                            if should_draw_ray:
                                painter.setPen(QPen(QColor(*color), 1))
                                painter.drawLine(int(w / 2), int(h), int(sx), int(sy))

                            label_parts = []
                            if self.config.show_names:
                                label_parts.append(label)
                            if self.config.show_distance:
                                d = int(dist(pos, cam["loc"]) / 100)
                                label_parts.append(f"{d}m")
                            if label_parts:
                                painter.setPen(QPen(QColor(*color)))
                                text = " | ".join(label_parts)
                                tx, ty = self._fit_label_point(sx + self.config.dot_radius + 6, sy, w, h)
                                painter.drawText(int(tx), int(ty), text)

                            if collect_frame_debug:
                                debug_targets.append({
                                    "idx": idx,
                                    "player_id": target["player_id"],
                                    "short_id": target["short_id"],
                                    "name": label,
                                    "local": is_local,
                                    "role": target["role"],
                                    "stable_role": target["stable_role"],
                                    "filter_role": target["filter_role"],
                                    "converted_to_hunter": target["converted_to_hunter"],
                                    "converted_hunter_age": target["converted_hunter_age"],
                                    "form": target["form"],
                                    "class": target["class_name"],
                                    "player_state": target["player_state"],
                                    "pawn": target["pawn"],
                                    "position_jump": target["position_jump"],
                                    "world": self._round_pos(pos),
                                    "screen": [round(float(sx), 2), round(float(sy), 2)],
                                    "edge": True,
                                    "projection": projection,
                                    "distance_m": int(dist(pos, cam["loc"]) / 100),
                                    "dot": bool(self.config.box_esp),
                                    "ray": bool(should_draw_ray),
                                    "drawn": True,
                                    "reason": projection.get("reason") or "not_visible",
                                })
                            count += 1
                            continue

                        if collect_frame_debug:
                            debug_targets.append({
                                "idx": idx,
                                "player_id": target["player_id"],
                                "short_id": target["short_id"],
                                "name": label,
                                "local": is_local,
                                "role": target["role"],
                                "stable_role": target["stable_role"],
                                "filter_role": target["filter_role"],
                                "converted_to_hunter": target["converted_to_hunter"],
                                "converted_hunter_age": target["converted_hunter_age"],
                                "form": target["form"],
                                "class": target["class_name"],
                                "player_state": target["player_state"],
                                "pawn": target["pawn"],
                                "position_jump": target["position_jump"],
                                "world": self._round_pos(pos),
                                "projection": projection,
                                "drawn": False,
                                "reason": projection.get("reason") or "not_visible",
                            })
                        continue
                    sx, sy = screen_info

                    if self.config.box_esp:
                        self._draw_dot(painter, sx, sy, color)

                    should_draw_ray = self.config.snap_lines and (not is_local or self.config.show_local_snap_line)
                    if should_draw_ray:
                        painter.setPen(QPen(QColor(*color), 1))
                        painter.drawLine(int(w / 2), int(h), int(sx), int(sy))

                    label_parts = []
                    if self.config.show_names:
                        label_parts.append(label)
                    if self.config.show_distance:
                        d = int(dist(pos, cam["loc"]) / 100)
                        label_parts.append(f"{d}m")
                    if label_parts:
                        painter.setPen(QPen(QColor(*color)))
                        text = " | ".join(label_parts)
                        painter.drawText(int(sx + self.config.dot_radius + 4), int(sy), text)

                    if collect_frame_debug:
                        debug_targets.append({
                            "idx": idx,
                            "player_id": target["player_id"],
                            "short_id": target["short_id"],
                            "name": label,
                            "local": is_local,
                            "role": target["role"],
                            "stable_role": target["stable_role"],
                            "filter_role": target["filter_role"],
                            "converted_to_hunter": target["converted_to_hunter"],
                            "converted_hunter_age": target["converted_hunter_age"],
                            "form": target["form"],
                            "class": target["class_name"],
                            "player_state": target["player_state"],
                            "pawn": target["pawn"],
                            "position_jump": target["position_jump"],
                            "world": self._round_pos(pos),
                            "screen": [round(float(sx), 2), round(float(sy), 2)],
                            "distance_m": int(dist(pos, cam["loc"]) / 100),
                            "dot": bool(self.config.box_esp),
                            "ray": bool(should_draw_ray),
                            "drawn": True,
                        })
                    count += 1

            if self.config.show_debug:
                painter.setPen(QPen(QColor(255, 255, 255)))
                painter.drawText(14, 24, f"玩家：{count}")
                stats = getattr(esp, "_last_iter_stats", {})
                line = (f"PA:{stats.get('pa_total', 0)}/{stats.get('pa_valid', 0)} "
                        f"PD:{stats.get('pa_dead', 0)} "
                        f"PS:{stats.get('pa_suspect', 0)} "
                        f"PO:{stats.get('pa_orphan', 0)} "
                        f"LA:{stats.get('level_total', 0)}/{stats.get('level_valid', 0)} "
                        f"OR:{stats.get('level_orphan', 0)}")
                painter.drawText(14, 42, line)
                perf = f"采样:{self._last_sample_ms:.1f}ms 绘制:{self._last_paint_ms:.1f}ms"
                painter.drawText(14, 60, perf)

            radar_points = self._draw_radar(painter, w, h, cam, players)
            if collect_frame_debug:
                self._record_debug_frame(esp, cam, players, debug_targets, radar_points, count, w, h)
        finally:
            self._last_paint_ms = (time.perf_counter() - started) * 1000.0

    def _unpack_player(self, player):
        if len(player) >= 5:
            return player
        is_local, pos, idx, display_name = player
        return is_local, pos, idx, display_name, 0

    def _target_info(self, player):
        if hasattr(player, "pos"):
            return {
                "is_local": bool(player.is_local),
                "pos": player.pos,
                "idx": player.idx,
                "display_name": player.display_name,
                "player_id": player.player_id,
                "short_id": player.short_id,
                "player_state": self._hex_ptr(player.player_state),
                "pawn": self._hex_ptr(player.pawn),
                "class_name": player.class_name,
                "role": player.role,
                "stable_role": player.stable_role,
                "filter_role": player.filter_role,
                "converted_to_hunter": bool(getattr(player, "converted_to_hunter", False)),
                "converted_hunter_age": float(getattr(player, "converted_hunter_age", 0.0)),
                "form": player.form,
                "source": player.source,
                "position_jump": bool(player.position_jump),
            }
        is_local, pos, idx, display_name, player_id = self._unpack_player(player)
        return {
            "is_local": is_local,
            "pos": pos,
            "idx": idx,
            "display_name": display_name,
            "player_id": player_id,
            "short_id": "",
            "player_state": "0x0",
            "pawn": "0x0",
            "class_name": "",
            "role": "unknown",
            "stable_role": "unknown",
            "filter_role": "unknown",
            "converted_to_hunter": False,
            "converted_hunter_age": 0.0,
            "form": "unknown",
            "source": "tuple",
            "position_jump": False,
        }

    def _target_label(self, target):
        if target["is_local"]:
            return "自己"
        if target["display_name"]:
            return target["display_name"]
        if target["short_id"]:
            return f"玩家 {target['short_id']}"
        if target["player_id"]:
            return f"ID {target['player_id']}"
        return f"目标 {target['idx']}"

    def _target_color(self, target):
        if target["is_local"]:
            return self.config.local_color
        # 颜色表达当前读到的明确身份；过滤仍单独使用 filter_role 防止瞬时切换漏绘制。
        role = self._current_role_for_display(target)
        if role == "hunter":
            return self.config.hunter_color
        if role == "survivor":
            return self.config.survivor_color
        return self.config.enemy_color

    @staticmethod
    def _current_role_for_display(target):
        role = target.get("role") or ""
        if role in ("hunter", "survivor"):
            return role
        return target.get("filter_role") or role

    @staticmethod
    def _hex_ptr(value):
        return f"0x{int(value):X}" if value else "0x0"

    def _draw_dot(self, painter, cx, cy, color):
        r = self.config.dot_radius
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(*color))
        painter.drawEllipse(int(cx - r), int(cy - r), r * 2, r * 2)

    def _draw_offscreen_target(self, painter, cx, cy, color):
        """把屏幕外目标钳到边缘绘制，避免候选已读到但视觉上像漏绘制。"""
        if not self.config.box_esp:
            return
        r = max(self.config.dot_radius + 2, 6)
        qcolor = QColor(*color)
        painter.setPen(QPen(QColor(qcolor.red(), qcolor.green(), qcolor.blue(), 220), 2))
        painter.setBrush(QColor(qcolor.red(), qcolor.green(), qcolor.blue(), 56))
        painter.drawEllipse(QPointF(cx, cy), r, r)
        painter.setPen(Qt.NoPen)
        painter.setBrush(qcolor)
        painter.drawEllipse(QPointF(cx, cy), 3.5, 3.5)

    def _fit_label_point(self, x, y, screen_w, screen_h):
        return (
            max(6, min(float(x), screen_w - 132)),
            max(14, min(float(y), screen_h - 8)),
        )

    def _edge_point_for_projection(self, projection, screen_w, screen_h):
        margin = max(18, self.config.dot_radius + 10)
        cx = screen_w / 2
        cy = screen_h / 2

        screen = projection.get("screen")
        if screen:
            tx, ty = float(screen[0]), float(screen[1])
        else:
            view = projection.get("view") or [0.0, 0.0, 0.0]
            if len(view) < 3:
                return None
            _, right, up = view
            # behind_camera 没有屏幕坐标，用相机空间方向给出一个稳定边缘位置。
            tx = cx - float(right)
            ty = cy + float(up)

        dx = tx - cx
        dy = ty - cy
        if abs(dx) < 0.01 and abs(dy) < 0.01:
            dx, dy = 0.0, 1.0

        candidates = []
        if dx > 0:
            candidates.append((screen_w - margin - cx) / dx)
        elif dx < 0:
            candidates.append((margin - cx) / dx)
        if dy > 0:
            candidates.append((screen_h - margin - cy) / dy)
        elif dy < 0:
            candidates.append((margin - cy) / dy)

        positive = [t for t in candidates if t > 0]
        if not positive:
            return None
        t = min(positive)
        x = max(margin, min(screen_w - margin, cx + dx * t))
        y = max(margin, min(screen_h - margin, cy + dy * t))
        return x, y

    def _round_pos(self, pos):
        return [round(float(v), 3) for v in pos] if pos else None

    def _debug_config_snapshot(self):
        return {
            "enabled": self.config.enabled,
            "esp_enabled": self.config.esp_enabled,
            "show_hunter_esp": self.config.show_hunter_esp,
            "box_esp": self.config.box_esp,
            "show_local": self.config.show_local,
            "show_names": self.config.show_names,
            "show_distance": self.config.show_distance,
            "snap_lines": self.config.snap_lines,
            "show_local_snap_line": self.config.show_local_snap_line,
            "show_edge_indicators": self.config.show_edge_indicators,
            "radar_enabled": self.config.radar_enabled,
        }

    def _debug_config_changes(self, current):
        previous = self._last_debug_config
        self._last_debug_config = dict(current)
        if previous is None:
            return []
        source_info = getattr(self.config, "_last_change_source", {}) or {}
        source = source_info.get("source") or "unknown_or_menu"
        changes = []
        for key, value in current.items():
            old_value = previous.get(key)
            if old_value != value:
                changes.append({
                    "field": key,
                    "from": old_value,
                    "to": value,
                    "source": source if source_info.get("field") == key else "unknown_or_menu",
                })
        return changes

    def _record_debug_frame(self, esp, camera, players, targets, radar_points, drawn_count, screen_w, screen_h):
        if not self.config.record_debug_data:
            return
        stats = getattr(esp, "_last_iter_stats", {})
        config_snapshot = self._debug_config_snapshot()
        config_changes = self._debug_config_changes(config_snapshot)
        projection_reasons = {}
        edge_reasons = {}
        for item in targets:
            if item.get("edge"):
                reason = item.get("reason") or "unknown"
                edge_reasons[reason] = edge_reasons.get(reason, 0) + 1
                continue
            if item.get("drawn"):
                continue
            reason = item.get("reason") or "unknown"
            projection_reasons[reason] = projection_reasons.get(reason, 0) + 1
        self.debug_recorder.write({
            "screen": {"w": screen_w, "h": screen_h},
            "config": config_snapshot,
            "config_changes": config_changes,
            "camera": {
                "loc": self._round_pos(camera.get("loc")),
                "rot": self._round_pos(camera.get("rot")),
                "fov": round(float(camera.get("fov", 0.0)), 3),
            },
            "runtime": {
                "status": self.runtime.status,
                "last_error": self.runtime.last_error,
            },
            "performance": {
                "sample_ms": round(float(self._last_sample_ms), 3),
                "paint_ms": round(float(self._last_paint_ms), 3),
                "sample_interval_ms": self.SNAPSHOT_INTERVAL_MS,
                "paint_interval_ms": self.PAINT_INTERVAL_MS,
                "geometry_interval_ms": self.GEOMETRY_INTERVAL_MS,
            },
            "stats": stats,
            "player_candidates": len(players),
            "drawn": drawn_count,
            "projection_reasons": projection_reasons,
            "edge_reasons": edge_reasons,
            "targets": targets,
            "radar_targets": radar_points,
            "reader_context": getattr(esp, "_last_iter_context", {}),
            "position_jumps": getattr(esp, "_last_position_jumps", []),
            "emitted_targets": getattr(esp, "_last_emit_debug", []),
            "player_array_debug": getattr(esp, "_last_playerarray_debug", []),
            "level_actor_debug": getattr(esp, "_last_level_debug", []),
        })

    def _draw_radar(self, painter, screen_w, screen_h, camera, players):
        if not self.config.radar_enabled:
            return []

        size = max(120, min(self.config.radar_size, 280))
        margin = 24
        position = self.config.radar_position
        x = margin if "左" in position else screen_w - size - margin
        y = margin if "上" in position else screen_h - size - margin
        cx = x + size / 2
        cy = y + size / 2
        radius = size / 2
        inner_radius = radius - 12
        radar_points = self._radar_points(players, camera, inner_radius)

        painter.save()
        painter.setOpacity(max(0.2, min(self.config.radar_opacity / 100.0, 1.0)))
        painter.setPen(QPen(QColor(94, 234, 212, 120), 1))
        painter.setBrush(QColor(13, 17, 23, 174))
        painter.drawEllipse(QPointF(cx, cy), radius, radius)
        painter.setBrush(Qt.NoBrush)
        painter.setPen(QPen(QColor(226, 232, 240, 28), 1))
        for scale in (0.35, 0.7):
            painter.drawEllipse(QPointF(cx, cy), radius * scale, radius * scale)
        painter.drawLine(int(cx - radius), int(cy), int(cx + radius), int(cy))
        painter.drawLine(int(cx), int(cy - radius), int(cx), int(cy + radius))

        painter.setPen(QPen(QColor(94, 234, 212, 150), 2))
        painter.drawLine(QPointF(cx, cy), QPointF(cx, cy - radius + 14))

        for item in radar_points:
            color = QColor(*item["color"])
            px = cx + item["x"]
            py = cy + item["y"]
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor(color.red(), color.green(), color.blue(), 46))
            painter.drawEllipse(QPointF(px, py), 7, 7)
            painter.setBrush(color)
            painter.drawEllipse(QPointF(px, py), 4, 4)
            if item["clamped"]:
                painter.setPen(QPen(QColor(color.red(), color.green(), color.blue(), 150), 1.4))
                painter.setBrush(Qt.NoBrush)
                painter.drawEllipse(QPointF(px, py), 8.5, 8.5)

        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor("#5eead4"))
        painter.drawEllipse(QPointF(cx, cy), 5, 5)
        painter.setPen(QPen(QColor("#687486"), 1))
        painter.setFont(QFont("Microsoft YaHei UI", 9))
        painter.drawText(int(x), int(y + size + 18), f"目标 {len(radar_points)} · {self.config.radar_range}m")
        painter.restore()
        return radar_points

    def _radar_points(self, players, camera, inner_radius):
        cam_loc = camera.get("loc")
        cam_rot = camera.get("rot")
        if not cam_loc or not cam_rot:
            return []
        out = []
        for player in players:
            target = self._target_info(player)
            if target["is_local"]:
                continue
            if self._target_hidden_by_role(target):
                continue
            pos = target["pos"]
            radar = project_radar_point(pos, cam_loc, cam_rot[1], self.config.radar_range, inner_radius)
            out.append({
                "idx": target["idx"],
                "player_id": target["player_id"],
                "short_id": target["short_id"],
                "name": self._target_label(target),
                "role": target["role"],
                "stable_role": target["stable_role"],
                "filter_role": target["filter_role"],
                "converted_to_hunter": target["converted_to_hunter"],
                "converted_hunter_age": target["converted_hunter_age"],
                "form": target["form"],
                "x": radar["x"],
                "y": radar["y"],
                "distance_m": radar["distance_m"],
                "clamped": radar["clamped"],
                "color": self._target_color(target),
            })
        return out

    def _target_hidden_by_role(self, target):
        role = target.get("filter_role") or target.get("role")
        return role == "hunter" and not self.config.show_hunter_esp

    def _mark_disconnected(self, exc):
        self._camera_missing_since = None
        self.runtime.disconnect("连接已断开，等待游戏进程重新出现...", str(exc))
        if self.on_status_changed:
            self.on_status_changed()
