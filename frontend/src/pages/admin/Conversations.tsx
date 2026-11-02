import { useCallback, useEffect, useState } from 'react'
import { api } from '../../lib/api'
import { Conversation, INTENT_LABELS, STATUS_LABELS } from '../../types'
import ConversationDetail from './ConversationDetail'

const STATUSES = ['', 'bot', 'human_pending', 'human_active', 'closed'] as const
const INTENTS = ['', 'refund', 'order_query', 'tech_support', 'general'] as const

export default function Conversations() {
  const [list, setList] = useState<Conversation[]>([])
  const [status, setStatus] = useState<string>('')
  const [intent, setIntent] = useState<string>('')
  const [selected, setSelected] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(async () => {
    try {
      const params = new URLSearchParams()
      if (status) params.set('status', status)
      if (intent) params.set('intent', intent)
      const data = await api.get<{ conversations: Conversation[] }>(`/api/admin/conversations?${params}`)
      setList(data.conversations)
    } catch (e) {
      setError((e as Error).message)
    }
  }, [status, intent])

  useEffect(() => {
    load()
  }, [load])

  return (
    <div className="flex h-full">
      <div className="flex w-[480px] shrink-0 flex-col border-r border-slate-200 bg-white">
        <div className="border-b border-slate-100 p-4">
          <h2 className="mb-3 text-base font-semibold">对话记录</h2>
          <div className="flex gap-2">
            <select value={status} onChange={(e) => setStatus(e.target.value)} className="rounded-lg border border-slate-200 px-3 py-2 text-sm">
              {STATUSES.map((s) => (
                <option key={s} value={s}>{s ? STATUS_LABELS[s as Conversation['status']] : '全部状态'}</option>
              ))}
            </select>
            <select value={intent} onChange={(e) => setIntent(e.target.value)} className="rounded-lg border border-slate-200 px-3 py-2 text-sm">
              {INTENTS.map((i) => (
                <option key={i} value={i}>{i ? INTENT_LABELS[i] : '全部意图'}</option>
              ))}
            </select>
            <button onClick={load} className="ml-auto rounded-lg border border-slate-200 px-3 py-2 text-sm hover:bg-slate-50">
              刷新
            </button>
          </div>
        </div>
        <div className="flex-1 space-y-2 overflow-y-auto p-4">
          {error && <div className="rounded-lg bg-rose-50 px-3 py-2 text-sm text-rose-600">{error}</div>}
          {list.length === 0 && !error && <div className="mt-10 text-center text-sm text-slate-400">暂无会话记录</div>}
          {list.map((c) => (
            <button
              key={c.id}
              onClick={() => setSelected(c.id)}
              className={`w-full rounded-lg border p-3 text-left text-sm transition ${
                selected === c.id ? 'border-indigo-400 bg-indigo-50' : 'border-slate-100 hover:bg-slate-50'
              }`}
            >
              <div className="mb-1 flex items-center gap-2 text-xs">
                <span
                  className={`rounded-full px-2 py-0.5 ${
                    c.status === 'human_pending'
                      ? 'bg-amber-100 text-amber-700'
                      : c.status === 'human_active'
                        ? 'bg-sky-100 text-sky-700'
                        : c.status === 'closed'
                          ? 'bg-slate-100 text-slate-500'
                          : 'bg-emerald-100 text-emerald-700'
                  }`}
                >
                  {STATUS_LABELS[c.status]}
                </span>
                {c.intent && <span className="rounded bg-indigo-50 px-1.5 py-0.5 text-indigo-600">{INTENT_LABELS[c.intent] ?? c.intent}</span>}
                {c.rating != null && <span className="text-amber-500">{'★'.repeat(c.rating)}</span>}
                <span className="ml-auto text-slate-400">{c.updatedAt.slice(5, 16).replace('T', ' ')}</span>
              </div>
              <p className="truncate">{c.lastMessage || '（无消息）'}</p>
              <p className="mt-0.5 text-xs text-slate-400">访客 {c.visitorId.slice(0, 8)} · {c.messageCount} 条消息</p>
            </button>
          ))}
        </div>
      </div>
      <div className="flex-1 overflow-y-auto">
        {selected ? <ConversationDetail conversationId={selected} /> : <div className="flex h-full items-center justify-center text-sm text-slate-400">选择左侧会话查看详情</div>}
      </div>
    </div>
  )
}
