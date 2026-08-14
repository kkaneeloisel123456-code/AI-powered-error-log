/** AI 答疑 store（T-M5-01/02/03）：SSE 流式、停止/继续、会话历史、加入错题本草稿。 */
import { defineStore } from 'pinia'
import { chatApi } from '@/api/chat'
import { streamSSE } from '@/api/client'
import type { ChatMessage, ConversationItem, ExtractDraft } from '@/api/chat'

export interface UIMessage extends ChatMessage {
  streaming?: boolean
}

interface State {
  conversations: ConversationItem[]
  conversationId: string | null
  messages: UIMessage[]
  sending: boolean
  streaming: boolean
  error: string | null
  abortController: AbortController | null
  draft: ExtractDraft | null
  draftLoading: boolean
}

export const useChatStore = defineStore('chat', {
  state: (): State => ({
    conversations: [],
    conversationId: null,
    messages: [],
    sending: false,
    streaming: false,
    error: null,
    abortController: null,
    draft: null,
    draftLoading: false,
  }),
  actions: {
    async fetchConversations(q?: string) {
      this.conversations = await chatApi.listConversations(q)
    },
    async openConversation(id: string | null) {
      this.stop()
      if (id) {
        this.conversationId = id
        this.messages = await chatApi.getMessages(id)
      } else {
        this.conversationId = null
        this.messages = []
      }
    },
    async send(content: string) {
      if (!content.trim() || this.sending) return
      this.error = null
      this.sending = true
      this.streaming = true
      // 用户消息先行上屏
      const optimistic: UIMessage = {
        id: `tmp_${Date.now()}`,
        conversation_id: this.conversationId ?? '',
        role: 'user',
        content,
        meta_json: null,
        created_at: new Date().toISOString(),
      }
      this.messages.push(optimistic)
      const assistant: UIMessage = {
        id: `tmp_a_${Date.now()}`,
        conversation_id: this.conversationId ?? '',
        role: 'assistant',
        content: '',
        meta_json: null,
        created_at: new Date().toISOString(),
        streaming: true,
      }
      this.messages.push(assistant)

      this.abortController = streamSSE('/chat', {
        conversation_id: this.conversationId,
        content,
        attachments: [],
      }, (event, data) => {
        const d = data as Record<string, unknown>
        if (event === 'token') {
          assistant.content += String(d.delta ?? '')
        } else if (event === 'done') {
          this.conversationId = String(d.conversation_id)
          assistant.id = String(d.message_id)
          assistant.conversation_id = String(d.conversation_id)
          assistant.streaming = false
          this.streaming = false
          this.sending = false
          this.abortController = null
          void this.fetchConversations()
        } else if (event === 'error') {
          assistant.streaming = false
          this.streaming = false
          this.sending = false
          this.abortController = null
          this.error = String(d.message ?? 'AI 服务暂时繁忙，请稍后重试')
          if (!assistant.content) assistant.content = '（生成中断）'
        }
      })
    },
    /** 中断生成：保留已渲染内容（PRD 5.8）。 */
    stop() {
      this.abortController?.abort()
      this.abortController = null
      this.streaming = false
      this.sending = false
      const last = this.messages[this.messages.length - 1]
      if (last?.streaming) {
        last.streaming = false
        if (!last.content) last.content = '（已停止）'
      }
    },
    /** 继续生成：把已渲染内容作为上下文续写。 */
    continueLast() {
      const last = this.messages[this.messages.length - 1]
      if (!last || last.role !== 'assistant' || this.sending) return
      const prefix = last.content
      last.content = ''
      last.streaming = true
      this.streaming = true
      this.sending = true
      this.abortController = streamSSE('/chat', {
        conversation_id: this.conversationId,
        content: `（继续上文，不要重复：${prefix.slice(-80)}）请接着讲下去`,
        attachments: [],
      }, (event, data) => {
        const d = data as Record<string, unknown>
        if (event === 'token') last.content += String(d.delta ?? '')
        else if (event === 'done') {
          last.streaming = false
          this.streaming = false
          this.sending = false
          this.abortController = null
        } else if (event === 'error') {
          last.streaming = false
          this.streaming = false
          this.sending = false
          this.error = String(d.message ?? '')
          if (!last.content) last.content = '（生成中断）'
        }
      })
    },
    async renameCurrent(title: string) {
      if (!this.conversationId) return
      await chatApi.updateConversation(this.conversationId, { title })
      await this.fetchConversations()
    },
    async removeConversation(id: string) {
      await chatApi.deleteConversation(id)
      if (this.conversationId === id) await this.openConversation(null)
      await this.fetchConversations()
    },
    async clearCurrent() {
      if (!this.conversationId) return
      await chatApi.clearConversation(this.conversationId)
      this.messages = []
      await this.fetchConversations()
    },
    async extractToDraft(messageId: string) {
      if (!this.conversationId) return
      this.draftLoading = true
      try {
        this.draft = await chatApi.extract(this.conversationId, messageId)
      } finally {
        this.draftLoading = false
      }
    },
  },
})
