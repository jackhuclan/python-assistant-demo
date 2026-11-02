import { useEffect, useState } from 'react'
import { api } from '../../lib/api'
import type { Conversation } from '../../types'

/** 只读会话详情视图（对话记录页用）。 */
export default function ConversationDetail({ conversationId }: { conversationId: string }) {
  const [data, setData] = useState<{
    conversation: Conversation
    messages: { id: number; role: string; content: string; createdAt: string }[]
  } | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    api
      .get<NonNullable<typeof data>>(`/api/admin/conversations/${conversationId}`)
      .then(setData)
      .catch((e) => setError((e as Error).message))
  }, [conversationId])

  if (error) return <div className="p-6 text-sm text-rose-600">{error}</div>
  if (!data) return <div className="p-6 text-sm text-slate-400">加载中…</div>

  const roleLabel: Record<string, string> = { user: '访客', assistant: '机器人', human_agent: '人工客服' }
  return (
    <div className="space-y-3 p-5">
      <div className="flex flex-wrap gap-x-6 gap-y-1 rounded-lg bg-slate-50 p-3 text-xs text-slate-500">
        <span>会话 ID：{data.conversation.id}</span>
        <span>访客：{data.conversation.visitorId.slice(0, 12)}</span>
        <span>创建：{data.conversation.createdAt.slice(0, 19).replace('T', ' ')}</span>
      </div>
      {data.messages.map((m) => (
        <div key={m.id} className={`flex ${m.role === 'user' ? 'justify-start' : 'justify-end'}`}>
          <div
            className={`max-w-[75%] whitespace-pre-wrap rounded-2xl px-4 py-2.5 text-sm ${
              m.role === 'user'
                ? 'rounded-bl-md bg-slate-100'
                : m.role === 'human_agent'
                  ? 'rounded-br-md bg-emerald-600 text-white'
                  : 'rounded-br-md bg-indigo-50'
            }`}
          >
            <div className="mb-0.5 text-xs opacity-70">
              {roleLabel[m.role]} · {m.createdAt.slice(11, 19)}
            </div>
            {m.content}
          </div>
        </div>
      ))}
      {data.messages.length === 0 && <div className="text-center text-sm text-slate-400">暂无消息</div>}
    </div>
  )
}
