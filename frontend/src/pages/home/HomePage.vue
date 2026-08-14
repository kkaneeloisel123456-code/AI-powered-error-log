<script setup lang="ts">
/** 首页（UI/UX 4.1）：今日待办卡（一键复习 + 复习确认弹窗）、计划 Tabs（每日/周度/考前）、
 * 周度分布条、快捷入口。Alt+R 一键复习。 */
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { Bot, CalendarDays, FileInput, LayoutDashboard, Play, SkipForward } from 'lucide-vue-next'
import { plansApi } from '@/api/plans'
import type { TodayPlan, WeekPlan } from '@/api/plans'
import { useReviewStore } from '@/stores/review'
import { toast } from '@/components/common/toast'
import SkeletonList from '@/components/common/SkeletonList.vue'
import ConfirmDialog from '@/components/common/ConfirmDialog.vue'
import EmptyState from '@/components/common/EmptyState.vue'

const router = useRouter()
const reviewStore = useReviewStore()

const todayPlan = ref<TodayPlan | null>(null)
const weekPlan = ref<WeekPlan | null>(null)
const loading = ref(true)
const tab = ref<'daily' | 'weekly' | 'exam'>('daily')
const reviewDialogOpen = ref(false)
const examDate = ref('')
const examTarget = ref(10)
const examPlan = ref<{ total: number; items: Array<Record<string, unknown>> } | null>(null)
const examGenerating = ref(false)

const todayLabel = computed(() => {
  const d = new Date()
  const week = ['周日', '周一', '周二', '周三', '周四', '周五', '周六'][d.getDay()]
  return `${d.getMonth() + 1}月${d.getDate()}日 ${week}`
})

onMounted(async () => {
  await refresh()
  window.addEventListener('keydown', onKeydown)
})

onBeforeUnmount(() => window.removeEventListener('keydown', onKeydown))

function onKeydown(e: KeyboardEvent) {
  // Alt+R：从首页开始复习
  if (e.altKey && (e.key === 'r' || e.key === 'R')) {
    e.preventDefault()
    startReview()
  }
}

async function refresh() {
  loading.value = true
  try {
    const [today, week] = await Promise.all([plansApi.today(), plansApi.week()])
    todayPlan.value = today
    weekPlan.value = week
  } catch (err) {
    toast.error((err as Error).message)
  } finally {
    loading.value = false
  }
}

function startReview() {
  if (!todayPlan.value || todayPlan.value.due_count === 0) {
    reviewStore.config = null
    router.push('/review')
    return
  }
  reviewDialogOpen.value = true
}

function startSingleReview(mistakeId: string) {
  reviewStore.config = {
    subject_ids: [],
    count: 5,
    difficulty: 'auto',
    scope: 'manual',
    mistake_ids: [mistakeId],
  }
  router.push('/review')
}

async function confirmStartReview() {
  reviewDialogOpen.value = false
  reviewStore.config = {
    subject_ids: [],
    count: Math.min(10, Math.max(5, todayPlan.value!.due_count)),
    difficulty: 'auto',
    scope: 'due',
    mistake_ids: [],
  }
  router.push('/review')
}

async function skipItem(itemId: string) {
  try {
    await plansApi.updateItem(itemId, 'skip')
    await refresh()
    toast.info('已跳过，明日重新出现')
  } catch (err) {
    toast.error((err as Error).message)
  }
}

async function generateExamPlan() {
  if (!examDate.value) {
    toast.error('请先选择考试日期')
    return
  }
  examGenerating.value = true
  try {
    examPlan.value = await plansApi.exam(examDate.value, examTarget.value)
  } catch (err) {
    toast.error((err as Error).message)
  } finally {
    examGenerating.value = false
  }
}

const weekBars = computed(() => {
  if (!weekPlan.value) return []
  const max = Math.max(...weekPlan.value.days.map((d) => d.count), 1)
  return weekPlan.value.days.map((d) => ({ ...d, height: `${Math.max((d.count / max) * 100, 6)}%` }))
})

const shortcuts = [
  { icon: FileInput, label: '录入', to: '/import' },
  { icon: Bot, label: 'AI 答疑', to: '/chat' },
  { icon: LayoutDashboard, label: '数据看板', to: '/dashboard' },
]
</script>

