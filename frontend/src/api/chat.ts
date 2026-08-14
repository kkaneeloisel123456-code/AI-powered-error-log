import { request } from './client'

export interface ConversationItem {
  id: string
  title: string
  created_at: string
  updated_at: string
  archived: boolean
  message_count: number
}

export interface ChatMessage {
  id: string
  conversation_id: string
  role: 'user' | 'assistant' | 'system'
  content: string
  meta_json: string | null
  created_at: string
}

export interface ExtractDraft {
  question_text: string
  options: string[]
  answer: string
  analysis: string
  mock: boolean
}

export const chatApi = {
  listConversations(q?: string): Promise<ConversationItem[]> {
    return request(`/conversations${q ? `?q=${encodeURIComponent(q)}` : ''}`)
  },
  createConversation(): Promise<ConversationItem> {
    return request('/conversations', { method: 'POST' })
  },
  getMessages(conversationId: string): Promise<ChatMessage[]> {
    return request(`/conversations/${conversationId}/messages`)
  },
  updateConversation(conversationId: string, payload: { title?: string; archived?: boolean }): Promise<ConversationItem> {
    return request(`/conversations/${conversationId}`, { method: 'PATCH', body: JSON.stringify(payload) })
  },
  deleteConversation(conversationId: string): Promise<void> {
    return request(`/conversations/${conversationId}`, { method: 'DELETE' })
  },
  clearConversation(conversationId: string): Promise<void> {
    return request(`/conversations/${conversationId}/clear`, { method: 'POST' })
  },
  extract(conversationId: string, messageId: string): Promise<ExtractDraft> {
    return request('/chat/extract', {
      method: 'POST',
      body: JSON.stringify({ conversation_id: conversationId, message_id: messageId }),
    })
  },
}
