<script setup lang="ts">
/** 复习页阶段一「选范围」（单栏 768px，阶段指示 1/3）。 */
import ScopeConfig from '@/components/review/ScopeConfig.vue'
</script>

<template>
  <div class="review-page">
    <div style="display: flex; align-items: center; gap: var(--space-2); margin-bottom: var(--space-3);">
      <h1 style="font-size: var(--fs-page-title); font-weight: 600;">一键复习</h1>
      <span class="chip">阶段 1 / 3 · 选范围</span>
    </div>
    <ScopeConfig />
  </div>
</template>

<style scoped>
.review-page { max-width: 768px; margin: 0 auto; }
</style>
