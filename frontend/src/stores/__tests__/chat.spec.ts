import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { useChatStore } from '../chat'

const mockList = vi.fn()
const mockGetMessages = vi.fn()
const mockDelete = vi.fn()
const mockClear = vi.fn()
const mockExtract = vi.fn()
const mockUpdate = vi.fn()

vi.mock('@/api/chat', () => ({
  chatApi: {
    listConversations: (...a: unknown[]) => mockList(...a),
    createConversation: vi.fn(),
    getMessages: (...a: unknown[]) => mockGetMessages(...a),
    updateConversation: (...a: unknown[]) => mockUpdate(...a),
    deleteConversation: (...a: unknown[]) => mockDelete(...a),
    clearConversation: (...a: unknown[]) => mockClear(...a),
    extract: (...a: unknown[]) => mockExtract(...a),
  },
}))

const mockStreamSSE = vi.fn()
vi.mock('@/api/client', () => ({
  streamSSE: (...a: unknown[]) => mockStreamSSE(...a),
}))

describe('chat store（M5：流式/停止/继续/提取草稿）', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
    mockList.mockResolvedValue([])
    mockGetMessages.mockResolvedValue([])
  })

  it('send 时用户消息先行上屏，token 流式累加', async () => {
    let onEvent: ((event: string, data: unknown) => void) | null = null
    mockStreamSSE.mockImplementation((_path: string, _body: unknown, cb: typeof onEvent) => {
      onEvent = cb
      return { abort: vi.fn() }
    })
    const store = useChatStore()
    await store.send('为什么选 C？')
    expect(store.messages).toHaveLength(2)
    expect(store.messages[0].role).toBe('user')
    onEvent!('token', { delta: '这' })
    onEvent!('token', { delta: '道题' })
    expect(store.messages[1].content).toBe('这道题')
    expect(store.messages[1].streaming).toBe(true)
  })

  it('done 事件结束流式并记录会话', async () => {
    let onEvent: ((event: string, data: unknown) => void) | null = null
    mockStreamSSE.mockImplementation((_p: string, _b: unknown, cb: typeof onEvent) => {
      onEvent = cb
      return { abort: vi.fn() }
    })
    const store = useChatStore()
    await store.send('x')
    onEvent!('token', { delta: 'a' })
    onEvent!('done', { conversation_id: 'conv_1', message_id: 'msg_1' })
    expect(store.streaming).toBe(false)
    expect(store.conversationId).toBe('conv_1')
    expect(store.messages[1].streaming).toBe(false)
  })

  it('error 事件保留已渲染内容并置错误态', async () => {
    let onEvent: ((event: string, data: unknown) => void) | null = null
    mockStreamSSE.mockImplementation((_p: string, _b: unknown, cb: typeof onEvent) => {
      onEvent = cb
      return { abort: vi.fn() }
    })
    const store = useChatStore()
    await store.send('x')
    onEvent!('token', { delta: '部分内容' })
    onEvent!('error', { code: 'AI_UNAVAILABLE', message: 'AI 服务暂时繁忙，请稍后重试' })
    expect(store.error).toBe('AI 服务暂时繁忙，请稍后重试')
    expect(store.messages[1].content).toBe('部分内容')  // 中断保留已渲染部分
    expect(store.messages[1].streaming).toBe(false)
  })

  it('stop 中断保留内容', async () => {
    const abortSpy = vi.fn()
    mockStreamSSE.mockReturnValue({ abort: abortSpy })
    const store = useChatStore()
    await store.send('x')
    store.stop()
    expect(abortSpy).toHaveBeenCalled()
    expect(store.streaming).toBe(false)
  })

  it('extractToDraft 加载草稿', async () => {
    mockExtract.mockResolvedValue({ question_text: 'q', options: [], answer: '', analysis: 'a', mock: true })
    const store = useChatStore()
    store.conversationId = 'conv_1'
    await store.extractToDraft('msg_1')
    expect(store.draft!.question_text).toBe('q')
    expect(store.draft!.mock).toBe(true)
  })
})
