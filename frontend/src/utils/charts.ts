/**
 * ECharts 封装（开发规划 5.2：图表统一封装 + 主题切换统一换色）。
 * 配色经过 CVD/对比度校验（validate_palette）：
 *   亮色 #4F46E5 #14B8A6 #F59E0B #0EA5E9 #F43F5E #8B5CF6 #84CC16 #C026D3
 *   暗色 #6366F1 #0D9488 #D97706 #0284C7 #E11D48 #7C3AED #65A30D #C026D3
 * 类别色固定顺序分配、不随排名换色；状态色（灰/红/橙/绿）保留给状态语义。
 */
import * as echarts from 'echarts/core'
import { BarChart, GraphChart, LineChart, PieChart } from 'echarts/charts'
import { GridComponent, LegendComponent, TooltipComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import { onBeforeUnmount, onMounted, ref, type Ref } from 'vue'

echarts.use([LineChart, PieChart, BarChart, GraphChart, GridComponent, TooltipComponent, LegendComponent, CanvasRenderer])

export { echarts }

const LIGHT_CATEGORICAL = ['#4F46E5', '#14B8A6', '#F59E0B', '#0EA5E9', '#F43F5E', '#8B5CF6', '#84CC16', '#C026D3']
const DARK_CATEGORICAL = ['#6366F1', '#0D9488', '#D97706', '#0284C7', '#E11D48', '#7C3AED', '#65A30D', '#C026D3']

/** 主题感知类别色（固定顺序）。 */
export function categorical(i?: number): string | string[] {
  const palette = isDark() ? DARK_CATEGORICAL : LIGHT_CATEGORICAL
  return i === undefined ? palette : palette[i % palette.length]
}

/** 掌握度顺序色带（单色相 浅→深；0=浅，1=深）。 */
export function masteryRamp(mastery: number): string {
  const light = ['#DCFCE7', '#86EFAC', '#22C55E', '#15803D']
  const dark = ['#052E16', '#166534', '#16A34A', '#4ADE80']
  const ramp = isDark() ? dark : light
  const idx = Math.min(Math.max(Math.floor(mastery * 4), 0), 3)
  return ramp[idx]
}

/** 状态色（主题感知，状态语义专用）。 */
export function statusColors(): Record<string, string> {
  const s = getComputedStyle(document.documentElement)
  return {
    pending: s.getPropertyValue('--status-none').trim() || '#6B7280',
    wrong: s.getPropertyValue('--status-wrong').trim() || '#DC2626',
    fixing: s.getPropertyValue('--status-fixing').trim() || '#EA8C00',
    mastered: s.getPropertyValue('--status-mastered').trim() || '#16A34A',
  }
}

export function isDark(): boolean {
  return document.documentElement.getAttribute('data-theme') === 'dark'
}

/** 文本色（文字使用文本 token，不用序列色）。 */
export function textColors() {
  const s = getComputedStyle(document.documentElement)
  return {
    primary: s.getPropertyValue('--text-primary').trim() || '#1A1D23',
    secondary: s.getPropertyValue('--text-secondary').trim() || '#5B6472',
    border: s.getPropertyValue('--border').trim() || '#E6E8EC',
  }
}

/** 基础 tooltip / 坐标轴样式（低视觉噪音：浅色细网格、无竖线）。 */
export function baseAxisStyle() {
  const c = textColors()
  return {
    axisLine: { lineStyle: { color: c.border } },
    axisTick: { show: false },
    axisLabel: { color: c.secondary, fontSize: 12 },
    splitLine: { lineStyle: { color: c.border, type: 'dashed' as const } },
  }
}

export function baseTooltip() {
  const c = textColors()
  return {
    backgroundColor: c.primary,
    borderWidth: 0,
    textStyle: { color: isDark() ? '#121418' : '#FFFFFF', fontSize: 12 },
  }
}

/** useChart：挂载时初始化、resize 自适应、卸载销毁；主题切换时重新 setOption 换色。 */
export function useChart(elRef: Ref<HTMLElement | null>, buildOption: () => echarts.EChartsCoreOption) {
  const chart = ref<echarts.ECharts | null>(null)
  let observer: ResizeObserver | null = null

  onMounted(() => {
    if (!elRef.value) return
    chart.value = echarts.init(elRef.value)
    chart.value.setOption(buildOption())
    observer = new ResizeObserver(() => chart.value?.resize())
    observer.observe(elRef.value)
  })

  onBeforeUnmount(() => {
    observer?.disconnect()
    chart.value?.dispose()
    chart.value = null
  })

  /** 主题切换时统一 setOption 换色（UI/UX 2.4：不用两套实例）。 */
  function refresh() {
    chart.value?.setOption(buildOption(), true)
  }

  return { chart, refresh }
}
