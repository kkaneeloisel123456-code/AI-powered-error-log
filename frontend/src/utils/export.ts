/** 导出工具（PRD 5.7）：Markdown 文件下载 / PDF 新标签打印；超 200 题提示分批。 */
import { getToken } from '@/api/client'

const EXPORT_LIMIT = 200

export interface ExportFilters {
  q?: string
  subject_id?: number
  status?: string
  error_type?: string
  tags?: string
  source?: string
  date_from?: string
  date_to?: string
  kp_id?: number
  sort?: string
  order?: string
}

function buildQuery(filters: ExportFilters): string {
  const params = new URLSearchParams()
  for (const [key, value] of Object.entries(filters)) {
    if (value !== undefined && value !== null && value !== '') params.set(key, String(value))
  }
  const qs = params.toString()
  return qs ? `?${qs}` : ''
}

export async function exportMarkdown(filters: ExportFilters): Promise<void> {
  const token = getToken()
  const resp = await fetch(`/api/v1/export/markdown${buildQuery(filters)}`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  })
  if (!resp.ok) {
    const body = await resp.json().catch(() => null)
    throw new Error(body?.message ?? '导出失败，请重试；超过 200 题请分批导出')
  }
  const blob = await resp.blob()
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  const now = new Date()
  const pad = (n: number) => String(n).padStart(2, '0')
  a.download = `Recall_错题_${now.getFullYear()}${pad(now.getMonth() + 1)}${pad(now.getDate())}.md`
  a.click()
  URL.revokeObjectURL(url)
}

export function exportPdf(filters: ExportFilters): void {
  // PDF 打印排版页：新标签打开（?token= 仅本机使用，见 exports.py 注释）
  const token = getToken()
  const url = `/api/v1/export/pdf${buildQuery(filters)}${buildQuery(filters) ? '&' : '?'}token=${encodeURIComponent(token ?? '')}`
  window.open(url, '_blank')
}

export function needsBatchWarning(total: number): boolean {
  return total > EXPORT_LIMIT
}
