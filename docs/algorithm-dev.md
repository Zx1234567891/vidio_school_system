# Campus Guard AI - 算法与 AI Runtime 开发文档

## 1. 系统概述

AI Runtime 是 Campus Guard AI 的智能核心，负责视频帧的检测、跟踪、姿态估计、行为识别、规则融合和事件聚合。系统采用模块化 Pipeline 架构，所有模块均支持 Mock/真实模型切换。

### 1.1 技术栈

| 技术 | 用途 |
|------|------|
| Python 3.10+ | 运行时 |
| YOLOv8 (ultralytics) | 目标检测、姿态估计 |
| ONNX Runtime | 模型推理加速 |
| NumPy | 数值计算 |
| Shapely | 几何计算（ROI/禁区/越线检测） |
| OpenCV | 图像处理 |

### 1.2 模型文件

```
services/ai-runtime/models/
├── yolov8n.pt                # YOLOv8n 检测模型（COCO 预训练）
├── yolov8n.onnx              # ONNX 格式检测模型
├── yolov8n-pose.pt           # YOLOv8n-pose 姿态估计模型
└── yolov8n-pose.onnx         # ONNX 格式姿态模型
```

## 2. 项目结构

```
services/ai-runtime/
├── main.py                              # 服务入口
├── requirements.txt                     # Python 依赖
├── models/                              # 模型文件目录
├── src/ai_runtime/
│   ├── __init__.py
│   ├── config.py                        # 配置（模型路径、阈值等）
│   ├── models.py                        # 数据模型定义（Pydantic）
│   ├── pipeline.py                      # 主 Pipeline（串联所有模块）
│   ├── detector/
│   │   └── detector.py                  # 目标检测器（YOLO / Mock）
│   ├── tracker/
│   │   └── tracker.py                   # 多目标跟踪器（ByteTrack / Mock）
│   ├── pose/
│   │   └── pose_estimator.py            # 姿态估计器（YOLO-Pose / Mock）
│   ├── behavior/
│   │   └── behavior_recognizer.py       # 行为识别 Pipeline（9 种识别器）
│   ├── rules/
│   │   └── rule_engine.py               # 规则引擎（ROI/禁区/停留/越线）
│   ├── event_agg/
│   │   └── event_aggregator.py          # 事件聚合器（时间窗口去重）
│   └── models/
│       └── onnx_exporter.py             # ONNX 模型导出工具
├── demo_behavior_detection.py           # 行为检测演示脚本
├── demo_final.py                        # 最终演示脚本
├── demo_simple.py                       # 简化演示脚本
├── test_single_video.py                 # 单视频测试脚本
└── video_test.py                        # 视频测试
```

## 3. Pipeline 架构

### 3.1 处理流程

```
输入帧 (BGR numpy array)
    │
    ▼
┌──────────────┐
│  1. Detection │  目标检测（YOLO）
│  YOLODetector │  输出：List[Detection] {class, bbox, confidence}
└──────┬───────┘
       │
       ▼
┌──────────────┐
│  2. Tracking  │  多目标跟踪（ByteTrack）
│  ByteTracker  │  输出：List[Track] {track_id, history, velocity}
└──────┬───────┘
       │
       ▼
┌───────────────┐
│  3. Pose Est.  │  姿态估计（YOLO-Pose）
│  YOLOPose     │  输出：List[PoseSkeleton] {17 个关键点}
└──────┬────────┘
       │
       ▼
┌────────────────────┐
│  4. Behavior Recog. │  行为识别（9 种识别器）
│  BehaviorPipeline   │  输出：List[BehaviorResult]
└──────┬─────────────┘
       │
       ▼
┌──────────────┐
│  5. Rule Eng. │  规则引擎（ROI/禁区/越线/停留）
│  RuleEngine   │  输出：List[RuleTrigger]
└──────┬───────┘
       │
       ▼
┌───────────────┐
│  6. Event Agg. │  事件聚合（时间窗口去重）
│  EventAggregator│ 输出：List[BehaviorEvent]
└──────┬────────┘
       │
       ▼
  事件回调 → API → 前端
```

