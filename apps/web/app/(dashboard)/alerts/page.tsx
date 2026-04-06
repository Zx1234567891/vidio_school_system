'use client';

import { useEffect, useState, useRef } from 'react';
import { AlertTriangle, CheckCircle, Clock, Video, X } from 'lucide-react';
import apiClient from '@/lib/api';

interface Alert {
  id: string;
  event_id: string;
  severity: 'high' | 'medium' | 'low';
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

  useEffect(() => {
    fetchAlerts();
    connectWebSocket();

    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, []);

  const fetchAlerts = async () => {
    try {
      setLoading(true);
      const response = await apiClient.get('/demo/alerts') as { code: number; data: { items: Alert[] } };
      if (response.code === 0) {
        setAlerts(response.data.items);
      }
    } catch (err) {
      // 尝试普通API
      try {
        const response = await apiClient.get('/alerts') as { code: number; data: { items: Alert[] } };
        if (response.code === 0) {
          setAlerts(response.data.items);
        }
      } catch (err2) {
        console.error('获取告警失败:', err2);
      }
    } finally {
      setLoading(false);
    }
  };

  const connectWebSocket = () => {
    const wsUrl = process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8080/ws';

    try {
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        console.log('WebSocket已连接');
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
        console.log('WebSocket已断开');
        setWsConnected(false);
        // 3秒后重连
        setTimeout(connectWebSocket, 3000);
      };

      ws.onerror = (error) => {
        console.error('WebSocket错误:', error);
      };
    } catch (err) {
      console.error('WebSocket连接失败:', err);
    }
  };

  const acknowledgeAlert = (alertId: string) => {
    setAlerts((prev) =>
      prev.map((a) =>
        a.id === alertId ? { ...a, acknowledged: true } : a
      )
    );
  };

  const getSeverityConfig = (severity: string) => {
    const configs = {
      high: {
        icon: AlertTriangle,
        bgColor: 'bg-red-50',
        borderColor: 'border-red-200',
        iconColor: 'text-red-600',
        label: '高风险',
      },
      medium: {
        icon: AlertTriangle,
        bgColor: 'bg-orange-50',
        borderColor: 'border-orange-200',
        iconColor: 'text-orange-600',
        label: '中风险',
      },
      low: {
        icon: AlertTriangle,
        bgColor: 'bg-yellow-50',
        borderColor: 'border-yellow-200',
        iconColor: 'text-yellow-600',
        label: '低风险',
      },
    };
    return configs[severity as keyof typeof configs] || configs.low;
  };

  const formatTime = (timestamp: string) => {
    const date = new Date(timestamp);
    return date.toLocaleString('zh-CN', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    });
  };

  const unacknowledgedAlerts = alerts.filter((a) => !a.acknowledged);
  const acknowledgedAlerts = alerts.filter((a) => a.acknowledged);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">实时告警</h1>
          <p className="text-sm text-gray-500 mt-1">
            {unacknowledgedAlerts.length} 个未确认告警 | {' '}
            <span className={wsConnected ? 'text-green-600' : 'text-red-600'}>
              {wsConnected ? 'WebSocket已连接' : 'WebSocket未连接'}
            </span>
          </p>
        </div>
        <button
          onClick={fetchAlerts}
          className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
        >
          刷新
        </button>
      </div>

      {loading ? (
        <div className="flex items-center justify-center h-64">
          <div className="text-gray-500">加载中...</div>
        </div>
      ) : alerts.length === 0 ? (
        <div className="bg-white rounded-xl border border-gray-200 p-12 text-center">
          <AlertTriangle className="w-12 h-12 text-gray-300 mx-auto mb-4" />
          <p className="text-gray-500">暂无告警</p>
          <p className="text-sm text-gray-400 mt-2">
            {wsConnected ? '等待新的告警事件...' : 'WebSocket未连接，无法接收实时告警'}
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          {/* 未确认告警 */}
          {unacknowledgedAlerts.length > 0 && (
            <div>
              <h2 className="text-sm font-medium text-gray-700 mb-3">
                未确认告警 ({unacknowledgedAlerts.length})
              </h2>
              <div className="space-y-3">
                {unacknowledgedAlerts.map((alert) => {
                  const config = getSeverityConfig(alert.severity);
                  const Icon = config.icon;

                  return (
                    <div
                      key={alert.id}
                      className={`${config.bgColor} ${config.borderColor} border rounded-xl p-4`}
                    >
                      <div className="flex items-start gap-4">
                        <div className={`p-2 rounded-lg bg-white ${config.iconColor}`}>
                          <Icon className="w-6 h-6" />
                        </div>
                        <div className="flex-1 min-w-0">
                          <div className="flex items-start justify-between gap-4">
                            <div>
                              <h3 className="font-semibold text-gray-900">{alert.title}</h3>
                              <p className="text-sm text-gray-600 mt-1">{alert.message}</p>
                            </div>
                            <span className={`px-2 py-1 text-xs rounded-full bg-white ${config.iconColor}`}>
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
                          className="flex items-center gap-1 px-3 py-1.5 bg-white text-gray-700 rounded-lg hover:bg-gray-50 text-sm"
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
              <h2 className="text-sm font-medium text-gray-700 mb-3">
                已确认告警 ({acknowledgedAlerts.length})
              </h2>
              <div className="space-y-2">
                {acknowledgedAlerts.slice(0, 5).map((alert) => (
                  <div
                    key={alert.id}
                    className="bg-gray-50 border border-gray-200 rounded-lg p-3 opacity-60"
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        <CheckCircle className="w-4 h-4 text-green-600" />
                        <span className="font-medium text-gray-700">{alert.title}</span>
                        <span className="text-sm text-gray-500">{alert.stream_name}</span>
                      </div>
                      <span className="text-sm text-gray-400">{formatTime(alert.timestamp)}</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
