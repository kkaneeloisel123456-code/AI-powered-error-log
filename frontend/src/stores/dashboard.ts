/** 看板 store：聚合数据 + 范围切换 + 图谱。 */
import { defineStore } from 'pinia'
import { dashboardApi } from '@/api/dashboard'
import type { DashboardSummary, GraphData } from '@/api/dashboard'

export const useDashboardStore = defineStore('dashboard', {
  state: () => ({
    rangeDays: 7 as 7 | 30,
    summary: null as DashboardSummary | null,
    graph: null as GraphData | null,
    loading: false,
    error: null as string | null,
  }),
  getters: {
    isEmpty(): boolean {
      return !!this.summary && this.summary.totals.mistakes === 0
    },
  },
  actions: {
    async fetchSummary() {
      this.loading = true
      this.error = null
      try {
        this.summary = await dashboardApi.summary(this.rangeDays)
      } catch (err) {
        this.error = (err as Error).message
      } finally {
        this.loading = false
      }
    },
    async fetchGraph(subjectId?: number) {
      try {
        this.graph = await dashboardApi.graph(subjectId)
      } catch (err) {
        this.error = (err as Error).message
      }
    },
    async setRange(days: 7 | 30) {
      this.rangeDays = days
      await this.fetchSummary()
    },
  },
})