### 3.2 Pipeline 初始化

```python
from ai_runtime.pipeline import create_pipeline

# Mock 模式（开发/测试）
pipeline = create_pipeline(use_real_models=False, device="cpu")

# 真实模型模式
pipeline = create_pipeline(use_real_models=True, device="cuda")
```

### 3.3 单帧处理

```python
result = pipeline.process_frame(
    image=frame,           # BGR numpy array (H, W, 3)
    stream_id="stream_001",
    frame_id="frame_12345"
)

# result.frame_result   → 检测结果
# result.tracks         → 跟踪列表
# result.events         → 产生的事件
# result.rule_triggers  → 规则触发
# result.total_processing_time_ms → 总处理时间
```

## 4. 模块详解

### 4.1 目标检测器 (Detector)

#### 架构

```python
BaseDetector (ABC)
├── YOLODetector     # 真实 YOLOv8 检测
└── MockDetector     # Mock 测试用
```

#### YOLODetector

- **模型**：YOLOv8n（COCO 预训练）
- **输入**：BGR 图像 numpy array
- **输出**：`List[Detection]`，每个包含 `class_name`、`class_id`、`confidence`、`bbox`（归一化坐标）

**关注的目标类别（校园安防场景）**：

| 类别 | COCO ID | 用途 |
|------|---------|------|
| person | 0 | 人员检测（核心） |
| backpack | 24 | 物品检测 |
| handbag | 26 | 物品检测 |
| suitcase | 28 | 物品检测 |
| bottle | 39 | 物品检测 |
| knife | 43 | 危险物品 |
| cell phone | 67 | 手机使用检测 |
| laptop | 63 | 设施检测 |

**关键配置**：
- `DETECTOR_CONFIDENCE`：置信度阈值
- `DETECTOR_IOU`：NMS IoU 阈值

#### 工厂函数

```python
detector = create_detector("yolo", device="cpu")   # 真实模型
detector = create_detector("mock")                   # Mock
```

---

### 4.2 多目标跟踪器 (Tracker)

#### 架构

```python
BaseTracker (ABC)
├── ByteTrackTracker  # ByteTrack 实现
└── MockTracker       # Mock 测试用
```

#### ByteTrackTracker

**算法特点**：
1. **高低置信度分离匹配**：高置信度检测优先匹配已有轨迹，低置信度二次匹配
2. **基于 IoU 的匹配**：计算检测框与轨迹预测框的交并比
3. **轨迹管理**：自动创建新轨迹、清除丢失轨迹

**关键参数**：

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `track_thresh` | 0.5 | 高/低置信度分界阈值 |
| `match_thresh` | 0.8 | IoU 匹配阈值 |
| `track_buffer` | 30 | 轨迹丢失缓冲帧数 |
| `frame_rate` | 30 | 帧率 |

**Track ID 格式**：`track_{6位序号}`，如 `track_000001`

**轨迹状态维护**：
- `hit_count`：成功匹配次数
- `missed_count`：连续未匹配帧数
- `history`：历史位置列表（保留最近 50 帧）
- `velocity`：速度估计 (vx, vy)
- `dwell_time`：停留时间

---

### 4.3 姿态估计器 (Pose Estimator)

#### 架构

```python
BasePoseEstimator (ABC)
├── YOLOPoseEstimator  # YOLOv8-Pose 实现
└── MockPoseEstimator  # Mock 测试用
```

#### YOLOPoseEstimator

**模型**：YOLOv8n-pose

**输出**：17 个 COCO 关键点（归一化到 0-1 坐标）

```
0: nose            1: left_eye        2: right_eye
3: left_ear        4: right_ear       5: left_shoulder
6: right_shoulder  7: left_elbow      8: right_elbow
9: left_wrist     10: right_wrist    11: left_hip
12: right_hip     13: left_knee      14: right_knee
15: left_ankle    16: right_ankle
```

**PoseSkeleton 数据结构**：
```python
class PoseSkeleton:
    nose: KeyPoint        # {x, y, confidence, visible}
    left_shoulder: KeyPoint
    right_shoulder: KeyPoint
    left_hip: KeyPoint
    right_hip: KeyPoint
    left_wrist: KeyPoint
    right_wrist: KeyPoint
    # ... 共 17 个关键点
```

