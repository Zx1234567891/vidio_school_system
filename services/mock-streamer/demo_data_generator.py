"""
演示数据生成器 - 基于检测视频生成模拟事件和告警
"""
import os
import json
import random
from datetime import datetime, timedelta
from typing import List, Dict, Any
from dataclasses import dataclass, asdict


# 行为定义
BEHAVIORS = {
    "打架斗殴": {"severity": "high", "category": "高风险异常", "description": "检测到多人肢体冲突"},
    "校园霸凌": {"severity": "high", "category": "高风险异常", "description": "检测到单向攻击行为"},
    "摔倒": {"severity": "high", "category": "高风险异常", "description": "检测到人员跌倒"},
    "疑似轻生": {"severity": "high", "category": "高风险异常", "description": "检测到危险行为"},
    "破坏设施": {"severity": "high", "category": "高风险异常", "description": "检测到破坏公共设施"},
    "吸烟": {"severity": "medium", "category": "敏感行为", "description": "检测到吸烟行为"},
    "低头看手机": {"severity": "medium", "category": "敏感行为", "description": "检测到长时间使用手机"},
    "摄像头遮挡": {"severity": "medium", "category": "敏感行为", "description": "检测到摄像头被遮挡"},
    "异常徘徊": {"severity": "low", "category": "可疑行为", "description": "检测到异常徘徊"},
    "翻越围栏": {"severity": "low", "category": "可疑行为", "description": "检测到翻越围栏"},
}


@dataclass
class DetectionEvent:
    """检测事件"""
    id: str
    stream_id: str
    stream_name: str
    behavior_label: str
    severity: str
    category: str
    description: str
    timestamp: str
    frame_idx: int
    confidence: float
    bbox: Dict[str, float]
    participants: List[Dict[str, Any]]
    video_clip_path: str = ""
    reviewed: bool = False
    review_result: str = ""  # confirmed, false_positive, pending
    review_comment: str = ""


@dataclass
class Alert:
    """实时告警"""
    id: str
    event_id: str
    severity: str
    title: str
    message: str
    timestamp: str
    stream_id: str
    stream_name: str
    acknowledged: bool = False


