<script setup lang="ts">
/** 错因分布（1 列，默认 Top 5）：横向条形图 + 直接标签。 */
import { computed, ref } from 'vue'
import { ZH } from '@/constants/zh'
import { baseAxisStyle, categorical, textColors, useChart } from '@/utils/charts'
import ChartCard from './ChartCard.vue'

const props = defineProps<{ errors: Array<{ type: string; value: number }> }>()
const el = ref<HTMLElement | null>(null)

const rows = computed(() =>
  props.errors.map((e) => ({
    label: ZH.errorTypes[e.type as keyof typeof ZH.errorTypes] ?? e.type,
    value: e.value,
  })),
)

useChart(el, () => {
  const c = textColors()
  return {
    grid: { left: 8, right: 24, top: 8, bottom: 8, containLabel: true },
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    xAxis: { type: 'value', minInterval: 1, ...baseAxisStyle() },
    yAxis: { type: 'category', data: rows.value.map((r) => r.label).reverse(), ...baseAxisStyle() },
    series: [{
      type: 'bar',
      barWidth: 14,
      data: [...rows.value.map((r) => ({ value: r.value, itemStyle: { color: categorical(0), borderRadius: [0, 4, 4, 0] } }))].reverse(),
      label: { show: true, position: 'right', color: c.secondary, fontSize: 12 },
    }],
  }
})
</script>

<template>
  <ChartCard title="错因分布" hint="默认展示 Top 5">
    <div ref="el" style="height: 220px;"></div>
  </ChartCard>
</template>
