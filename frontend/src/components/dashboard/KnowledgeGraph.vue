<script setup lang="ts">
/** 知识图谱（占 2 列）：节点大小映射错题数、颜色映射掌握度（绿色单色相色带）、父子边；
 * 点击节点联动错题列表（PRD 7.6-19）。 */
import { computed, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { isDark, masteryRamp, textColors, useChart } from '@/utils/charts'
import type { GraphData } from '@/api/dashboard'
import ChartCard from './ChartCard.vue'

const props = defineProps<{ graph: GraphData }>()
const router = useRouter()
const el = ref<HTMLElement | null>(null)

const nodeCount = computed(() => props.graph.nodes.length)
const edgeCount = computed(() => props.graph.edges.length)

const chart = useChart(el, () => {
  const c = textColors()
  return {
    tooltip: {
      formatter: (p: { data?: { name?: string; value?: number; mastery?: number } }) => {
        const d = p.data ?? {}
        return `${d.name ?? ''}<br/>错题 ${d.value ?? 0} 题 · 掌握度 ${Math.round((d.mastery ?? 0) * 100)}%`
      },
    },
    series: [{
      type: 'graph',
      layout: 'force',
      roam: true,
      draggable: true,
      force: { repulsion: 120, edgeLength: [60, 140], gravity: 0.08 },
      label: { show: true, color: c.primary, fontSize: 12 },
      edgeSymbol: ['none', 'none'],
      lineStyle: { color: c.border, width: 1, curveness: 0 },
      data: props.graph.nodes.map((n) => ({
        id: n.id,
        name: n.name,
        value: n.value,
        mastery: n.mastery,
        symbolSize: 12 + Math.min(Math.sqrt(n.value) * 10, 40),  // 节点大小映射错题数
        itemStyle: {
          color: n.value === 0 ? c.border : masteryRamp(n.mastery),  // 颜色映射掌握度（0 值祖先节点用中性色）
          borderColor: isDark() ? '#1B1E24' : '#FFFFFF',
          borderWidth: 1.5,
        },
      })),
      links: props.graph.edges.map((e) => ({ source: e.source, target: e.target })),
    }],
  }
})

function onClickNode(params: unknown) {
  const data = (params as { data?: { id?: number; value?: number } | null }).data
  const id = data?.id
  if (id !== undefined && (data?.value ?? 0) > 0) {
    router.push({ path: '/mistakes', query: { kp_id: String(id) } })
  }
}

// ECharts 事件绑定（初始化后注册）
onMounted(() => {
  chart.chart.value?.on('click', onClickNode)
})

watch(() => props.graph, () => chart.refresh())
</script>

<template>
  <ChartCard title="知识图谱" :hint="`节点大小=错题数，颜色=掌握度（绿越深越熟练）；共 ${nodeCount} 个节点、${edgeCount} 条关系边；点击节点查看错题`">
    <div ref="el" style="height: 400px;"></div>
  </ChartCard>
</template>
