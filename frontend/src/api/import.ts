import { request } from './client'

export interface TaskView {
  task_id: string
  type: string
  status: string
  progress: { phase: string; percent: number }
  result_url: string | null
  error: string | null
}

export interface Candidate {
  question_text: string
  options: string[]
  answer: string
  analysis: string
  knowledge_point: string
  difficulty: string
  error_type: string
  tags: string[]
  subject_id: number | null
  confidence_fields: string[]
  task_id: string | null
}

export interface CandidatesResponse {
  task_id: string
  status: string
  candidates: Candidate[]
}

export interface ImportResult {
  imported: number
  duplicates: number
  mistake_ids: string[]
}

export interface TextSuggest {
  subject_id: number | null
  subject_name: string
  kp_id: number | null
  kp_name: string
  error_type: string
  difficulty: string
  mock: boolean
}

export const importApi = {
  upload(file: File, clientId: string): Promise<{ task_id: string; status: string; progress: { phase: string; percent: number } }> {
    const form = new FormData()
    form.append('file', file)
    form.append('client_id', clientId)
    return request('/uploads', { method: 'POST', body: form })
  },
  getTask(taskId: string): Promise<TaskView> {
    return request(`/tasks/${taskId}`)
  },
  getCandidates(taskId: string): Promise<CandidatesResponse> {
    return request(`/tasks/${taskId}/candidates`)
  },
  retryTask(taskId: string): Promise<TaskView> {
    return request(`/tasks/${taskId}/retry`, { method: 'POST' })
  },
  cancelTask(taskId: string): Promise<void> {
    return request(`/tasks/${taskId}/cancel`, { method: 'POST' })
  },
  importCandidates(candidates: Candidate[], taskId?: string): Promise<ImportResult> {
    return request('/problems/import', {
      method: 'POST',
      body: JSON.stringify({ candidates, task_id: taskId ?? undefined }),
    })
  },
  textSuggest(payload: {
    question_text: string
    options: string[]
    answer_text: string
    analysis: string
  }): Promise<TextSuggest> {
    return request('/problems/text', { method: 'POST', body: JSON.stringify({ ...payload, use_ai: true }) })
  },
}
