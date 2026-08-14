import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { useMistakesStore } from '../mistakes'

const mockList = vi.fn()
const mockSubjects = vi.fn()
const mockKps = vi.fn()

vi.mock('@/api/mistakes', () => ({
  mistakesApi: {
    list: (...args: unknown[]) => mockList(...args),
    detail: vi.fn(),
    create: vi.fn(),
    update: vi.fn(),
    remove: vi.fn(),
    batch: vi.fn(),
  },
}))
vi.mock('@/api/subjects', () => ({
  subjectsApi: {
    list: () => mockSubjects(),
    knowledgePoints: (id?: number) => mockKps(id),
    create: vi.fn(),
    update: vi.fn(),
    remove: vi.fn(),
  },
}))

function makeItem(id: string, overrides: Record<string, unknown> = {}) {
  return {
    id,
    subject_id: 1,
    subject_name: '数学',
    kp_id: null,
    knowledge_point: '',
    question_excerpt: `题目 ${id}`,
    status: 'pending',
    color: '#6B7280',
    tags: [],
    error_type: 'other',
    source: 'text',
    last_reviewed_at: null,
    review_count: 0,
    correct_count: 0,
    wrong_count: 0,
    mastery: 0,
    created_at: '2026-08-14T10:00:00',
    ...overrides,
  }
}

describe('mistakes store（M1：列表/筛选/分页/批量）', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
    mockSubjects.mockResolvedValue([{ id: 1, name: '数学', sort_order: 0, is_active: true, mistake_count: 0 }])
    mockKps.mockResolvedValue([])
  })

  it('fetchList 重置并填充数据', async () => {
    mockList.mockResolvedValue({ items: [makeItem('m_1'), makeItem('m_2')], total: 2, page: 1, page_size: 20 })
    const store = useMistakesStore()
    await store.fetchList(true)
    expect(store.items).toHaveLength(2)
    expect(store.total).toBe(2)
    expect(store.loading).toBe(false)
  })

  it('loadMore 追加下一页且 hasMore 正确', async () => {
    mockList
      .mockResolvedValueOnce({ items: [makeItem('m_1')], total: 2, page: 1, page_size: 1 })
      .mockResolvedValueOnce({ items: [makeItem('m_2')], total: 2, page: 2, page_size: 1 })
    const store = useMistakesStore()
    await store.fetchList(true)
    expect(store.hasMore).toBe(true)
    await store.loadMore()
    expect(store.items).toHaveLength(2)
    expect(store.hasMore).toBe(false)
  })

  it('fetchList 失败时进入 error 态', async () => {
    mockList.mockRejectedValue(new Error('网络异常'))
    const store = useMistakesStore()
    await store.fetchList(true)
    expect(store.error).toBe('网络异常')
    expect(store.loading).toBe(false)
  })

  it('筛选条件激活判断与重置', () => {
    const store = useMistakesStore()
    expect(store.filtersActive).toBe(false)
    store.setFilter({ status: 'wrong' })
    expect(store.filtersActive).toBe(true)
    store.resetFilters()
    expect(store.filtersActive).toBe(false)
    expect(store.filters.sort).toBe('created_at')
  })

  it('从 URL query 恢复筛选', () => {
    const store = useMistakesStore()
    store.applyFiltersFromQuery({ q: '动能', subject_id: '1', status: 'fixing' })
    expect(store.filters.q).toBe('动能')
    expect(store.filters.subject_id).toBe(1)
    expect(store.filters.status).toBe('fixing')
    expect(store.filtersActive).toBe(true)
  })

  it('批量选择与清除', () => {
    const store = useMistakesStore()
    store.items = [makeItem('m_1'), makeItem('m_2')]
    store.toggleSelect('m_1')
    store.toggleSelect('m_2')
    expect(store.selectedCount).toBe(2)
    store.selectAllVisible(true)
    expect(store.selectedIds).toHaveLength(2)
    store.clearSelection()
    expect(store.selectedCount).toBe(0)
  })

  it('updateMistake 同步列表与详情', async () => {
    const { mistakesApi } = await import('@/api/mistakes')
    const updated = makeItem('m_1', { status: 'mastered', color: '#16A34A' })
    vi.mocked(mistakesApi.update).mockResolvedValue(updated as never)
    const store = useMistakesStore()
    store.items = [makeItem('m_1')]
    const result = await store.updateMistake('m_1', { status: 'mastered' })
    expect(result.color).toBe('#16A34A')
    expect(store.items[0].status).toBe('mastered')
  })
})
