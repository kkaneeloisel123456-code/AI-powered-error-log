/**
 * 轻量 Toast（UI/UX 2.3）：顶部居中 320px、3s 自动消失、可手动关闭。
 * 用法：app.use(toastPlugin) 后组件内 import { toast } from '@/components/common/toast'
 */
import { createApp, defineComponent, h, reactive } from 'vue'
import { X } from 'lucide-vue-next'
import type { Plugin } from 'vue'

export interface ToastItem {
  id: number
  message: string
  type: 'info' | 'success' | 'error'
}

export const toastState = reactive<{ items: ToastItem[] }>({ items: [] })

let nextId = 1

export const toast = {
  show(message: string, type: ToastItem['type'] = 'info', durationMs = 3000) {
    const id = nextId++
    toastState.items.push({ id, message, type })
    if (durationMs > 0) {
      setTimeout(() => toast.dismiss(id), durationMs)
    }
  },
  info(message: string) {
    toast.show(message, 'info')
  },
  success(message: string) {
    toast.show(message, 'success')
  },
  error(message: string) {
    toast.show(message, 'error', 4000)
  },
  dismiss(id: number) {
    const idx = toastState.items.findIndex((t) => t.id === id)
    if (idx >= 0) toastState.items.splice(idx, 1)
  },
}

const ToastContainer = defineComponent({
  setup() {
    return () =>
      h(
        'div',
        { class: 'toast-container', role: 'status', 'aria-live': 'polite' },
        toastState.items.map((t) =>
          h(
            'div',
            { class: ['toast', t.type === 'error' ? 'toast-error' : t.type === 'success' ? 'toast-success' : ''] },
            [
              h('span', { style: 'flex:1' }, t.message),
              h(
                'button',
                {
                  class: 'btn-text',
                  'aria-label': '关闭提示',
                  style: 'padding:0; height:24px; width:24px; display:flex; align-items:center; justify-content:center;',
                  onClick: () => toast.dismiss(t.id),
                },
                [h(X, { size: 14 })],
              ),
            ],
          ),
        ),
      )
  },
})

export const toastPlugin: Plugin = {
  install(app) {
    app.component('ToastContainer', ToastContainer)
    // 挂载全局容器
    if (typeof document !== 'undefined' && !document.querySelector('.toast-container')) {
      const el = document.createElement('div')
      document.body.appendChild(el)
      createApp(ToastContainer).mount(el)
    }
  },
}
