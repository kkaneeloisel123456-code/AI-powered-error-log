/**
 * API 客户端（开发规划 5.2：页面只能通过 api/ 层调用后端）
 * - Bearer 本地令牌
 * - 网络错误自动重试 3 次（指数退避），仍失败抛 ApiError
 * - 错误统一归一化为 { code, message, details }
 */
export interface ApiErrorBody {
  code: string
  message: string
  details: Record<string, unknown>
}

export class ApiError extends Error {
  code: string
  details: Record<string, unknown>
  status: number

  constructor(status: number, body: ApiErrorBody) {
    super(body.message)
    this.code = body.code
    this.details = body.details
    this.status = status
  }
}

const TOKEN_KEY = 'recall-token'
const MAX_RETRIES = 3

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY)
}

export function setToken(token: string) {
  localStorage.setItem(TOKEN_KEY, token)
}

export function clearToken() {
  localStorage.removeItem(TOKEN_KEY)
}

export function hasToken(): boolean {
  return !!getToken()
}

async function sleep(ms: number) {
  return new Promise((r) => setTimeout(r, ms))
}

export async function request<T>(
  path: string,
  options: RequestInit = {},
  retries = MAX_RETRIES,
): Promise<T> {
  const headers: Record<string, string> = {
    ...(options.headers as Record<string, string> | undefined),
  }
  const token = getToken()
  if (token) headers['Authorization'] = `Bearer ${token}`
  // JSON body 显式声明 Content-Type（无此头时 FastAPI 无法解析请求体）
  if (options.body && typeof options.body === 'string' && !headers['Content-Type']) {
    headers['Content-Type'] = 'application/json'
  }

  let attempt = 0
  for (;;) {
    attempt += 1
    try {
      const resp = await fetch(`/api/v1${path}`, { ...options, headers })
      if (resp.status === 401) {
        // 令牌失效：清空并通知（由路由守卫跳登录）
        clearToken()
        window.dispatchEvent(new CustomEvent('recall:unauthorized'))
        throw new ApiError(401, {
          code: 'NOT_AUTHENTICATED',
          message: '本地访问令牌无效',
          details: {},
        })
      }
      if (!resp.ok) {
        let body: ApiErrorBody = { code: 'INTERNAL_ERROR', message: `请求失败（${resp.status}）`, details: {} }
        try {
          body = (await resp.json()) as ApiErrorBody
        } catch {
          /* 非 JSON 错误体 */
        }
        throw new ApiError(resp.status, body)
      }
      if (resp.status === 204) return undefined as T
      return (await resp.json()) as T
    } catch (err) {
      if (err instanceof ApiError) throw err
      // 网络层错误：指数退避重试（EX-05），保留幂等语义由后端幂等键兜底
      if (attempt < retries) {
        await sleep(300 * 2 ** (attempt - 1))
        continue
      }
      throw new ApiError(0, { code: 'NETWORK_ERROR', message: '网络异常，请检查网络后重试', details: {} })
    }
  }
}

/** SSE 流式请求：回调 onEvent(event, data)，返回 AbortController。 */
export function streamSSE(
  path: string,
  body: unknown,
  onEvent: (event: string, data: unknown) => void,
): AbortController {
  const controller = new AbortController()
  void (async () => {
    try {
      const headers: Record<string, string> = { 'Content-Type': 'application/json' }
      const token = getToken()
      if (token) headers['Authorization'] = `Bearer ${token}`
      const resp = await fetch(`/api/v1${path}`, {
        method: 'POST',
        headers,
        body: JSON.stringify(body),
        signal: controller.signal,
      })
      if (!resp.ok || !resp.body) {
        let msg = `请求失败（${resp.status}）`
        try {
          msg = ((await resp.json()) as ApiErrorBody).message
        } catch {
          /* ignore */
        }
        onEvent('error', { code: 'AI_UNAVAILABLE', message: msg })
        return
      }
      const reader = resp.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''
      for (;;) {
        const { done, value } = await reader.read()
        if (done) break
        buffer += decoder.decode(value, { stream: true })
        // SSE 帧按 \n\n 分隔
        let idx: number
        while ((idx = buffer.indexOf('\n\n')) >= 0) {
          const frame = buffer.slice(0, idx)
          buffer = buffer.slice(idx + 2)
          for (const line of frame.split('\n')) {
            if (line.startsWith('event:')) continue
            if (line.startsWith('data:')) {
              const eventName = frame
                .split('\n')
                .find((l) => l.startsWith('event:'))
                ?.slice(6)
                .trim() ?? 'message'
              try {
                onEvent(eventName, JSON.parse(line.slice(5).trim()))
              } catch {
                onEvent(eventName, line.slice(5).trim())
              }
            }
          }
        }
      }
    } catch (err) {
      if ((err as Error).name !== 'AbortError') {
        onEvent('error', { code: 'NETWORK_ERROR', message: '网络异常，请检查网络后重试' })
      }
    }
  })()
  return controller
}
