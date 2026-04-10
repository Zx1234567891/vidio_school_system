'use client';

import { useState } from 'react';
import { CheckCircle, XCircle, Clock, AlertTriangle, Video, Filter, ChevronDown } from 'lucide-react';

// 简化版 fake 数据
const makeData = () => {
  const raw = [
    { id: 'e1', stream_name: '打架斗殴检测', behavior_label: '打架斗殴', severity: 'high', description: '教学楼前两学生发生肢体冲突', confidence: 0.94, reviewed: false, result: 'pending' },
    { id: 'e2', stream_name: '校园霸凌检测', behavior_label: '校园霸凌', severity: 'high', description: '操场角落多名学生围堵一名学生', confidence: 0.89, reviewed: false, result: 'pending' },
    { id: 'e3', stream_name: '疑似轻生检测', behavior_label: '疑似轻生', severity: 'high', description: '学生长时间站在天台边缘', confidence: 0.76, reviewed: false, result: 'pending' },
    { id: 'e4', stream_name: '摔倒检测', behavior_label: '摔倒', severity: 'high', description: '学生在校门口台阶处突然摔倒', confidence: 0.91, reviewed: true, result: 'confirmed' },
    { id: 'e5', stream_name: '吸烟检测', behavior_label: '吸烟', severity: 'medium', description: '教学楼男厕检测到学生吸烟', confidence: 0.87, reviewed: false, result: 'pending' },
    { id: 'e6', stream_name: '异常徘徊检测', behavior_label: '异常徘徊', severity: 'low', description: '外来人员在围墙附近反复徘徊', confidence: 0.72, reviewed: false, result: 'pending' },
    { id: 'e7', stream_name: '低头看手机', behavior_label: '低头看手机', severity: 'medium', description: '学生上课期间长时间使用手机', confidence: 0.83, reviewed: true, result: 'false_positive' },
    { id: 'e8', stream_name: '破坏公共设施', behavior_label: '破坏设施', severity: 'high', description: '学生用脚踢踹校园公告栏', confidence: 0.86, reviewed: true, result: 'confirmed' },
    { id: 'e9', stream_name: '翻越围栏检测', behavior_label: '翻越围栏', severity: 'low', description: '学生翻越校园围墙外出', confidence: 0.79, reviewed: true, result: 'confirmed' },
    { id: 'e10', stream_name: '摄像头遮挡', behavior_label: '摄像头遮挡', severity: 'medium', description: '摄像头前方出现大面积遮挡', confidence: 0.95, reviewed: true, result: 'confirmed' },
  ];
  return raw.map((item, i) => ({
    ...item,
    stream_id: `stream_${String(i + 1).padStart(3, '0')}`,
    timestamp: new Date(Date.now() - (i + 1) * 25 * 60000).toISOString(),
    participants: i < 3 ? [{ track_id: `T${i}01`, role: '目标人物', confidence: item.confidence }] : [],
  }));
};

type EventItem = ReturnType<typeof makeData>[number];

