/** 错题本 store：列表（筛选/排序/分页/滚动加载）、详情、批量选择、学科/知识点字典。 */
import { defineStore } from 'pinia'
import { mistakesApi } from '@/api/mistakes'
import { subjectsApi } from '@/api/subjects'
import type { KnowledgePoint, MistakeDetail, MistakeFilters, MistakeListItem, Subject } from '@/api/types'

const DEFAULT_FILTERS: MistakeFilters = { sort: 'created_at', order: 'desc' }

interface State {
  items: MistakeListItem[]
  total: number
  page: number
  loading: boolean
  loadingMore: boolean
  error: string | null
  filters: MistakeFilters
  filtersActive: boolean
  selectedIds: string[]
  detail: MistakeDetail | null
  detailLoading: boolean
  detailError: string | null
  subjects: Subject[]
  kps: KnowledgePoint[]
  notebookCreated: boolean
}

export const useMistakesStore = defineStore('mistakes', {
  state: (): State => ({
    items: [],
    total: 0,
    page: 1,
    loading: false,
    loadingMore: false,
    error: null,
    filters: { ...DEFAULT_FILTERS },
    filtersActive: false,
    selectedIds: [],
    detail: null,
    detailLoading: false,
    detailError: null,
    subjects: [],
    kps: [],
    notebookCreated: false,
  }),
  getters: {
    hasMore: (state) => state.items.length < state.total,
    selectedCount: (state) => state.selectedIds.length,
  },
  actions: {
    async fetchSubjects() {
      this.subjects = await subjectsApi.list()
    },
    async fetchKnowledgePoints(subjectId?: number) {
      this.kps = await subjectsApi.knowledgePoints(subjectId)
    },
    /** 从 URL query 同步筛选（切回页面恢复筛选，UI/UX 5.1）。 */
    applyFiltersFromQuery(query: Record<string, unknown>) {
      const f = { ...DEFAULT_FILTERS }
      const str = (v: unknown) => (typeof v === 'string' && v ? v : undefined)
      const num = (v: unknown) => (typeof v === 'string' && v ? Number(v) : undefined)
      f.q = str(query.q)
      f.subject_id = num(query.subject_id)
      f.status = str(query.status)
      f.error_type = str(query.error_type)
      f.source = str(query.source)
      f.tags = str(query.tags)
      f.date_from = str(query.date_from)
      f.date_to = str(query.date_to)
      f.kp_id = num(query.kp_id)  // 知识图谱/薄弱点联动
      if (str(query.sort)) f.sort = str(query.sort) as string
      if (str(query.order)) f.order = str(query.order) as string
      this.filters = f
      this.filtersActive = Object.entries(f).some(
        ([k, v]) => k !== 'sort' && k !== 'order' && v !== undefined && v !== '',
      )
    },
    async fetchList(reset = true) {
      if (reset) {
        this.page = 1
        this.loading = true
        this.error = null
      } else {
        if (!this.hasMore) return
        this.loadingMore = true
      }
      try {
        const resp = await mistakesApi.list(this.filters, this.page)
        if (reset) {
          this.items = resp.items
        } else {
          this.items = [...this.items, ...resp.items]
        }
        this.total = resp.total
        this.notebookCreated = resp.total > 0 || this.notebookCreated
      } catch (err) {
        if (reset) this.error = (err as Error).message
      } finally {
        this.loading = false
        this.loadingMore = false
      }
    },
    async loadMore() {
      this.page += 1
      await this.fetchList(false)
    },
    setFilter(patch: Partial<MistakeFilters>) {
      this.filters = { ...this.filters, ...patch }
      this.filtersActive = Object.entries(this.filters).some(
        ([k, v]) => k !== 'sort' && k !== 'order' && v !== undefined && v !== '',
      )
    },
    resetFilters() {
      this.filters = { ...DEFAULT_FILTERS }
      this.filtersActive = false
    },
    async fetchDetail(id: string) {
      this.detailLoading = true
      this.detailError = null
      try {
        this.detail = await mistakesApi.detail(id)
      } catch (err) {
        this.detailError = (err as Error).message
      } finally {
        this.detailLoading = false
      }
    },
    toggleSelect(id: string) {
      const idx = this.selectedIds.indexOf(id)
      if (idx >= 0) this.selectedIds.splice(idx, 1)
      else this.selectedIds.push(id)
    },
    selectAllVisible(checked: boolean) {
      this.selectedIds = checked ? this.items.map((it) => it.id) : []
    },
    clearSelection() {
      this.selectedIds = []
    },
    async updateMistake(id: string, payload: Record<string, unknown>) {
      const updated = await mistakesApi.update(id, payload)
      this.detail = updated
      const idx = this.items.findIndex((it) => it.id === id)
      if (idx >= 0) this.items[idx] = updated
      return updated
    },
    async removeMistake(id: string) {
      await mistakesApi.remove(id)
      this.items = this.items.filter((it) => it.id !== id)
      this.total -= 1
      if (this.detail?.id === id) this.detail = null
    },
    async batchOp(action: 'delete' | 'set_status' | 'set_color' | 'add_tags', value?: string) {
      const resp = await mistakesApi.batch(action, this.selectedIds, value)
      this.clearSelection()
      await this.fetchList(true)
      return resp
    },
  },
})
