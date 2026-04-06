'use client';

import { useEffect, useState } from 'react';
import { Search, Filter, Download, Calendar, Video, AlertTriangle } from 'lucide-react';
import apiClient from '@/lib/api';

interface Event {
  id: string;
  stream_name: string;
  behavior_label: string;
  severity: string;
  category: string;
  description: string;
  timestamp: string;
  confidence: number;
  reviewed: boolean;
  review_result: string;
  participants: Array<{
    track_id: string;
    role: string;
    confidence: number;
  }>;
}

export default function HistoryPage() {
  const [events, setEvents] = useState<Event[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState({
    severity: '',
    category: '',
    search: '',
  });

  useEffect(() => {
    fetchEvents();
  }, []);

  const fetchEvents = async () => {
    try {
      setLoading(true);
      const response = await apiClient.get('/demo/events?limit=100') as { code: number; data: { items: Event[] } };
      if (response.code === 0) {
        setEvents(response.data.items);
      }
    } catch (err) {
      try {
        const response = await apiClient.get('/events?limit=100') as { code: number; data: { items: Event[] } };
        if (response.code === 0) {
          setEvents(response.data.items);
        }
      } catch (err2) {
        console.error('获取事件失败:', err2);
      }
    } finally {
      setLoading(false);
    }
  };

  const filteredEvents = events.filter((event) => {
    if (filter.severity && event.severity !== filter.severity) return false;
    if (filter.category && event.category !== filter.category) return false;
    if (filter.search) {
      const searchLower = filter.search.toLowerCase();
      return (
        event.behavior_label.toLowerCase().includes(searchLower) ||
        event.stream_name.toLowerCase().includes(searchLower) ||
        event.description.toLowerCase().includes(searchLower)
      );
    }
    return true;
  });

  const getSeverityColor = (severity: string) => {
    const colors: Record<string, string> = {
      high: 'bg-red-100 text-red-700 border-red-200',
      medium: 'bg-orange-100 text-orange-700 border-orange-200',
      low: 'bg-yellow-100 text-yellow-700 border-yellow-200',
    };
    return colors[severity] || 'bg-gray-100 text-gray-700';
  };

  const getReviewStatusColor = (result: string) => {
    const colors: Record<string, string> = {
      confirmed: 'bg-green-100 text-green-700',
      false_positive: 'bg-gray-100 text-gray-700',
      pending: 'bg-yellow-100 text-yellow-700',
    };
    return colors[result] || 'bg-gray-100 text-gray-700';
  };

  const formatTime = (timestamp: string) => {
    const date = new Date(timestamp);
    return date.toLocaleString('zh-CN');
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">历史记录</h1>
          <p className="text-sm text-gray-500 mt-1">
            共 {filteredEvents.length} 条记录
          </p>
        </div>
        <button className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700">
          <Download className="w-4 h-4" />
          导出
        </button>
      </div>

      {/* 筛选器 */}
      <div className="bg-white p-4 rounded-xl border border-gray-200">
        <div className="flex flex-wrap gap-4">
          <div className="flex-1 min-w-[200px]">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
              <input
                type="text"
                placeholder="搜索事件..."
                value={filter.search}
                onChange={(e) => setFilter({ ...filter, search: e.target.value })}
                className="w-full pl-10 pr-4 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
          </div>
          <select
            value={filter.severity}
            onChange={(e) => setFilter({ ...filter, severity: e.target.value })}
            className="px-4 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="">所有风险等级</option>
            <option value="high">高风险</option>
            <option value="medium">中风险</option>
            <option value="low">低风险</option>
          </select>
          <select
            value={filter.category}
            onChange={(e) => setFilter({ ...filter, category: e.target.value })}
            className="px-4 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="">所有类别</option>
            <option value="高风险异常">高风险异常</option>
            <option value="敏感行为">敏感行为</option>
            <option value="可疑行为">可疑行为</option>
          </select>
        </div>
      </div>

      {/* 事件列表 */}
      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        {loading ? (
          <div className="flex items-center justify-center h-64">
            <div className="text-gray-500">加载中...</div>
          </div>
        ) : filteredEvents.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-64 text-gray-500">
            <AlertTriangle className="w-12 h-12 mb-4" />
            <p>暂无符合条件的事件</p>
          </div>
        ) : (
          <table className="w-full">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">时间</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">视频流</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">行为</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">严重度</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">置信度</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">审核状态</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {filteredEvents.map((event) => (
                <tr key={event.id} className="hover:bg-gray-50">
                  <td className="px-6 py-4 text-sm text-gray-600">
                    {formatTime(event.timestamp)}
                  </td>
                  <td className="px-6 py-4">
                    <div className="flex items-center gap-2">
                      <Video className="w-4 h-4 text-gray-400" />
                      <span className="text-sm text-gray-900">{event.stream_name}</span>
                    </div>
                  </td>
                  <td className="px-6 py-4">
                    <div>
                      <span className="font-medium text-gray-900">{event.behavior_label}</span>
                      <p className="text-xs text-gray-500 mt-0.5">{event.description}</p>
                    </div>
                  </td>
                  <td className="px-6 py-4">
                    <span className={`px-2 py-1 text-xs rounded border ${getSeverityColor(event.severity)}`}>
                      {event.severity === 'high' ? '高风险' : event.severity === 'medium' ? '中风险' : '低风险'}
                    </span>
                  </td>
                  <td className="px-6 py-4 text-sm text-gray-600">
                    {(event.confidence * 100).toFixed(1)}%
                  </td>
                  <td className="px-6 py-4">
                    <span className={`px-2 py-1 text-xs rounded ${getReviewStatusColor(event.review_result)}`}>
                      {event.review_result === 'confirmed' ? '已确认' :
                        event.review_result === 'false_positive' ? '误报' : '待审核'}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
