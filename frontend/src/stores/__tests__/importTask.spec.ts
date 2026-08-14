import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { useImportStore } from '../importTask'

const mockUpload = vi.fn()
const mockGetTask = vi.fn()
const mockGetCandidates = vi.fn()
const mockImport = vi.fn()
const mockRetry = vi.fn()
const mockCancel = vi.fn()

vi.mock('@/api/import', () => ({
  importApi: {
    upload: (...args: unknown[]) => mockUpload(...args),
    getTask: (id: string) => mockGetTask(id),
    getCandidates: (id: string) => mockGetCandidates(id),
    retryTask: (id: string) => mockRetry(id),
    cancelTask: (id: string) => mockCancel(id),
    importCandidates: (...args: unknown[]) => mockImport(...args),
    textSuggest: vi.fn(),
  },
}))

function makeCandidate(overrides: Record<string, unknown> = {}) {
  return {
    question_text: '一物体做匀加速运动',
    options: ['A. 10m', 'B. 25m'],
    answer: 'B',
    analysis: '由位移公式得',
    knowledge_point: '牛顿运动定律',
    difficulty: 'medium',
    error_type: 'calculation',
    tags: [],
    subject_id: null,
    confidence_fields: [],
    task_id: 'task_1',
    selected: true,
    ...overrides,
  }
}

describe('importTask store（M2：任务状态机/候选题/草稿）', () => {
  beforeEach(() => {
    localStorage.clear()
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('upload 后进入轮询并加载候选题', async () => {
    mockUpload.mockResolvedValue({ task_id: 'task_1', status: 'ocr_running', progress: { phase: 'ocr_running', percent: 10 } })
    mockGetTask.mockResolvedValue({ task_id: 'task_1', type: 'ocr', status: 'awaiting_confirm', progress: { phase: 'awaiting_confirm', percent: 70 }, result_url: '/candidates', error: null })
    mockGetCandidates.mockResolvedValue({ task_id: 'task_1', status: 'awaiting_confirm', candidates: [makeCandidate()] })

    const store = useImportStore()
    await store.upload(new File(['x'], 'exam.png', { type: 'image/png' }), 'c1')
    expect(store.taskId).toBe('task_1')
    await store.poll('task_1')
    expect(store.taskStatus).toBe('awaiting_confirm')
    expect(store.candidates).toHaveLength(1)
    expect(store.candidates[0].selected).toBe(true)
    expect(localStorage.getItem('recall-import-draft')).toBeTruthy()
  })

  it('failed 状态进入错误态并可重试', async () => {
    mockGetTask.mockResolvedValue({ task_id: 'task_2', type: 'ocr', status: 'failed', progress: { phase: 'failed', percent: 100 }, result_url: null, error: '未识别到清晰文字' })
    const store = useImportStore()
    store.taskId = 'task_2'
    await store.poll('task_2')
    expect(store.taskError).toBe('未识别到清晰文字')
  })

  it('候选题勾选/编辑/删除', () => {
    const store = useImportStore()
    store.candidates = [makeCandidate(), makeCandidate({ question_text: '第二题' })]
    store.toggleCandidate(0)
    expect(store.selectedCandidates).toHaveLength(1)
    store.updateCandidate(1, { answer: 'C' })
    expect(store.candidates[1].answer).toBe('C')
    store.removeCandidate(1)
    expect(store.candidates).toHaveLength(1)
  })

  it('编辑后清除对应低置信度标记', () => {
    const store = useImportStore()
    store.candidates = [makeCandidate({ confidence_fields: ['answer', 'analysis'] })]
    store.updateCandidate(0, { answer: 'B' })
    expect(store.candidates[0].confidence_fields).toEqual(['analysis'])
  })

  it('导入只提交勾选题并清理草稿', async () => {
    mockImport.mockResolvedValue({ imported: 1, duplicates: 0, mistake_ids: ['m_1'] })
    const store = useImportStore()
    store.candidates = [makeCandidate(), makeCandidate({ question_text: '第二题', selected: false })]
    const result = await store.importSelected()
    expect(result!.imported).toBe(1)
    expect(store.taskId).toBeNull()
    expect(localStorage.getItem('recall-import-draft')).toBeNull()
  })

  it('草稿恢复', () => {
    localStorage.setItem('recall-import-draft', JSON.stringify({
      taskId: 'task_9', candidates: [makeCandidate({ task_id: 'task_9' })], savedAt: new Date().toISOString(),
    }))
    mockGetCandidates.mockResolvedValue({ task_id: 'task_9', status: 'awaiting_confirm', candidates: [makeCandidate({ task_id: 'task_9' })] })
    const store = useImportStore()
    expect(store.hasDraft).toBe(true)
    store.restoreDraft()
    expect(store.taskId).toBe('task_9')
    expect(store.taskStatus).toBe('awaiting_confirm')
  })
})
