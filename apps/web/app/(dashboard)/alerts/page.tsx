'use client';

import { useEffect, useState, useRef } from 'react';
import { AlertTriangle, CheckCircle, Clock, Video, X, Bell, Wifi, WifiOff } from 'lucide-react';
import apiClient from '@/lib/api';

// Fake 告警数据（后端未连接时兜底）
const FAKE_ALERTS = [
  { id: 'a1', event_id: 'e1', severity: 'high', title: '打架斗殴检测', message: '检测到 stream_004 区域内发生打架斗殴行为，已持续 12 秒', timestamp: new Date(Date.now() - 2 * 60000).toISOString(), stream_id: 'stream_004', stream_name: '打架斗殴检测', acknowledged: false },
  { id: 'a2', event_id: 'e2', severity: 'high', title: '校园霸凌检测', message: '检测到 stream_007 区域存在霸凌行为，涉及多名学生', timestamp: new Date(Date.now() - 8 * 60000).toISOString(), stream_id: 'stream_007', stream_name: '校园霸凌检测', acknowledged: false },
  { id: 'a3', event_id: 'e3', severity: 'high', title: '疑似轻生检测', message: '检测到 stream_010 区域学生行为异常，请立即关注', timestamp: new Date(Date.now() - 15 * 60000).toISOString(), stream_id: 'stream_010', stream_name: '疑似轻生检测', acknowledged: false },
  { id: 'a4', event_id: 'e4', severity: 'medium', title: '吸烟行为检测', message: '检测到 stream_002 区域有学生吸烟', timestamp: new Date(Date.now() - 25 * 60000).toISOString(), stream_id: 'stream_002', stream_name: '吸烟检测', acknowledged: false },
  { id: 'a5', event_id: 'e5', severity: 'high', title: '摔倒检测', message: 'stream_006 区域检测到学生摔倒，请及时确认情况', timestamp: new Date(Date.now() - 35 * 60000).toISOString(), stream_id: 'stream_006', stream_name: '摔倒检测', acknowledged: false },
  { id: 'a6', event_id: 'e6', severity: 'medium', title: '摄像头遮挡告警', message: 'stream_005 摄像头疑似被遮挡，画面异常', timestamp: new Date(Date.now() - 50 * 60000).toISOString(), stream_id: 'stream_005', stream_name: '摄像头遮挡检测', acknowledged: false },
  { id: 'a7', event_id: 'e7', severity: 'low', title: '异常徘徊检测', message: 'stream_003 区域检测到人员在敏感区域徘徊超过 5 分钟', timestamp: new Date(Date.now() - 70 * 60000).toISOString(), stream_id: 'stream_003', stream_name: '异常徘徊检测', acknowledged: true },
  { id: 'a8', event_id: 'e8', severity: 'high', title: '破坏公共设施', message: 'stream_008 区域检测到破坏公共设施行为', timestamp: new Date(Date.now() - 90 * 60000).toISOString(), stream_id: 'stream_008', stream_name: '破坏公共设施检测', acknowledged: true },
  { id: 'a9', event_id: 'e9', severity: 'low', title: '翻越围栏检测', message: 'stream_009 区域检测到学生翻越围栏', timestamp: new Date(Date.now() - 120 * 60000).toISOString(), stream_id: 'stream_009', stream_name: '翻越围栏检测', acknowledged: true },
];

interface Alert {
  id: string;
  event_id: string;
  severity: string;
  title: string;
  message: string;
  timestamp: string;
  stream_id: string;
  stream_name: string;
  acknowledged?: boolean;
}

