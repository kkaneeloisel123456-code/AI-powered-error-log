import { request } from './client'

export interface PlanItem {
  id: string
  mistake_id: string
  due_date: string
  interval_days: number
  ease_factor: number
  status: string
  last_quality: number | null
  question_excerpt: string
  subject_name: string
  knowledge_point: string
  mistake_status: string
}

export interface TodayPlan {
  date: string
  due_count: number
  estimated_minutes: number
  items: PlanItem[]
}

export interface WeekPlan {
  start: string
  days: Array<{ date: string; count: number; suggested: number }>
}

export interface ExamPlan {
  exam_date: string
  daily_target: number
  total: number
  items: Array<Record<string, unknown>>
}

export const plansApi = {
  today(): Promise<TodayPlan> {
    return request('/plans/today')
  },
  week(): Promise<WeekPlan> {
    return request('/plans/week')
  },
  exam(examDate: string, dailyTarget: number): Promise<ExamPlan> {
    return request('/plans/exam', { method: 'POST', body: JSON.stringify({ exam_date: examDate, daily_target: dailyTarget }) })
  },
  updateItem(itemId: string, action: 'complete' | 'skip' | 'reset'): Promise<{ id: string; status: string }> {
    return request(`/plans/items/${itemId}`, { method: 'PATCH', body: JSON.stringify({ action }) })
  },
}
