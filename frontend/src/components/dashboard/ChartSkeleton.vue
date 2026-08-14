<script setup lang="ts">
/** 图表骨架屏（UI/UX 7.2）：卡片内 200px 灰块 + 标题条，数据到达后替换为 ECharts。 */
</script>

<template>
  <div class="card" style="padding: var(--space-4);" aria-busy="true" aria-label="图表加载中">
    <div class="skeleton" style="height: 16px; width: 40%; margin-bottom: var(--space-3);"></div>
    <div class="skeleton" style="height: 200px; border-radius: var(--radius-md);"></div>
  </div>
</template>
