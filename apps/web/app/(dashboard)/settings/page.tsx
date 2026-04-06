'use client';

import { Settings } from 'lucide-react';

export default function SettingsPage() {
  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-gray-900">系统设置</h1>
      <div className="bg-white rounded-xl border border-gray-200 p-6">
        <div className="flex items-center gap-4 mb-6">
          <Settings className="w-8 h-8 text-gray-400" />
          <div>
            <h2 className="font-medium text-gray-900">系统配置</h2>
            <p className="text-sm text-gray-500">管理系统的基本配置</p>
          </div>
        </div>
        <p className="text-gray-500">设置功能开发中...</p>
      </div>
    </div>
  );
}
