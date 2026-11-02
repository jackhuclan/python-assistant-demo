import { useCallback, useEffect, useRef, useState } from 'react'
import { api, streamSse } from '../lib/api'
import type { ChatMessage } from '../types'

const POLL_INTERVAL = 3000

export default function Chat() {
  const [conversationId, setConversationId] = useState<string | null>(null)
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [input, setInput] = useState('')
  const [sending, setSending] = useState(false)
  const [status, setStatus] = useState<'bot' | 'human_pending' | 'human_active' | 'closed'>('bot')
  const [intentTag, setIntentTag] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [showFeedback, setShowFeedback] = useState(false)
  const bottomRef = useRef<HTMLDivElement>(null)
  const lastIdRef = useRef(0)
  const pollTimer = useRef<ReturnType<typeof setInterval> | null>(null)

  const scrollToBottom = () => bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  useEffect(scrollToBottom, [messages])

  const refreshMessages = useCallback(async (cid: string) => {
    const data = await api.get<{ status: typeof status; messages: ChatMessage[] }>(
      `/api/chat/${cid}/messages?afterId=0`,
    )
    setStatus(data.status)
    lastIdRef.current = data.messages[data.messages.length - 1]?.id ?? 0
    setMessages(data.messages)
  }, [])

  const pollMessages = useCallback(
    async (cid: string) => {
      try {
        const data = await api.get<{ status: typeof status; messages: ChatMessage[] }>(
          `/api/chat/${cid}/messages?afterId=${lastIdRef.current}`,
        )
        setStatus(data.status)
        if (data.messages.length > 0) {
          lastIdRef.current = data.messages[data.messages.length - 1].id ?? 0
          setMessages((prev) => [...prev, ...data.messages])
        }
      } catch {
        /* 轮询失败静默，下轮重试 */
      }
    },
    [],
  )

  const startPolling = useCallback(
    (cid: string) => {
      if (pollTimer.current) clearInterval(pollTimer.current)
      pollTimer.current = setInterval(() => pollMessages(cid), POLL_INTERVAL)
    },
    [pollMessages],
  )

  // 初始化：恢复或创建会话
  useEffect(() => {
    const init = async () => {
      const saved = sessionStorage.getItem('csa_conversation_id')
      if (saved) {
        try {
          const data = await api.get<{ status: typeof status; messages: ChatMessage[] }>(
            `/api/chat/${saved}/messages`,
          )
          setConversationId(saved)
          setStatus(data.status)
          lastIdRef.current = data.messages[data.messages.length - 1]?.id ?? 0
          setMessages(data.messages)
          startPolling(saved)
          return
        } catch {
          sessionStorage.removeItem('csa_conversation_id')
        }
      }
      const created = await api.post<{ conversationId: string }>('/api/chat/start', {})
      sessionStorage.setItem('csa_conversation_id', created.conversationId)
      setConversationId(created.conversationId)
      startPolling(created.conversationId)
    }
    init().catch((e) => setError(e.message))
    return () => {
      if (pollTimer.current) clearInterval(pollTimer.current)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const send = async () => {
    const text = input.trim()
    if (!text || !conversationId || sending) return
    setInput('')
    setError(null)
    setSending(true)
    setMessages((prev) => [...prev, { role: 'user', content: text }])

    let botReply = ''
    try {
      await streamSse(
        `/api/chat/${conversationId}/message`,
        { content: text },
        (ev) => {
          if (ev.event === 'meta') {
            const label = (ev.data.intentLabel as string) || null
            setIntentTag(label)
          } else if (ev.event === 'delta') {
            botReply += ev.data.content as string
            setMessages((prev) => {
              const last = prev[prev.length - 1]
              if (last?.role === 'assistant' && last.streaming) {
                return [...prev.slice(0, -1), { role: 'assistant', content: botReply, streaming: true }]
              }
              return [...prev, { role: 'assistant', content: botReply, streaming: true }]
            })
          } else if (ev.event === 'transfer') {
            setStatus('human_pending')
          } else if (ev.event === 'done') {
            lastIdRef.current = 0 // 触发全量拉取，对齐服务端消息 id
          }
        },
      )
      // done 后以服务端数据为准，替换本地流式副本
      await refreshMessages(conversationId)
    } catch (e) {
      setError((e as Error).message)
    } finally {
      setSending(false)
    }
  }

  const submitFeedback = async (rating: number, comment: string) => {
    if (!conversationId) return
    await api.post(`/api/chat/${conversationId}/feedback`, { rating, comment })
    setShowFeedback(false)
    setStatus('closed')
    sessionStorage.removeItem('csa_conversation_id')
    setConversationId(null)
    setMessages([])
    setIntentTag(null)
  }

  const statusBanner =
    status === 'human_pending'
      ? { text: '已转接人工客服，请稍候…', cls: 'bg-amber-50 text-amber-700 border-amber-200' }
      : status === 'human_active'
        ? { text: '人工客服正在为您服务', cls: 'bg-sky-50 text-sky-700 border-sky-200' }
        : null

  return (
    <div className="mx-auto flex h-full max-w-3xl flex-col p-4">
      <header className="mb-3 flex items-center justify-between rounded-xl border border-slate-200 bg-white px-5 py-3 shadow-sm">
        <div className="flex items-center gap-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-full bg-indigo-600 text-lg text-white">客</div>
          <div>
            <h1 className="text-base font-semibold">智能客服</h1>
            <p className="text-xs text-slate-400">
              {status === 'closed' ? '会话已结束' : statusBanner ? statusBanner.text : 'AI 智能为您服务'}
            </p>
          </div>
        </div>
        {intentTag && (
          <span className="rounded-full bg-indigo-50 px-2.5 py-1 text-xs text-indigo-600">意图：{intentTag}</span>
        )}
      </header>

      {statusBanner && (
        <div className={`mb-3 rounded-lg border px-4 py-2 text-sm ${statusBanner.cls}`}>{statusBanner.text}</div>
      )}

      <div className="flex-1 space-y-3 overflow-y-auto rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
        {messages.length === 0 && (
          <div className="mt-16 text-center text-sm text-slate-400">
            您好，我是智能客服助手，请问有什么可以帮您？
            <div className="mt-2 text-xs">例如：如何申请退款 / 查询订单状态 / 软件无法登录</div>
          </div>
        )}
        {messages.map((m, i) => (
          <div key={m.id ?? `local-${i}`} className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div
              className={`max-w-[80%] whitespace-pre-wrap rounded-2xl px-4 py-2.5 text-sm leading-relaxed ${
                m.role === 'user'
                  ? 'rounded-br-md bg-indigo-600 text-white'
                  : m.role === 'human_agent'
                    ? 'rounded-bl-md border border-sky-200 bg-sky-50 text-slate-800'
                    : 'rounded-bl-md bg-slate-100 text-slate-800'
              }`}
            >
              {m.role === 'human_agent' && (
                <div className="mb-1 text-xs font-medium text-sky-600">人工客服</div>
              )}
              {m.content}
              {m.streaming && <span className="ml-1 inline-block animate-pulse">▌</span>}
            </div>
          </div>
        ))}
        <div ref={bottomRef} />
      </div>

      {error && <div className="mt-2 rounded-lg bg-rose-50 px-4 py-2 text-sm text-rose-600">{error}</div>}

      <footer className="mt-3 flex items-center gap-2">
        {conversationId && status !== 'closed' ? (
          <>
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && !e.shiftKey && send()}
              placeholder={status === 'bot' ? '输入消息，Enter 发送…' : '人工服务中，输入消息…'}
              className="flex-1 rounded-xl border border-slate-200 bg-white px-4 py-3 text-sm outline-none focus:border-indigo-400"
              disabled={sending}
            />
            <button
              onClick={send}
              disabled={sending || !input.trim()}
              className="rounded-xl bg-indigo-600 px-5 py-3 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-40"
            >
              发送
            </button>
            <button
              onClick={() => setShowFeedback(true)}
              className="rounded-xl border border-slate-200 bg-white px-4 py-3 text-sm text-slate-500 hover:bg-slate-50"
              title="结束本次会话并评价"
            >
              结束
            </button>
          </>
        ) : (
          <button
            onClick={() => window.location.reload()}
            className="mx-auto rounded-xl bg-indigo-600 px-6 py-3 text-sm font-medium text-white hover:bg-indigo-700"
          >
            开启新会话
          </button>
        )}
      </footer>

      {showFeedback && <FeedbackModal onSubmit={submitFeedback} onClose={() => setShowFeedback(false)} />}
    </div>
  )
}

function FeedbackModal({
  onSubmit,
  onClose,
}: {
  onSubmit: (rating: number, comment: string) => void
  onClose: () => void
}) {
  const [rating, setRating] = useState(5)
  const [comment, setComment] = useState('')
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
      <div className="w-full max-w-sm rounded-2xl bg-white p-6 shadow-xl">
        <h3 className="mb-1 text-lg font-semibold">为本次服务评分</h3>
        <p className="mb-4 text-xs text-slate-400">您的反馈将帮助我们改进服务质量</p>
        <div className="mb-4 flex justify-center gap-2 text-3xl">
          {[1, 2, 3, 4, 5].map((n) => (
            <button key={n} onClick={() => setRating(n)} className={n <= rating ? 'text-amber-400' : 'text-slate-200'}>
              ★
            </button>
          ))}
        </div>
        <textarea
          value={comment}
          onChange={(e) => setComment(e.target.value)}
          placeholder='补充意见（选填）'
          className="mb-4 w-full rounded-lg border border-slate-200 p-3 text-sm outline-none focus:border-indigo-400"
          rows={3}
        />
        <div className="flex gap-2">
          <button onClick={onClose} className="flex-1 rounded-lg border border-slate-200 py-2.5 text-sm">
            取消
          </button>
          <button
            onClick={() => onSubmit(rating, comment)}
            className="flex-1 rounded-lg bg-indigo-600 py-2.5 text-sm text-white hover:bg-indigo-700"
          >
            提交评价
          </button>
        </div>
      </div>
    </div>
  )
}
