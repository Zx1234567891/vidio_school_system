/**
 * Campus Guard AI - 统一类型定义
 *
 * 所有模块必须围绕此 Schema 协作
 */

// ============ 基础枚举 ============

export type Severity = "low" | "medium" | "high" | "critical";

export type ReviewStatus = "pending" | "approved" | "rejected" | "modified";

export type StreamStatus =
  | "init"
  | "connecting"
  | "running"
  | "degraded"
  | "reconnecting"
  | "stopped"
  | "error";

export type ParticipantRole = "aggressor" | "victim" | "bystander" | "mutual";

export type EventCategory =
  | "high_risk"
  | "management_sensitive"
  | "suspicious"
  | "normal";

export type EventType =
  // 高风险
  | "fighting"
  | "bullying"
  | "falling"
  | "suicide_risk"
  | "vandalism"
  // 管理敏感
  | "smoking"
  | "phone_use"
  | "camera_blocking"
  // 可疑行为
  | "loitering"
  | "prolonged_stay"
  | "fence_climbing"
  | "intrusion"
  // 正常
  | "person_detected"
  | "normal_walking"
  | "crowd_gathering";

export type RuleType =
  | "roi"
  | "forbidden_area"
  | "dwell_time"
  | "trajectory"
  | "crossing_line"
  | "speed"
  | "crowd";

// ============ 基础结构 ============

export interface BoundingBox {
  x: number;
  y: number;
  width: number;
  height: number;
}

export interface KeyPoint {
  x: number;
  y: number;
  confidence: number;
  visible: boolean;
}

export interface PoseSkeleton {
  nose?: KeyPoint;
  left_eye?: KeyPoint;
  right_eye?: KeyPoint;
  left_ear?: KeyPoint;
  right_ear?: KeyPoint;
  left_shoulder?: KeyPoint;
  right_shoulder?: KeyPoint;
  left_elbow?: KeyPoint;
  right_elbow?: KeyPoint;
  left_wrist?: KeyPoint;
  right_wrist?: KeyPoint;
  left_hip?: KeyPoint;
  right_hip?: KeyPoint;
  left_knee?: KeyPoint;
  right_knee?: KeyPoint;
  left_ankle?: KeyPoint;
  right_ankle?: KeyPoint;
}

// ============ 检测与跟踪 ============

export interface Detection {
  class_name: string;
  class_id: number;
  confidence: number;
  bbox: BoundingBox;
  track_id?: string;
  pose?: PoseSkeleton;
}

export interface Track {
  track_id: string;
  class_name: string;
  history: Array<{
    frame: number;
    bbox: number[];
    confidence: number;
  }>;
  velocity?: { vx: number; vy: number };
  trajectory: BoundingBox[];
  pose_history: Array<PoseSkeleton | null>;
  first_seen?: string;
  last_seen?: string;
  dwell_time: number;
  dwell_zones: Record<string, number>;
}

// ============ 角色与参与者 ============

export interface RoleAssignment {
  track_id: string;
  role: ParticipantRole;
  confidence: number;
  reasoning?: string;
}

export interface Participant {
  track_id: string;
  person_id?: string;
  bbox?: BoundingBox;
  bbox_history: BoundingBox[];
  pose?: PoseSkeleton;
  role?: ParticipantRole;
  features: Record<string, unknown>;
}

// ============ 规则触发 ============

export interface RuleTrigger {
  rule_type: RuleType;
  rule_id: string;
  rule_name: string;
  triggered_by: string[];
  details: Record<string, unknown>;
}

// ============ 行为识别结果 ============

export interface BehaviorResult {
  behavior_type: EventType;
  category: EventCategory;
  confidence: number;
  window_size: number;
  temporal_scores: Record<number, number>;
  interaction_features: Record<string, unknown>;
  pose_features: Record<string, unknown>;
  evidence: Record<string, unknown>;
}

// ============ 核心事件结构 ============

export interface BehaviorEvent {
  event_id: string;
  stream_id: string;
  event_type: EventType;
  category: EventCategory;
  severity: Severity;
  confidence: number;
  timestamp: string;
  start_time?: string;
  end_time?: string;
  duration: number;
  track_ids: string[];
  participants: Participant[];
  roles: RoleAssignment[];
  behavior_result?: BehaviorResult;
  rule_trigger?: RuleTrigger;
  source_frame_ref?: string;
  clip_ref?: string;
  key_frame_refs: string[];
  review_status: ReviewStatus;
  reviewer_note?: string;
  reviewed_by?: string;
  reviewed_at?: string;
  metadata: Record<string, unknown>;
}

// ============ Pipeline 结果 ============

export interface DetectionFrameResult {
  frame_id: string;
  stream_id: string;
  timestamp_ms: number;
  width: number;
  height: number;
  detections: Detection[];
  processing_time_ms: number;
}

export interface PipelineResult {
  frame_result: DetectionFrameResult;
  tracks: Track[];
  events: BehaviorEvent[];
  rule_triggers: RuleTrigger[];
  total_processing_time_ms: number;
}

// ============ 流相关 ============

export interface StreamInput {
  type: "rtsp" | "rtmp" | "file";
  url: string;
}

export interface Stream {
  id: string;
  name: string;
  input: StreamInput;
  status: StreamStatus;
  enabled: boolean;
  createdAt: string;
  updatedAt: string;
  metrics?: StreamMetrics;
}

export interface StreamMetrics {
  fps: number;
  queueDepth: number;
  droppedFrames: number;
  decodeLatencyMs: number;
  reconnectCount: number;
  uptime: number;
}

// ============ 系统相关 ============

export interface SystemMetrics {
  cpuPercent: number;
  memoryPercent: number;
  diskUsagePercent: number;
  activeStreams: number;
  totalEventsToday: number;
  alertsPending: number;
  timestamp: string;
}

export interface WebSocketMessage {
  type: "alert" | "status" | "heartbeat" | "echo";
  payload: unknown;
  timestamp: string;
}

export interface ApiResponse<T> {
  success: boolean;
  data?: T;
  error?: {
    code: string;
    message: string;
    details?: unknown;
  };
  meta?: {
    page?: number;
    pageSize?: number;
    total?: number;
  };
}

// ============ 规则配置 ============

export interface RuleConfig {
  rule_id: string;
  rule_name: string;
  rule_type: RuleType;
  enabled: boolean;
  polygon?: Array<[number, number]>;
  line?: Array<[number, number]>;
  threshold: number;
  severity: Severity;
  stream_id?: string;
}
