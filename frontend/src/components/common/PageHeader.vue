<script setup lang="ts">
/** 页面标题区（页面标题 18-20px）。 */
defineProps<{ title: string; subtitle?: string }>()
</script>

<template>
  <div style="margin-bottom: var(--space-5);">
    <h1 style="font-size: var(--fs-page-title); line-height: var(--lh-title); font-weight: 600;">{{ title }}</h1>
    <p v-if="subtitle" style="color: var(--text-secondary); font-size: var(--fs-body); margin-top: var(--space-1);">{{ subtitle }}</p>
  </div>
</template>