---

### 4.4 行为识别器 (Behavior Recognizer)

#### 架构

```python
BehaviorRecognizerPipeline
├── PoseFeatureExtractor    # 共享特征提取器
├── FallRecognizer          # 跌倒检测
├── FightRecognizer         # 打架/霸凌检测
├── LoiteringRecognizer     # 徘徊检测
├── SuicideRiskRecognizer   # 疑似轻生检测
├── FenceClimbingRecognizer # 围栏翻越检测
├── SmokingRecognizer       # 吸烟检测
├── PhoneUseRecognizer      # 手机使用检测
├── VandalismRecognizer     # 破坏设施检测
└── CameraBlockingRecognizer # 摄像头遮挡检测
```

**核心设计原则**：使用 16/32/64 帧时序窗口进行行为建模，不允许只看单帧。

#### 4.4.1 共享特征提取器 (PoseFeatureExtractor)

所有识别器共享一个特征提取器，提供两类特征：

**运动特征 (`get_motion_features`)**：

| 特征 | 说明 |
|------|------|
| `velocity_mean` | 平均速度 |
| `velocity_std` | 速度标准差 |
| `velocity_max` | 最大速度 |
| `acceleration_mean` | 平均加速度 |
| `acceleration_max` | 最大加速度 |
| `height_change_ratio` | 高度变化比 |
| `vertical_velocity` | 垂直速度 |

**姿态特征 (`get_pose_features`)**：

| 特征 | 说明 |
|------|------|
| `head_tilt_mean` | 头部倾斜角均值 |
| `head_tilt_std` | 头部倾斜角标准差 |
| `wrist_mouth_dist_mean` | 手腕-嘴部距离均值 |
| `wrist_mouth_dist_min` | 手腕-嘴部距离最小值 |
| `wrist_y_mean` | 手腕 Y 坐标均值 |
| `hip_y_mean` | 髋部 Y 坐标均值 |
| `wrist_above_hip` | 手腕是否在髋部以上 |

#### 4.4.2 跌倒检测 (FallRecognizer)

**时序窗口**：16 帧

**检测条件**（需同时满足）：
1. 高度下降超过 35%（`height_change_ratio > 0.35`）
2. 垂直速度明显（`vertical_velocity > 0.005`）
3. 宽高比变化：从站立（> 1.3）变为躺下（< 1.1）

**触发阈值**：连续 3 帧检测到

**置信度计算**：`min(0.95, 0.6 + height_change_ratio * 0.5)`

#### 4.4.3 打架/霸凌检测 (FightRecognizer)

**时序窗口**：32 帧

**检测条件**（需同时满足）：
1. 两人距离 < 0.25（归一化坐标）
2. 双方都有快速运动（`velocity_mean > 0.012`）
3. 高加速度（`acceleration_max > 0.015`）

**互殴 vs 霸凌区分**：
- 互殴（fighting）：双方速度差异 < 0.008
- 霸凌（bullying）：速度差异明显（一方攻击，一方被动）

**触发阈值**：累积计数 ≥ 10

**角色输出**：
- `aggressor`：攻击者（速度更大的一方）
- `victim`：受害者（速度更小的一方）
- `mutual`：互殴双方

#### 4.4.4 徘徊检测 (LoiteringRecognizer)

**时序窗口**：60 帧

**检测条件**（需同时满足）：
1. 停留时间超过阈值（可配置，默认来自 `settings.DWELL_TIME_THRESHOLD`）
2. 运动范围小于 0.15（归一化坐标距离）

**置信度计算**：`min(0.95, 0.5 + (dwell_time - threshold) / 60)`

#### 4.4.5 疑似轻生检测 (SuicideRiskRecognizer)

**时序窗口**：24 帧（特征），90 帧（静止判断）

**检测条件**（需同时满足）：
1. 长时间静止 ≥ 90 帧（约 3 秒）：`velocity_mean < 0.002`
2. 持续低头 ≥ 45 帧（约 1.5 秒）：`head_tilt_mean < -0.12`

