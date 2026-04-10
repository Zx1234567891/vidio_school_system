'use client';

import { useEffect, useState } from 'react';
import { AlertTriangle, Video, Activity, Clock, TrendingUp, Users, Wifi, WifiOff } from 'lucide-react';
import apiClient from '@/lib/api';

const FAKE_STATS = {
  total_streams: 10,
  active_streams: 3,
  total_events: 56,
  total_alerts: 19,
  unacknowledged_alerts: 5,
  pending_reviews: 5,
  severity_distribution: { high: 8, medium: 6, low: 3 },
};

const FAKE_EVENTS = [
  { id: 'e1', stream_name: '打架斗殴检测', behavior_label: '打架斗殴', severity: 'high', timestamp: new Date(Date.now() - 2 * 60000).toISOString(), confidence: 0.94 },
  { id: 'e2', stream_name: '校园霸凌检测', behavior_label: '校园霸凌', severity: 'high', timestamp: new Date(Date.now() - 8 * 60000).toISOString(), confidence: 0.89 },
  { id: 'e3', stream_name: '疑似轻生检测', behavior_label: '疑似轻生', severity: 'high', timestamp: new Date(Date.now() - 15 * 60000).toISOString(), confidence: 0.76 },
  { id: 'e4', stream_name: '吸烟检测', behavior_label: '吸烟', severity: 'medium', timestamp: new Date(Date.now() - 25 * 60000).toISOString(), confidence: 0.87 },
  { id: 'e5', stream_name: '摔倒检测', behavior_label: '摔倒', severity: 'high', timestamp: new Date(Date.now() - 35 * 60000).toISOString(), confidence: 0.91 },
];

interface DashboardStats {
  total_streams: number;
  active_streams: number;
  total_events: number;
  total_alerts: number;
  unacknowledged_alerts: number;
  pending_reviews: number;
  severity_distribution: { high: number; medium: number; low: number };
}

interface RecentEvent {
  id: string;
  stream_name: string;
  behavior_label: string;
  severity: string;
  timestamp: string;
  confidence: number;
}

