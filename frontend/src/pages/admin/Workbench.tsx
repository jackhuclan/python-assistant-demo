import { useCallback, useEffect, useRef, useState } from 'react'
import { api } from '../../lib/api'
import { Conversation, INTENT_LABELS, STATUS_LABELS } from '../../types'

export default function Workbench() {
  const [list, setList] = useState<Conversation[]>([])
  const [selected, setSelected] = useState<string | null>(null)
  const timer = useRef<ReturnType<typeof setInterval> | null>(null)

  const load = useCallback(async () => {
    try {
      const data = await api.get<{ conversations: Conversation[] }>('/api/admin/workbench/pending')
      setList(data.conversations)
      setSelected((prev) => (prev && data.conversations.some((c) => c.id === prev) ? prev : null))
    } catch {
      /* 静默重试 */
    }
  }, [])

  useEffect(() => {
    load()
    timer.current = setInterval(load, 5000)
    return () => {
      if (timer.current) clearInterval(timer.current)
    }
  }, [load])

  return (
    <div className="flex h-full">
      <div className="w-80 shrink-0 overflow-y-auto border-r border-slate-200 bg-white p-4">
        <h2 className="mb-3 text-base font-semibold">待处理会话</h2>
        {list.length === 0 && <div className="mt-10 text-center text-sm text-slate-400">暂无待处理的人工会话</div>}
        <div className="space-y-2">
          {list.map((c) => (
            <button
              key={c.id}
              onClick={() => setSelected(c.id)}
              className={`w-full rounded-lg border p-3 text-left text-sm transition ${
                selected === c.id ? 'border-indigo-400 bg-indigo-50' : 'border-slate-100 hover:bg-slate-50'
              }`}
            >
              <div className="mb-1 flex items-center justify-between">
                <span className="font-medium">
                  访客 {c.visitorId.slice(0, 8)}
                  {c.intent && (
                    <span className="ml-2 rounded bg-slate-100 px-1.5 py-0.5 text-xs text-slate-500">
                      {INTENT_LABELS[c.intent] ?? c.intent}
                    </span>
                  )}
                </span>
                <span
                  className={`rounded-full px-2 py-0.5 text-xs ${
                    c.status === 'human_pending' ? 'bg-amber-100 text-amber-700' : 'bg-sky-100 text-sky-700'
                  }`}
                >
                  {STATUS_LABELS[c.status]}
                </span>
              </div>
              <p className="truncate text-xs text-slate-400">{c.lastMessage}</p>
            </button>
          ))}
        </div>
      </div>

      <div className="flex-1">
        {selected ? (
          <WorkbenchChat conversationId={selected} onResolved={() => load()} />
        ) : (
          <div className="flex h-full items-center justify-center text-sm text-slate-400">
            从左侧选择一个会话开始人工服务
          </div>
        )}
      </div>
    </div>
  )
}

function WorkbenchChat({ conversationId, onResolved }: { conversationId: string; onResolved: () => void }) {
  const [messages, setMessages] = useState<{ id: number; role: string; content: string }[]>([])
  const [status, setStatus] = useState<Conversation['status']>('human_pending')
  const [reply, setReply] = useState('')
  const [error, setError] = useState<string | null>(null)
  const bottomRef = useRef<HTMLDivElement>(null)

  const load = useCallback(async () => {
    try {
      const data = await api.get<{
        conversation: { status: Conversation['status'] }
        messages: { id: number; role: string; content: string }[]
      }>(`/api/admin/conversations/${conversationId}`)
      setStatus(data.conversation.status)
      setMessages(data.messages)
    } catch (e) {
      setError((e as Error).message)
    }
  }, [conversationId])

  useEffect(() => {
    load()
    const t = setInterval(load, 3000)
    return () => clearInterval(t)
  }, [load])

  useEffect(() => bottomRef.current?.scrollIntoView({ behavior: 'smooth' }), [messages])

  const sendReply = async () => {
    const text = reply.trim()
    if (!text) return
    setReply('')
    try {
      await api.post(`/api/admin/conversations/${conversationId}/reply`, { content: text })
      await load()
    } catch (e) {
      setError((e as Error).message)
    }
  }

  const resolve = async () => {
    try {
      await api.post(`/api/admin/conversations/${conversationId}/resolve`)
      onResolved()
    } catch (e) {
      setError((e as Error).message)
    }
  }

  return (
    <div className="flex h-full flex-col">
      <div className="flex items-center justify-between border-b border-slate-200 bg-white px-5 py-3">
        <div>
          <span className="font-medium">会话 {conversationId.slice(0, 12)}…</span>
          <span className="ml-3 text-xs text-slate-400">
            状态：{STATUS_LABELS[status]}（每 3 秒自动刷新）
          </span>
        </div>
        <button onClick={resolve} className="rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-1.5 text-sm text-emerald-700 hover:bg-emerald-100">
          处理完成，交还机器人
        </button>
      </div>

      <div className="flex-1 space-y-3 overflow-y-auto p-5">
        {messages.map((m) => (
          <div key={m.id} className={`flex ${m.role === 'user' ? 'justify-start' : 'justify-end'}`}>
            <div
              className={`max-w-[75%] whitespace-pre-wrap rounded-2xl px-4 py-2.5 text-sm ${
                m.role === 'user'
                  ? 'rounded-bl-md bg-slate-100'
                  : m.role === 'human_agent'
                    ? 'rounded-br-md bg-emerald-600 text-white'
                    : 'rounded-br-md bg-indigo-50 text-slate-700'
              }`}
            >
              {m.role !== 'user' && (
                <div className="mb-0.5 text-xs opacity-70">{m.role === 'human_agent' ? '我（人工）' : '机器人'}</div>
              )}
              {m.content}
            </div>
          </div>
        ))}
        <div ref={bottomRef} />
      </div>

      {error && <div className="mx-5 mb-2 rounded-lg bg-rose-50 px-3 py-2 text-sm text-rose-600">{error}</div>}

      <div className="flex gap-2 border-t border-slate-200 bg-white p-4">
        <textarea
          value={reply}
          onChange={(e) => setReply(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
              e.preventDefault()
              sendReply()
            }
          }}
          placeholder="以人工客服身份回复…（Enter 发送）"
          rows={2}
          className="flex-1 resize-none rounded-lg border border-slate-200 p-3 text-sm outline-none focus:border-indigo-400"
        />
        <button onClick={sendReply} disabled={!reply.trim()} className="rounded-lg bg-emerald-600 px-5 text-sm font-medium text-white hover:bg-emerald-700 disabled:opacity-40">
          回复
        </button>
      </div>
    </div>
  )
}
