'use client';

import { useEffect, useState, useRef, useCallback } from 'react';
import { Play, Square, RefreshCw, Plus, Trash2, Video, AlertCircle } from 'lucide-react';
import { Stream } from '@/types';
import apiClient from '@/lib/api';

interface StreamWithBehavior extends Stream {
  behavior_label?: string;
  severity?: string;
  category?: string;
}

const API_BASE = process.env.NEXT_PUBLIC_API_URL?.replace('/api/v1', '') || 'http://localhost:8888';

/** 快照轮询视频组件 - 用定时请求单帧 JPEG 替代 MJPEG 长连接，突破浏览器 6 并发限制 */
function SnapshotPlayer({ streamId, fps }: { streamId: string; fps: number }) {
  const imgRef = useRef<HTMLImageElement>(null);
  const timerRef = useRef<ReturnType<typeof setInterval>>();

  useEffect(() => {
    let seq = 0;
    const interval = Math.max(1000 / Math.min(fps, 10), 100); // 最高 10fps，最低 100ms

    const tick = () => {
      if (imgRef.current) {
        seq++;
        imgRef.current.src = `${API_BASE}/api/v1/streams/${streamId}/snapshot?_t=${seq}`;
      }
    };

    tick(); // 立即加载首帧
    timerRef.current = setInterval(tick, interval);

    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, [streamId, fps]);

  return (
    <img
      ref={imgRef}
      alt=""
      className="w-full h-full object-contain"
    />
  );
}

export default function StreamsPage() {
  const [streams, setStreams] = useState<StreamWithBehavior[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchStreams();
  }, []);

  const fetchStreams = async () => {
    try {
      setLoading(true);
      // 尝试演示模式API
      const response = await apiClient.get('/demo/streams') as { code: number; data: { items: StreamWithBehavior[] } };
      if (response.code === 0) {
        setStreams(response.data.items);
      }
    } catch (err) {
      // 降级到普通API
      try {
        const response = await apiClient.get('/streams') as { code: number; data: { items: StreamWithBehavior[] } };
        if (response.code === 0) {
          setStreams(response.data.items);
        }
      } catch (err2) {
        setError('无法连接到服务器，请确保演示服务器已启动 (python services/mock-streamer/demo_server.py)');
      }
    } finally {
      setLoading(false);
    }
  };

  const handleStart = async (id: string) => {
    try {
      await apiClient.post(`/demo/streams/${id}/start`);
      fetchStreams();
    } catch (err) {
      // 降级
      try {
        await apiClient.post(`/streams/${id}/start`);
        fetchStreams();
      } catch (err2) {
        alert('操作失败: ' + (err2 instanceof Error ? err2.message : '未知错误'));
      }
    }
  };

  const handleStop = async (id: string) => {
    try {
      await apiClient.post(`/demo/streams/${id}/stop`);
      fetchStreams();
    } catch (err) {
      try {
        await apiClient.post(`/streams/${id}/stop`);
        fetchStreams();
      } catch (err2) {
        alert('操作失败: ' + (err2 instanceof Error ? err2.message : '未知错误'));
      }
    }
  };

  const getStatusColor = (status: string) => {
    const colors: Record<string, string> = {
      running: 'bg-green-100 text-green-700',
      stopped: 'bg-gray-100 text-gray-700',
      error: 'bg-red-100 text-red-700',
      connecting: 'bg-yellow-100 text-yellow-700',
      reconnecting: 'bg-orange-100 text-orange-700',
    };
    return colors[status] || 'bg-gray-100 text-gray-700';
  };

  const getSeverityColor = (severity?: string) => {
    const colors: Record<string, string> = {
      high: 'bg-red-100 text-red-700 border-red-200',
      medium: 'bg-orange-100 text-orange-700 border-orange-200',
      low: 'bg-yellow-100 text-yellow-700 border-yellow-200',
    };
    return colors[severity || ''] || 'bg-gray-100 text-gray-700';
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
      <div className="flex flex-col items-center justify-center h-64 space-y-4">
        <AlertCircle className="w-12 h-12 text-orange-500" />
        <div className="text-gray-700 text-center max-w-md">
          <p className="font-medium mb-2">连接失败</p>
          <p className="text-sm text-gray-500">{error}</p>
        </div>
        <button
          onClick={fetchStreams}
          className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
        >
          重试
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">视频流管理</h1>
          <p className="text-sm text-gray-500 mt-1">
            共 {streams.length} 路视频流 | 演示模式
          </p>
        </div>
        <button className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700">
          <Plus className="w-4 h-4" />
          添加流
        </button>
      </div>

      {/* 视频流卡片网格 */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {streams.length === 0 ? (
          <div className="col-span-full text-center py-12 text-gray-500">
            暂无视频流
          </div>
        ) : (
          streams.map((stream) => (
            <div key={stream.id} className="bg-white rounded-xl border border-gray-200 overflow-hidden hover:shadow-md transition-shadow">
              {/* 视频预览区域 */}
              <div className="aspect-video bg-gray-900 relative flex items-center justify-center overflow-hidden">
                {stream.status === 'running' ? (
                  <SnapshotPlayer streamId={stream.id} fps={stream.fps || 30} />
                ) : (
                  <Video className="w-12 h-12 text-gray-600" />
                )}
                {stream.behavior_label && (
                  <div className={`absolute top-2 right-2 px-2 py-1 text-xs rounded border ${getSeverityColor(stream.severity)}`}>
                    {stream.behavior_label}
                  </div>
                )}
                <div className={`absolute top-2 left-2 px-2 py-1 text-xs rounded-full ${getStatusColor(stream.status)}`}>
                  {stream.status === 'running' ? '运行中' : '已停止'}
                </div>
                {stream.status === 'running' && (
                  <div className="absolute bottom-2 right-2 flex items-center gap-1">
                    <span className="w-2 h-2 bg-red-500 rounded-full animate-pulse"></span>
                    <span className="text-xs text-white">LIVE</span>
                  </div>
                )}
              </div>

              {/* 信息区域 */}
              <div className="p-4">
                <div className="flex items-start justify-between mb-2">
                  <div>
                    <h3 className="font-medium text-gray-900">{stream.name}</h3>
                    <p className="text-xs text-gray-500">{stream.id}</p>
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-2 text-sm text-gray-600 mb-4">
                  <div>
                    <span className="text-gray-400">分辨率:</span>{' '}
                    {stream.width && stream.height ? `${stream.width}x${stream.height}` : '-'}
                  </div>
                  <div>
                    <span className="text-gray-400">帧率:</span>{' '}
                    {stream.fps ? `${stream.fps.toFixed(1)} fps` : '-'}
                  </div>
                  <div>
                    <span className="text-gray-400">类型:</span>{' '}
                    <span className="uppercase">{stream.input_type}</span>
                  </div>
                  <div>
                    <span className="text-gray-400">类别:</span>{' '}
                    {stream.category || '-'}
                  </div>
                </div>

                {/* 操作按钮 */}
                <div className="flex items-center gap-2 pt-3 border-t border-gray-100">
                  {stream.status === 'running' ? (
                    <button
                      onClick={() => handleStop(stream.id)}
                      className="flex-1 flex items-center justify-center gap-2 px-3 py-2 bg-red-50 text-red-600 rounded-lg hover:bg-red-100"
                    >
                      <Square className="w-4 h-4" />
                      停止
                    </button>
                  ) : (
                    <button
                      onClick={() => handleStart(stream.id)}
                      className="flex-1 flex items-center justify-center gap-2 px-3 py-2 bg-green-50 text-green-600 rounded-lg hover:bg-green-100"
                    >
                      <Play className="w-4 h-4" />
                      启动
                    </button>
                  )}
                  <button className="p-2 text-gray-600 hover:bg-gray-100 rounded-lg" title="重启">
                    <RefreshCw className="w-4 h-4" />
                  </button>
                  <button className="p-2 text-red-600 hover:bg-red-50 rounded-lg" title="删除">
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </div>
            </div>
          ))
        )}
      </div>

      {/* 说明 */}
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
        <h4 className="text-sm font-medium text-blue-900 mb-2">演示模式说明</h4>
        <ul className="text-sm text-blue-700 space-y-1 list-disc list-inside">
          <li>当前使用检测好的视频文件模拟推流</li>
          <li>每个视频对应一种异常行为检测场景</li>
          <li>点击"启动"开始模拟推流，"停止"结束推流</li>
          <li>实际项目中会连接真实RTSP摄像头流</li>
        </ul>
      </div>
    </div>
  );
}
