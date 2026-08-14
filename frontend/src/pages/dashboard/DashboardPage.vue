<script setup lang="ts">
/** 数据看板（UI/UX 3.6 / 4.6）：2 列网格；趋势与图谱 span-2；范围 Tabs + 刷新；
 * 学科筛选图谱；空状态 SVG + 去录入；图表骨架屏。 */
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { RefreshCw } from 'lucide-vue-next'
import { useDashboardStore } from '@/stores/dashboard'
import { useMistakesStore } from '@/stores/mistakes'
import { ZH } from '@/constants/zh'
import TrendChart from '@/components/dashboard/TrendChart.vue'
import SubjectChart from '@/components/dashboard/SubjectChart.vue'
import ErrorTypeChart from '@/components/dashboard/ErrorTypeChart.vue'
import MasteryChart from '@/components/dashboard/MasteryChart.vue'
import WeakRank from '@/components/dashboard/WeakRank.vue'
import KnowledgeGraph from '@/components/dashboard/KnowledgeGraph.vue'
import ChartSkeleton from '@/components/dashboard/ChartSkeleton.vue'
import EmptyState from '@/components/common/EmptyState.vue'

const store = useDashboardStore()
const mistakesStore = useMistakesStore()
const router = useRouter()
const graphSubjectId = ref<number | undefined>(undefined)

onMounted(async () => {
  if (mistakesStore.subjects.length === 0) await mistakesStore.fetchSubjects()
  await Promise.all([store.fetchSummary(), store.fetchGraph()])
})

async function refresh() {
  await Promise.all([store.fetchSummary(), store.fetchGraph(graphSubjectId.value)])
}

async function changeGraphSubject(subjectId: number | undefined) {
  graphSubjectId.value = subjectId
  await store.fetchGraph(subjectId)
}
</script>

<template>
  <div>
    <!-- 标题 + 范围 Tabs + 刷新 -->
    <div style="display: flex; align-items: center; gap: var(--space-3); margin-bottom: var(--space-4);">
      <h1 style="font-size: var(--fs-page-title); font-weight: 600;">数据看板</h1>
      <span class="spacer" />
      <div class="segmented">
        <button :class="{ active: store.rangeDays === 7 }" @click="store.setRange(7)">近 7 天</button>
        <button :class="{ active: store.rangeDays === 30 }" @click="store.setRange(30)">近 30 天</button>
      </div>
      <button class="btn btn-icon" aria-label="刷新看板" @click="refresh"><RefreshCw :size="16" :stroke-width="1.5" /></button>
    </div>

    <!-- 错误态 -->
    <div v-if="store.error" class="card" style="padding: var(--space-4); margin-bottom: var(--space-4); display: flex; align-items: center; gap: var(--space-3);">
      <span style="color: var(--error);">{{ store.error }}</span>
      <span class="spacer" />
      <button class="btn btn-secondary btn-sm" @click="refresh">重试</button>
    </div>

    <!-- 空状态（PRD 7.6-20 / UI/UX 7.1：SVG + 说明 + 入口） -->
    <EmptyState
      v-if="store.isEmpty"
      :title="ZH.emptyStates.dashboardTitle"
      desc="录入错题并完成复习后，这里会展示趋势、分布与知识图谱"
    >
      <div style="display: flex; gap: var(--space-2);">
        <button class="btn btn-primary" @click="router.push('/import')">{{ ZH.emptyStates.dashboardAction }}</button>
        <button class="btn btn-secondary" @click="router.push('/chat')">{{ ZH.emptyStates.dashboardSecondary }}</button>
      </div>
    </EmptyState>

    <!-- 骨架屏 -->
    <div v-else-if="store.loading || !store.summary" class="dashboard-grid">
      <div class="span-2"><ChartSkeleton /></div>
      <ChartSkeleton v-for="i in 4" :key="i" />
      <div class="span-2"><ChartSkeleton /></div>
    </div>

    <!-- 2 列网格 -->
    <div v-else class="dashboard-grid">
      <div class="span-2"><TrendChart :trend="store.summary.trend" /></div>
      <SubjectChart :subjects="store.summary.subjects" />
      <ErrorTypeChart :errors="store.summary.errors" />
      <MasteryChart :statuses="store.summary.statuses" />
      <WeakRank :weak-points="store.summary.weak_points" />
      <div class="span-2">
        <div style="display: flex; gap: var(--space-2); margin-bottom: var(--space-3);">
          <button class="chip clickable" :style="graphSubjectId === undefined ? { background: 'var(--brand-8)', color: 'var(--brand)' } : {}" @click="changeGraphSubject(undefined)">全部学科</button>
          <button
            v-for="s in mistakesStore.subjects"
            :key="s.id"
            class="chip clickable"
            :style="graphSubjectId === s.id ? { background: 'var(--brand-8)', color: 'var(--brand)' } : {}"
            @click="changeGraphSubject(s.id)"
          >{{ s.name }}</button>
        </div>
        <KnowledgeGraph v-if="store.graph" :graph="store.graph" />
        <ChartSkeleton v-else />
      </div>
    </div>
  </div>
</template>

<style scoped>
.spacer { flex: 1; }
/* UI/UX 3.6：2 列网格，趋势与图谱 span 2；平板/移动 1 列 */
.dashboard-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: var(--space-4);
}
.span-2 { grid-column: span 2; }
@media (max-width: 1199px) {
  .dashboard-grid { grid-template-columns: minmax(0, 1fr); }
  .span-2 { grid-column: span 1; }
}
</style>
