/** 复习会话 store（T-M3-01~06）：配置 -> 变体题 -> 逐题作答 -> 交卷 -> 批改结果 -> 重批。 */
import { defineStore } from 'pinia'
import { reviewsApi } from '@/api/reviews'
import type { ReviewConfig, ReviewReport, Variant } from '@/api/reviews'

interface AnswerEntry {
  answer: string
  unsure: boolean
}

interface State {
  config: ReviewConfig | null
  sessionId: string | null
  status: 'idle' | 'generating' | 'answering' | 'submitting' | 'grading' | 'done'
  variants: Variant[]
  replaceLeft: number
  answers: Record<string, AnswerEntry>
  currentIndex: number
  startedAt: number | null
  report: ReviewReport | null
  error: string | null
  pollTimer: number | null
}

export const useReviewStore = defineStore('review', {
  state: (): State => ({
    config: null,
    sessionId: null,
    status: 'idle',
    variants: [],
    replaceLeft: 0,
    answers: {},
    currentIndex: 0,
    startedAt: null,
    report: null,
    error: null,
    pollTimer: null,
  }),
  getters: {
    total: (state) => state.variants.length,
    answeredCount: (state) => Object.values(state.answers).filter((a) => a.answer.trim() !== '').length,
    unansweredCount(): number {
      return this.total - this.answeredCount
    },
  },
  actions: {
    async createSession(config: ReviewConfig) {
      this.config = config
      this.status = 'generating'
      this.error = null
      this.variants = []
      this.answers = {}
      this.currentIndex = 0
      this.report = null
      this.startedAt = Date.now()
      const resp = await reviewsApi.createSession(config)
      this.sessionId = resp.session_id
      this.startGeneratePolling()
    },
    startGeneratePolling() {
      this.stopPolling()
      this.pollTimer = window.setInterval(() => void this.pollGenerate(), 500)
    },
    async pollGenerate() {
      if (!this.sessionId) return
      try {
        const resp = await reviewsApi.generate(this.sessionId)
        if (resp.status === 'answering' && resp.variants.length) {
          this.variants = resp.variants
          this.replaceLeft = resp.replace_left
          this.status = 'answering'
          this.stopPolling()
        } else if (resp.status === 'failed') {
          this.status = 'idle'
          this.error = '变体题生成失败，请重试'
          this.stopPolling()
        }
      } catch (err) {
        this.error = (err as Error).message
        this.stopPolling()
      }
    },
    async replaceVariant(variantId: string) {
      if (!this.sessionId) return
      try {
        const resp = await reviewsApi.generate(this.sessionId, variantId)
        this.variants = resp.variants
        this.replaceLeft = resp.replace_left
        delete this.answers[variantId]
      } catch (err) {
        this.error = (err as Error).message
      }
    },
    setAnswer(variantId: string, answer: string, unsure: boolean) {
      this.answers[variantId] = { answer, unsure }
    },
    async submit() {
      if (!this.sessionId) return
      // EX-08：未作答确认由页面弹窗处理；确认交卷后未答题按错误计
      this.status = 'submitting'
      const answers = Object.entries(this.answers).map(([variant_id, a]) => ({
        variant_id, answer: a.answer, unsure: a.unsure,
      }))
      await reviewsApi.submit(this.sessionId, answers)
      this.status = 'grading'
      this.startGradingPolling()
    },
    startGradingPolling() {
      this.stopPolling()
      this.pollTimer = window.setInterval(() => void this.pollResult(), 500)
    },
    async pollResult() {
      if (!this.sessionId) return
      try {
        const resp = await reviewsApi.result(this.sessionId)
        if (resp.status === 'done' && resp.report) {
          this.report = resp.report
          this.status = 'done'
          this.stopPolling()
        }
      } catch (err) {
        this.error = (err as Error).message
        this.stopPolling()
      }
    },
    async regrade(variantId: string) {
      if (!this.sessionId) return
      const resp = await reviewsApi.regrade(this.sessionId, variantId)
      this.report = resp.report
    },
    stopPolling() {
      if (this.pollTimer !== null) {
        clearInterval(this.pollTimer)
        this.pollTimer = null
      }
    },
    reset() {
      this.stopPolling()
      this.$reset()
    },
  },
})
