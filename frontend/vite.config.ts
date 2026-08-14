import { fileURLToPath, URL } from 'node:url'

import vue from '@vitejs/plugin-vue'
import { defineConfig } from 'vitest/config'

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  server: {
    port: 5173,
    host: '127.0.0.1',  // 显式 IPv4：Playwright 与 curl 均经 127.0.0.1 访问
    proxy: {
      // 开发环境：/api 转发本地后端，SSE 长连接透传
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
    },
  },
  build: {
    // 首屏可交互 < 2s（NFR-04）：重依赖单独分块
    rollupOptions: {
      output: {
        manualChunks: {
          echarts: ['echarts/core'],
          markdown: ['marked', 'dompurify'],
          icons: ['lucide-vue-next'],
          vendor: ['vue', 'vue-router', 'pinia'],
        },
      },
    },
  },
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['src/tests/setup.ts'],
    css: false,
    exclude: ['node_modules/**', 'dist/**', 'e2e/**'],  // E2E 由 Playwright 运行
  },
})
