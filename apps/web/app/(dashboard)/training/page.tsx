'use client';

import { Brain } from 'lucide-react';

export default function TrainingPage() {
  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-gray-900">模型训练</h1>
      <div className="bg-white rounded-xl border border-gray-200 p-12 text-center">
        <Brain className="w-12 h-12 text-gray-300 mx-auto mb-4" />
        <p className="text-gray-500">暂无训练任务</p>
      </div>
    </div>
  );
}
