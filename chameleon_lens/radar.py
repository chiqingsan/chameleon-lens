"""雷达坐标转换。"""
import math


def project_radar_point(pos, cam_loc, cam_yaw, radar_range_m, inner_radius):
    """把世界坐标转换成以相机朝向为正上方的雷达盘面坐标。"""
    world_range = max(1, int(radar_range_m)) * 100.0
    yaw_rad = math.radians(cam_yaw)
    cos_y = math.cos(yaw_rad)
    sin_y = math.sin(yaw_rad)

    dx = pos[0] - cam_loc[0]
    dy = pos[1] - cam_loc[1]

    # 前方映射到雷达 y 负方向，右侧映射到 x 正方向。
    forward = dx * cos_y + dy * sin_y
    right = -dx * sin_y + dy * cos_y
    distance = (right * right + forward * forward) ** 0.5

    clamped = distance > world_range
    if clamped and distance > 0:
        ratio = world_range / distance
        right *= ratio
        forward *= ratio

    scale = inner_radius / world_range
    return {
        "x": right * scale,
        "y": -forward * scale,
        "distance_m": int(distance / 100),
        "clamped": clamped,
    }
