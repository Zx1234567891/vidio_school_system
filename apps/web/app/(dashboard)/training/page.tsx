'use client';

import { useState } from 'react';
import { Brain, Play, Pause, Trash2, Clock, CheckCircle, XCircle, AlertCircle, Database, Cpu, Zap, Settings, ChevronDown, Terminal } from 'lucide-react';

const FAKE_JOBS = [
  {
    id: 'job-001',
    name: '打架斗殴检测模型 v3.2',
    model_type: '行为识别',
    dataset: '校园安防数据集 v2.1',
    status: 'training',
    progress: 67,
    epoch: 45,
    total_epochs: 67,
    metrics: { mAP: 0.854, recall: 0.821, precision: 0.812 },
    created_at: new Date(Date.now() - 3 * 3600000).toISOString(),
    estimated_finish: new Date(Date.now() + 2 * 3600000).toISOString(),
    gpu: 'NVIDIA RTX 4090',
    description: '基于 ResNet50 + TSN 的打架斗殴检测模型，新增注意力机制',
  },
  {
    id: 'job-002',
    name: '摔倒检测模型 v2.1',
    model_type: '姿态估计',
    dataset: '摔倒数据集 v1.5',
    status: 'completed',
    progress: 100,
    epoch: 80,
    total_epochs: 80,
    metrics: { mAP: 0.912, recall: 0.893, precision: 0.876 },
    created_at: new Date(Date.now() - 24 * 3600000).toISOString(),
    estimated_finish: new Date(Date.now() - 12 * 3600000).toISOString(),
    gpu: 'NVIDIA RTX 4090',
    description: '基于 HRNet 的摔倒姿态估计模型，支持遮挡场景',
  },
  {
    id: 'job-003',
    name: '霸凌行为识别模型 v1.0',
    model_type: '多标签分类',
    dataset: '霸凌场景数据集 v1.0',
    status: 'queued',
    progress: 0,
    epoch: 0,
    total_epochs: 60,
    metrics: null,
    created_at: new Date(Date.now() - 1 * 3600000).toISOString(),
    estimated_finish: new Date(Date.now() + 10 * 3600000).toISOString(),
    gpu: 'NVIDIA RTX 4090',
    description: '基于图卷积的多人交互行为识别模型',
  },
  {
    id: 'job-004',
    name: '轻生行为预警模型 v1.2',
    model_type: '时序分析',
    dataset: '敏感行为数据集 v2.0',
    status: 'failed',
    progress: 38,
    epoch: 23,
    total_epochs: 60,
    metrics: null,
    created_at: new Date(Date.now() - 48 * 3600000).toISOString(),
    estimated_finish: null,
    gpu: 'NVIDIA RTX 4090',
    description: '基于时空图卷积网络的异常行为预警模型（训练中断）',
  },
];

interface TrainingJob {
  id: string;
  name: string;
  model_type: string;
  dataset: string;
  status: 'training' | 'completed' | 'queued' | 'failed';
  progress: number;
  epoch: number;
  total_epochs: number;
  metrics: { mAP: number; recall: number; precision: number } | null;
  created_at: string;
  estimated_finish: string | null;
  gpu: string;
  description: string;
}

