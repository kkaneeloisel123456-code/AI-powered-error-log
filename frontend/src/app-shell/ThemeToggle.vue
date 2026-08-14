<script setup lang="ts">
/** 主题切换（亮/暗），持久化 localStorage，图标按钮 44px 点击区。 */
import { Moon, Sun } from 'lucide-vue-next'
import { useThemeStore } from '@/stores/theme'

const themeStore = useThemeStore()
</script>

<template>
  <button
    class="btn-icon"
    :title="themeStore.theme === 'light' ? '切换到暗色主题' : '切换到亮色主题'"
    aria-label="切换主题"
    @click="themeStore.toggle()"
  >
    <Sun v-if="themeStore.theme === 'light'" :size="18" :stroke-width="1.5" />
    <Moon v-else :size="18" :stroke-width="1.5" />
  </button>
</template>
