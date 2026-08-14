import { request } from './client'

export interface ReviewConfig {
  subject_ids: number[]
  count: number
  difficulty: string
  scope: string
  mistake_ids: string[]
}

export interface Variant {
  variant_id: string
  source_mistake_id: string
  question_text: string
  options: string[]
  answer: string
  analysis: string
  knowledge_point: string
}

export interface ReviewReportItem {
  variant_id: string
  source_mistake_id: string
  is_correct: boolean
  quality: number
  my_answer: string
  correct_answer: string
  analysis: string
  error_type: string
  knowledge_point: string
  question_excerpt: string
}

export interface ReviewReport {
  score: number
  correct: number
  wrong: number
  duration_s: number
  weak_points: string[]
  compared_last: { score_delta: number } | null
  items: ReviewReportItem[]
  session_id: string
}

export const reviewsApi = {
  createSession(config: ReviewConfig): Promise<{ session_id: string; status: string }> {
    return request('/reviews/sessions', { method: 'POST', body: JSON.stringify(config) })
  },
  generate(sessionId: string, replaceVariantId?: string): Promise<{
    session_id: string
    status: string
    variants: Variant[]
    replace_left: number
  }> {
    return request('/reviews/generate', {
      method: 'POST',
      body: JSON.stringify({ session_id: sessionId, replace_variant_id: replaceVariantId ?? null }),
    })
  },
  submit(sessionId: string, answers: Array<{ variant_id: string; answer: string; unsure: boolean }>): Promise<{ session_id: string; status: string }> {
    return request(`/reviews/${sessionId}/submit`, { method: 'POST', body: JSON.stringify({ answers }) })
  },
  result(sessionId: string): Promise<{ session_id: string; status: string; report: ReviewReport | null }> {
    return request(`/reviews/${sessionId}/result`)
  },
  regrade(sessionId: string, variantId: string): Promise<{ session_id: string; report: ReviewReport; flipped: boolean }> {
    return request(`/reviews/${sessionId}/regrade`, { method: 'POST', body: JSON.stringify({ variant_id: variantId }) })
  },
}
