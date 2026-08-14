<script setup lang="ts">
/** 列表骨架屏（UI/UX 7.2）：行高 88px，左窄条 + 两行文本 + 标签条。 */
withDefaults(defineProps<{ rows?: number }>(), { rows: 6 })
</script>

<template>
  <div aria-busy="true" aria-label="加载中">
    <div v-for="i in rows" :key="i" class="card" style="padding: var(--space-3); margin-bottom: var(--space-2); display: flex; gap: var(--space-3); align-items: flex-start; height: 88px; overflow: hidden;">
      <div class="skeleton" style="width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; margin-top: 6px;"></div>
      <div style="flex: 1; display: flex; flex-direction: column; gap: var(--space-2);">
        <div class="skeleton" style="height: 14px; width: 90%;"></div>
        <div class="skeleton" style="height: 14px; width: 60%;"></div>
        <div style="display: flex; gap: var(--space-2);">
          <div class="skeleton" style="height: 20px; width: 64px; border-radius: var(--radius-sm);"></div>
          <div class="skeleton" style="height: 20px; width: 64px; border-radius: var(--radius-sm);"></div>
        </div>
      </div>
    </div>
  </div>
</template>
