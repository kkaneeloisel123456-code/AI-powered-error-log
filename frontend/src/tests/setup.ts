import { config } from '@vue/test-utils'

// 测试环境：禁用 transition 动画，避免异步挂起
config.global.stubs = { transition: false, 'transition-group': false }

// jsdom 未实现 matchMedia：mock 为固定 light 偏好
if (typeof window !== 'undefined' && !window.matchMedia) {
  Object.defineProperty(window, 'matchMedia', {
    writable: true,
    value: (query: string) => ({
      matches: false,
      media: query,
      onchange: null,
      addListener: () => {},
      removeListener: () => {},
      addEventListener: () => {},
      removeEventListener: () => {},
      dispatchEvent: () => false,
    }),
  })
}
