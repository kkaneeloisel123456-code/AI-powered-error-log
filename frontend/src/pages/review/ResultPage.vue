<script setup lang="ts">
/** 复习页阶段三「批改结果」（896px）：得分总览 + 逐题详情（绿/红边框、认可/不认可）+ 完成/重做/回首页。 */
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { RefreshCw, RotateCcw } from 'lucide-vue-next'
import { useReviewStore } from '@/stores/review'
import { disableCockpit, isCockpitEnabled } from '@/utils/cockpit'
import { toast } from '@/components/common/toast'
import ResultOverview from '@/components/review/ResultOverview.vue'
import ResultItem from '@/components/review/ResultItem.vue'
import SkeletonList from '@/components/common/SkeletonList.vue'

const store = useReviewStore()
const route = useRoute()
const router = useRouter()

const sessionId = computed(() => route.params.sessionId as string)
const cockpitWasOn = ref(false)

onMounted(() => {
  if (store.status !== 'done' && store.sessionId !== sessionId.value) {
    // 直达结果页：恢复会话并等待批改
    store.sessionId = sessionId.value
    store.status = 'grading'
    store.startGradingPolling()
  }
  cockpitWasOn.value = isCockpitEnabled()
  if (cockpitWasOn.value) disableCockpit()
})

onBeforeUnmount(() => store.stopPolling())

async function onRegrade(variantId: string) {
  try {
    await store.regrade(variantId)
    toast.success('已重新批改（不重复计入统计）')
  } catch (err) {
    toast.error((err as Error).message)
  }
}

function redo() {
  const config = store.config
  store.reset()
  router.push({ path: '/review' })
  if (config) {
    void import('@/stores/review').then(({ useReviewStore }) => {
      useReviewStore().config = config
    })
  }
}
</script>

<template>
  <div class="review-result-page">
    <div style="display: flex; align-items: center; gap: var(--space-2); margin-bottom: var(--space-4);">
      <h1 style="font-size: var(--fs-page-title); font-weight: 600;">批改结果</h1>
      <span class="chip">阶段 3 / 3 · 批改结果</span>
    </div>

    <template v-if="store.report">
      <ResultOverview :report="store.report" />
      <ResultItem
        v-for="(item, i) in store.report.items"
        :key="item.variant_id"
        :item="item"
        :index="i"
        @regrade="onRegrade"
      />
      <div style="display: flex; gap: var(--space-2); justify-content: center; margin-top: var(--space-4);">
        <button class="btn btn-primary" @click="router.push('/')">完成并更新计划</button>
        <button class="btn btn-secondary" @click="redo"><RotateCcw :size="14" /> 重做一次</button>
        <button class="btn btn-text" @click="router.push('/')">返回首页</button>
      </div>
    </template>
    <template v-else>
      <SkeletonList :rows="3" />
      <p style="display: flex; align-items: center; justify-content: center; gap: var(--space-2); color: var(--text-secondary); margin-top: var(--space-4);">
        <RefreshCw :size="14" class="spin" /> AI 正在批改…
      </p>
      <div v-if="store.error" class="field-error" style="text-align: center; margin-top: var(--space-3);">{{ store.error }}</div>
    </template>
  </div>
</template>

<style scoped>
.review-result-page { max-width: 896px; margin: 0 auto; }
.spin { animation: spin 1s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }
</style>