**置信度计算**：`min(0.95, 0.6 + still_frames * 0.002 + |head_tilt| * 0.5)`

#### 4.4.6 围栏翻越检测 (FenceClimbingRecognizer)

**时序窗口**：48 帧

**检测条件**：
1. 垂直运动范围 > 0.1
2. 高度变化模式匹配（翻越上升或翻越下降曲线）:
   - 模式1：起始高 → 中段低 → 结束恢复（翻越下降）
   - 模式2：起始正常 → 中段升高 → 结束恢复（翻越上升）

**触发阈值**：累积计数 ≥ 12

#### 4.4.7 吸烟检测 (SmokingRecognizer)

**时序窗口**：24 帧

**检测条件**（需同时满足）：
1. 手腕靠近嘴部（距离 < 0.15）
2. 相对静止（`velocity_mean < 0.008`）
3. 头部倾斜不严重（`head_tilt > -0.18`，区别于手机使用）

**触发阈值**：累积计数 ≥ 30 帧（约 1 秒）

#### 4.4.8 手机使用检测 (PhoneUseRecognizer)

**时序窗口**：24 帧

**检测条件**（需同时满足）：
1. 强烈低头（`head_tilt < -0.15`）
2. 手腕在胸前区域（`wrist_y < hip_y`）
3. 相对静止（`velocity_mean < 0.005`）

**触发阈值**：累积计数 ≥ 48 帧（约 1.5 秒）

#### 4.4.9 破坏设施检测 (VandalismRecognizer)

**时序窗口**：20 帧

**检测条件**（需同时满足）：
1. 人员靠近设施物体（距离 < 0.15）
2. 存在暴力动作（`acceleration_max > 0.02` 或 `velocity_max > 0.025`）

**触发阈值**：累积计数 ≥ 20

#### 4.4.10 摄像头遮挡检测 (CameraBlockingRecognizer)

**检测条件**：
1. 最大目标面积占画面 > 80%
2. 持续 ≥ 15 帧

### 4.5 互斥规则与优先级

#### 互斥行为组

同一组内的行为不会同时输出，高优先级压制低优先级：

| 组别 | 行为 |
|------|------|
| 手部相关（静态） | 吸烟 vs 手机使用 |
| 暴力行为（动态） | 打架 vs 霸凌 vs 破坏设施 |
| 静止行为 | 疑似轻生 vs 徘徊 |
| 身体姿态剧变 | 跌倒 vs 翻越围栏 |

#### 优先级排序

| 行为 | 优先级 |
|------|--------|
| 打架 / 霸凌 | 100（最高） |
| 跌倒 / 疑似轻生 | 90 |
| 破坏设施 | 80 |
| 翻越围栏 | 70 |
| 吸烟 / 手机使用 | 60 |
| 摄像头遮挡 | 50 |
| 徘徊 | 40（最低） |

#### 动态/静态压制

当检测到**动态行为**（打架、霸凌、跌倒、破坏、翻越）时，自动压制所有**静态行为**（吸烟、手机使用、疑似轻生）。

---

### 4.5 规则引擎 (Rule Engine)

#### 架构

```python
RuleEngine
├── ROIChecker            # 区域入侵检测
├── ForbiddenAreaChecker  # 禁区检测
├── DwellTimeChecker      # 停留超时检测
└── CrossingLineChecker   # 越线检测
```

#### 规则配置 (RuleConfig)

```python
class RuleConfig(BaseModel):
    rule_id: str                                    # 规则 ID
    rule_name: str                                  # 规则名称
    rule_type: RuleType                             # ROI/FORBIDDEN_AREA/DWELL_TIME/CROSSING_LINE
    enabled: bool = True                            # 是否启用
    polygon: List[Tuple[float, float]]              # 区域多边形（归一化坐标）
    line: List[Tuple[float, float]]                 # 越线定义
    threshold: float = 10.0                         # 阈值（停留时间秒数等）
    severity: Severity = Severity.MEDIUM            # 严重级别
    stream_id: str                                  # 关联流
```

