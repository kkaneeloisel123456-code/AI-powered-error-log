import { request } from './client'
import type { KnowledgePoint, Subject } from './types'

export const subjectsApi = {
  list(): Promise<Subject[]> {
    return request<Subject[]>('/subjects')
  },
  create(name: string): Promise<Subject> {
    return request<Subject>('/subjects', { method: 'POST', body: JSON.stringify({ name }) })
  },
  update(id: number, payload: { name?: string; sort_order?: number; is_active?: boolean }): Promise<Subject> {
    return request<Subject>(`/subjects/${id}`, { method: 'PATCH', body: JSON.stringify(payload) })
  },
  remove(id: number): Promise<void> {
    return request<void>(`/subjects/${id}`, { method: 'DELETE' })
  },
  knowledgePoints(subjectId?: number): Promise<KnowledgePoint[]> {
    return request<KnowledgePoint[]>(`/knowledge-points${subjectId ? `?subject_id=${subjectId}` : ''}`)
  },
}
