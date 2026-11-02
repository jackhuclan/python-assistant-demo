import { useEffect, useState } from 'react'
import { api } from '../../lib/api'
import type { Faq } from '../../types'

export default function FaqManager() {
  const [faqs, setFaqs] = useState<Faq[]>([])
  const [editing, setEditing] = useState<Faq | 'new' | null>(null)
  const [error, setError] = useState<string | null>(null)

  const load = () =>
    api
      .get<{ faqs: Faq[] }>('/api/faqs')
      .then((d) => setFaqs(d.faqs))
      .catch((e) => setError((e as Error).message))

  useEffect(() => {
    load()
  }, [])

  const toggle = async (faq: Faq) => {
    await api.put(`/api/faqs/${faq.id}`, { enabled: !faq.enabled })
    load()
  }

  const remove = async (faq: Faq) => {
    if (!window.confirm(`确定删除 FAQ「${faq.question}」？此操作不可恢复。`)) return
    await api.del(`/api/faqs/${faq.id}`)
    load()
  }

  return (
    <div className="p-6">
      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-base font-semibold">FAQ 知识库（{faqs.length} 条）</h2>
        <button
          onClick={() => setEditing('new')}
          className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700"
        >
          + 新增 FAQ
        </button>
      </div>
      {error && <div className="mb-3 rounded-lg bg-rose-50 px-3 py-2 text-sm text-rose-600">{error}</div>}

      <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
        <table className="w-full text-sm">
          <thead className="bg-slate-50 text-left text-xs text-slate-500">
            <tr>
              <th className="px-4 py-3">问题</th>
              <th className="px-4 py-3">关键词</th>
              <th className="px-4 py-3">状态</th>
              <th className="px-4 py-3 text-right">操作</th>
            </tr>
          </thead>
          <tbody>
            {faqs.map((f) => (
              <tr key={f.id} className="border-t border-slate-100">
                <td className="max-w-md px-4 py-3">
                  <div className="font-medium">{f.question}</div>
                  <div className="mt-0.5 line-clamp-1 text-xs text-slate-400">{f.answer}</div>
                </td>
                <td className="px-4 py-3 text-xs text-slate-500">{f.keywords}</td>
                <td className="px-4 py-3">
                  <button
                    onClick={() => toggle(f)}
                    className={`rounded-full px-2.5 py-1 text-xs ${
                      f.enabled ? 'bg-emerald-100 text-emerald-700' : 'bg-slate-100 text-slate-500'
                    }`}
                  >
                    {f.enabled ? '已启用' : '已停用'}
                  </button>
                </td>
                <td className="px-4 py-3 text-right">
                  <button onClick={() => setEditing(f)} className="mr-2 text-sm text-indigo-600 hover:underline">
                    编辑
                  </button>
                  <button onClick={() => remove(f)} className="text-sm text-rose-500 hover:underline">
                    删除
                  </button>
                </td>
              </tr>
            ))}
            {faqs.length === 0 && (
              <tr>
                <td colSpan={4} className="py-10 text-center text-slate-400">
                  暂无 FAQ
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {editing && (
        <FaqModal
          faq={editing === 'new' ? null : editing}
          onClose={() => setEditing(null)}
          onSaved={() => {
            setEditing(null)
            load()
          }}
        />
      )}
    </div>
  )
}

function FaqModal({ faq, onClose, onSaved }: { faq: Faq | null; onClose: () => void; onSaved: () => void }) {
  const [question, setQuestion] = useState(faq?.question ?? '')
  const [answer, setAnswer] = useState(faq?.answer ?? '')
  const [keywords, setKeywords] = useState(faq?.keywords ?? '')
  const [error, setError] = useState<string | null>(null)

  const save = async () => {
    try {
      if (faq) await api.put(`/api/faqs/${faq.id}`, { question, answer, keywords })
      else await api.post('/api/faqs', { question, answer, keywords })
      onSaved()
    } catch (e) {
      setError((e as Error).message)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
      <div className="w-full max-w-lg rounded-2xl bg-white p-6 shadow-xl">
        <h3 className="mb-4 text-lg font-semibold">{faq ? '编辑 FAQ' : '新增 FAQ'}</h3>
        <label className="mb-1 block text-xs text-slate-500">问题 *</label>
        <input
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          className="mb-3 w-full rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none focus:border-indigo-400"
        />
        <label className="mb-1 block text-xs text-slate-500">答案 *</label>
        <textarea
          value={answer}
          onChange={(e) => setAnswer(e.target.value)}
          rows={4}
          className="mb-3 w-full rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none focus:border-indigo-400"
        />
        <label className="mb-1 block text-xs text-slate-500">关键词（英文逗号分隔，用于检索加权）</label>
        <input
          value={keywords}
          onChange={(e) => setKeywords(e.target.value)}
          placeholder="退款,退货"
          className="mb-4 w-full rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none focus:border-indigo-400"
        />
        {error && <div className="mb-3 rounded-lg bg-rose-50 px-3 py-2 text-sm text-rose-600">{error}</div>}
        <div className="flex gap-2">
          <button onClick={onClose} className="flex-1 rounded-lg border border-slate-200 py-2.5 text-sm">
            取消
          </button>
          <button
            onClick={save}
            disabled={!question.trim() || !answer.trim()}
            className="flex-1 rounded-lg bg-indigo-600 py-2.5 text-sm text-white hover:bg-indigo-700 disabled:opacity-40"
          >
            保存
          </button>
        </div>
      </div>
    </div>
  )
}
