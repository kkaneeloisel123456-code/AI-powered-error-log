<script setup lang="ts">
/** 移动端底部导航 56px：首页 / 错题本 / 复习 / AI / 看板。 */
import { BookOpen, Bot, GraduationCap, Home, LayoutDashboard } from 'lucide-vue-next'
import { ZH } from '@/constants/zh'

const items = [
  { to: '/', label: ZH.nav.home, icon: Home },
  { to: '/mistakes', label: ZH.nav.mistakes, icon: BookOpen },
  { to: '/review', label: ZH.nav.review, icon: GraduationCap },
  { to: '/chat', label: ZH.nav.chat, icon: Bot },
  { to: '/dashboard', label: ZH.nav.dashboard, icon: LayoutDashboard },
]
</script>

<template>
  <nav class="bottom-nav" aria-label="底部导航">
    <RouterLink
      v-for="item in items"
      :key="item.to"
      :to="item.to"
      :class="{ active: $route.path === item.to || (item.to !== '/' && $route.path.startsWith(item.to)) }"
    >
      <component :is="item.icon" :size="20" :stroke-width="1.5" />
      {{ item.label }}
    </RouterLink>
  </nav>
</template>
