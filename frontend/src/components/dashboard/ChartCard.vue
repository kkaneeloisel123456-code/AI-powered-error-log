<script setup lang="ts">
/** 看板卡片（UI/UX 图表规范：「标题 + 大数字 + 小趋势」紧凑结构）。 */
withDefaults(defineProps<{ title: string; bigNumber?: string | number; bigNumberUnit?: string; hint?: string }>(), {})
</script>

<template>
  <div class="card chart-card">
    <div class="chart-card-head">
      <span class="chart-card-title">{{ title }}</span>
      <span class="spacer" />
      <span v-if="bigNumber !== undefined" class="chart-card-big num">
        {{ bigNumber }}<span v-if="bigNumberUnit" class="unit">{{ bigNumberUnit }}</span>
      </span>
    </div>
    <p v-if="hint" class="chart-card-hint">{{ hint }}</p>
    <slot />
  </div>
</template>

<style scoped>
.chart-card { padding: var(--space-4); }
.chart-card-head {
  display: flex;
  align-items: baseline;
  gap: var(--space-2);
  margin-bottom: var(--space-2);
}
.chart-card-title { font-size: var(--fs-card-title); font-weight: 600; }
.spacer { flex: 1; }
.chart-card-big { font-size: var(--fs-big-number); font-weight: 700; }
.unit { font-size: var(--fs-aux2); color: var(--text-secondary); font-weight: 400; margin-left: 2px; }
.chart-card-hint { font-size: var(--fs-aux2); color: var(--text-secondary); margin-bottom: var(--space-3); }
</style>
