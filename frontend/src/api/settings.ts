import { request } from './client'
import type { SettingsView } from './types'

export const settingsApi = {
  get(): Promise<SettingsView> {
    return request<SettingsView>('/settings')
  },
  update(payload: Record<string, unknown>): Promise<SettingsView> {
    return request<SettingsView>('/settings', { method: 'PATCH', body: JSON.stringify(payload) })
  },
  testAi(payload: { base_url?: string; model?: string; api_key?: string }): Promise<{
    ok: boolean
    latency_ms: number
    model: string
    mock: boolean
    message: string
  }> {
    return request('/settings/test-ai', { method: 'POST', body: JSON.stringify(payload) })
  },
}
