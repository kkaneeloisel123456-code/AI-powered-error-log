/** 时间与数字格式化（ISO 8601 本地时间入参）。 */

export function formatDate(iso: string | null | undefined): string {
  if (!iso) return '—'
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return '—'
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`
}

export function formatRelative(iso: string | null | undefined): string {
  if (!iso) return '未复习'
  const d = new Date(iso).getTime()
  if (Number.isNaN(d)) return '未复习'
  const diff = Date.now() - d
  const day = 24 * 3600 * 1000
  if (diff < day) return '今天'
  if (diff < 2 * day) return '1 天前'
  if (diff < 7 * day) return `${Math.floor(diff / day)} 天前`
  return formatDate(iso)
}

export function formatDuration(totalSeconds: number): string {
  if (totalSeconds < 60) return `${totalSeconds}s`
  const m = Math.floor(totalSeconds / 60)
  const s = totalSeconds % 60
  return s === 0 ? `${m}m` : `${m}m${s}s`
}

export function percent(value: number): string {
  return `${Math.round(value * 100)}%`
}
