import { request } from './client'

export interface TrendDay {
  date: string
  created: number
  reviewed: number
  accuracy: number
}

export interface DashboardSummary {
  range_days: number
  totals: { mistakes: number; reviews: number }
  trend: TrendDay[]
  subjects: Array<{ name: string; value: number }>
  errors: Array<{ type: string; value: number }>
  statuses: Array<{ status: string; value: number }>
  weak_points: Array<{ kp_id: number; name: string; subject_name: string; mistake_count: number; recent_wrong: number; score: number }>
}

export interface GraphNode {
  id: number
  name: string
  level: number
  subject_id: number
  value: number
  mastery: number
  status_counts: Record<string, number>
}

export interface GraphData {
  subject_id: number | null
  nodes: GraphNode[]
  edges: Array<{ source: number; target: number; type: string }>
}

export const dashboardApi = {
  summary(rangeDays: 7 | 30): Promise<DashboardSummary> {
    return request(`/dashboard/summary?range_days=${rangeDays}`)
  },
  graph(subjectId?: number): Promise<GraphData> {
    return request(`/graph/knowledge${subjectId ? `?subject_id=${subjectId}` : ''}`)
  },
}