#### 规则类型说明

| 类型 | 说明 | 判断逻辑 |
|------|------|---------|
| `ROI` | 区域入侵 | 人员中心点落入多边形区域（Shapely contains） |
| `FORBIDDEN_AREA` | 禁区检测 | 同 ROI，语义为禁止进入 |
| `DWELL_TIME` | 停留超时 | track.dwell_time > threshold |
| `CROSSING_LINE` | 越线检测 | 前后帧轨迹线段与定义线段相交（Shapely crosses） |

---

### 4.6 事件聚合器 (Event Aggregator)

**职责**：将连续的行为识别结果聚合为事件，避免同一行为重复产生大量事件。

**核心机制**：
- 时间窗口去重
- 行为结果和规则触发统一处理
- 关联 track 和 participants 信息
- 支持事件结束（flush）

---

## 5. 数据模型

### 5.1 核心数据结构

```python
# 边界框（归一化坐标 0-1）
class BoundingBox:
    x: float          # 左上角 x
    y: float          # 左上角 y
    width: float      # 宽度
    height: float     # 高度

# 检测结果
class Detection:
    class_name: str        # 类别名
    class_id: int          # 类别 ID
    confidence: float      # 置信度
    bbox: BoundingBox      # 边界框
    track_id: str          # 跟踪 ID（由 Tracker 分配）
    pose: PoseSkeleton     # 姿态（由 PoseEstimator 填充）

# 关键点
class KeyPoint:
    x: float               # 归一化 x 坐标
    y: float               # 归一化 y 坐标
    confidence: float      # 置信度
    visible: bool          # 是否可见

# 跟踪轨迹
class Track:
    track_id: str          # 轨迹 ID
    class_name: str        # 类别名
    history: List[dict]    # 历史帧记录
    velocity: dict         # 速度 {vx, vy}
    trajectory: List[BoundingBox]  # 轨迹
    dwell_time: float      # 停留时间（秒）
    pose_history: List[PoseSkeleton]  # 姿态历史

# 行为识别结果
class BehaviorResult:
    behavior_type: EventType     # 行为类型
    category: EventCategory      # 类别
    confidence: float            # 置信度
    window_size: int             # 使用的时序窗口大小
    temporal_scores: dict        # 各窗口分数
    evidence: dict               # 证据信息

# 行为事件（最终输出）
class BehaviorEvent:
    event_id: str
    stream_id: str
    event_type: EventType
    category: EventCategory
    severity: Severity
    confidence: float
    start_time: datetime
    end_time: datetime
    participants: List[Participant]
    roles: List[RoleAssignment]

# 参与者角色
class ParticipantRole(str, Enum):
    AGGRESSOR = "aggressor"      # 攻击者
    VICTIM = "victim"            # 受害者
    BYSTANDER = "bystander"      # 旁观者
    MUTUAL = "mutual"            # 互殴参与者
```

### 5.2 事件类型枚举

```python
class EventType(str, Enum):
    FIGHTING = "fighting"              # 打架斗殴
    BULLYING = "bullying"              # 校园霸凌
    FALLING = "falling"                # 跌倒/昏厥
    SUICIDE_RISK = "suicide_risk"      # 疑似轻生
    VANDALISM = "vandalism"            # 破坏公共设施
    SMOKING = "smoking"                # 吸烟
    PHONE_USE = "phone_use"            # 手机使用
    CAMERA_BLOCKING = "camera_blocking" # 摄像头遮挡
    LOITERING = "loitering"            # 异常徘徊
    INTRUSION = "intrusion"            # 闯入限制区域
    FENCE_CLIMBING = "fence_climbing"  # 翻越围栏
```

## 6. C++ 流媒体核心 (Stream Core)

### 6.1 项目结构

