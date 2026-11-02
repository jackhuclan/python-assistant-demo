export type Role = 'user' | 'assistant' | 'human_agent'

export interface ChatMessage {
  id?: number
  role: Role
  content: string
  intent?: string | null
  createdAt?: string
  streaming?: boolean
}

export interface Conversation {
  id: string
  visitorId: string
  status: 'bot' | 'human_pending' | 'human_active' | 'closed'
  intent: string | null
  messageCount?: number
  lastMessage?: string | null
  rating?: number | null
  createdAt: string
  updatedAt: string
}

export interface Faq {
  id: number
  question: string
  answer: string
  keywords: string
  enabled: boolean
  createdAt: string
}

export interface Stats {
  totalConversations: number
  totalMessages: number
  transferredConversations: number
  feedback: { count: number; avgRating: number | null; distribution: Record<string, number> }
  intentDistribution: Record<string, number>
  intentLabels: Record<string, string>
}

export const STATUS_LABELS: Record<Conversation['status'], string> = {
  bot: '机器人',
  human_pending: '待人工',
  human_active: '人工中',
  closed: '已结束',
}

export const INTENT_LABELS: Record<string, string> = {
  refund: '退款',
  order_query: '查询订单',
  tech_support: '技术支持',
  general: '一般咨询',
}
