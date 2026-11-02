import { useEffect, useState } from 'react'
import { api } from '../../lib/api'
import type { Stats } from '../../types'

export default function Stats() {
  const [stats, setStats] = useState<Stats | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    api
      .get<Stats>('/api/admin/stats')
      .then(setStats)
      .catch((e) => setError((e as Error).message))
  }, [])

  if (error) return <div className="p-6 text-sm text-rose-600">{error}</div>
  if (!stats) return <div className="p-6 text-sm text-slate-400">加载中…</div>

  const cards = [
    { label: '总会话数', value: stats.totalConversations, cls: 'text-indigo-600' },
    { label: '总消息数', value: stats.totalMessages, cls: 'text-sky-600' },
    { label: '转人工会话', value: stats.transferredConversations, cls: 'text-amber-600' },
    {
      label: '平均满意度',
      value: stats.feedback.avgRating != null ? `${stats.feedback.avgRating} / 5` : '暂无评价',
      cls: 'text-emerald-600',
    },
  ]

  const maxFb = Math.max(1, ...Object.values(stats.feedback.distribution).map(Number))
  const maxIntent = Math.max(1, ...Object.values(stats.intentDistribution).map(Number))

  return (
    <div className="space-y-6 p-6">
      <h2 className="text-base font-semibold">满意度统计</h2>

      <div className="grid grid-cols-4 gap-4">
        {cards.map((c) => (
          <div key={c.label} className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
            <div className="text-xs text-slate-400">{c.label}</div>
            <div className={`mt-1 text-2xl font-semibold ${c.cls}`}>{c.value}</div>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
          <h3 className="mb-4 text-sm font-medium">
            评分分布（共 {stats.feedback.count} 次评价）
          </h3>
          {stats.feedback.count === 0 ? (
            <div className="py-8 text-center text-sm text-slate-400">暂无评价数据</div>
          ) : (
            <div className="space-y-2">
              {[5, 4, 3, 2, 1].map((star) => {
                const count = Number(stats.feedback.distribution[String(star)] ?? 0)
                return (
                  <div key={star} className="flex items-center gap-3 text-xs">
                    <span className="w-14 text-slate-500">{'★'.repeat(star)}</span>
                    <div className="h-4 flex-1 overflow-hidden rounded bg-slate-100">
                      <div
                        className="h-full rounded bg-amber-400"
                        style={{ width: `${(count / maxFb) * 100}%` }}
                      />
                    </div>
                    <span className="w-8 text-right text-slate-500">{count}</span>
                  </div>
                )
              })}
            </div>
          )}
        </div>

        <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
          <h3 className="mb-4 text-sm font-medium">意图分布（会话数）</h3>
          {Object.keys(stats.intentDistribution).length === 0 ? (
            <div className="py-8 text-center text-sm text-slate-400">暂无数据</div>
          ) : (
            <div className="space-y-2">
              {Object.entries(stats.intentDistribution).map(([intent, count]) => (
                <div key={intent} className="flex items-center gap-3 text-xs">
                  <span className="w-16 text-slate-500">{stats.intentLabels[intent] ?? intent}</span>
                  <div className="h-4 flex-1 overflow-hidden rounded bg-slate-100">
                    <div
                      className="h-full rounded bg-indigo-500"
                      style={{ width: `${(Number(count) / maxIntent) * 100}%` }}
                    />
                  </div>
                  <span className="w-8 text-right text-slate-500">{count}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