<template>
  <div class="home-page">
    <!-- 今日待办卡 -->
    <div class="card today-card">
      <template v-if="loading">
        <div class="skeleton" style="height: 88px;"></div>
      </template>
      <template v-else-if="todayPlan">
        <div class="today-left">
          <div class="today-title">{{ todayLabel }}</div>
          <div class="today-count num">
            今日到期 <strong>{{ todayPlan.due_count }}</strong> 题
            <span v-if="todayPlan.due_count" style="color: var(--text-secondary); font-size: var(--fs-body); font-weight: 400;"> · 预计 {{ todayPlan.estimated_minutes }} 分钟</span>
          </div>
        </div>
        <div class="today-actions">
          <button class="btn btn-primary" @click="startReview"><Play :size="16" /> 一键复习</button>
          <button class="btn btn-secondary" @click="tab = 'daily'">调整计划</button>
        </div>
      </template>
    </div>

    <!-- 计划 Tabs -->
    <div class="segmented" style="margin-bottom: var(--space-4);">
      <button :class="{ active: tab === 'daily' }" @click="tab = 'daily'">每日</button>
      <button :class="{ active: tab === 'weekly' }" @click="tab = 'weekly'">周度</button>
      <button :class="{ active: tab === 'exam' }" @click="tab = 'exam'">考前</button>
    </div>

    <!-- 每日计划列表 -->
    <template v-if="tab === 'daily'">
      <div v-if="loading"><SkeletonList :rows="3" /></div>
      <template v-else-if="todayPlan">
        <EmptyState v-if="todayPlan.items.length === 0" title="今天没有到期错题" desc="新错题将于次日进入复习计划">
          <button class="btn btn-primary" @click="router.push('/import')">去录入</button>
        </EmptyState>
        <div v-else class="card plan-list">
          <div v-for="item in todayPlan.items" :key="item.id" class="plan-row">
            <span class="status-dot" :style="{ background: `var(--status-${item.mistake_status === 'wrong' ? 'wrong' : item.mistake_status === 'fixing' ? 'fixing' : item.mistake_status === 'mastered' ? 'mastered' : 'none'})` }"></span>
            <div class="plan-info">
              <div class="plan-excerpt">{{ item.question_excerpt }}</div>
              <div class="plan-meta">
                <span class="chip">{{ item.subject_name }}</span>
                <span v-if="item.knowledge_point" class="chip">{{ item.knowledge_point }}</span>
                <span class="plan-due num">间隔 {{ item.interval_days }} 天</span>
              </div>
            </div>
            <span class="spacer" />
            <button class="btn btn-secondary btn-sm" @click="startSingleReview(item.mistake_id)">开始</button>
            <button class="btn btn-text btn-sm" @click="skipItem(item.id)"><SkipForward :size="14" /> 跳过</button>
          </div>
        </div>
      </template>
    </template>

    <!-- 周度分布条 -->
    <template v-else-if="tab === 'weekly'">
      <div class="card" style="padding: var(--space-5);">
        <div class="week-title"><CalendarDays :size="16" /> 未来 7 天到期分布</div>
        <div class="week-bars">
          <div v-for="(d, i) in weekBars" :key="d.date" class="week-bar-col">
            <div class="week-bar-num num">{{ d.count }}</div>
            <div class="week-bar-track">
              <div class="week-bar-fill" :style="{ height: d.height }"></div>
            </div>
            <div class="week-bar-label">{{ ['今', '明'][i] ?? new Date(d.date).getMonth() + 1 + '/' + new Date(d.date).getDate() }}</div>
          </div>
        </div>
        <p style="color: var(--text-secondary); font-size: var(--fs-aux2); margin-top: var(--space-3);">每日建议题量不超过 10 题；点击「一键复习」从今日到期开始。</p>
      </div>
    </template>

    <!-- 考前计划 -->
    <template v-else>
      <div class="card" style="padding: var(--space-5);">
        <div class="field-row">
          <div class="field" style="flex: 1;">
            <label class="field-label" for="exam-date">考试日期</label>
            <input id="exam-date" v-model="examDate" type="date" class="input" />
          </div>
          <div class="field" style="flex: 1;">
            <label class="field-label" for="exam-target">每日目标题量</label>
            <input id="exam-target" v-model="examTarget" type="number" min="1" max="100" class="input num" />
          </div>
          <button class="btn btn-primary" style="align-self: flex-end;" :disabled="examGenerating" @click="generateExamPlan">
            {{ examGenerating ? '生成中…' : '生成考前计划' }}
          </button>
        </div>
        <div v-if="examPlan" style="margin-top: var(--space-4);">
          <p style="font-size: var(--fs-aux2); color: var(--text-secondary); margin-bottom: var(--space-2);">
            共 {{ examPlan.total }} 题 · 按薄弱知识点权重（0.6）+ 到期紧急度（0.4）排序
          </p>
          <div class="plan-list">
            <div v-for="(item, i) in examPlan.items" :key="i" class="plan-row">
              <span class="chip num">第 {{ (item.day_offset as number) }} 天</span>
              <div class="plan-info">
                <div class="plan-excerpt">{{ item.question_excerpt }}</div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </template>

    <!-- 快捷入口 -->
    <div class="shortcuts">
      <button v-for="s in shortcuts" :key="s.to" class="card shortcut-card" @click="router.push(s.to)">
        <component :is="s.icon" :size="18" :stroke-width="1.5" style="color: var(--brand);" />
        {{ s.label }}
      </button>
    </div>

    <!-- 复习确认弹窗 -->
    <ConfirmDialog
      v-if="reviewDialogOpen"
      title="开始今日复习？"
      :message="`今日到期 ${todayPlan?.due_count ?? 0} 题 · 预计 ${todayPlan?.estimated_minutes ?? 0} 分钟。将按到期顺序生成变体题。`"
      confirm-text="开始复习"
      @confirm="confirmStartReview"
      @cancel="reviewDialogOpen = false"
    />
  </div>
