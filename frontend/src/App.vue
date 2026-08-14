<script setup lang="ts">
import { onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { useThemeStore } from '@/stores/theme'
import AppShell from '@/app-shell/AppShell.vue'

const themeStore = useThemeStore()
const route = useRoute()

onMounted(() => themeStore.apply())
</script>

<template>
  <!-- 登录页为独立全屏布局 -->
  <component :is="route.name === 'login' ? 'RouterView' : AppShell" />
</template>
