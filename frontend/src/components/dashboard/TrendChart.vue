<script setup lang="ts">
/** 趋势图卡（占 2 列）：录入数/复习数折线（同一量纲单轴）+ 正确率独立小面积图（各自单轴）。 */
import { ref, watch } from 'vue'
import { useThemeStore } from '@/stores/theme'
import { baseAxisStyle, baseTooltip, categorical, textColors, useChart } from '@/utils/charts'
import type { TrendDay } from '@/api/dashboard'
import ChartCard from './ChartCard.vue'

const props = defineProps<{ trend: TrendDay[] }>()
const themeStore = useThemeStore()

const countEl = ref<HTMLElement | null>(null)
const accEl = ref<HTMLElement | null>(null)

const countChart = useChart(countEl, () => {
  const c = textColors()
  return {
    grid: { left: 8, right: 16, top: 36, bottom: 8, containLabel: true },
    legend: { data: ['录入数', '复习数'], textStyle: { color: c.secondary }, top: 0 },
    tooltip: { trigger: 'axis', ...baseTooltip() },
    xAxis: { type: 'category', data: props.trend.map((d) => d.date.slice(5)), ...baseAxisStyle() },
    yAxis: { type: 'value', minInterval: 1, ...baseAxisStyle() },
    series: [
      { name: '录入数', type: 'line', data: props.trend.map((d) => d.created), itemStyle: { color: categorical(0) }, lineStyle: { width: 2 }, symbolSize: 6 },
      { name: '复习数', type: 'line', data: props.trend.map((d) => d.reviewed), itemStyle: { color: categorical(1) }, lineStyle: { width: 2 }, symbolSize: 6 },
    ],
  }
})

const accChart = useChart(accEl, () => {
  return {
    grid: { left: 8, right: 16, top: 16, bottom: 8, containLabel: true },
    tooltip: { trigger: 'axis', ...baseTooltip(), valueFormatter: (v: number) => `${v}%` },
    xAxis: { type: 'category', data: props.trend.map((d) => d.date.slice(5)), ...baseAxisStyle() },
    yAxis: { type: 'value', min: 0, max: 100, ...baseAxisStyle() },
    series: [{
      name: '正确率', type: 'line', data: props.trend.map((d) => d.accuracy),
      areaStyle: { opacity: 0.15 }, itemStyle: { color: categorical(2) }, lineStyle: { width: 2 }, symbolSize: 6,
    }],
  }
})

// 主题切换统一 setOption 换色（UI/UX 2.4：不用两套图表实例）
watch(() => themeStore.theme, () => {
  countChart.refresh()
  accChart.refresh()
})
</script>

<template>
  <ChartCard title="学习趋势" big-number-unit="天" :hint="`近 ${trend.length} 天录入与复习变化；正确率 = 答对 / 复习总数`">
    <div ref="countEl" style="height: 220px;"></div>
    <div style="display: flex; align-items: center; gap: var(--space-2); font-size: var(--fs-aux2); color: var(--text-secondary); margin: var(--space-2) 0;">
      <span class="status-dot" :style="{ background: categorical(2) as string }"></span> 正确率（0-100%）
    </div>
    <div ref="accEl" style="height: 120px;"></div>
  </ChartCard>
</template>