</template>

<style scoped>
.home-page { max-width: 768px; margin: 0 auto; }
.today-card {
  padding: var(--space-5);
  display: flex;
  align-items: center;
  gap: var(--space-4);
  margin-bottom: var(--space-4);
}
.today-left { flex: 1; }
.today-title { font-size: var(--fs-aux2); color: var(--text-secondary); margin-bottom: var(--space-1); }
.today-count { font-size: var(--fs-body-lg); }
.today-count strong { font-size: var(--fs-big-number); color: var(--brand); font-weight: 700; }
.today-actions { display: flex; gap: var(--space-2); }
.plan-list { padding: var(--space-2); }
.plan-row {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-3);
  border-bottom: var(--border-1);
}
.plan-row:last-child { border-bottom: none; }
.plan-info { flex: 1; min-width: 0; }
.plan-excerpt {
  font-size: var(--fs-body);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.plan-meta { display: flex; gap: var(--space-1); margin-top: var(--space-1); }
.plan-due { font-size: var(--fs-aux); color: var(--text-disabled); align-self: center; }
.spacer { flex: 1; }
.week-title { display: flex; align-items: center; gap: var(--space-2); font-weight: 600; margin-bottom: var(--space-4); }
.week-bars { display: flex; gap: var(--space-3); align-items: flex-end; height: 140px; }
.week-bar-col { flex: 1; display: flex; flex-direction: column; align-items: center; gap: var(--space-1); height: 100%; justify-content: flex-end; }
.week-bar-num { font-size: var(--fs-aux2); color: var(--text-secondary); }
.week-bar-track { width: 100%; max-width: 48px; flex: 1; display: flex; align-items: flex-end; background: var(--bg-subtle); border-radius: var(--radius-sm); overflow: hidden; }
.week-bar-fill { width: 100%; background: var(--brand); border-radius: var(--radius-sm) var(--radius-sm) 0 0; min-height: 4px; }
.week-bar-label { font-size: var(--fs-aux); color: var(--text-secondary); }
.field-row { display: flex; gap: var(--space-3); align-items: flex-start; }
.shortcuts { display: flex; gap: var(--space-3); margin-top: var(--space-5); }
.shortcut-card {
  flex: 1;
  padding: var(--space-4);
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-2);
  cursor: pointer;
  color: var(--text-primary);
  font-size: var(--fs-body);
}
.shortcut-card:hover { border-color: var(--brand); color: var(--brand); }
</style>
