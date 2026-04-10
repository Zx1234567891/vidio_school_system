'use client';

import { useState } from 'react';
import { Shield, User, Bell, Monitor, Keyboard, Lock, Info, Camera, Check } from 'lucide-react';

type Section = 'account' | 'notification' | 'display' | 'shortcuts' | 'security' | 'about';

const navItems = [
  { id: 'account' as Section, label: '账号设置', icon: User },
  { id: 'notification' as Section, label: '通知设置', icon: Bell },
  { id: 'display' as Section, label: '显示设置', icon: Monitor },
  { id: 'shortcuts' as Section, label: '快捷键', icon: Keyboard },
  { id: 'security' as Section, label: '安全设置', icon: Lock },
  { id: 'about' as Section, label: '关于', icon: Info },
];

function Toggle({ checked, onChange }: { checked: boolean; onChange: (v: boolean) => void }) {
  return (
    <button
      onClick={() => onChange(!checked)}
      className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${checked ? 'bg-blue-600' : 'bg-gray-200'}`}
    >
      <span className={`inline-block h-4 w-4 transform rounded-full bg-white shadow transition-transform ${checked ? 'translate-x-6' : 'translate-x-1'}`} />
    </button>
  );
}

export default function SettingsPage() {
  const [active, setActive] = useState<Section>('account');
  const [saved, setSaved] = useState(false);

  // 账号
  const user = JSON.parse(localStorage.getItem('auth_user') || '{"username":"admin","role":"管理员","avatar":"A"}');
  const [form, setForm] = useState({ username: user.username, name: user.username === 'admin' ? '系统管理员' : '值班员', email: 'admin@campusguard.edu.cn' });

  // 通知
  const [notif, setNotif] = useState({ sound: true, desktop: true, email: false, wechat: false, high: true, medium: true, low: false });

  // 显示
  const [darkMode, setDarkMode] = useState(false);
  const [fps, setFps] = useState('15');

  // 安全
  const [pwd, setPwd] = useState({ old: '', newPwd: '', confirm: '' });
  const [pwdMsg, setPwdMsg] = useState('');

  const saveAccount = () => {
    localStorage.setItem('auth_user', JSON.stringify({ ...user, username: form.username }));
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  };

  const handlePwd = () => {
    if (!pwd.old) { setPwdMsg('请输入原密码'); return; }
    if (!pwd.newPwd) { setPwdMsg('请输入新密码'); return; }
    if (pwd.newPwd !== pwd.confirm) { setPwdMsg('两次密码不一致'); return; }
    setPwdMsg('密码修改成功（演示模式）');
    setPwd({ old: '', newPwd: '', confirm: '' });
  };

  const shortcuts = [
    { scope: '全局', action: '打开/关闭侧边栏', key: 'Alt + S' },
    { scope: '告警', action: '跳转至实时告警', key: 'Alt + A' },
    { scope: '视频', action: '跳转至视频流管理', key: 'Alt + V' },
    { scope: '历史', action: '跳转至历史记录', key: 'Alt + H' },
    { scope: '全屏', action: '视频流全屏播放', key: 'F' },
    { scope: '刷新', action: '刷新当前页面', key: 'R' },
    { scope: '搜索', action: '聚焦搜索框', key: '/' },
    { scope: '帮助', action: '打开快捷键说明', key: '?' },
  ];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">设置</h1>
        <p className="text-sm text-gray-500 mt-1">管理您的账户和系统偏好</p>
      </div>

      <div className="flex gap-6">
        {/* 左侧导航 */}
        <div className="w-48 flex-shrink-0">
          <nav className="space-y-1">
            {navItems.map((item) => {
              const Icon = item.icon;
              return (
                <button
                  key={item.id}
                  onClick={() => setActive(item.id)}
                  className={`w-full flex items-center gap-2.5 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                    active === item.id ? 'bg-blue-50 text-blue-700' : 'text-gray-600 hover:bg-gray-100'
                  }`}
                >
                  <Icon className="w-4 h-4" />
                  {item.label}
                </button>
              );
            })}
          </nav>
        </div>

        {/* 右侧内容 */}
        <div className="flex-1 bg-white rounded-xl border border-gray-200 p-6 min-h-[500px] space-y-6">

          {/* ===== 账号设置 ===== */}
          {active === 'account' && (
            <div className="space-y-6">
              <div>
                <h2 className="text-lg font-semibold text-gray-900">账号设置</h2>
                <p className="text-sm text-gray-500 mt-1">管理您的个人信息</p>
              </div>
              <div className="flex items-center gap-4">
                <div className="relative">
                  <div className="w-20 h-20 rounded-full bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center text-white text-2xl font-bold">
                    {user.avatar || user.username[0].toUpperCase()}
                  </div>
                  <button className="absolute bottom-0 right-0 w-7 h-7 bg-white border border-gray-200 rounded-full flex items-center justify-center text-gray-500 hover:text-gray-700 shadow-sm">
                    <Camera className="w-3.5 h-3.5" />
                  </button>
                </div>
                <div>
                  <p className="font-medium text-gray-900">{form.name}</p>
                  <p className="text-sm text-gray-500">点击相机图标更换头像</p>
                </div>
              </div>
              <div className="space-y-4 max-w-lg">
                {[
                  { label: '用户名', key: 'username', val: form.username, type: 'text' },
                  { label: '姓名', key: 'name', val: form.name, type: 'text' },
                  { label: '邮箱', key: 'email', val: form.email, type: 'email' },
                ].map((f) => (
                  <div key={f.key}>
                    <label className="block text-sm font-medium text-gray-700 mb-1.5">{f.label}</label>
                    <input
                      type={f.type}
                      value={f.val}
                      onChange={(e) => setForm({ ...form, [f.key]: e.target.value })}
                      className="w-full px-4 py-2.5 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                    />
                  </div>
                ))}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1.5">角色</label>
                  <input value={user.role} disabled className="w-full px-4 py-2.5 border border-gray-200 rounded-lg bg-gray-50 text-gray-400 cursor-not-allowed" />
                </div>
              </div>
              <div className="flex items-center gap-3 pt-2">
                <button onClick={saveAccount} className="flex items-center gap-2 px-5 py-2.5 bg-blue-600 text-white rounded-lg hover:bg-blue-700 text-sm font-medium">
                  {saved ? <><Check className="w-4 h-4" />已保存</> : '保存设置'}
                </button>
                <button onClick={() => setForm({ username: user.username, name: user.username === 'admin' ? '系统管理员' : '值班员', email: 'admin@campusguard.edu.cn' })} className="px-5 py-2.5 border border-gray-200 rounded-lg hover:bg-gray-50 text-sm">取消</button>
              </div>
            </div>
          )}

          {/* ===== 通知设置 ===== */}
          {active === 'notification' && (
            <div className="space-y-6">
              <div>
                <h2 className="text-lg font-semibold text-gray-900">通知设置</h2>
                <p className="text-sm text-gray-500 mt-1">配置告警通知方式和范围</p>
              </div>
              <div className="space-y-5 max-w-lg">
                <div>
                  <h3 className="text-sm font-medium text-gray-700 mb-3">通知方式</h3>
                  <div className="space-y-3">
                    {[
                      { k: 'sound', label: '声音提醒', desc: '告警时播放提示音' },
                      { k: 'desktop', label: '桌面通知', desc: '浏览器桌面推送通知' },
                      { k: 'email', label: '邮件通知', desc: '重要告警发送至邮箱' },
                      { k: 'wechat', label: '微信推送', desc: '接入企业微信机器人' },
                    ].map((item) => (
                      <div key={item.k} className="flex items-center justify-between">
                        <div>
                          <p className="text-sm font-medium text-gray-800">{item.label}</p>
                          <p className="text-xs text-gray-400">{item.desc}</p>
                        </div>
                        <Toggle checked={notif[item.k as keyof typeof notif] as boolean} onChange={(v) => setNotif({ ...notif, [item.k]: v })} />
                      </div>
                    ))}
                  </div>
                </div>
                <div className="border-t border-gray-100 pt-4">
                  <h3 className="text-sm font-medium text-gray-700 mb-3">通知风险等级</h3>
                  <div className="space-y-3">
                    {[
                      { k: 'high', label: '高风险告警', color: 'bg-red-500' },
                      { k: 'medium', label: '中风险告警', color: 'bg-orange-500' },
                      { k: 'low', label: '低风险告警', color: 'bg-yellow-500' },
                    ].map((item) => (
                      <div key={item.k} className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <span className={`w-2.5 h-2.5 rounded-full ${item.color}`} />
                          <span className="text-sm text-gray-800">{item.label}</span>
                        </div>
                        <Toggle checked={notif[item.k as keyof typeof notif] as boolean} onChange={(v) => setNotif({ ...notif, [item.k]: v })} />
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* ===== 显示设置 ===== */}
          {active === 'display' && (
            <div className="space-y-6">
              <div>
                <h2 className="text-lg font-semibold text-gray-900">显示设置</h2>
                <p className="text-sm text-gray-500 mt-1">自定义界面显示偏好</p>
              </div>
              <div className="space-y-5 max-w-lg">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium text-gray-800">深色模式</p>
                    <p className="text-xs text-gray-400">切换系统至深色主题</p>
                  </div>
                  <Toggle checked={darkMode} onChange={(v) => setDarkMode(v)} />
                </div>
                <div className="border-t border-gray-100 pt-4">
                  <label className="block text-sm font-medium text-gray-700 mb-2">视频流帧率上限</label>
                  <select value={fps} onChange={(e) => setFps(e.target.value)} className="w-full px-4 py-2.5 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500">
                    <option value="5">5 fps（省流模式）</option>
                    <option value="10">10 fps（标准）</option>
                    <option value="15">15 fps（流畅）</option>
                    <option value="30">30 fps（高帧率）</option>
                  </select>
                  <p className="text-xs text-gray-400 mt-1.5">降低帧率可减少浏览器资源占用</p>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">视频网格布局</label>
                  <div className="grid grid-cols-3 gap-2">
                    {['1×1', '2×2', '3×3'].map((l, i) => (
                      <button key={l} className={`py-2 rounded-lg text-sm border transition-colors ${i === 1 ? 'bg-blue-50 border-blue-300 text-blue-700' : 'border-gray-200 text-gray-600 hover:bg-gray-50'}`}>{l}</button>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* ===== 快捷键 ===== */}
          {active === 'shortcuts' && (
            <div className="space-y-6">
              <div>
                <h2 className="text-lg font-semibold text-gray-900">快捷键</h2>
                <p className="text-sm text-gray-500 mt-1">系统快捷键操作说明</p>
              </div>
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
                {shortcuts.map((s) => (
                  <div key={s.scope + s.action} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg border border-gray-100">
                    <div className="flex items-center gap-2">
                      <span className="text-xs px-2 py-0.5 bg-gray-200 text-gray-600 rounded">{s.scope}</span>
                      <span className="text-sm text-gray-700">{s.action}</span>
                    </div>
                    <kbd className="px-2.5 py-1 text-xs font-mono bg-white border border-gray-200 rounded shadow-sm text-gray-600">{s.key}</kbd>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* ===== 安全设置 ===== */}
          {active === 'security' && (
            <div className="space-y-6">
              <div>
                <h2 className="text-lg font-semibold text-gray-900">安全设置</h2>
                <p className="text-sm text-gray-500 mt-1">管理密码和账户安全</p>
              </div>
              <div className="space-y-5 max-w-lg">
                <div className="bg-amber-50 border border-amber-200 rounded-lg p-3 text-sm text-amber-700">
                  演示模式下密码修改仅做演示，不会真正更新账户密码
                </div>
                <div>
                  <h3 className="text-sm font-medium text-gray-700 mb-3">修改密码</h3>
                  <div className="space-y-3">
                    {[
                      { label: '原密码', key: 'old', val: pwd.old },
                      { label: '新密码', key: 'newPwd', val: pwd.newPwd },
                      { label: '确认密码', key: 'confirm', val: pwd.confirm },
                    ].map((f) => (
                      <div key={f.key}>
                        <label className="block text-sm text-gray-600 mb-1.5">{f.label}</label>
                        <input
                          type="password"
                          value={f.val}
                          onChange={(e) => setPwd({ ...pwd, [f.key]: e.target.value })}
                          className="w-full px-4 py-2.5 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                        />
                      </div>
                    ))}
                    {pwdMsg && <p className={`text-sm ${pwdMsg.includes('成功') ? 'text-green-600' : 'text-red-500'}`}>{pwdMsg}</p>}
                    <button onClick={handlePwd} className="px-5 py-2.5 bg-blue-600 text-white rounded-lg hover:bg-blue-700 text-sm font-medium">确认修改</button>
                  </div>
                </div>
                <div className="border-t border-gray-100 pt-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-sm font-medium text-gray-800">登录日志</p>
                      <p className="text-xs text-gray-400">查看近期登录记录</p>
                    </div>
                    <button className="text-sm text-blue-600 hover:underline">查看全部</button>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* ===== 关于 ===== */}
          {active === 'about' && (
            <div className="space-y-6">
              <div>
                <h2 className="text-lg font-semibold text-gray-900">关于</h2>
                <p className="text-sm text-gray-500 mt-1">系统版本和版权信息</p>
              </div>
              <div className="flex items-start gap-4 p-4 bg-gray-50 rounded-xl border border-gray-100 max-w-md">
                <div className="w-14 h-14 bg-gradient-to-br from-blue-500 to-purple-600 rounded-2xl flex items-center justify-center flex-shrink-0">
                  <Shield className="w-8 h-8 text-white" />
                </div>
                <div>
                  <h3 className="font-bold text-gray-900 text-lg">Campus Guard AI</h3>
                  <p className="text-sm text-gray-500 mt-0.5">校园安防智能预警系统</p>
                  <div className="mt-2 space-y-1 text-xs text-gray-400">
                    <p>版本 1.0.0</p>
                    <p>基于 Next.js 14 + FastAPI 构建</p>
                    <p>AI 行为识别 · 实时告警 · 事件审核</p>
                  </div>
                </div>
              </div>
              <div className="space-y-2 text-sm text-gray-500 max-w-md">
                <p>© 2024 Campus Guard AI. 保留所有权利。</p>
                <p>本系统仅供校园安防场景使用，勿用于其他用途。</p>
              </div>
            </div>
          )}

        </div>
      </div>
    </div>
  );
}
