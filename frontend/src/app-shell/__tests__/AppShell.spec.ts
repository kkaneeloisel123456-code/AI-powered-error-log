import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia } from 'pinia'
import { createRouter, createMemoryHistory } from 'vue-router'
import AppShell from '../AppShell.vue'
import { ZH } from '@/constants/zh'

function makeRouter() {
  return createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/', component: { template: '<div>home</div>' } },
      { path: '/import', component: { template: '<div>import</div>' } },
      { path: '/mistakes', component: { template: '<div>mistakes</div>' } },
      { path: '/review', component: { template: '<div>review</div>' } },
      { path: '/dashboard', component: { template: '<div>dash</div>' } },
      { path: '/chat', component: { template: '<div>chat</div>' } },
      { path: '/help', component: { template: '<div>help</div>' } },
      { path: '/settings', component: { template: '<div>settings</div>' } },
    ],
  })
}

describe('AppShell（M0：路由壳）', () => {
  it('左侧导航包含 8 个入口', async () => {
    const router = makeRouter()
    router.push('/')
    await router.isReady()
    const wrapper = mount(AppShell, { global: { plugins: [createPinia(), router] } })
    const labels = wrapper.findAll('.nav-item .nav-label').map((n) => n.text())
    expect(labels).toEqual([
      ZH.nav.home,
      ZH.nav.import,
      ZH.nav.mistakes,
      ZH.nav.review,
      ZH.nav.dashboard,
      ZH.nav.chat,
      ZH.nav.help,
      ZH.nav.settings,
    ])
  })

  it('当前路由的导航项高亮', async () => {
    const router = makeRouter()
    router.push('/mistakes')
    await router.isReady()
    const wrapper = mount(AppShell, { global: { plugins: [createPinia(), router] } })
    const active = wrapper.find('.nav-item.active .nav-label')
    expect(active.text()).toBe(ZH.nav.mistakes)
  })

  it('顶栏与底部导航存在', async () => {
    const router = makeRouter()
    router.push('/')
    await router.isReady()
    const wrapper = mount(AppShell, { global: { plugins: [createPinia(), router] } })
    expect(wrapper.find('.topbar').exists()).toBe(true)
    expect(wrapper.find('.bottom-nav').exists()).toBe(true)
  })
})