class DemoDataGenerator:
    """演示数据生成器"""

    def __init__(self, output_dir: str = "./demo_data"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

        self.events: List[DetectionEvent] = []
        self.alerts: List[Alert] = []
        self.event_counter = 0
        self.alert_counter = 0

    def generate_events_from_video(self, video_info: Dict[str, Any], count: int = 5) -> List[DetectionEvent]:
        """基于视频信息生成事件"""
        events = []
        base_time = datetime.now() - timedelta(hours=random.randint(1, 24))

        behavior_label = video_info.get("behavior_label", "未知行为")
        behavior_def = BEHAVIORS.get(behavior_label, {
            "severity": "medium",
            "category": "其他",
            "description": "检测到异常行为"
        })

        for i in range(count):
            self.event_counter += 1
            event_id = f"EVT{self.event_counter:06d}"

            # 时间分散
            event_time = base_time + timedelta(minutes=random.randint(5, 120))

            # 生成参与者
            num_participants = random.randint(1, 3)
            participants = []
            for j in range(num_participants):
                role = "aggressor" if j == 0 and behavior_label in ["打架斗殴", "校园霸凌"] else "victim" if j == 1 else "bystander"
                participants.append({
                    "track_id": f"P{j:03d}",
                    "role": role,
                    "confidence": random.uniform(0.75, 0.98)
                })

            event = DetectionEvent(
                id=event_id,
                stream_id=video_info["id"],
                stream_name=video_info["name"],
                behavior_label=behavior_label,
                severity=behavior_def["severity"],
                category=behavior_def["category"],
                description=behavior_def["description"],
                timestamp=event_time.isoformat(),
                frame_idx=random.randint(100, video_info.get("total_frames", 1000)),
                confidence=random.uniform(0.75, 0.98),
                bbox={
                    "x": random.uniform(0.1, 0.5),
                    "y": random.uniform(0.1, 0.5),
                    "width": random.uniform(0.1, 0.3),
                    "height": random.uniform(0.2, 0.4)
                },
                participants=participants,
                video_clip_path=f"/clips/{event_id}.mp4",
                reviewed=random.random() > 0.7,
                review_result=random.choice(["confirmed", "false_positive", "pending"]) if random.random() > 0.7 else "pending",
                review_comment=""
            )

            events.append(event)

            # 为高严重度事件生成告警
            if behavior_def["severity"] == "high" and random.random() > 0.3:
                self.alert_counter += 1
                alert = Alert(
                    id=f"ALERT{self.alert_counter:06d}",
                    event_id=event_id,
                    severity=behavior_def["severity"],
                    title=f"{behavior_label}告警",
                    message=behavior_def["description"],
                    timestamp=event_time.isoformat(),
                    stream_id=video_info["id"],
                    stream_name=video_info["name"],
                    acknowledged=random.random() > 0.5
                )
                self.alerts.append(alert)

        self.events.extend(events)
        return events

    def generate_all_demo_data(self, streams: List[Dict[str, Any]]):
        """为所有流生成演示数据"""
        print("[*] 生成演示事件数据...")

        for stream in streams:
            count = random.randint(3, 8)
            events = self.generate_events_from_video(stream, count)
            print(f"  - {stream['name']}: 生成 {len(events)} 个事件")

        print(f"[*] 共生成 {len(self.events)} 个事件, {len(self.alerts)} 个告警")

    def save_to_json(self):
        """保存数据到JSON文件"""
        events_file = os.path.join(self.output_dir, "events.json")
        alerts_file = os.path.join(self.output_dir, "alerts.json")

        with open(events_file, 'w', encoding='utf-8') as f:
            json.dump([asdict(e) for e in self.events], f, ensure_ascii=False, indent=2)

        with open(alerts_file, 'w', encoding='utf-8') as f:
            json.dump([asdict(a) for a in self.alerts], f, ensure_ascii=False, indent=2)

        print(f"[*] 数据已保存到 {self.output_dir}")
        return events_file, alerts_file

    def get_recent_events(self, limit: int = 20) -> List[Dict]:
        """获取最近的事件"""
        sorted_events = sorted(self.events, key=lambda e: e.timestamp, reverse=True)
        return [asdict(e) for e in sorted_events[:limit]]

    def get_unacknowledged_alerts(self) -> List[Dict]:
        """获取未确认告警"""
        unack = [a for a in self.alerts if not a.acknowledged]
        return [asdict(a) for a in sorted(unack, key=lambda x: x.timestamp, reverse=True)]

    def get_stats(self) -> Dict[str, Any]:
        """获取统计数据"""
        severity_counts = {"high": 0, "medium": 0, "low": 0}
        category_counts = {}

        for e in self.events:
            severity_counts[e.severity] = severity_counts.get(e.severity, 0) + 1
            category_counts[e.category] = category_counts.get(e.category, 0) + 1

        return {
            "total_events": len(self.events),
            "total_alerts": len(self.alerts),
            "unacknowledged_alerts": len([a for a in self.alerts if not a.acknowledged]),
            "pending_reviews": len([e for e in self.events if e.review_result == "pending"]),
            "severity_distribution": severity_counts,
            "category_distribution": category_counts
        }


if __name__ == "__main__":
    # 测试
    generator = DemoDataGenerator()

    # 模拟流数据
    mock_streams = [
        {"id": "stream_001", "name": "教学楼A-1F大厅", "behavior_label": "打架斗殴", "total_frames": 1000},
        {"id": "stream_002", "name": "操场西侧", "behavior_label": "校园霸凌", "total_frames": 2000},
        {"id": "stream_003", "name": "食堂入口", "behavior_label": "摔倒", "total_frames": 1500},
    ]

    generator.generate_all_demo_data(mock_streams)
    generator.save_to_json()

    print("\n[*] 统计:")
    print(json.dumps(generator.get_stats(), ensure_ascii=False, indent=2))
