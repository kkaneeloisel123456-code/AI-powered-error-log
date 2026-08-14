<script setup lang="ts">
/** 复习页阶段二「逐题作答」（单栏 768px）：
 * 顶部固定进度条（第 N 题/共 M、计时、退出）、题目卡、上一题/下一题/提交交卷、
 * 交卷确认弹窗（EX-08）、专注舱切换。 */
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ChevronLeft, ChevronRight, Moon } from 'lucide-vue-next'
import { useReviewStore } from '@/stores/review'
import { disableCockpit, enableCockpit, isCockpitEnabled } from '@/utils/cockpit'
import { formatDuration } from '@/utils/format'
import QuestionCard from '@/components/review/QuestionCard.vue'
import SkeletonList from '@/components/common/SkeletonList.vue'
import ConfirmDialog from '@/components/common/ConfirmDialog.vue'
import { toast } from '@/components/common/toast'

const store = useReviewStore()
const router = useRouter()

const submitDialogOpen = ref(false)
const elapsed = ref(0)
const cockpit = ref(false)
let timer: number | null = null

const current = computed(() => store.variants[store.currentIndex])
const currentAnswer = computed(() => (current.value ? store.answers[current.value.variant_id] : undefined))
const replacing = ref(false)

onMounted(() => {
  // 仅在无会话时弹回选范围页；generating 阶段 total=0 属正常等待
  if (!store.sessionId || store.status === 'idle') {
    router.replace('/review')
    return
  }
  cockpit.value = isCockpitEnabled()
  if (cockpit.value) enableCockpit()
  timer = window.setInterval(() => {
    if (store.startedAt) elapsed.value = Math.floor((Date.now() - store.startedAt) / 1000)
  }, 1000)
})

onBeforeUnmount(() => {
  if (timer) clearInterval(timer)
  if (cockpit.value) disableCockpit()
})

function toggleCockpit() {
  cockpit.value = !cockpit.value
  if (cockpit.value) enableCockpit()
  else disableCockpit()
}

function prev() {
  if (store.currentIndex > 0) store.currentIndex -= 1
}

function next() {
  if (store.currentIndex < store.total - 1) store.currentIndex += 1
}

function trySubmit() {
  // EX-08：存在未作答题时弹窗确认
  if (store.unansweredCount > 0) {
    submitDialogOpen.value = true
  } else {
    void doSubmit()
  }
}

async function doSubmit() {
  submitDialogOpen.value = false
  await store.submit()
  router.push(`/review/result/${store.sessionId}`)
}

async function onReplace() {
  if (!current.value) return
  replacing.value = true
  try {
    await store.replaceVariant(current.value.variant_id)
  } catch (err) {
    toast.error((err as Error).message)
  } finally {
    replacing.value = false
  }
}

function exit() {
  store.reset()
  router.push('/')
}
</script>

<template>
  <div class="review-page">
    <!-- 顶部固定进度条 -->
    <div class="answer-topbar">
      <span class="num" style="font-weight: 600;">第 {{ store.currentIndex + 1 }} 题 / 共 {{ store.total }} 题</span>
      <div class="progress-track" style="flex: 1; max-width: 320px;">
        <div class="progress-fill" :style="{ width: `${(store.currentIndex / store.total) * 100}%` }"></div>
      </div>
      <span class="num" style="color: var(--text-secondary); font-size: var(--fs-aux2);">{{ formatDuration(elapsed) }}</span>
      <span class="spacer" />
      <button class="btn btn-icon" :title="cockpit ? '退出专注舱' : '进入专注舱'" @click="toggleCockpit"><Moon :size="16" :stroke-width="1.5" /></button>
      <button class="btn btn-text btn-sm" @click="exit">退出</button>
    </div>

    <div v-if="store.status === 'generating'" style="margin-top: var(--space-4);">
      <SkeletonList :rows="2" />
      <p style="text-align: center; color: var(--text-secondary); font-size: var(--fs-aux2);">AI 正在生成变体题…</p>
    </div>
    <template v-else-if="current">
      <QuestionCard
        :variant="current"
        :index="store.currentIndex"
        :total="store.total"
        :answer="currentAnswer"
        :replace-left="store.replaceLeft"
        :replacing="replacing"
        @answer="(answer, unsure) => store.setAnswer(current.variant_id, answer, unsure)"
        @replace="onReplace"
      />
      <div style="display: flex; gap: var(--space-2); justify-content: space-between;">
        <button class="btn btn-secondary" :disabled="store.currentIndex === 0" @click="prev"><ChevronLeft :size="16" /> 上一题</button>
        <button v-if="store.currentIndex < store.total - 1" class="btn btn-primary" @click="next">下一题 <ChevronRight :size="16" /></button>
        <button v-else class="btn btn-primary" :disabled="store.status === 'submitting'" @click="trySubmit">
          {{ store.status === 'submitting' ? '提交中…' : '提交交卷' }}
        </button>
      </div>
    </template>

    <!-- EX-08：交卷确认弹窗 -->
    <ConfirmDialog
      v-if="submitDialogOpen"
      title="还有未作答的题目"
      :message="`还有 ${store.unansweredCount} 题未作答，确认交卷后未答题按错误计。`"
      confirm-text="确认交卷"
      danger
      @confirm="doSubmit"
      @cancel="submitDialogOpen = false"
    >
      <button class="btn btn-secondary" style="width: 100%; margin-bottom: var(--space-3);" @click="submitDialogOpen = false">继续作答</button>
    </ConfirmDialog>
  </div>
</template>

<style scoped>
.review-page { max-width: 768px; margin: 0 auto; }
.answer-topbar {
  position: sticky;
  top: var(--topbar-height);
  z-index: 20;
  display: flex;
  align-items: center;
  gap: var(--space-3);
  background: var(--bg-card);
  border: var(--border-1);
  border-radius: var(--radius-lg);
  padding: var(--space-2) var(--space-4);
  margin-bottom: var(--space-4);
}
.spacer { flex: 1; }
.progress-track { height: 4px; border-radius: 2px; background: var(--bg-subtle); overflow: hidden; }
.progress-fill { height: 100%; background: var(--brand); transition: width var(--dur-collapse) ease; }
</style>
