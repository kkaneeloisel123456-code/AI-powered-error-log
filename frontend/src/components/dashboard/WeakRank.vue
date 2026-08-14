<script setup lang="ts">
/** 薄弱点排行（1 列）：HTML 排名列表（文字优先，比例条辅助），点击联动错题列表（PRD 7.6-20）。 */
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { statusColors } from '@/utils/charts'
import ChartCard from './ChartCard.vue'

const props = defineProps<{
  weakPoints: Array<{ kp_id: number; name: string; subject_name: string; mistake_count: number; recent_wrong: number; score: number }>
}>()

const router = useRouter()
const maxScore = computed(() => Math.max(...props.weakPoints.map((w) => w.score), 1))

function goMistakes(kpId: number) {
  router.push({ path: '/mistakes', query: { kp_id: String(kpId) } })
}
</script>

<template>
  <ChartCard title="薄弱点排行" hint="按错题数 × 近 30 天复错率加权；点击查看该知识点错题">
    <div v-if="!weakPoints.length" style="color: var(--text-secondary); font-size: var(--fs-aux2); padding: var(--space-3) 0;">
      暂无数据，复习后生成排行
    </div>
    <button v-for="(w, i) in weakPoints" :key="w.kp_id" class="weak-row" @click="goMistakes(w.kp_id)">
      <span class="rank num">{{ i + 1 }}</span>
      <div class="weak-info">
        <div class="weak-name">{{ w.name }}<span class="weak-subject"> · {{ w.subject_name }}</span></div>
        <div class="weak-bar-track">
          <div class="weak-bar-fill" :style="{ width: `${(w.score / maxScore) * 100}%`, background: statusColors().wrong }"></div>
        </div>
      </div>
      <div class="weak-nums num">
        <div>{{ w.mistake_count }} 题</div>
        <div style="color: var(--status-wrong);">{{ w.recent_wrong }} 近错</div>
      </div>
    </button>
  </ChartCard>
</template>

<style scoped>
.weak-row {
  width: 100%;
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-2) 0;
  border-bottom: var(--border-1);
  text-align: left;
  border-radius: var(--radius-sm);
}
.weak-row:last-child { border-bottom: none; }
.weak-row:hover { background: var(--brand-8); }
.rank {
  width: 24px;
  height: 24px;
  border-radius: var(--radius-sm);
  background: var(--bg-subtle);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: var(--fs-aux2);
  flex-shrink: 0;
}
.weak-info { flex: 1; min-width: 0; }
.weak-name { font-size: var(--fs-body); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.weak-subject { font-size: var(--fs-aux); color: var(--text-secondary); }
.weak-bar-track { height: 4px; border-radius: 2px; background: var(--bg-subtle); margin-top: var(--space-1); overflow: hidden; }
.weak-bar-fill { height: 100%; border-radius: 2px; opacity: 0.8; }
.weak-nums { text-align: right; font-size: var(--fs-aux2); color: var(--text-secondary); flex-shrink: 0; }
</style>
