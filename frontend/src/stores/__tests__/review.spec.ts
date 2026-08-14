import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { useReviewStore } from '../review'

const mockCreate = vi.fn()
const mockGenerate = vi.fn()
const mockSubmit = vi.fn()
const mockResult = vi.fn()
const mockRegrade = vi.fn()

vi.mock('@/api/reviews', () => ({
  reviewsApi: {
    createSession: (...a: unknown[]) => mockCreate(...a),
    generate: (...a: unknown[]) => mockGenerate(...a),
    submit: (...a: unknown[]) => mockSubmit(...a),
    result: (...a: unknown[]) => mockResult(...a),
    regrade: (...a: unknown[]) => mockRegrade(...a),
  },
}))

function variant(id: string) {
  return {
    variant_id: id,
    source_mistake_id: 'm_1',
    question_text: `【变式】题目 ${id}`,
    options: ['A. 2m', 'B. 4m'],
    answer: 'B',
    analysis: '解析',
    knowledge_point: '动能定理',
  }
}

const report = {
  score: 50,
  correct: 1,
  wrong: 1,
  duration_s: 120,
  weak_points: ['动能定理'],
  compared_last: null,
  items: [
    { variant_id: 'v_1', source_mistake_id: 'm_1', is_correct: true, quality: 5, my_answer: 'B', correct_answer: 'B', analysis: '对', error_type: 'none', knowledge_point: '动能定理', question_excerpt: '题1' },
    { variant_id: 'v_2', source_mistake_id: 'm_1', is_correct: false, quality: 0, my_answer: '', correct_answer: 'B', analysis: '未作答', error_type: 'other', knowledge_point: '', question_excerpt: '题2' },
  ],
  session_id: 'rev_1',
}

describe('review store（M3：会话状态机/作答/交卷/批改）', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('createSession -> 轮询变体题', async () => {
    mockCreate.mockResolvedValue({ session_id: 'rev_1', status: 'generating' })
    mockGenerate.mockResolvedValue({ session_id: 'rev_1', status: 'answering', variants: [variant('v_1'), variant('v_2')], replace_left: 3 })
    const store = useReviewStore()
    await store.createSession({ subject_ids: [], count: 5, difficulty: 'auto', scope: 'all', mistake_ids: [] })
    expect(store.sessionId).toBe('rev_1')
    await store.pollGenerate()
    expect(store.status).toBe('answering')
    expect(store.total).toBe(2)
    expect(store.replaceLeft).toBe(3)
    store.stopPolling()
  })

  it('换一题递减剩余次数并清除作答', async () => {
    mockGenerate.mockResolvedValue({ session_id: 'rev_1', status: 'answering', variants: [variant('v_1')], replace_left: 2 })
    const store = useReviewStore()
    store.sessionId = 'rev_1'
    store.variants = [variant('v_1')]
    store.setAnswer('v_1', 'A', false)
    await store.replaceVariant('v_1')
    expect(store.replaceLeft).toBe(2)
    expect(store.answers['v_1']).toBeUndefined()
  })

  it('作答与未作答计数', () => {
    const store = useReviewStore()
    store.variants = [variant('v_1'), variant('v_2')]
    store.setAnswer('v_1', 'B', false)
    expect(store.answeredCount).toBe(1)
    expect(store.unansweredCount).toBe(1)
  })

  it('submit -> grading -> 轮询到报告', async () => {
    mockSubmit.mockResolvedValue({ session_id: 'rev_1', status: 'grading' })
    mockResult.mockResolvedValue({ session_id: 'rev_1', status: 'done', report })
    const store = useReviewStore()
    store.sessionId = 'rev_1'
    store.variants = [variant('v_1'), variant('v_2')]
    await store.submit()
    expect(store.status).toBe('grading')
    await store.pollResult()
    expect(store.status).toBe('done')
    expect(store.report!.score).toBe(50)
    expect(store.report!.items).toHaveLength(2)
    store.stopPolling()
  })

  it('regrade 更新报告', async () => {
    const newReport = { ...report, score: 100, items: report.items.map((it) => ({ ...it, is_correct: true })) }
    mockRegrade.mockResolvedValue({ session_id: 'rev_1', report: newReport, flipped: true })
    const store = useReviewStore()
    store.sessionId = 'rev_1'
    store.report = report
    await store.regrade('v_2')
    expect(store.report!.score).toBe(100)
  })
})
