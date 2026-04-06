import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'Campus Guard AI - 校园安防智能预警系统',
  description: '面向校园安防的视频行为感知与异常事件智能预警系统',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="zh-CN">
      <body className="min-h-screen bg-gray-50 font-sans antialiased">
        {children}
      </body>
    </html>
  );
}
