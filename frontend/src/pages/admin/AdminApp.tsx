import { useEffect, useState } from 'react'
import { Link, NavLink, Navigate, Route, Routes } from 'react-router-dom'
import { api } from '../../lib/api'
import Conversations from './Conversations'
import FaqManager from './FaqManager'
import Login from './Login'
import Stats from './Stats'
import Workbench from './Workbench'

export default function AdminApp() {
  const [authed, setAuthed] = useState<boolean | null>(null)

  useEffect(() => {
    api
      .get('/api/admin/me')
      .then(() => setAuthed(true))
      .catch(() => setAuthed(false))
  }, [])

  if (authed === null) return <div className="p-10 text-center text-slate-400">加载中…</div>
  if (!authed) return <Login onSuccess={() => setAuthed(true)} />

  return (
    <div className="flex h-full">
      <aside className="flex w-52 flex-col border-r border-slate-200 bg-white">
        <div className="border-b border-slate-100 px-5 py-4">
          <div className="text-base font-semibold">智能客服后台</div>
          <div className="text-xs text-slate-400">管理控制台</div>
        </div>
        <nav className="flex-1 space-y-1 p-3">
          {[
            // 注意：必须用绝对路径。本组件挂在 splat 路由 /admin/* 下，
            // v7_relativeSplatPath 下相对路径会基于当前完整 URL 追加，导致路径累积错误
            { to: '/admin/workbench', label: '客服工作台', icon: '💬' },
            { to: '/admin/conversations', label: '对话记录', icon: '📋' },
            { to: '/admin/faqs', label: 'FAQ 管理', icon: '📚' },
            { to: '/admin/stats', label: '满意度统计', icon: '📊' },
          ].map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) =>
                `flex items-center gap-2 rounded-lg px-3 py-2.5 text-sm ${
                  isActive ? 'bg-indigo-50 font-medium text-indigo-700' : 'text-slate-600 hover:bg-slate-50'
                }`
              }
            >
              <span>{item.icon}</span>
              {item.label}
            </NavLink>
          ))}
        </nav>
        <div className="border-t border-slate-100 p-3">
          <Link to="/" className="block rounded-lg px-3 py-2 text-sm text-slate-500 hover:bg-slate-50">
            ← 返回聊天页
          </Link>
          <button
            onClick={async () => {
              await api.post('/api/admin/logout')
              setAuthed(false)
            }}
            className="w-full rounded-lg px-3 py-2 text-left text-sm text-rose-500 hover:bg-rose-50"
          >
            退出登录
          </button>
        </div>
      </aside>

      <main className="flex-1 overflow-y-auto">
        <Routes>
          <Route index element={<Navigate to="/admin/workbench" replace />} />
          <Route path="workbench" element={<Workbench />} />
          <Route path="conversations" element={<Conversations />} />
          <Route path="faqs" element={<FaqManager />} />
          <Route path="stats" element={<Stats />} />
        </Routes>
    </main>
    </div>
  )
}
