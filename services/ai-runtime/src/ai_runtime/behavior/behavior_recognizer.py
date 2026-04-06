"""
行为识别模块 - 时序行为分类

支持：
- 跌倒检测 (falling)
- 打架检测 (fighting) - 区分互殴和霸凌
- 徘徊检测 (loitering)
- 疑似轻生检测 (suicide_risk)
- 围栏翻越检测 (fence_climbing)
- 吸烟检测 (smoking)
- 长时间使用手机 (phone_use)
- 破坏公共设施 (vandalism)
- 摄像头遮挡 (camera_blocking)

关键：使用 16/32/64 帧窗口进行时序建模，不允许只看单帧
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any, Tuple
from collections import deque
import numpy as np
import time

from ai_runtime.models import (
    Track, BehaviorEvent, BehaviorResult, EventType, EventCategory,
    Severity, Participant, ParticipantRole, RoleAssignment,
    create_event, PoseSkeleton, KeyPoint
)
from ai_runtime.config import settings


# ============ 共享特征提取器 ============

class PoseFeatureExtractor:
    """统一共享的特征提取器，供所有检测器复用"""

    def __init__(self):
        self.pose_history: Dict[str, deque] = {}
        self.bbox_history: Dict[str, deque] = {}

    def update(self, tracks: List[Track]):
        for tid in list(self.pose_history.keys()):
            if tid not in {t.track_id for t in tracks}:
                del self.pose_history[tid]
        for tid in list(self.bbox_history.keys()):
            if tid not in {t.track_id for t in tracks}:
                del self.bbox_history[tid]

        for track in tracks:
            if track.track_id not in self.pose_history:
                self.pose_history[track.track_id] = deque(maxlen=64)
                self.bbox_history[track.track_id] = deque(maxlen=64)
            for pose in track.pose_history:
                self.pose_history[track.track_id].append(pose)
            for bbox in track.trajectory:
                self.bbox_history[track.track_id].append(bbox)

    def get_motion_features(self, track_id: str, window: int = 32) -> Dict[str, float]:
        bboxes = list(self.bbox_history.get(track_id, []))
        if len(bboxes) < 3:
            return {}
        bboxes = list(bboxes)[-window:]
        centers, heights, top_ys = [], [], []
        for b in bboxes:
            if b:
                centers.append((b.x + b.width / 2, b.y + b.height / 2))
                heights.append(b.height)
                top_ys.append(b.y)
        if len(centers) < 3:
            return {}
        velocities = [np.sqrt((centers[i][0]-centers[i-1][0])**2 + (centers[i][1]-centers[i-1][1])**2) for i in range(1, len(centers))]
        accels = [abs(velocities[i] - velocities[i-1]) for i in range(1, len(velocities))]
        return {
            "velocity_mean": float(np.mean(velocities)) if velocities else 0.0,
            "velocity_std": float(np.std(velocities)) if velocities else 0.0,
            "velocity_max": float(np.max(velocities)) if velocities else 0.0,
            "acceleration_mean": float(np.mean(accels)) if accels else 0.0,
            "acceleration_max": float(np.max(accels)) if accels else 0.0,
            "height_change_ratio": float((max(heights) - min(heights)) / max(heights)) if heights and max(heights) > 0 else 0.0,
            "vertical_velocity": float(np.mean([abs(top_ys[i] - top_ys[i-1]) for i in range(1, len(top_ys))])) if len(top_ys) > 1 else 0.0,
        }

    def get_pose_features(self, track_id: str, window: int = 32) -> Dict[str, Any]:
        poses = list(self.pose_history.get(track_id, []))
        if len(poses) < 3:
            return {}
        poses = poses[-window:]
        features: Dict[str, Any] = {}
        head_tilts, wrist_mouth_dists, wrist_face_dists = [], [], []
        hip_y_vals, wrist_y_vals = [], []
        for p in poses:
            if not p:
                continue
            nose = p.nose
            lh = p.left_hip
            rh = p.right_hip
            lw = p.left_wrist
            rw = p.right_wrist
            if nose and lh and rh:
                tilt = nose.y - (lh.y + rh.y) / 2
                head_tilts.append(tilt)
            if nose and (lw or rw):
                mouth_y = nose.y + 0.03
                if lw: wrist_mouth_dists.append(np.sqrt((lw.x - nose.x)**2 + (lw.y - mouth_y)**2))
                if rw: wrist_mouth_dists.append(np.sqrt((rw.x - nose.x)**2 + (rw.y - mouth_y)**2))
            if lw: wrist_y_vals.append(lw.y)
            if rw: wrist_y_vals.append(rw.y)
        # 计算髋部Y值（用于判断手腕相对位置）
        hip_vals = [p.left_hip.y for p in poses if p.left_hip] or []
        if hip_vals:
            features["hip_y_mean"] = float(np.mean(hip_vals))
        features["head_tilt_mean"] = float(np.mean(head_tilts)) if head_tilts else 0.0
        features["head_tilt_std"] = float(np.std(head_tilts)) if len(head_tilts) > 1 else 0.0
        features["wrist_mouth_dist_mean"] = float(np.mean(wrist_mouth_dists)) if wrist_mouth_dists else 1.0
        features["wrist_mouth_dist_min"] = float(np.min(wrist_mouth_dists)) if wrist_mouth_dists else 1.0
        features["wrist_y_mean"] = float(np.mean(wrist_y_vals)) if wrist_y_vals else 1.0
        # 判断手腕是否在胸前区域（用于区分吸烟和手机使用）
        if wrist_y_vals and hip_vals:
            features["wrist_above_hip"] = float(np.mean(wrist_y_vals)) < float(np.mean(hip_vals))
        else:
            features["wrist_above_hip"] = False
        return features


class BaseRecognizer(ABC):
    @abstractmethod
    def recognize(self, tracks: List[Track]) -> List[BehaviorResult]: pass


# ============ 跌倒识别器 ============

class FallRecognizer(BaseRecognizer):
    """
    跌倒检测 - 基于：
    1. 高度快速下降
    2. 宽高比变化（站立时 height > width，跌倒后 width > height）
    3. 垂直速度
    """
    def __init__(self, fe: PoseFeatureExtractor):
        self.fe = fe
        self.fall_frames: Dict[str, int] = {}

    def recognize(self, tracks: List[Track]) -> List[BehaviorResult]:
        results = []
        for track in tracks:
            mf = self.fe.get_motion_features(track.track_id, window=16)
            if not mf:
                continue

            # 获取轨迹历史计算宽高比
            bboxes = list(self.fe.bbox_history.get(track.track_id, []))[-16:]
            if len(bboxes) < 8:
                continue

            # 计算宽高比变化
            early_boxes = bboxes[:4]
            late_boxes = bboxes[-4:]

            early_height = np.mean([b.height for b in early_boxes])
            early_width = np.mean([b.width for b in early_boxes])
            late_height = np.mean([b.height for b in late_boxes])
            late_width = np.mean([b.width for b in late_boxes])

            early_ratio = early_height / (early_width + 1e-6)
            late_ratio = late_height / (late_width + 1e-6)

            # 跌倒条件：
            # 1. 高度下降超过40%
            # 2. 宽高比从 >1.5 变为 <1.2（从站立/行走变为躺下）
            # 3. 垂直速度足够
            height_drop = mf["height_change_ratio"] > 0.35
            vertical_vel = mf["vertical_velocity"] > 0.005
            ratio_change = early_ratio > 1.3 and late_ratio < 1.1

            is_fall = height_drop and vertical_vel and ratio_change

            if is_fall:
                self.fall_frames[track.track_id] = self.fall_frames.get(track.track_id, 0) + 1
            else:
                self.fall_frames[track.track_id] = max(0, self.fall_frames.get(track.track_id, 0) - 2)

            count = self.fall_frames.get(track.track_id, 0)
            if count >= 3:  # 连续3帧检测到
                conf = min(0.95, 0.6 + mf["height_change_ratio"] * 0.5)
                results.append(BehaviorResult(
                    behavior_type=EventType.FALLING, category=EventCategory.HIGH_RISK,
                    confidence=conf, window_size=16, temporal_scores={16: conf},
                    evidence={
                        "height_change_ratio": mf["height_change_ratio"],
                        "vertical_velocity": mf["vertical_velocity"],
                        "early_ratio": early_ratio,
                        "late_ratio": late_ratio
                    }))

        for tid in list(self.fall_frames.keys()):
            if tid not in {t.track_id for t in tracks}:
                self.fall_frames.pop(tid, None)

        return results


# ============ 打架/霸凌识别器 ============

class FightRecognizer(BaseRecognizer):
    """
    打架/霸凌检测 - 基于：
    1. 两人距离足够近
    2. 双方都有快速运动
    3. 高加速度
    4. 区分互殴（双方速度相近）和霸凌（一方主动一方被动）
    """
    def __init__(self, fe: PoseFeatureExtractor):
        self.fe = fe
        self.violent_pairs: Dict[Tuple[str, str], int] = {}
        self.proximity_threshold = 0.25  # 两人距离阈值（归一化坐标）

    def _get_center(self, track: Track) -> tuple:
        """获取轨迹中心点"""
        if not track.trajectory:
            return (0.5, 0.5)
        bbox = track.trajectory[-1]
        return (bbox.x + bbox.width/2, bbox.y + bbox.height/2)

    def _compute_distance(self, t1: Track, t2: Track) -> float:
        """计算两人距离"""
        c1 = self._get_center(t1)
        c2 = self._get_center(t2)
        return np.sqrt((c1[0] - c2[0])**2 + (c1[1] - c2[1])**2)

    def recognize(self, tracks: List[Track]) -> List[BehaviorResult]:
        results = []
        persons = [t for t in tracks if t.class_name == "person"]
        if len(persons) < 2:
            return results

        for i, t1 in enumerate(persons):
            for t2 in persons[i+1:]:
                # 检查距离
                dist = self._compute_distance(t1, t2)
                if dist > self.proximity_threshold:
                    continue

                mf1 = self.fe.get_motion_features(t1.track_id, 32)
                mf2 = self.fe.get_motion_features(t2.track_id, 32)
                if not mf1 or not mf2:
                    continue

                v1, v2 = mf1["velocity_mean"], mf2["velocity_mean"]
                a1, a2 = mf1["acceleration_max"], mf2["acceleration_max"]

                # 更严格的条件：双方都有明显运动且加速度高
                both_active = v1 > 0.012 and v2 > 0.012
                high_accel = a1 > 0.015 or a2 > 0.015

                pair_key = tuple(sorted([t1.track_id, t2.track_id]))

                if both_active and high_accel:
                    self.violent_pairs[pair_key] = self.violent_pairs.get(pair_key, 0) + 1
                    count = self.violent_pairs[pair_key]
                    if count >= 10:  # 增加触发阈值
                        conf = min(0.95, 0.6 + count * 0.02)
                        # 互殴：双方速度相近；霸凌：速度差异大
                        vel_diff = abs(v1 - v2)
                        is_mutual = vel_diff < 0.008
                        results.append(BehaviorResult(
                            behavior_type=EventType.FIGHTING if is_mutual else EventType.BULLYING,
                            category=EventCategory.HIGH_RISK, confidence=conf, window_size=32, temporal_scores={32: conf},
                            evidence={"pair_count": count, "v1": v1, "v2": v2, "distance": dist, "vel_diff": vel_diff}))
                else:
                    self.violent_pairs[pair_key] = max(0, self.violent_pairs.get(pair_key, 0) - 2)

        # 清理
        for k in list(self.violent_pairs.keys()):
            if self.violent_pairs[k] <= 0:
                del self.violent_pairs[k]

        return results


# ============ 徘徊识别器 ============

class LoiteringRecognizer(BaseRecognizer):
    """
    徘徊检测 - 基于：
    1. 停留时间超过阈值
    2. 运动范围小（在一个区域内来回走动）
    """
    def __init__(self, fe: PoseFeatureExtractor):
        self.fe = fe
        self.dwell_times: Dict[str, float] = {}
        self.movement_ranges: Dict[str, List[float]] = {}
        self.threshold = settings.DWELL_TIME_THRESHOLD
        self.movement_threshold = 0.15  # 运动范围阈值

    def recognize(self, tracks: List[Track]) -> List[BehaviorResult]:
        results = []
        for track in tracks:
            # 检查停留时间
            if track.dwell_time < self.threshold:
                continue

            # 检查运动范围
            bboxes = list(self.fe.bbox_history.get(track.track_id, []))[-60:]
            if len(bboxes) < 30:
                continue

            centers_x = [b.x + b.width/2 for b in bboxes]
            centers_y = [b.y + b.height/2 for b in bboxes]

            range_x = max(centers_x) - min(centers_x)
            range_y = max(centers_y) - min(centers_y)
            total_range = np.sqrt(range_x**2 + range_y**2)

            # 徘徊：停留时间长 + 运动范围小
            if total_range < self.movement_threshold:
                conf = min(0.95, 0.5 + (track.dwell_time - self.threshold) / 60)
                results.append(BehaviorResult(
                    behavior_type=EventType.LOITERING, category=EventCategory.SUSPICIOUS,
                    confidence=conf, evidence={"dwell_time": track.dwell_time, "movement_range": total_range}))

        return results


# ============ 疑似轻生识别器 ============

class SuicideRiskRecognizer(BaseRecognizer):
    """
    疑似轻生检测 - 基于：
    1. 长时间静止（>3秒）
    2. 危险位置（高处、边缘等）- 通过高度判断
    3. 低头或异常姿态
    """
    def __init__(self, fe: PoseFeatureExtractor):
        self.fe = fe
        self.still_frames: Dict[str, int] = {}
        self.head_down_frames: Dict[str, int] = {}
        self.min_still_frames = 90  # 约3秒@30fps
        self.min_head_down_frames = 45  # 约1.5秒

    def recognize(self, tracks: List[Track]) -> List[BehaviorResult]:
        results = []
        for track in tracks:
            mf = self.fe.get_motion_features(track.track_id, 24)
            pf = self.fe.get_pose_features(track.track_id, 24)

            if not mf or not pf:
                continue

            # 静止检测
            still = mf.get("velocity_mean", 1.0) < 0.002
            # 低头检测
            head_down = pf.get("head_tilt_mean", 0) < -0.12

            if still:
                self.still_frames[track.track_id] = self.still_frames.get(track.track_id, 0) + 1
            else:
                self.still_frames[track.track_id] = max(0, self.still_frames.get(track.track_id, 0) - 1)

            if head_down:
                self.head_down_frames[track.track_id] = self.head_down_frames.get(track.track_id, 0) + 1
            else:
                self.head_down_frames[track.track_id] = max(0, self.head_down_frames.get(track.track_id, 0) - 1)

            sf = self.still_frames.get(track.track_id, 0)
            hdf = self.head_down_frames.get(track.track_id, 0)

            # 轻生风险：长时间静止 + 低头
            if sf >= self.min_still_frames and hdf >= self.min_head_down_frames:
                conf = min(0.95, 0.6 + sf * 0.002 + abs(pf.get("head_tilt_mean", 0)) * 0.5)
                results.append(BehaviorResult(
                    behavior_type=EventType.SUICIDE_RISK, category=EventCategory.HIGH_RISK,
                    confidence=conf, window_size=90, temporal_scores={90: conf},
                    evidence={"still_frames": sf, "head_tilt": pf.get("head_tilt_mean", 0)}))

        # 清理
        current_ids = {t.track_id for t in tracks}
        for tid in list(self.still_frames.keys()):
            if tid not in current_ids:
                self.still_frames.pop(tid, None)
                self.head_down_frames.pop(tid, None)

        return results


# ============ 围栏翻越识别器 ============

class FenceClimbingRecognizer(BaseRecognizer):
    """
    围栏翻越检测 - 基于：
    1. 垂直方向运动明显
    2. 身体先升高后降低（翻越动作）
    3. 中段高度明显低于起始高度
    """
    def __init__(self, fe: PoseFeatureExtractor):
        self.fe = fe
        self.climb_frames: Dict[str, int] = {}
        self.height_history: Dict[str, List[float]] = {}

    def recognize(self, tracks: List[Track]) -> List[BehaviorResult]:
        results = []
        for track in tracks:
            bboxes = list(self.fe.bbox_history.get(track.track_id, []))[-48:]
            if len(bboxes) < 24:
                continue

            heights = [b.height for b in bboxes]
            centers_y = [b.y + b.height/2 for b in bboxes]

            # 分析高度变化模式
            first_q = heights[:len(heights)//4]
            mid_q = heights[len(heights)//4:3*len(heights)//4]
            last_q = heights[3*len(heights)//4:]

            first_avg = np.mean(first_q) if first_q else 0
            mid_avg = np.mean(mid_q) if mid_q else 0
            last_avg = np.mean(last_q) if last_q else 0

            # 垂直运动幅度
            vertical_range = max(centers_y) - min(centers_y)

            # 翻越模式：起始高度正常 -> 中段降低（攀爬）-> 结束高度恢复
            # 或者：起始高度正常 -> 中段升高（翻越顶部）-> 结束高度恢复
            climb_pattern1 = first_avg > mid_avg * 1.2 and last_avg > mid_avg * 1.1  # 翻越下降
            climb_pattern2 = mid_avg > first_avg * 1.15 and mid_avg > last_avg * 1.1  # 翻越上升
            significant_vertical = vertical_range > 0.1

            is_climbing = (climb_pattern1 or climb_pattern2) and significant_vertical

            if is_climbing:
                self.climb_frames[track.track_id] = self.climb_frames.get(track.track_id, 0) + 1
            else:
                self.climb_frames[track.track_id] = max(0, self.climb_frames.get(track.track_id, 0) - 1)

            count = self.climb_frames.get(track.track_id, 0)
            if count >= 12:
                conf = min(0.95, 0.6 + count * 0.02)
                results.append(BehaviorResult(
                    behavior_type=EventType.FENCE_CLIMBING, category=EventCategory.SUSPICIOUS,
                    confidence=conf, window_size=48, evidence={
                        "first_h": first_avg,
                        "mid_h": mid_avg,
                        "last_h": last_avg,
                        "vertical_range": vertical_range
                    }))

        for tid in list(self.climb_frames.keys()):
            if tid not in {t.track_id for t in tracks}:
                self.climb_frames.pop(tid, None)

        return results


# ============ 吸烟检测器 ============

class SmokingRecognizer(BaseRecognizer):
    """
    吸烟检测 - 条件：
    1. 手腕靠近嘴部（手腕-嘴距离小）
    2. 相对静止
    3. 头部倾斜不严重（区别于手机使用的大幅度低头）
    """
    def __init__(self, fe: PoseFeatureExtractor):
        self.fe = fe
        self.smoke_count: Dict[str, int] = {}
        self.contact_threshold = 0.15  # 手腕靠近嘴的阈值
        self.min_frames = 30  # 约1秒@30fps
        self.velocity_threshold = 0.008  # 相对静止
        self.tilt_threshold = -0.18  # 允许一定低头

    def recognize(self, tracks: List[Track]) -> List[BehaviorResult]:
        results = []
        for track in tracks:
            mf = self.fe.get_motion_features(track.track_id, 24)
            pf = self.fe.get_pose_features(track.track_id, 24)
            if not mf or not pf:
                continue

            dist = pf.get("wrist_mouth_dist_min", 1.0)
            vel = mf.get("velocity_mean", 1.0)
            tilt = pf.get("head_tilt_mean", 0)

            # 吸烟：手腕靠近嘴 + 相对静止 + 头部不严重低头
            is_smoking = (
                dist < self.contact_threshold and
                vel < self.velocity_threshold and
                tilt > self.tilt_threshold
            )

            if is_smoking:
                self.smoke_count[track.track_id] = self.smoke_count.get(track.track_id, 0) + 2
            else:
                self.smoke_count[track.track_id] = max(0, self.smoke_count.get(track.track_id, 0) - 1)

            count = self.smoke_count.get(track.track_id, 0)
            if count >= self.min_frames:
                conf = min(0.95, 0.6 + count * 0.005)
                results.append(BehaviorResult(
                    behavior_type=EventType.SMOKING, category=EventCategory.MANAGEMENT_SENSITIVE,
                    confidence=conf, evidence={"wrist_mouth_dist": dist, "count": count, "head_tilt": tilt}))

        for tid in list(self.smoke_count.keys()):
            if tid not in {t.track_id for t in tracks}:
                self.smoke_count.pop(tid, None)

        return results


# ============ 手机使用检测器 ============

class PhoneUseRecognizer(BaseRecognizer):
    """
    低头看手机检测：
    1. 强烈头部倾斜（低头）
    2. 手腕在胸前区域（胸以上）
    3. 相对静止
    4. 手腕靠近身体中线（双手握持或单手在胸前）
    """
    def __init__(self, fe: PoseFeatureExtractor):
        self.fe = fe
        self.phone_frames: Dict[str, int] = {}
        self.min_frames = 48  # 约1.5秒@30fps
        self.tilt_threshold = -0.15  # 低头阈值
        self.velocity_threshold = 0.005

    def recognize(self, tracks: List[Track]) -> List[BehaviorResult]:
        results = []
        for track in tracks:
            pf = self.fe.get_pose_features(track.track_id, 24)
            mf = self.fe.get_motion_features(track.track_id, 24)
            if not pf or not mf:
                continue

            tilt = pf.get("head_tilt_mean", 0)
            vel = mf.get("velocity_mean", 1.0)
            wrist_y = pf.get("wrist_y_mean", 1.0)
            hip_y = pf.get("hip_y_mean", 0.5)

            # 条件：低头 + 手腕在胸前（高于髋部）+ 相对静止
            is_phone = (
                tilt < self.tilt_threshold and  # 低头
                wrist_y < hip_y and  # 手腕在胸前
                vel < self.velocity_threshold  # 相对静止
            )

            if is_phone:
                self.phone_frames[track.track_id] = self.phone_frames.get(track.track_id, 0) + 2
            else:
                self.phone_frames[track.track_id] = max(0, self.phone_frames.get(track.track_id, 0) - 1)

            count = self.phone_frames.get(track.track_id, 0)
            if count >= self.min_frames:
                conf = min(0.95, 0.6 + abs(tilt) * 0.5 + count * 0.003)
                results.append(BehaviorResult(
                    behavior_type=EventType.PHONE_USE, category=EventCategory.MANAGEMENT_SENSITIVE,
                    confidence=conf, evidence={"head_tilt": tilt, "phone_frames": count, "wrist_y": wrist_y}))

        for tid in list(self.phone_frames.keys()):
            if tid not in {t.track_id for t in tracks}:
                self.phone_frames.pop(tid, None)

        return results


# ============ 破坏设施检测器 ============

class VandalismRecognizer(BaseRecognizer):
    """
    破坏设施检测 - 基于：
    1. 检测到设施物体（摄像头、设备等）
    2. 人员靠近设施
    3. 快速/暴力动作
    """
    def __init__(self, fe: PoseFeatureExtractor):
        self.fe = fe
        self.vandal_count: Dict[str, int] = {}
        self.min_frames = 20
        self.proximity_threshold = 0.15  # 靠近设施的距离阈值
        self.violence_threshold = 0.02   # 暴力动作阈值

    def _compute_distance(self, b1, b2) -> float:
        """计算两个bbox中心距离"""
        c1 = (b1.x + b1.width/2, b1.y + b1.height/2)
        c2 = (b2.x + b2.width/2, b2.y + b2.height/2)
        return np.sqrt((c1[0] - c2[0])**2 + (c1[1] - c2[1])**2)

    def recognize(self, tracks: List[Track]) -> List[BehaviorResult]:
        results = []
        persons = [t for t in tracks if t.class_name == "person"]
        # 设施包括：摄像头、电子设备等
        facilities = [t for t in tracks if t.class_name in ["cell phone", "laptop", "camera", "tv", "microwave"]]

        for p in persons:
            mf = self.fe.get_motion_features(p.track_id, 20)
            if not mf:
                continue

            near_facility = False
            if facilities:
                pb = list(self.fe.bbox_history.get(p.track_id, []))
                if pb:
                    for f in facilities:
                        fb = list(self.fe.bbox_history.get(f.track_id, []))
                        if fb:
                            dist = self._compute_distance(pb[-1], fb[-1])
                            if dist < self.proximity_threshold:
                                near_facility = True
                                break

            # 暴力动作：高加速度或高速度
            is_violent = (
                mf["acceleration_max"] > self.violence_threshold or
                mf["velocity_max"] > 0.025
            )

            if near_facility and is_violent:
                self.vandal_count[p.track_id] = self.vandal_count.get(p.track_id, 0) + 1
            else:
                self.vandal_count[p.track_id] = max(0, self.vandal_count.get(p.track_id, 0) - 1)

            count = self.vandal_count.get(p.track_id, 0)
            if count >= self.min_frames:
                conf = min(0.95, 0.6 + count * 0.015)
                results.append(BehaviorResult(
                    behavior_type=EventType.VANDALISM, category=EventCategory.HIGH_RISK,
                    confidence=conf, evidence={"vandal_frames": count, "near_facility": near_facility}))

        for tid in list(self.vandal_count.keys()):
            if tid not in {t.track_id for t in tracks}:
                self.vandal_count.pop(tid, None)

        return results


# ============ 摄像头遮挡检测器 ============

class CameraBlockingRecognizer(BaseRecognizer):
    """
    摄像头遮挡检测 - 基于：
    1. 目标占据画面大面积（>80%）
    2. 持续多帧
    3. 通常是人体或物体直接贴近摄像头
    """
    def __init__(self, fe: PoseFeatureExtractor):
        self.fe = fe
        self.block_frames = 0
        self.area_threshold = 0.80  # 面积阈值
        self.min_frames = 15

    def recognize(self, tracks: List[Track]) -> List[BehaviorResult]:
        results = []

        # 计算最大目标占据面积
        max_area = 0
        if tracks:
            for t in tracks:
                if t.trajectory:
                    bbox = t.trajectory[-1]
                    area = bbox.width * bbox.height
                    max_area = max(max_area, area)

        # 条件：大面积遮挡
        if max_area > self.area_threshold:
            self.block_frames += 1
        else:
            self.block_frames = max(0, self.block_frames - 2)

        if self.block_frames >= self.min_frames:
            conf = min(0.95, 0.6 + self.block_frames * 0.01)
            results.append(BehaviorResult(
                behavior_type=EventType.CAMERA_BLOCKING, category=EventCategory.MANAGEMENT_SENSITIVE,
                confidence=conf, evidence={"max_area": max_area, "block_frames": self.block_frames}))

        return results


# ============ Pipeline ============

class BehaviorRecognizerPipeline:
    # 互斥行为组 - 同一组内的行为不会同时输出
    MUTUALLY_EXCLUSIVE_GROUPS = [
        # 手部相关行为（靠近脸部）- 静态行为
        [EventType.SMOKING, EventType.PHONE_USE],
        # 暴力行为 - 动态行为，与静态行为互斥
        [EventType.FIGHTING, EventType.BULLYING, EventType.VANDALISM],
        # 静止行为
        [EventType.SUICIDE_RISK, EventType.LOITERING],
        # 身体姿态剧变
        [EventType.FALLING, EventType.FENCE_CLIMBING],
    ]

    # 行为优先级（高优先级会压制低优先级）
    BEHAVIOR_PRIORITY = {
        EventType.FIGHTING: 100,
        EventType.BULLYING: 100,
        EventType.FALLING: 90,
        EventType.SUICIDE_RISK: 90,
        EventType.VANDALISM: 80,
        EventType.FENCE_CLIMBING: 70,
        EventType.SMOKING: 60,
        EventType.PHONE_USE: 60,
        EventType.CAMERA_BLOCKING: 50,
        EventType.LOITERING: 40,
    }

    # 动态行为会压制静态行为
    DYNAMIC_BEHAVIORS = {EventType.FIGHTING, EventType.BULLYING, EventType.FALLING, EventType.VANDALISM, EventType.FENCE_CLIMBING}
    STATIC_BEHAVIORS = {EventType.SMOKING, EventType.PHONE_USE, EventType.SUICIDE_RISK}

    def __init__(self):
        fe = PoseFeatureExtractor()
        self.fe = fe
        self.feature_extractor = fe  # 别名供外部访问
        self.recognizers: List[BaseRecognizer] = [
            FallRecognizer(fe), FightRecognizer(fe), LoiteringRecognizer(fe),
            SuicideRiskRecognizer(fe), FenceClimbingRecognizer(fe), SmokingRecognizer(fe),
            PhoneUseRecognizer(fe), VandalismRecognizer(fe), CameraBlockingRecognizer(fe),
        ]

    def update(self, tracks: List[Track]):
        self.fe.update(tracks)
        for r in self.recognizers:
            if hasattr(r, 'recognize'):
                pass  # recognize is called separately

    def _apply_mutual_exclusion(self, results: List[BehaviorResult]) -> List[BehaviorResult]:
        """应用互斥规则，过滤掉低优先级的冲突行为"""
        if not results:
            return results

        # 检查是否有动态行为（任何帧中有动态行为就过滤静态行为）
        has_dynamic = any(r.behavior_type in self.DYNAMIC_BEHAVIORS for r in results)

        # 按优先级排序（优先级高的在前，同优先级置信度高的在前）
        sorted_results = sorted(
            results,
            key=lambda r: (self.BEHAVIOR_PRIORITY.get(r.behavior_type, 0), r.confidence),
            reverse=True
        )

        filtered = []
        blocked_types = set()

        for result in sorted_results:
            behavior_type = result.behavior_type

            # 检查是否被互斥组阻塞
            if behavior_type in blocked_types:
                continue

            # 如果有动态行为，阻塞所有静态行为（不管优先级）
            if has_dynamic and behavior_type in self.STATIC_BEHAVIORS:
                continue

            # 添加到结果
            filtered.append(result)

            # 阻塞互斥组中的其他行为
            for group in self.MUTUALLY_EXCLUSIVE_GROUPS:
                if behavior_type in group:
                    for bt in group:
                        if bt != behavior_type:
                            blocked_types.add(bt)

        return filtered

    def recognize(self, tracks: List[Track]) -> List[BehaviorResult]:
        all_results = []
        for r in self.recognizers:
            results = r.recognize(tracks)
            all_results.extend(results)

        # 应用互斥规则
        filtered_results = self._apply_mutual_exclusion(all_results)

        return filtered_results
