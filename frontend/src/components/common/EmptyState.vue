<script setup lang="ts">
/** 通用空状态（UI/UX 7.1）：渐变 SVG 图标 + 标题 + 说明 + 操作。 */
withDefaults(defineProps<{ title: string; desc?: string }>(), { desc: '' })
</script>

<template>
  <div class="empty-state">
    <div class="empty-icon" aria-hidden="true">
      <svg width="48" height="48" viewBox="0 0 48 48" fill="none">
        <path d="M10 12a4 4 0 0 1 4-4h12l8 8v20a4 4 0 0 1-4 4H14a4 4 0 0 1-4-4V12z" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round" />
        <path d="M26 8v8h8" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round" />
        <path d="M18 26h12M18 32h8" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" />
      </svg>
    </div>
    <h3>{{ title }}</h3>
    <p v-if="desc">{{ desc }}</p>
    <slot />
  </div>
</template>
