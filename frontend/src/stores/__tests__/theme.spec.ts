import { beforeEach, describe, expect, it } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { useThemeStore } from '../theme'

describe('theme store（M0：主题切换与持久化）', () => {
  beforeEach(() => {
    localStorage.clear()
    setActivePinia(createPinia())
  })

  it('默认跟随系统偏好并写入 data-theme', () => {
    const store = useThemeStore()
    store.apply()
    const attr = document.documentElement.getAttribute('data-theme')
    expect(['light', 'dark']).toContain(attr)
  })

  it('toggle 后持久化到 localStorage', () => {
    const store = useThemeStore()
    const before = store.theme
    store.toggle()
    expect(store.theme).not.toBe(before)
    expect(localStorage.getItem('recall-theme')).toBe(store.theme)
    expect(document.documentElement.getAttribute('data-theme')).toBe(store.theme)
  })

  it('已保存主题优先于系统偏好', () => {
    localStorage.setItem('recall-theme', 'dark')
    const store = useThemeStore()
    expect(store.theme).toBe('dark')
  })

  it('set 显式切换主题', () => {
    const store = useThemeStore()
    store.set('light')
    expect(store.theme).toBe('light')
    store.set('dark')
    expect(store.theme).toBe('dark')
  })
})
