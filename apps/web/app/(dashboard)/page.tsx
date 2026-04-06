'use client';

import { useEffect, useState } from 'react';
import { AlertTriangle, Video, Activity, Clock, TrendingUp, Users } from 'lucide-react';
import apiClient from '@/lib/api';

interface DashboardStats {
  total_streams: number;
  active_streams: number;
  total_events: number;
  total_alerts: number;
  unacknowledged_alerts: number;
  pending_reviews: number;
  severity_distribution: {
    high: number;
    medium: number;
    low: number;
  };
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
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchDashboardData();
  }, []);

  const fetchDashboardData = async () => {
    try {
      setLoading(true);

      // 获取统计数据
      const statsRes = await apiClient.get('/demo/stats') as { code: number; data: DashboardStats };
      if (statsRes.code === 0) {
        setStats(statsRes.data);
      }

      // 获取最近事件
      const eventsRes = await apiClient.get('/demo/events?limit=5') as { code: number; data: { items: RecentEvent[] } };
      if (eventsRes.code === 0) {
        setRecentEvents(eventsRes.data.items);
      }
    } catch (err) {
      // 降级到普通API
      try {
        const statsRes = await apiClient.get('/metrics/dashboard') as { code: number; data: DashboardStats };
        if (statsRes.code === 0) {
          setStats(statsRes.data);
        }
      } catch (err2) {
        setError('无法连接到服务器，请确保演示服务器已启动');
      }
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
    const labels: Record<string, string> = {
      high: '高风险',
      medium: '中风险',
      low: '低风险',
    };
    return labels[severity] || severity;
  };

  const formatTime = (timestamp: string) => {
    const date = new Date(timestamp);
    return date.toLocaleString('zh-CN', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-gray-500">加载中...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-red-500">{error}</div>
      </div>
    );
  }

  const statCards = [
    {
      title: '总视频流',
      value: stats?.total_streams || 0,
      subValue: `${stats?.active_streams || 0} 运行中`,
      icon: Video,
      color: 'blue',
    },
    {
      title: '检测事件',
      value: stats?.total_events || 0,
      subValue: `${stats?.pending_reviews || 0} 待审核`,
      icon: TrendingUp,
      color: 'purple',
    },
    {
      title: '实时告警',
      value: stats?.unacknowledged_alerts || 0,
      subValue: `共 ${stats?.total_alerts || 0} 个`,
      icon: AlertTriangle,
      color: 'orange',
    },
    {
      title: '系统状态',
      value: '正常',
      subValue: '演示模式运行中',
      icon: Activity,
      color: 'green',
    },
  ];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">系统概览</h1>
        <p className="text-sm text-gray-500 mt-1">实时监控校园安防状态</p>
      </div>

      {/* 统计卡片 */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {statCards.map((card) => {
          const Icon = card.icon;
          const colorClasses = {
            blue: 'bg-blue-50 text-blue-600',
            orange: 'bg-orange-50 text-orange-600',
            green: 'bg-green-50 text-green-600',
            purple: 'bg-purple-50 text-purple-600',
          }[card.color];

          return (
            <div key={card.title} className="bg-white p-6 rounded-xl border border-gray-200">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-gray-500">{card.title}</p>
                  <p className="text-2xl font-bold text-gray-900 mt-1">{card.value}</p>
                  <p className="text-xs text-gray-400 mt-1">{card.subValue}</p>
                </div>
                <div className={`p-3 rounded-lg ${colorClasses}`}>
                  <Icon className="w-6 h-6" />
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* 严重度分布 */}
      {stats?.severity_distribution && (
        <div className="bg-white p-6 rounded-xl border border-gray-200">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">事件风险分布</h2>
          <div className="grid grid-cols-3 gap-4">
            <div className="text-center p-4 bg-red-50 rounded-lg">
              <p className="text-3xl font-bold text-red-600">{stats.severity_distribution.high}</p>
              <p className="text-sm text-red-700 mt-1">高风险事件</p>
            </div>
            <div className="text-center p-4 bg-orange-50 rounded-lg">
              <p className="text-3xl font-bold text-orange-600">{stats.severity_distribution.medium}</p>
              <p className="text-sm text-orange-700 mt-1">中风险事件</p>
            </div>
            <div className="text-center p-4 bg-yellow-50 rounded-lg">
              <p className="text-3xl font-bold text-yellow-600">{stats.severity_distribution.low}</p>
              <p className="text-sm text-yellow-700 mt-1">低风险事件</p>
            </div>
          </div>
        </div>
      )}

      {/* 最近事件 */}
      <div className="bg-white rounded-xl border border-gray-200">
        <div className="p-6 border-b border-gray-200">
          <h2 className="text-lg font-semibold text-gray-900">最近检测事件</h2>
        </div>
        <div className="divide-y divide-gray-200">
          {recentEvents.length === 0 ? (
            <div className="p-6 text-center text-gray-500">暂无事件数据</div>
          ) : (
            recentEvents.map((event) => (
              <div key={event.id} className="p-4 hover:bg-gray-50">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <span className={`px-2 py-1 text-xs rounded-full ${getSeverityColor(event.severity)}`}>
                      {getSeverityLabel(event.severity)}
                    </span>
                    <span className="font-medium text-gray-900">{event.behavior_label}</span>
                    <span className="text-sm text-gray-500">{event.stream_name}</span>
                  </div>
                  <div className="flex items-center gap-4 text-sm text-gray-500">
                    <span>置信度: {(event.confidence * 100).toFixed(1)}%</span>
                    <span className="flex items-center gap-1">
                      <Clock className="w-4 h-4" />
                      {formatTime(event.timestamp)}
                    </span>
                  </div>
                </div>
              </div>
            ))
          )}
        </div>
      </div>

      {/* 演示模式提示 */}
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
        <div className="flex items-start gap-3">
          <Activity className="w-5 h-5 text-blue-600 mt-0.5" />
          <div>
            <h4 className="text-sm font-medium text-blue-900">演示模式</h4>
            <p className="text-sm text-blue-700 mt-1">
              当前系统运行在演示模式，使用检测好的视频数据模拟完整功能。
              数据包括 {stats?.total_streams || 0} 路视频流、{stats?.total_events || 0} 个检测事件和 {stats?.total_alerts || 0} 个告警。
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