export default function TrainingPage() {
  const [jobs, setJobs] = useState<TrainingJob[]>(FAKE_JOBS);
  const [expandedId, setExpandedId] = useState<string | null>(null);

  const getStatusConfig = (status: string) => {
    const configs: Record<string, { bg: string; text: string; label: string; icon: typeof Clock }> = {
      training: { bg: 'bg-blue-50', text: 'text-blue-600', label: '训练中', icon: Zap },
      completed: { bg: 'bg-green-50', text: 'text-green-600', label: '已完成', icon: CheckCircle },
      queued: { bg: 'bg-amber-50', text: 'text-amber-600', label: '排队中', icon: Clock },
      failed: { bg: 'bg-red-50', text: 'text-red-600', label: '已失败', icon: XCircle },
    };
    return configs[status] || configs.queued;
  };

  const formatTime = (ts: string) => new Date(ts).toLocaleString('zh-CN');

  const trainingCount = jobs.filter((j) => j.status === 'training').length;
  const completedCount = jobs.filter((j) => j.status === 'completed').length;
  const queuedCount = jobs.filter((j) => j.status === 'queued').length;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">模型训练</h1>
          <p className="text-sm text-gray-500 mt-1">管理 AI 模型训练任务，支持 ONNX 导出与部署</p>
        </div>
        <button className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 text-sm">
          <Play className="w-4 h-4" />
          新建训练任务
        </button>
      </div>

      {/* 统计 */}
      <div className="grid grid-cols-4 gap-4">
        {[
          { label: '训练中', value: trainingCount, icon: Zap, color: 'text-blue-500', bg: 'bg-blue-50' },
          { label: '已完成', value: completedCount, icon: CheckCircle, color: 'text-green-500', bg: 'bg-green-50' },
          { label: '排队中', value: queuedCount, icon: Clock, color: 'text-amber-500', bg: 'bg-amber-50' },
          { label: '已失败', value: jobs.filter((j) => j.status === 'failed').length, icon: XCircle, color: 'text-red-500', bg: 'bg-red-50' },
        ].map((stat) => {
          const Icon = stat.icon;
          return (
            <div key={stat.label} className="bg-white rounded-xl border border-gray-200 p-4">
              <div className="flex items-center gap-3">
                <div className={`w-10 h-10 rounded-lg ${stat.bg} flex items-center justify-center`}>
                  <Icon className={`w-5 h-5 ${stat.color}`} />
                </div>
                <div>
                  <p className="text-2xl font-bold text-gray-900">{stat.value}</p>
                  <p className="text-sm text-gray-500">{stat.label}</p>
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* GPU 资源 */}
      <div className="bg-white rounded-xl border border-gray-200 p-4">
        <div className="flex items-center gap-2 mb-3">
          <Cpu className="w-4 h-4 text-gray-500" />
          <span className="text-sm font-medium text-gray-700">GPU 资源状态</span>
        </div>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <div className="flex items-center justify-between text-sm mb-1">
              <span className="text-gray-500">NVIDIA RTX 4090</span>
              <span className="text-gray-700 font-medium">67%</span>
            </div>
            <div className="w-full bg-gray-100 rounded-full h-2">
              <div className="bg-blue-500 h-2 rounded-full" style={{ width: '67%' }} />
            </div>
            <p className="text-xs text-gray-400 mt-1">显存: 14.5GB / 24GB · 温度: 62°C</p>
          </div>
          <div>
            <div className="flex items-center justify-between text-sm mb-1">
              <span className="text-gray-500">空闲</span>
              <span className="text-green-600 font-medium">33%</span>
            </div>
            <div className="w-full bg-gray-100 rounded-full h-2">
              <div className="bg-green-400 h-2 rounded-full" style={{ width: '33%' }} />
            </div>
            <p className="text-xs text-gray-400 mt-1">显存: 8GB / 24GB · 温度: 41°C</p>
          </div>
        </div>
      </div>

      {/* 训练任务列表 */}
      <div className="space-y-3">
        {jobs.map((job) => {
          const statusCfg = getStatusConfig(job.status);
          const StatusIcon = statusCfg.icon;
          const isExpanded = expandedId === job.id;

          return (
            <div key={job.id} className="bg-white rounded-xl border border-gray-200 overflow-hidden">
              <div
                className="p-4 cursor-pointer hover:bg-gray-50"
                onClick={() => setExpandedId(isExpanded ? null : job.id)}
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className={`w-9 h-9 rounded-lg ${statusCfg.bg} flex items-center justify-center`}>
                      <StatusIcon className={`w-5 h-5 ${statusCfg.text}`} />
                    </div>
                    <div>
                      <h3 className="font-medium text-gray-900">{job.name}</h3>
                      <p className="text-xs text-gray-400 mt-0.5">{job.id} · {job.gpu}</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-4">
                    <span className={`px-2.5 py-1 text-xs rounded-lg font-medium ${statusCfg.bg} ${statusCfg.text}`}>
                      {statusCfg.label}
                    </span>
                    {job.status === 'training' && (
                      <div className="text-right min-w-[120px]">
                        <p className="text-sm font-medium text-gray-700">Epoch {job.epoch}/{job.total_epochs}</p>
                        <div className="w-full bg-gray-100 rounded-full h-1.5 mt-1">
                          <div className="bg-blue-500 h-1.5 rounded-full transition-all" style={{ width: `${job.progress}%` }} />
                        </div>
                      </div>
                    )}
                    <ChevronDown className={`w-4 h-4 text-gray-400 transition-transform ${isExpanded ? 'rotate-180' : ''}`} />
                  </div>
                </div>
              </div>

              {isExpanded && (
                <div className="border-t border-gray-100 p-4 bg-gray-50 space-y-4">
                  {/* 进度条（训练中） */}
                  {job.status === 'training' && (
                    <div>
                      <div className="flex items-center justify-between text-sm mb-1.5">
                        <span className="text-gray-500">训练进度</span>
                        <span className="font-medium text-blue-600">{job.progress}%</span>
                      </div>
                      <div className="w-full bg-gray-200 rounded-full h-2.5">
                        <div className="bg-gradient-to-r from-blue-500 to-purple-500 h-2.5 rounded-full" style={{ width: `${job.progress}%` }} />
                      </div>
                      <p className="text-xs text-gray-400 mt-1">预计完成: {job.estimated_finish ? formatTime(job.estimated_finish) : '-'}</p>
                    </div>
                  )}

                  {/* 指标 */}
                  {job.metrics && (
                    <div>
                      <p className="text-sm font-medium text-gray-700 mb-2">训练指标</p>
                      <div className="grid grid-cols-3 gap-3">
                        {[
                          { label: 'mAP', value: job.metrics.mAP },
                          { label: 'Recall', value: job.metrics.recall },
                          { label: 'Precision', value: job.metrics.precision },
                        ].map((m) => (
                          <div key={m.label} className="bg-white rounded-lg border border-gray-200 p-3 text-center">
                            <p className="text-xs text-gray-400 mb-1">{m.label}</p>
                            <p className="text-lg font-bold text-gray-900">{(m.value * 100).toFixed(1)}%</p>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* 失败原因 */}
                  {job.status === 'failed' && (
                    <div className="flex items-start gap-2 p-3 bg-red-50 rounded-lg border border-red-200">
                      <AlertCircle className="w-4 h-4 text-red-500 mt-0.5" />
                      <div>
                        <p className="text-sm font-medium text-red-700">训练中断</p>
                        <p className="text-xs text-red-500 mt-0.5">GPU 内存不足，训练在 Epoch {job.epoch} 中断。请降低 batch size 后重试。</p>
                      </div>
                    </div>
                  )}

                  {/* 详情 */}
                  <div className="grid grid-cols-2 gap-3 text-sm">
                    <div className="flex items-center gap-2">
                      <Database className="w-4 h-4 text-gray-400" />
                      <span className="text-gray-500">数据集:</span>
                      <span className="text-gray-700">{job.dataset}</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <Brain className="w-4 h-4 text-gray-400" />
                      <span className="text-gray-500">模型类型:</span>
                      <span className="text-gray-700">{job.model_type}</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <Clock className="w-4 h-4 text-gray-400" />
                      <span className="text-gray-500">创建时间:</span>
                      <span className="text-gray-700">{formatTime(job.created_at)}</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <Cpu className="w-4 h-4 text-gray-400" />
                      <span className="text-gray-500">GPU:</span>
                      <span className="text-gray-700">{job.gpu}</span>
                    </div>
                  </div>

                  <p className="text-sm text-gray-500 bg-white rounded-lg p-3 border border-gray-200">{job.description}</p>

                  {/* 操作 */}
                  <div className="flex items-center gap-3 pt-1">
                    {job.status === 'training' ? (
                      <>
                        <button className="flex items-center gap-1.5 px-4 py-2 bg-amber-100 text-amber-700 rounded-lg hover:bg-amber-200 text-sm">
                          <Pause className="w-4 h-4" />
                          暂停
                        </button>
                        <button className="flex items-center gap-1.5 px-4 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300 text-sm">
                          <Terminal className="w-4 h-4" />
                          查看日志
                        </button>
                      </>
                    ) : job.status === 'completed' ? (
                      <>
                        <button className="flex items-center gap-1.5 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 text-sm">
                          <Zap className="w-4 h-4" />
                          导出 ONNX
                        </button>
                        <button className="flex items-center gap-1.5 px-4 py-2 bg-green-100 text-green-700 rounded-lg hover:bg-green-200 text-sm">
                          <CheckCircle className="w-4 h-4" />
                          部署上线
                        </button>
                      </>
                    ) : job.status === 'queued' ? (
                      <button className="flex items-center gap-1.5 px-4 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300 text-sm">
                        <XCircle className="w-4 h-4" />
                        取消任务
                      </button>
                    ) : (
                      <>
                        <button className="flex items-center gap-1.5 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 text-sm">
                          <Play className="w-4 h-4" />
                          重新训练
                        </button>
                        <button className="flex items-center gap-1.5 px-4 py-2 bg-red-50 text-red-600 rounded-lg hover:bg-red-100 text-sm">
                          <Trash2 className="w-4 h-4" />
                          删除记录
                        </button>
                      </>
                    )}
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