```
services/stream-core/
├── CMakeLists.txt                    # CMake 构建配置
├── README.md
├── include/stream_core/             # 头文件
│   ├── bounded_queue.hpp            # 有界队列
│   ├── c_api.hpp                    # C 语言 API
│   ├── clip_exporter.hpp            # 切片导出器
│   ├── ffmpeg_decoder.hpp           # FFmpeg 解码器
│   ├── metrics_collector.hpp        # 指标收集器
│   ├── reconnect_controller.hpp     # 重连控制器
│   ├── ring_buffer.hpp              # 环形缓冲区
│   ├── stream_manager.hpp           # 流管理器
│   ├── stream_session.hpp           # 流会话
│   ├── thread_pool.hpp              # 固定线程池
│   └── types.hpp                    # 类型定义
├── src/                              # 源文件
│   ├── main.cpp                     # 主程序入口
│   ├── bounded_queue.cpp
│   ├── c_api.cpp
│   ├── clip_exporter.cpp
│   ├── ffmpeg_decoder.cpp
│   ├── metrics_collector.cpp
│   ├── reconnect_controller.cpp
│   ├── stream_manager.cpp
│   ├── stream_session.cpp
│   ├── thread_pool.cpp
│   └── types.cpp
├── tests/                            # 测试
│   ├── CMakeLists.txt
│   ├── stream_core_tests.cpp
│   ├── test_bounded_queue.cpp
│   ├── test_stream_lifecycle.cpp
│   └── test_thread_pool.cpp
└── bindings/python/
    └── stream_core.py               # Python ctypes 绑定
```

### 6.2 核心组件

| 组件 | 职责 | 关键特性 |
|------|------|---------|
| `StreamManager` | 管理最多 20 路流 | 线程安全、全局指标聚合 |
| `StreamSession` | 单路流生命周期 | 状态机、双线程模型（Ingest + Process） |
| `FFmpegDecoder` | 视频解码 | 支持 RTSP/RTMP/文件输入 |
| `ThreadPool` | 固定线程池 | 8 线程、任务队列 |
| `BoundedQueue` | 有界队列 | 背压策略、满时丢旧帧 |
| `RingBuffer` | 环形缓冲区 | 30秒滑动窗口 |
| `ReconnectController` | 重连控制 | 指数退避（1s→2s→4s→8s，最大30s，最多5次） |
| `ClipExporter` | 切片导出 | 异常事件视频导出 |
| `MetricsCollector` | 指标收集 | FPS/延迟/丢帧/码率 |

### 6.3 线程模型

```
StreamSession 双线程模型：

┌─────────────┐     ┌──────────────┐
│ Ingest Thread│ ──→ │ BoundedQueue │ ──→ Process Thread
│  (FFmpeg解码) │     │  (有界,背压)  │     (AI推理/缓存)
└─────────────┘     └──────────────┘
                                          │
                                          ▼
                                    ┌──────────┐
                                    │RingBuffer│
                                    │(30s环形) │
                                    └──────────┘
```

**关键约束**：Ingest 线程不得因慢推理阻塞。

### 6.4 状态机

```
INIT → CONNECTING → RUNNING ←──────────┐
              ↓         │               │
              ↓    DEGRADED             │
              ↓         │               │
              └──→ ERROR ─→ RECONNECTING ┘
                          ↓
                    STOPPED
```

### 6.5 背压策略

当 `BoundedQueue` 满时：
1. 丢弃新帧（默认策略）
2. 增加 `dropped_frames` 计数
3. 记录日志
4. 可选降级到更低帧率

### 6.6 构建说明

```bash
cd services/stream-core
mkdir -p build && cd build
cmake ..
make -j$(nproc)

# 运行测试
ctest --output-on-failure

# MinGW 构建（Windows）
mkdir build_mingw && cd build_mingw
cmake -G "MinGW Makefiles" ..
mingw32-make
```

**依赖**：
- CMake >= 3.20
- C++20 编译器
- FFmpeg 开发库（libavcodec, libavformat, libavutil, libswscale）

### 6.7 Python 绑定

通过 `ctypes` 调用 C API：

```python
# bindings/python/stream_core.py
import ctypes

lib = ctypes.CDLL("campus_guard_stream.dll")  # 或 .so

# 创建管理器
handle = lib.cg_stream_manager_create(20, 8)

# 创建并启动流
lib.cg_stream_create(handle, config, stream_id)
lib.cg_stream_start(handle, stream_id)

# 获取指标
lib.cg_stream_get_metrics(handle, stream_id, ctypes.byref(metrics))
```

