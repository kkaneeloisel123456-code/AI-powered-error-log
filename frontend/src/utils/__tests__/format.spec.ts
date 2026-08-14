import { describe, expect, it } from 'vitest'
import { formatDate, formatDuration, formatRelative, percent } from '../format'

describe('format 工具（M1）', () => {
  it('formatDate 输出 YYYY-MM-DD，非法/空值返回 —', () => {
    expect(formatDate('2026-08-14T10:00:00')).toBe('2026-08-14')
    expect(formatDate(null)).toBe('—')
    expect(formatDate('not-a-date')).toBe('—')
  })

  it('formatRelative 分级输出', () => {
    expect(formatRelative(null)).toBe('未复习')
    const today = new Date().toISOString()
    expect(formatRelative(today)).toBe('今天')
    const yesterday = new Date(Date.now() - 24 * 3600 * 1000).toISOString()
    expect(formatRelative(yesterday)).toBe('1 天前')
  })

  it('formatDuration 输出 m/s 组合', () => {
    expect(formatDuration(45)).toBe('45s')
    expect(formatDuration(500)).toBe('8m20s')
    expect(formatDuration(120)).toBe('2m')
  })

  it('percent 保留整数百分比', () => {
    expect(percent(0.823)).toBe('82%')
  })
})
