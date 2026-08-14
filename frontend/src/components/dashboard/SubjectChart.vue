<script setup lang="ts">
/** 学科分布（1 列）：环图 + 图例（类别色固定顺序）。 */
import { computed, ref } from 'vue'
import { categorical, isDark, textColors, useChart } from '@/utils/charts'
import ChartCard from './ChartCard.vue'

const props = defineProps<{ subjects: Array<{ name: string; value: number }> }>()
const el = ref<HTMLElement | null>(null)

const total = computed(() => props.subjects.reduce((s, x) => s + x.value, 0))

useChart(el, () => {
  const c = textColors()
  return {
    tooltip: { trigger: 'item', formatter: '{b}: {c} 题 ({d}%)' },
    legend: { bottom: 0, textStyle: { color: c.secondary, fontSize: 12 }, icon: 'circle', itemWidth: 8, itemHeight: 8 },
    series: [{
      type: 'pie',
      radius: ['42%', '68%'],
      center: ['50%', '44%'],
      itemStyle: { borderColor: isDark() ? '#1B1E24' : '#FFFFFF', borderWidth: 2 },
      label: { show: true, formatter: '{b}\n{c} 题', color: c.secondary, fontSize: 12 },
      data: props.subjects.map((s, i) => ({
        name: s.name, value: s.value,
        itemStyle: { color: categorical(i) },
      })),
    }],
  }
})
</script>

<template>
  <ChartCard title="学科分布" :big-number="total" big-number-unit="题" hint="各学科错题数量占比">
    <div ref="el" style="height: 220px;"></div>
  </ChartCard>
</template>