export default function AlertsPage() {
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [wsConnected, setWsConnected] = useState(false);
  const [loading, setLoading] = useState(true);
  const wsRef = useRef<WebSocket | null>(null);
  const useFake = useRef(false);

  useEffect(() => {
    fetchAlerts();
    connectWebSocket();
    return () => {
      if (wsRef.current) wsRef.current.close();
    };
  }, []);

  const fetchAlerts = async () => {
    try {
      setLoading(true);
      const response = await apiClient.get('/demo/alerts') as { code: number; data: { items: Alert[] } };
      if (response.code === 0) {
        setAlerts(response.data.items);
        useFake.current = false;
      }
    } catch {
      // 降级到普通API
      try {
        const response = await apiClient.get('/alerts') as { code: number; data: { items: Alert[] } };
        if (response.code === 0) {
          setAlerts(response.data.items);
          useFake.current = false;
        }
      } catch {
        // 使用 fake 数据
        setAlerts(FAKE_ALERTS);
        useFake.current = true;
      }
    } finally {
      setLoading(false);
    }
  };

  const connectWebSocket = () => {
    const wsUrl = process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8888/ws';
    try {
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;
      ws.onopen = () => {
        setWsConnected(true);
        ws.send(JSON.stringify({ type: 'subscribe', channels: ['alerts'] }));
      };
      ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        if (data.type === 'alert') {
          setAlerts((prev) => [data.data, ...prev].slice(0, 50));
        }
      };
      ws.onclose = () => {
        setWsConnected(false);
        setTimeout(connectWebSocket, 3000);
      };
      ws.onerror = () => {
        setWsConnected(false);
      };
    } catch {
      setWsConnected(false);
    }
  };

  const acknowledgeAlert = (alertId: string) => {
    setAlerts((prev) =>
      prev.map((a) => (a.id === alertId ? { ...a, acknowledged: true } : a))
    );
  };

  const getSeverityConfig = (severity: string) => {
    const configs: Record<string, { icon: typeof AlertTriangle; bgColor: string; borderColor: string; iconColor: string; label: string; dotColor: string }> = {
      high: { icon: AlertTriangle, bgColor: 'bg-red-50', borderColor: 'border-red-200', iconColor: 'text-red-600', label: '高风险', dotColor: 'bg-red-500' },
      medium: { icon: AlertTriangle, bgColor: 'bg-orange-50', borderColor: 'border-orange-200', iconColor: 'text-orange-600', label: '中风险', dotColor: 'bg-orange-500' },
      low: { icon: AlertTriangle, bgColor: 'bg-yellow-50', borderColor: 'border-yellow-200', iconColor: 'text-yellow-600', label: '低风险', dotColor: 'bg-yellow-500' },
    };
    return configs[severity] || configs.low;
  };

  const formatTime = (timestamp: string) => {
    const date = new Date(timestamp);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMin = Math.floor(diffMs / 60000);
    if (diffMin < 1) return '刚刚';
    if (diffMin < 60) return `${diffMin} 分钟前`;
    return date.toLocaleString('zh-CN', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
  };

  const unacknowledgedAlerts = alerts.filter((a) => !a.acknowledged);
  const acknowledgedAlerts = alerts.filter((a) => a.acknowledged);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">实时告警</h1>
          <p className="text-sm text-gray-500 mt-1">
            {unacknowledgedAlerts.length} 个未确认告警 | 共 {alerts.length} 条记录
          </p>
        </div>
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-1.5 text-sm">
            {wsConnected ? (
              <>
                <Wifi className="w-4 h-4 text-green-500" />
                <span className="text-green-600">实时推送已连接</span>
              </>
            ) : (
              <>
                <WifiOff className="w-4 h-4 text-gray-400" />
                <span className="text-gray-400">实时推送未连接</span>
              </>
            )}
          </div>
          <button
            onClick={fetchAlerts}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 text-sm"
          >
            刷新
          </button>
        </div>
      </div>

      {useFake.current && (
        <div className="bg-amber-50 border border-amber-200 rounded-lg px-4 py-2 text-sm text-amber-700">
          当前显示演示数据，后端未连接时可正常预览告警功能
        </div>
      )}

      {loading ? (
        <div className="flex items-center justify-center h-64">
          <div className="w-8 h-8 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
        </div>
      ) : alerts.length === 0 ? (
        <div className="bg-white rounded-xl border border-gray-200 p-12 text-center">
          <Bell className="w-12 h-12 text-gray-300 mx-auto mb-4" />
          <p className="text-gray-500">暂无告警</p>
        </div>
      ) : (
        <div className="space-y-4">
          {/* 未确认告警 */}
          {unacknowledgedAlerts.length > 0 && (
            <div>
              <h2 className="text-sm font-semibold text-gray-700 mb-3 flex items-center gap-2">
                <span className="w-2 h-2 bg-red-500 rounded-full animate-pulse" />
                未确认告警 ({unacknowledgedAlerts.length})
              </h2>
              <div className="space-y-3">
                {unacknowledgedAlerts.map((alert) => {
                  const config = getSeverityConfig(alert.severity);
                  const Icon = config.icon;
                  return (
                    <div key={alert.id} className={`${config.bgColor} ${config.borderColor} border rounded-xl p-4`}>
                      <div className="flex items-start gap-4">
                        <div className={`p-2 rounded-lg bg-white ${config.iconColor}`}>
                          <Icon className="w-5 h-5" />
                        </div>
                        <div className="flex-1 min-w-0">
                          <div className="flex items-start justify-between gap-4">
                            <div>
                              <h3 className="font-semibold text-gray-900">{alert.title}</h3>
                              <p className="text-sm text-gray-600 mt-1">{alert.message}</p>
                            </div>
                            <span className={`px-2 py-1 text-xs rounded-full bg-white ${config.iconColor} font-medium`}>
                              {config.label}
                            </span>
                          </div>
                          <div className="flex items-center gap-4 mt-3 text-sm text-gray-500">
                            <span className="flex items-center gap-1">
                              <Video className="w-4 h-4" />
                              {alert.stream_name}
                            </span>
                            <span className="flex items-center gap-1">
                              <Clock className="w-4 h-4" />
                              {formatTime(alert.timestamp)}
                            </span>
                          </div>
                        </div>
                        <button
                          onClick={() => acknowledgeAlert(alert.id)}
                          className="flex items-center gap-1 px-3 py-1.5 bg-white text-gray-700 rounded-lg hover:bg-gray-50 text-sm border border-gray-200"
                        >
                          <CheckCircle className="w-4 h-4" />
                          确认
                        </button>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* 已确认告警 */}
          {acknowledgedAlerts.length > 0 && (
            <div>
              <h2 className="text-sm font-semibold text-gray-700 mb-3">
                已确认告警 ({acknowledgedAlerts.length})
              </h2>
              <div className="space-y-2">
                {acknowledgedAlerts.slice(0, 5).map((alert) => {
                  const config = getSeverityConfig(alert.severity);
                  return (
                    <div key={alert.id} className="bg-gray-50 border border-gray-200 rounded-lg p-3">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-3">
                          <CheckCircle className="w-4 h-4 text-green-500" />
                          <span className="font-medium text-gray-700">{alert.title}</span>
                          <span className="text-sm text-gray-400">{alert.stream_name}</span>
                        </div>
                        <span className="text-sm text-gray-400">{formatTime(alert.timestamp)}</span>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
