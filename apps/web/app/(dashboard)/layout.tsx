'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import {
  LayoutDashboard,
  Video,
  AlertTriangle,
  History,
  CheckCircle,
  Settings,
  Brain,
  Menu
} from 'lucide-react';
import { useState } from 'react';

const navItems = [
  { href: '/', label: '概览', icon: LayoutDashboard },
  { href: '/streams', label: '视频流', icon: Video },
  { href: '/alerts', label: '实时告警', icon: AlertTriangle },
  { href: '/history', label: '历史记录', icon: History },
  { href: '/review', label: '审核', icon: CheckCircle },
  { href: '/training', label: '模型训练', icon: Brain },
  { href: '/settings', label: '设置', icon: Settings },
];

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const pathname = usePathname();
  const [sidebarOpen, setSidebarOpen] = useState(true);

  return (
    <div className="min-h-screen bg-gray-50 flex">
      {/* Sidebar */}
      <aside
        className={`bg-white border-r border-gray-200 transition-all duration-300 ${
          sidebarOpen ? 'w-64' : 'w-16'
        }`}
      >
        <div className="h-16 flex items-center justify-between px-4 border-b border-gray-200">
          {sidebarOpen && (
            <h1 className="text-lg font-semibold text-gray-900">Campus Guard</h1>
          )}
          <button
            onClick={() => setSidebarOpen(!sidebarOpen)}
            className="p-2 rounded-lg hover:bg-gray-100"
          >
            <Menu className="w-5 h-5 text-gray-600" />
          </button>
        </div>

        <nav className="p-2 space-y-1">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = pathname === item.href || pathname.startsWith(`${item.href}/`);

            return (
              <Link
                key={item.href}
                href={item.href}
                className={`flex items-center gap-3 px-3 py-2.5 rounded-lg transition-colors ${
                  isActive
                    ? 'bg-blue-50 text-blue-600'
                    : 'text-gray-600 hover:bg-gray-100'
                }`}
              >
                <Icon className="w-5 h-5 flex-shrink-0" />
                {sidebarOpen && <span className="text-sm font-medium">{item.label}</span>}
              </Link>
            );
          })}
        </nav>
      </aside>

      {/* Main Content */}
      <main className="flex-1 overflow-auto">
        <div className="p-6">
          {children}
        </div>
      </main>
    </div>
  );
}
