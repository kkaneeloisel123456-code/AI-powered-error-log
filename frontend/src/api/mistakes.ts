import { request } from './client'
import type { MistakeCreatePayload, MistakeDetail, MistakeFilters, MistakeListResponse, MistakeUpdatePayload } from './types'

function buildQuery(filters: Partial<MistakeFilters> & { page?: number; page_size?: number }): string {
  const params = new URLSearchParams()
  for (const [key, value] of Object.entries(filters)) {
    if (value !== undefined && value !== null && value !== '') {
      params.set(key, String(value))
    }
  }
  const qs = params.toString()
  return qs ? `?${qs}` : ''
}

export const mistakesApi = {
  list(filters: Partial<MistakeFilters>, page = 1, pageSize = 20): Promise<MistakeListResponse> {
    return request<MistakeListResponse>(`/mistakes${buildQuery({ ...filters, page, page_size: pageSize })}`)
  },
  detail(id: string): Promise<MistakeDetail> {
    return request<MistakeDetail>(`/mistakes/${id}`)
  },
  create(payload: MistakeCreatePayload): Promise<MistakeDetail> {
    return request<MistakeDetail>('/mistakes', { method: 'POST', body: JSON.stringify(payload) })
  },
  update(id: string, payload: MistakeUpdatePayload): Promise<MistakeDetail> {
    return request<MistakeDetail>(`/mistakes/${id}`, { method: 'PATCH', body: JSON.stringify(payload) })
  },
  remove(id: string): Promise<void> {
    return request<void>(`/mistakes/${id}`, { method: 'DELETE' })
  },
  batch(action: 'delete' | 'set_status' | 'set_color' | 'add_tags' | 'remove_tags', ids: string[], value?: string) {
    return request<{ updated: number; deleted: number }>('/mistakes/batch', {
      method: 'POST',
      body: JSON.stringify({ action, ids, value }),
    })
  },
}