export default function ReviewPage() {
  const [events, setEvents] = useState<EventItem[]>(makeData());
  const [tab, setTab] = useState<'pending' | 'reviewed' | 'all'>('pending');
  const [expanded, setExpanded] = useState<string | null>(null);

  const filtered = tab === 'all' ? events : tab === 'pending' ? events.filter((e) => !e.reviewed) : events.filter((e) => e.reviewed);

  const pendingCount = events.filter((e) => !e.reviewed).length;
  const confirmedCount = events.filter((e) => e.result === 'confirmed').length;
  const falseCount = events.filter((e) => e.result === 'false_positive').length;

  const sevColor = (s: string) => ({ high: 'bg-red-50 text-red-600', medium: 'bg-orange-50 text-orange-600', low: 'bg-yellow-50 text-yellow-600' }[s] || '');
  const sevBadge = (s: string) => ({ high: '高风险', medium: '中风险', low: '低风险' }[s] || s);
  const resBadge = (r: string) => ({ confirmed: { cls: 'bg-green-100 text-green-700', label: '已确认' }, false_positive: { cls: 'bg-gray-100 text-gray-600', label: '误报' }, pending: { cls: 'bg-amber-100 text-amber-700', label: '待审核' } }[r] || { cls: '', label: r });

  const review = (id: string, result: 'confirmed' | 'false_positive') => {
    setEvents((prev) => prev.map((e) => (e.id === id ? { ...e, reviewed: true, result } : e)));
    setExpanded(null);
  };

  const undo = (id: string) => {
    setEvents((prev) => prev.map((e) => (e.id === id ? { ...e, reviewed: false, result: 'pending' } : e)));
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">事件审核</h1>
        <p className="text-sm text-gray-500 mt-1">
          待审核 <span className="text-red-500 font-semibold">{pendingCount}</span> 个 · 已确认 {confirmedCount} 个 · 误报 {falseCount} 个
        </p>
      </div>

      {/* 统计卡片 */}
      <div className="grid grid-cols-3 gap-4">
        {[
          { label: '待审核', count: pendingCount, icon: Clock, color: 'text-amber-500', bg: 'bg-amber-50' },
          { label: '已确认', count: confirmedCount, icon: CheckCircle, color: 'text-green-500', bg: 'bg-green-50' },
          { label: '误报', count: falseCount, icon: XCircle, color: 'text-gray-400', bg: 'bg-gray-100' },
        ].map((s) => {
          const Icon = s.icon;
          return (
            <div key={s.label} className="bg-white rounded-xl border border-gray-200 p-4">
              <div className="flex items-center gap-3">
                <div className={`w-10 h-10 rounded-lg ${s.bg} flex items-center justify-center`}><Icon className={`w-5 h-5 ${s.color}`} /></div>
                <div><p className="text-2xl font-bold text-gray-900">{s.count}</p><p className="text-sm text-gray-500">{s.label}</p></div>
              </div>
            </div>
          );
        })}
      </div>

      {/* 标签筛选 */}
      <div className="flex gap-2">
        {(['all', 'pending', 'reviewed'] as const).map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
              tab === t ? 'bg-blue-600 text-white' : 'bg-white border border-gray-200 text-gray-600 hover:bg-gray-50'
            }`}
          >
            {t === 'all' ? '全部' : t === 'pending' ? '待审核' : '已审核'}
          </button>
        ))}
      </div>

      {/* 事件列表 */}
      <div className="space-y-3">
        {filtered.map((event) => {
          const rc = resBadge(event.result);
          const isOpen = expanded === event.id;
          return (
            <div key={event.id} className="bg-white rounded-xl border border-gray-200 overflow-hidden">
              <div className="p-4 cursor-pointer hover:bg-gray-50" onClick={() => setExpanded(isOpen ? null : event.id)}>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <span className={`px-2 py-1 text-xs rounded border ${sevColor(event.severity)}`}>{sevBadge(event.severity)}</span>
                    <span className="font-medium text-gray-900">{event.behavior_label}</span>
                    <span className="text-sm text-gray-400">{event.stream_name}</span>
                  </div>
                  <div className="flex items-center gap-3">
                    <span className={`px-2 py-1 text-xs rounded ${rc.cls}`}>{rc.label}</span>
                    <span className="text-sm text-gray-400">{new Date(event.timestamp).toLocaleString('zh-CN')}</span>
                    <ChevronDown className={`w-4 h-4 text-gray-400 transition-transform ${isOpen ? 'rotate-180' : ''}`} />
                  </div>
                </div>
                <div className="mt-1.5 flex items-center gap-4 text-sm text-gray-500">
                  <span>{event.stream_id}</span>
                  <span>置信度 <span className="text-gray-700 font-medium">{(event.confidence * 100).toFixed(0)}%</span></span>
                  <span className="text-gray-400">{event.description}</span>
                </div>
              </div>

              {isOpen && (
                <div className="border-t border-gray-100 p-4 bg-gray-50">
                  {event.participants.length > 0 && (
                    <div className="mb-3 flex flex-wrap gap-2">
                      {event.participants.map((p) => (
                        <div key={p.track_id} className="flex items-center gap-1.5 bg-white border border-gray-200 rounded px-2.5 py-1 text-sm">
                          <AlertTriangle className="w-3.5 h-3.5 text-gray-400" />
                          <span className="font-medium">{p.role}</span>
                          <span className="text-gray-400">({(p.confidence * 100).toFixed(0)}%)</span>
                        </div>
                      ))}
                    </div>
                  )}
                  {!event.reviewed ? (
                    <div className="flex gap-3">
                      <button onClick={() => review(event.id, 'confirmed')} className="flex items-center gap-1.5 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 text-sm">
                        <CheckCircle className="w-4 h-4" />确认事件
                      </button>
                      <button onClick={() => review(event.id, 'false_positive')} className="flex items-center gap-1.5 px-4 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300 text-sm">
                        <XCircle className="w-4 h-4" />标记误报
                      </button>
                    </div>
                  ) : (
                    <div className="flex items-center gap-3">
                      <span className="text-sm text-gray-500">审核结果：</span>
                      <span className={`px-2.5 py-1 text-sm rounded-lg ${rc.cls}`}>{rc.label}</span>
                      <button onClick={() => undo(event.id)} className="text-sm text-blue-600 hover:underline">撤销</button>
                    </div>
                  )}
                </div>
              )}
            </div>
          );
        })}
        {filtered.length === 0 && (
          <div className="bg-white rounded-xl border border-gray-200 p-12 text-center text-gray-400">
            暂无数据
          </div>
        )}
      </div>
    </div>
  );
}
