/** 后端契约类型（与 app/schemas 对齐）。 */

export interface MistakeListItem {
  id: string
  subject_id: number
  subject_name: string
  kp_id: number | null
  knowledge_point: string
  question_excerpt: string
  status: string
  color: string
  tags: string[]
  error_type: string
  source: string
  last_reviewed_at: string | null
  review_count: number
  correct_count: number
  wrong_count: number
  mastery: number
  created_at: string
}

export interface MistakeListResponse {
  items: MistakeListItem[]
  total: number
  page: number
  page_size: number
}

export interface MistakeDetail extends MistakeListItem {
  question_text: string
  options: string[]
  answer_text: string
  analysis: string
  difficulty: string
  source_image_url: string | null
  note: string
  first_seen_at: string | null
  due_date: string | null
}

export interface MistakeCreatePayload {
  question_text: string
  options?: string[]
  answer_text?: string
  analysis?: string
  difficulty?: string
  subject_id: number
  kp_id?: number | null
  error_type?: string
  tags?: string[]
  note?: string
  source?: string
}

export interface MistakeUpdatePayload {
  question_text?: string
  options?: string[]
  answer_text?: string
  analysis?: string
  difficulty?: string
  subject_id?: number
  kp_id?: number | null
  error_type?: string
  status?: string
  color?: string
  tags?: string[]
  note?: string
}

export interface MistakeFilters {
  q?: string
  subject_id?: number
  status?: string
  color?: string
  error_type?: string
  tags?: string
  source?: string
  date_from?: string
  date_to?: string
  kp_id?: number
  sort: string
  order: string
}

export interface Subject {
  id: number
  name: string
  sort_order: number
  is_active: boolean
  mistake_count: number
}

export interface KnowledgePoint {
  id: number
  subject_id: number
  parent_id: number | null
  name: string
  level: number
  path: string
}

export interface SettingsView {
  ai: { provider: string; base_url: string; model: string; api_key_masked: string; has_api_key: boolean; mock: boolean }
  privacy: { send_question_to_ai: boolean; lan_enabled: boolean }
  default_review: { count: number; difficulty: string; scope: string }
  token_masked: string
  version: string
}
