'use client';

import { useEffect, useState, useRef, useCallback } from 'react';
import { Play, Square, RefreshCw, Plus, Trash2, Video, AlertCircle, X } from 'lucide-react';
import { Stream } from '@/types';
import apiClient from '@/lib/api';

interface StreamWithBehavior extends Stream {
  behavior_label?: string;
  severity?: string;
  category?: string;
}

type InputType = 'rtsp' | 'rtmp' | 'file' | 'webcam';

const INPUT_TYPE_OPTIONS: { value: InputType; label: string; placeholder: string; hint: string }[] = [
  { value: 'rtsp', label: 'RTSP 摄像头', placeholder: 'rtsp://user:pass@192.168.1.64:554/Streaming/Channels/101', hint: '网络摄像机 RTSP 地址' },
  { value: 'rtmp', label: 'RTMP 推流', placeholder: 'rtmp://live.example.com/app/stream', hint: 'RTMP 推流地址' },
  { value: 'file', label: '本地视频文件', placeholder: 'D:/videos/test.mp4', hint: '后端可访问的绝对路径' },
  { value: 'webcam', label: '本地摄像头', placeholder: '0', hint: '摄像头索引，默认 0' },
];

const API_BASE = process.env.NEXT_PUBLIC_API_URL?.replace('/api/v1', '') || 'http://localhost:8000';

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
  const [showAdd, setShowAdd] = useState(false);
  const [addForm, setAddForm] = useState<{
    url: string;
    input_type: InputType;
    name: string;
    auto_start: boolean;
  }>({ url: '', input_type: 'rtsp', name: '', auto_start: true });
  const [adding, setAdding] = useState(false);
  const [addErr, setAddErr] = useState<string | null>(null);
  const [localFiles, setLocalFiles] = useState<{ path: string; label: string; size_mb: number }[]>([]);
  const [localFilesLoading, setLocalFilesLoading] = useState(false);

  useEffect(() => {
    fetchStreams();
  }, []);

  // 打开对话框 + 类型是 file 时，拉取后端可见视频文件列表
  useEffect(() => {
    if (!showAdd || addForm.input_type !== 'file') return;
    let aborted = false;
    setLocalFilesLoading(true);
    apiClient
      .get('/streams/browse/local-files')
      .then((resp: unknown) => {
        if (aborted) return;
        const r = resp as { code: number; data?: { items?: { path: string; label: string; size_mb: number }[] } };
        if (r.code === 0 && r.data?.items) setLocalFiles(r.data.items);
      })
      .catch(() => {
        if (!aborted) setLocalFiles([]);
      })
      .finally(() => {
        if (!aborted) setLocalFilesLoading(false);
      });
    return () => {
      aborted = true;
    };
  }, [showAdd, addForm.input_type]);

  const fetchStreams = async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await apiClient.get('/streams') as { code: number; data: { items: StreamWithBehavior[] } };
      if (response.code === 0) {
        setStreams(response.data.items);
      }
    } catch (err) {
      setError('无法连接 apps/api (默认 :8000)。请确保已启动：cd apps/api && uvicorn main:app --reload');
    } finally {
      setLoading(false);
    }
  };

  const handleStart = async (id: string) => {
    try {
      await apiClient.post(`/streams/${id}/start`);
      fetchStreams();
    } catch (err) {
      alert('启动失败: ' + (err instanceof Error ? err.message : '未知错误'));
    }
  };

  const handleAddSubmit = async () => {
    setAddErr(null);
    if (!addForm.url.trim()) {
      setAddErr('请填写 URL / 路径 / 索引');
      return;
    }
    setAdding(true);
    try {
      const payload = {
        url: addForm.url.trim(),
        input_type: addForm.input_type,
        name: addForm.name.trim() || `Stream ${Date.now()}`,
        auto_start: addForm.auto_start,
      };
      const resp = await apiClient.post('/streams', payload) as { code: number; message?: string; data?: unknown };
      if (resp.code === 0) {
        setShowAdd(false);
        setAddForm({ url: '', input_type: 'rtsp', name: '', auto_start: true });
        fetchStreams();
      } else {
        setAddErr(resp.message || '添加失败');
      }
    } catch (err) {
      setAddErr(err instanceof Error ? err.message : '添加失败');
    } finally {
      setAdding(false);
    }
  };

  const handleDelete = async (id: string, name: string) => {
    if (!confirm(`确认删除「${name}」？`)) return;
    try {
      await apiClient.delete(`/streams/${id}`);
      fetchStreams();
    } catch (err) {
      alert('删除失败: ' + (err instanceof Error ? err.message : '未知错误'));
    }
  };

  const handleRestart = async (id: string) => {
    try {
      await apiClient.post(`/streams/${id}/restart`);
      fetchStreams();
    } catch (err) {
      alert('重启失败: ' + (err instanceof Error ? err.message : '未知错误'));
    }
  };

  const handleStop = async (id: string) => {
    try {
      await apiClient.post(`/streams/${id}/stop`);
      fetchStreams();
    } catch (err) {
      alert('停止失败: ' + (err instanceof Error ? err.message : '未知错误'));
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
        <button
          onClick={() => { setAddErr(null); setShowAdd(true); }}
          className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
        >
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
                  <button
                    onClick={() => handleRestart(stream.id)}
                    className="p-2 text-gray-600 hover:bg-gray-100 rounded-lg"
                    title="重启"
                  >
                    <RefreshCw className="w-4 h-4" />
                  </button>
                  <button
                    onClick={() => handleDelete(stream.id, stream.name)}
                    className="p-2 text-red-600 hover:bg-red-50 rounded-lg"
                    title="删除"
                  >
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
        <h4 className="text-sm font-medium text-blue-900 mb-2">YOLO26 校园行为检测</h4>
        <ul className="text-sm text-blue-700 space-y-1 list-disc list-inside">
          <li>使用自训练 YOLO26 模型实时检测：Kick / Laying / Phone / Pointing / Slap face / Slap table / Smoking / Squating / Stand / Touch / Hit wall（11 类）</li>
          <li>支持接入 RTSP / RTMP 网络流、本地视频文件或本地摄像头（点击右上角「添加流」）</li>
          <li>推流画面上会叠加检测框与标签，高风险行为以红色高亮</li>
          <li>若后端未安装 ultralytics / GPU 不可用，仍会推流原始画面（无叠加）</li>
        </ul>
      </div>

      {/* 添加流对话框 */}
      {showAdd && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40" onClick={() => !adding && setShowAdd(false)}>
          <div className="bg-white rounded-xl shadow-xl w-full max-w-md p-6" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold text-gray-900">添加视频流</h3>
              <button onClick={() => !adding && setShowAdd(false)} className="text-gray-400 hover:text-gray-600">
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">输入类型</label>
                <div className="grid grid-cols-2 gap-2">
                  {INPUT_TYPE_OPTIONS.map((opt) => (
                    <button
                      key={opt.value}
                      type="button"
                      onClick={() => setAddForm((f) => ({ ...f, input_type: opt.value }))}
                      className={`px-3 py-2 text-sm rounded-lg border ${
                        addForm.input_type === opt.value
                          ? 'border-blue-600 bg-blue-50 text-blue-700'
                          : 'border-gray-200 text-gray-700 hover:bg-gray-50'
                      }`}
                    >
                      {opt.label}
                    </button>
                  ))}
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  {addForm.input_type === 'file' ? '文件路径' : addForm.input_type === 'webcam' ? '摄像头索引' : '流地址'}
                </label>

                {addForm.input_type === 'file' && (
                  <div className="mb-2">
                    <select
                      value={localFiles.some((f) => f.path === addForm.url) ? addForm.url : ''}
                      onChange={(e) => {
                        const v = e.target.value;
                        const picked = localFiles.find((f) => f.path === v);
                        setAddForm((f) => ({
                          ...f,
                          url: v,
                          // 文件选完若 name 还空，自动用父目录名（类别）作为默认名
                          name: f.name || !picked ? f.name : picked.label.split('/')[0] || picked.label,
                        }));
                      }}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white"
                      disabled={localFilesLoading}
                    >
                      <option value="">
                        {localFilesLoading
                          ? '正在扫描后端可见文件…'
                          : localFiles.length === 0
                            ? '后端未发现可用视频（可在下方手填路径）'
                            : `从后端已扫描的 ${localFiles.length} 个视频中选一个`}
                      </option>
                      {localFiles.map((f) => (
                        <option key={f.path} value={f.path}>
                          {f.label}{f.size_mb ? `  (${f.size_mb} MB)` : ''}
                        </option>
                      ))}
                    </select>
                    <p className="text-xs text-gray-500 mt-1">
                      下拉来自后端 <code>FILE_BROWSE_ROOTS</code>（默认 <code>/project1</code>）；或手动输入：
                    </p>
                  </div>
                )}

                <input
                  type="text"
                  value={addForm.url}
                  onChange={(e) => setAddForm((f) => ({ ...f, url: e.target.value }))}
                  placeholder={INPUT_TYPE_OPTIONS.find((o) => o.value === addForm.input_type)?.placeholder}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
                <p className="text-xs text-gray-500 mt-1">
                  {INPUT_TYPE_OPTIONS.find((o) => o.value === addForm.input_type)?.hint}
                </p>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">显示名称（可选）</label>
                <input
                  type="text"
                  value={addForm.name}
                  onChange={(e) => setAddForm((f) => ({ ...f, name: e.target.value }))}
                  placeholder="如 教学楼-走廊-1F"
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>

              <label className="flex items-center gap-2 text-sm text-gray-700">
                <input
                  type="checkbox"
                  checked={addForm.auto_start}
                  onChange={(e) => setAddForm((f) => ({ ...f, auto_start: e.target.checked }))}
                  className="rounded"
                />
                创建后立即启动推流并开始 YOLO26 检测
              </label>

              {addErr && (
                <div className="text-sm text-red-600 bg-red-50 border border-red-200 rounded-lg p-2">
                  {addErr}
                </div>
              )}
            </div>

            <div className="flex justify-end gap-2 mt-6">
              <button
                onClick={() => !adding && setShowAdd(false)}
                disabled={adding}
                className="px-4 py-2 text-gray-700 border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-50"
              >
                取消
              </button>
              <button
                onClick={handleAddSubmit}
                disabled={adding}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
              >
                {adding ? '创建中…' : '创建'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