## 7. 性能指标

### 7.1 目标性能

| 指标 | 目标 |
|------|------|
| 单路 1080P 延迟 | < 300ms |
| 最大并发流数 | 20 路 |
| 长时间运行稳定性 | ≥ 1 小时 |
| 队列容量 | 可配置（默认 100） |

### 7.2 指标采集

| 指标 | 说明 | 采集方式 |
|------|------|---------|
| fps | 实际帧率 | 解码器统计 |
| queue_depth | 队列深度 | 实时查询 |
| dropped_frames | 丢帧数 | 背压触发时累加 |
| decode_latency_ms | 解码延迟 | 处理时间测量 |
| reconnect_count | 重连次数 | 重连控制器 |
| uptime | 运行时间 | 启动时间戳计算 |
| bitrate_kbps | 码率 | 字节数/时间 |

## 8. ONNX 模型导出

### 8.1 导出流程

```python
from ai_runtime.models.onnx_exporter import export_to_onnx

# 将 PyTorch 模型导出为 ONNX
export_to_onnx(
    model_path="models/yolov8n.pt",
    output_path="models/yolov8n.onnx",
    input_size=(1, 3, 640, 640)
)
```

### 8.2 ONNX Runtime 推理

支持通过 ONNX Runtime 加载和推理，提供跨平台部署能力。

## 9. 测试与演示

### 9.1 测试视频素材

```
sucai/
├── 打架.mp4          # 打架斗殴场景
├── 校园霸凌.mp4       # 校园霸凌场景
├── 摔倒.mp4          # 跌倒检测场景
├── 轻生.mp4          # 疑似轻生场景
├── 翻越围栏.mp4       # 翻越围栏场景
├── 吸烟.mp4          # 吸烟检测场景
├── 低头看手机.mp4     # 手机使用场景
├── 摄像头遮挡.mp4     # 摄像头遮挡场景
├── 异常徘徊.mp4       # 异常徘徊场景
├── 破坏公共设施.mp4    # 破坏设施场景
└── output/           # 检测结果视频输出
```

### 9.2 演示脚本

```bash
# 单视频测试
python services/ai-runtime/test_single_video.py

# 行为检测演示
python services/ai-runtime/demo_behavior_detection.py

# 完整演示
python services/ai-runtime/demo_final.py
```

### 9.3 性能压测

```bash
# 单路压测
python scripts/benchmark_single.py

# 多路压测
python scripts/benchmark_multi.py

# WebSocket 压测
python scripts/benchmark_websocket.py

# 全量压测
python scripts/benchmark_all.py
```

## 10. 开发指南

### 10.1 添加新的行为识别器

1. 在 `behavior_recognizer.py` 中创建继承 `BaseRecognizer` 的类
2. 实现 `recognize(tracks: List[Track]) -> List[BehaviorResult]` 方法
3. 在 `BehaviorRecognizerPipeline.__init__` 中注册
4. 在 `MUTUALLY_EXCLUSIVE_GROUPS` 中添加互斥关系
5. 在 `BEHAVIOR_PRIORITY` 中设置优先级
6. 在 `EventType` 枚举中添加新类型

### 10.2 添加新的规则类型

1. 在 `RuleType` 枚举中添加新类型
2. 创建继承 `BaseRuleChecker` 的类
3. 实现 `check(tracks, config) -> Optional[RuleTrigger]` 方法
4. 在 `RuleEngine.__init__` 的 `checkers` 字典中注册

### 10.3 切换真实模型

```python
# 使用真实模型
pipeline = create_pipeline(use_real_models=True, device="cuda")
# 等价于：
pipeline = AIPipeline(
    detector_type="yolo",
    tracker_type="bytetrack",
    pose_type="yolo",
    device="cuda"
)
```

### 10.4 自定义模型路径

修改 `config.py` 中的 `MODEL_PATH` 配置，或通过环境变量覆盖。
