<script setup lang="ts">
/** 顶部工具栏 56px：全局搜索（/ 聚焦，Enter 跳错题本搜索）、主题切换、快速录入。 */
import { onBeforeUnmount, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { Plus, Search } from 'lucide-vue-next'
import { ZH } from '@/constants/zh'
import ThemeToggle from './ThemeToggle.vue'

const router = useRouter()
const keyword = ref('')
const searchInput = ref<HTMLInputElement | null>(null)
const mobileSearchOpen = ref(false)

function submitSearch() {
  const q = keyword.value.trim()
  if (q) {
    router.push({ path: '/mistakes', query: { q } })
  } else {
    router.push({ path: '/mistakes' })
  }
  mobileSearchOpen.value = false
}

function onKeydown(e: KeyboardEvent) {
  // '/' 聚焦全局搜索（输入框中除外）
  if (e.key === '/' && !(e.target instanceof HTMLInputElement) && !(e.target instanceof HTMLTextAreaElement)) {
    e.preventDefault()
    searchInput.value?.focus()
  }
}

onMounted(() => window.addEventListener('keydown', onKeydown))
onBeforeUnmount(() => window.removeEventListener('keydown', onKeydown))
</script>

<template>
  <header class="topbar">
    <div class="topbar-search" :class="{ 'mobile-open': mobileSearchOpen }">
      <Search :size="16" :stroke-width="1.5" />
      <input
        ref="searchInput"
        v-model="keyword"
        type="text"
        :placeholder="ZH.common.searchPlaceholder"
        aria-label="全局搜索"
        @keydown.enter="submitSearch"
      />
      <kbd>/</kbd>
    </div>
    <button v-if="$route.path !== '/import'" class="btn btn-primary btn-sm" @click="router.push('/import')">
      <Plus :size="16" /> 快速录入
    </button>
    <div class="topbar-spacer" />
    <ThemeToggle />
  </header>
</template>
