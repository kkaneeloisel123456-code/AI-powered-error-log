<script setup lang="ts">
/** 左侧全局导航 240px（平板 64px 图标栏，移动端隐藏换底部导航）。 */
import { BookOpen, Bot, FileInput, GraduationCap, Home, LayoutDashboard, LifeBuoy, Settings } from 'lucide-vue-next'
import { ZH } from '@/constants/zh'

const items = [
  { to: '/', label: ZH.nav.home, icon: Home },
  { to: '/import', label: ZH.nav.import, icon: FileInput },
  { to: '/mistakes', label: ZH.nav.mistakes, icon: BookOpen },
  { to: '/review', label: ZH.nav.review, icon: GraduationCap },
  { to: '/dashboard', label: ZH.nav.dashboard, icon: LayoutDashboard },
  { to: '/chat', label: ZH.nav.chat, icon: Bot },
  { to: '/help', label: ZH.nav.help, icon: LifeBuoy },
  { to: '/settings', label: ZH.nav.settings, icon: Settings },
]
</script>

<template>
  <nav class="global-nav" aria-label="主导航">
    <div class="nav-logo">
      <span class="logo-mark"><BookOpen :size="16" /></span>
      <span class="logo-text">{{ ZH.app.name }}<span style="color: var(--text-secondary); font-weight: 400; font-size: var(--fs-aux); margin-left: 4px">{{ ZH.app.subtitle }}</span></span>
    </div>
    <RouterLink
      v-for="item in items"
      :key="item.to"
      :to="item.to"
      class="nav-item"
      :class="{ active: $route.path === item.to || (item.to !== '/' && $route.path.startsWith(item.to)) }"
    >
      <component :is="item.icon" :size="18" :stroke-width="1.5" />
      <span class="nav-label">{{ item.label }}</span>
    </RouterLink>
  </nav>
</template>
