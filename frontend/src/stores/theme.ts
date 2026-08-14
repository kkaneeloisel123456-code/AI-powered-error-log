/** 主题 store（UI/UX 2.4）：默认跟随系统，手动切换后持久化。 */
import { defineStore } from 'pinia'

export type Theme = 'light' | 'dark'

const STORAGE_KEY = 'recall-theme'

function systemTheme(): Theme {
  return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
}

function readSaved(): Theme | null {
  const v = localStorage.getItem(STORAGE_KEY)
  return v === 'light' || v === 'dark' ? v : null
}

export const useThemeStore = defineStore('theme', {
  state: () => ({
    theme: (readSaved() ?? systemTheme()) as Theme,
  }),
  actions: {
    apply() {
      document.documentElement.setAttribute('data-theme', this.theme)
    },
    toggle() {
      this.theme = this.theme === 'light' ? 'dark' : 'light'
      localStorage.setItem(STORAGE_KEY, this.theme)
      this.apply()
    },
    set(theme: Theme) {
      this.theme = theme
      localStorage.setItem(STORAGE_KEY, theme)
      this.apply()
    },
  },
})
