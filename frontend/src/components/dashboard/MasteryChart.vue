<script setup lang="ts">
/** 掌握状态分布（1 列）：状态色环图（灰/红/橙/绿 = 未开始/未掌握/待巩固/已掌握），色点+文字图例。 */
import { ref } from 'vue'
import { ZH } from '@/constants/zh'
import { isDark, statusColors, textColors, useChart } from '@/utils/charts'
import ChartCard from './ChartCard.vue'

const props = defineProps<{ statuses: Array<{ status: string; value: number }> }>()
const el = ref<HTMLElement | null>(null)

const ORDER = ['pending', 'wrong', 'fixing', 'mastered']

useChart(el, () => {
  const c = textColors()
  const colors = statusColors()
  const data = props.statuses
    .filter((s) => ORDER.includes(s.status))
    .sort((a, b) => ORDER.indexOf(a.status) - ORDER.indexOf(b.status))
    .map((s) => ({
      name: ZH.status[s.status as keyof typeof ZH.status] ?? s.status,
      value: s.value,
      itemStyle: { color: colors[s.status] },
    }))
  return {
    tooltip: { trigger: 'item', formatter: '{b}: {c} 题 ({d}%)' },
    legend: { bottom: 0, textStyle: { color: c.secondary, fontSize: 12 }, icon: 'circle', itemWidth: 8, itemHeight: 8 },
    series: [{
      type: 'pie',
      radius: ['42%', '68%'],
      center: ['50%', '44%'],
      itemStyle: { borderColor: isDark() ? '#1B1E24' : '#FFFFFF', borderWidth: 2 },
      label: { show: true, formatter: '{b}\n{c} 题', color: c.secondary, fontSize: 12 },
      data,
    }],
  }
})
</script>

<template>
  <ChartCard title="掌握状态" hint="灰=未开始 红=未掌握 橙=待巩固 绿=已掌握">
    <div ref="el" style="height: 220px;"></div>
  </ChartCard>
</template>
