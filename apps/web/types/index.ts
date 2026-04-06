/** 类型定义 */

export interface Stream {
  id: string;
  name: string;
  url: string;
  input_type: 'rtsp' | 'rtmp' | 'file';
  status: 'init' | 'connecting' | 'running' | 'degraded' | 'reconnecting' | 'stopped' | 'error';
  status_message?: string;
  target_fps: number;
  max_queue_size: number;
  width?: number;
  height?: number;
  fps?: number;
  location?: string;
  total_frames_decoded: number;
  total_dropped_frames: number;
  reconnect_count: number;
  created_at: string;
  updated_at: string;
}

export interface Event {
  id: string;
  stream_id: string;
  event_type: string;
  category: 'high_risk' | 'sensitive' | 'suspicious' | 'normal';
  severity: 'critical' | 'high' | 'medium' | 'low';
  status: 'pending' | 'confirmed' | 'false_positive' | 'resolved' | 'ignored';
  start_time: string;
  end_time?: string;
  confidence: number;
  participants?: Array<{
    track_id: string;
    bbox: number[];
    confidence: number;
  }>;
  roles?: {
    aggressor?: string[];
    victim?: string[];
    bystander?: string[];
    mutual?: string[];
  };
  location?: string;
  snapshot_url?: string;
  clip_id?: string;
  reviewed_by?: string;
  reviewed_at?: string;
  review_comment?: string;
  created_at: string;
}

export interface Alert {
  id: string;
  event_type: string;
  severity: 'critical' | 'high' | 'medium' | 'low';
  message: string;
  stream_id: string;
  stream_name?: string;
  timestamp: string;
  is_read: boolean;
}

export interface DashboardStats {
  total_streams: number;
  active_streams: number;
  total_events_7d: number;
  pending_reviews: number;
  event_trend: Record<string, { total: number; critical: number; high: number }>;
  event_types: Record<string, number>;
  stream_status: Record<string, number>;
}

export interface ApiResponse<T> {
  code: number;
  message: string;
  data: T;
}

export interface PaginatedData<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}
