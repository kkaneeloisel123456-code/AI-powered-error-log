<script setup lang="ts">
/** 阶段三总览卡（UI/UX 4.5/8.3）：分数大数字、答对/答错、用时、薄弱点 Top3、与上次对比。 */
import { computed } from 'vue'
import { TrendingDown, TrendingUp } from 'lucide-vue-next'
import type { ReviewReport } from '@/api/reviews'
import { formatDuration } from '@/utils/format'

const props = defineProps<{ report: ReviewReport }>()

const scoreColor = computed(() => (props.report.score >= 60 ? 'var(--status-mastered)' : 'var(--status-wrong)'))
</script>

<template>
  <div class="card overview-card">
    <div class="score-block">
      <div class="score-num num" :style="{ color: scoreColor }">{{ report.score }}</div>
      <div class="score-label">本次得分</div>
      <div v-if="report.compared_last" class="score-delta num" :style="{ color: report.compared_last.score_delta >= 0 ? 'var(--status-mastered)' : 'var(--status-wrong)' }">
        <TrendingUp v-if="report.compared_last.score_delta >= 0" :size="14" />
        <TrendingDown v-else :size="14" />
        {{ report.compared_last.score_delta >= 0 ? '+' : '' }}{{ report.compared_last.score_delta }} 较上次
      </div>
    </div>
    <div class="stat-grid">
      <div class="stat">
        <span class="stat-value num" style="color: var(--status-mastered);">答对 {{ report.correct }}</span>
        <span class="stat-label">/ 共 {{ report.correct + report.wrong }} 题</span>
      </div>
      <div class="stat">
        <span class="stat-value num" style="color: var(--status-wrong);">答错 {{ report.wrong }}</span>
        <span class="stat-label">未作答按错误计</span>
      </div>
      <div class="stat">
        <span class="stat-value num">{{ formatDuration(report.duration_s) }}</span>
        <span class="stat-label">本次用时</span>
      </div>
      <div class="stat">
        <span class="stat-value">{{ report.weak_points.length ? report.weak_points.join('、') : '无' }}</span>
        <span class="stat-label">薄弱知识点 Top3</span>
      </div>
    </div>
  </div>
</template>

<style scoped>
.overview-card {
  padding: var(--space-5);
  display: flex;
  gap: var(--space-6);
  align-items: center;
  margin-bottom: var(--space-4);
}
.score-block {
  text-align: center;
  min-width: 140px;
  border-right: var(--border-1);
  padding-right: var(--space-6);
}
.score-num {
  font-size: var(--fs-big-number);
  font-weight: 700;
  line-height: 1.1;
}
.score-label { font-size: var(--fs-aux2); color: var(--text-secondary); margin: var(--space-1) 0; }
.score-delta {
  display: inline-flex;
  align-items: center;
  gap: var(--space-1);
  font-size: var(--fs-aux2);
}
.stat-grid {
  flex: 1;
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: var(--space-4);
}
.stat { display: flex; flex-direction: column; gap: 2px; }
.stat-value { font-size: var(--fs-body-lg); font-weight: 600; }
.stat-label { font-size: var(--fs-aux); color: var(--text-secondary); }
</style>