export default function OverviewPage() {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [recentEvents, setRecentEvents] = useState<RecentEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [wsConnected, setWsConnected] = useState(false);
  const useFake = useState(false);

  useEffect(() => {
    fetchDashboardData();
  }, []);

  const fetchDashboardData = async () => {
    try {
      setLoading(true);
      const statsRes = await apiClient.get('/demo/stats') as { code: number; data: DashboardStats };
      if (statsRes.code === 0) {
        setStats(statsRes.data);
      }
      const eventsRes = await apiClient.get('/demo/events?limit=5') as { code: number; data: { items: RecentEvent[] } };
      if (eventsRes.code === 0) {
        setRecentEvents(eventsRes.data.items);
      }
    } catch {
      // 降级到 fake 数据
      setStats(FAKE_STATS);
      setRecentEvents(FAKE_EVENTS);
    } finally {
      setLoading(false);
    }
  };

  const getSeverityColor = (severity: string) => {
    const colors: Record<string, string> = {
      high: 'text-red-600 bg-red-50',
      medium: 'text-orange-600 bg-orange-50',
      low: 'text-yellow-600 bg-yellow-50',
    };
    return colors[severity] || 'text-gray-600 bg-gray-50';
  };

  const getSeverityLabel = (severity: string) => {
    const labels: Record<string, string> = { high: '高风险', medium: '中风险', low: '低风险' };
    return labels[severity] || severity;
  };

  const formatTime = (timestamp: string) => {
    const date = new Date(timestamp);
    return date.toLocaleString('zh-CN', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
  };

  const statCards = [
    { title: '总视频流', value: stats?.total_streams || 0, subValue: `${stats?.active_streams || 0} 运行中`, icon: Video, color: 'blue' },
    { title: '检测事件', value: stats?.total_events || 0, subValue: `${stats?.pending_reviews || 0} 待审核`, icon: TrendingUp, color: 'purple' },
    { title: '实时告警', value: stats?.unacknowledged_alerts || 0, subValue: `共 ${stats?.total_alerts || 0} 个`, icon: AlertTriangle, color: 'orange' },
    { title: '系统状态', value: '正常', subValue: '演示模式', icon: Activity, color: 'green' },
  ];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">系统概览</h1>
        <p className="text-sm text-gray-500 mt-1">实时监控校园安防状态 · 演示模式</p>
      </div>

      {/* 统计卡片 */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {statCards.map((card) => {
          const Icon = card.icon;
          const colorMap: Record<string, string> = {
            blue: 'bg-blue-50 text-blue-600',
            orange: 'bg-orange-50 text-orange-600',
            green: 'bg-green-50 text-green-600',
            purple: 'bg-purple-50 text-purple-600',
          };
          const colorClass = colorMap[card.color] || '';
          return (
            <div key={card.title} className="bg-white p-6 rounded-xl border border-gray-200">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-gray-500">{card.title}</p>
                  <p className="text-2xl font-bold text-gray-900 mt-1">{card.value}</p>
                  <p className="text-xs text-gray-400 mt-1">{card.subValue}</p>
                </div>
                <div className={`p-3 rounded-lg ${colorClass}`}>
                  <Icon className="w-6 h-6" />
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* 风险分布 + 最近事件并排 */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* 风险分布 */}
        {stats?.severity_distribution && (
          <div className="bg-white p-6 rounded-xl border border-gray-200">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">事件风险分布</h2>
            <div className="space-y-3">
              {[
                { key: 'high', label: '高风险', color: 'bg-red-500', count: stats.severity_distribution.high },
                { key: 'medium', label: '中风险', color: 'bg-orange-500', count: stats.severity_distribution.medium },
                { key: 'low', label: '低风险', color: 'bg-yellow-500', count: stats.severity_distribution.low },
              ].map((item) => {
                const total = stats.severity_distribution.high + stats.severity_distribution.medium + stats.severity_distribution.low;
                const pct = total > 0 ? (item.count / total * 100).toFixed(1) : '0';
                return (
                  <div key={item.key}>
                    <div className="flex items-center justify-between text-sm mb-1">
                      <span className="text-gray-600">{item.label}</span>
                      <span className="font-medium text-gray-900">{item.count} 个</span>
                    </div>
                    <div className="w-full bg-gray-100 rounded-full h-2">
                      <div className={`${item.color} h-2 rounded-full`} style={{ width: `${pct}%` }} />
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* 最近事件 */}
        <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
          <div className="p-6 border-b border-gray-200">
            <h2 className="text-lg font-semibold text-gray-900">最近检测事件</h2>
          </div>
          <div className="divide-y divide-gray-100">
            {recentEvents.length === 0 ? (
              <div className="p-6 text-center text-gray-500">暂无事件数据</div>
            ) : (
              recentEvents.map((event) => (
                <div key={event.id} className="p-4 hover:bg-gray-50 flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <span className={`px-2 py-1 text-xs rounded-full ${getSeverityColor(event.severity)}`}>
                      {getSeverityLabel(event.severity)}
                    </span>
                    <span className="font-medium text-gray-900">{event.behavior_label}</span>
                    <span className="text-sm text-gray-500">{event.stream_name}</span>
                  </div>
                  <div className="flex items-center gap-3 text-sm text-gray-500">
                    <span>{(event.confidence * 100).toFixed(0)}%</span>
                    <span className="flex items-center gap-1">
                      <Clock className="w-4 h-4" />
                      {formatTime(event.timestamp)}
                    </span>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      </div>

      {/* 演示模式提示 */}
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
        <div className="flex items-start gap-3">
          <Activity className="w-5 h-5 text-blue-600 mt-0.5" />
          <div>
            <h4 className="text-sm font-medium text-blue-900">演示模式</h4>
            <p className="text-sm text-blue-700 mt-1">
              当前系统运行在演示模式，使用预检测视频数据模拟完整功能。
              {stats && ` 共 ${stats.total_streams} 路视频流、${stats.total_events} 个检测事件和 ${stats.total_alerts} 个告警。`}
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
