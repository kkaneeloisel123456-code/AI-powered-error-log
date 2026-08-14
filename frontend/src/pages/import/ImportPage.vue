<script setup lang="ts">
/** 录入页（UI/UX 3.4 / 4.4）：单栏 768px，识图/文本分段控件，底部操作条吸附。
 * - 上传 -> OCR 三阶段进度 -> 候选题勾选/编辑/删除 -> 导入
 * - 草稿恢复（继续上次导入）；EX-03 兜底（换图/文本录入）。 */
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ArrowLeft, Download } from 'lucide-vue-next'
import { useImportStore } from '@/stores/importTask'
import { toast } from '@/components/common/toast'
import ImageUploader from '@/components/import/ImageUploader.vue'
import TaskProgress from '@/components/import/TaskProgress.vue'
import CandidateCard from '@/components/import/CandidateCard.vue'
import TextImportForm from '@/components/import/TextImportForm.vue'
import SkeletonList from '@/components/common/SkeletonList.vue'

const store = useImportStore()
const route = useRoute()
const router = useRouter()

const draftConfirm = ref(false)

const showUploader = computed(() => store.mode === 'image' && !store.taskId && !store.taskError)
const showProgress = computed(() => store.mode === 'image' && store.taskId)
const showCandidates = computed(() => store.mode === 'image' && store.taskStatus === 'awaiting_confirm' && store.candidates.length > 0)
const canImport = computed(() => store.selectedCandidates.length > 0)

onMounted(() => {
  const mode = route.query.mode
  store.setMode(mode === 'text' ? 'text' : 'image')
  if (store.hasDraft) draftConfirm.value = true
})

onBeforeUnmount(() => store.stopPolling())

function onUpload(file: File) {
  void store.upload(file, crypto.randomUUID())
}

function onUploadError(message: string) {
  toast.error(message)
}

async function doImport() {
  try {
    const result = await store.importSelected()
    if (result) {
      toast.success(`已导入 ${result.imported} 题${result.duplicates ? `，跳过重复 ${result.duplicates} 题` : ''}`)
      router.push('/mistakes')
    }
  } catch (err) {
    toast.error((err as Error).message)
  }
}

function toTextMode() {
  store.resetTask()
  store.setMode('text')
}

function restoreDraft() {
  draftConfirm.value = false
  store.restoreDraft()
  store.setMode('image')
}
</script>

<template>
  <div class="import-page">
    <!-- 标题与返回 -->
    <div style="display: flex; align-items: center; gap: var(--space-2); margin-bottom: var(--space-3);">
      <button class="btn btn-text btn-sm" aria-label="返回首页" @click="router.push('/')"><ArrowLeft :size="14" /></button>
      <h1 style="font-size: var(--fs-page-title); font-weight: 600;">录入错题</h1>
    </div>

    <!-- 草稿恢复 -->
    <div v-if="draftConfirm" class="card" style="padding: var(--space-3); margin-bottom: var(--space-3); display: flex; align-items: center; gap: var(--space-2);">
      <span style="font-size: var(--fs-aux2); color: var(--text-secondary);">检测到上次未完成的导入</span>
      <span class="spacer" />
      <button class="btn btn-primary btn-sm" @click="restoreDraft"><Download :size="14" /> 继续上次导入</button>
      <button class="btn btn-text btn-sm" @click="draftConfirm = false; store.clearDraft()">放弃</button>
    </div>

    <!-- 分段控件 -->
    <div class="segmented" style="margin-bottom: var(--space-4);">
      <button :class="{ active: store.mode === 'image' }" @click="store.setMode('image')">识图录入</button>
      <button :class="{ active: store.mode === 'text' }" @click="store.setMode('text')">文本录入</button>
    </div>

    <!-- 识图模式 -->
    <template v-if="store.mode === 'image'">
      <ImageUploader v-if="showUploader" @upload="onUpload" @error="onUploadError" />

      <TaskProgress
        v-if="showProgress"
        :status="store.taskStatus"
        :error="store.taskError"
        @retry="store.retry()"
        @reset="store.cancelTask()"
        @to-text="toTextMode"
      />

      <!-- OCR 识别中骨架屏 -->
      <SkeletonList v-if="store.taskStatus && !store.taskError && store.taskStatus !== 'awaiting_confirm'" :rows="2" />

      <!-- 候选题列表 -->
      <template v-if="showCandidates">
        <CandidateCard
          v-for="(cand, i) in store.candidates"
          :key="i"
          :candidate="cand"
          :index="i"
          @toggle="store.toggleCandidate"
          @update="store.updateCandidate"
          @remove="store.removeCandidate"
        />
      </template>
    </template>

    <!-- 文本模式 -->
    <TextImportForm v-else @saved="router.push('/mistakes')" />

    <!-- 底部操作条（吸附视口底部） -->
    <div v-if="showCandidates" class="import-actions">
      <span style="font-size: var(--fs-aux2); color: var(--text-secondary);">已选 {{ store.selectedCandidates.length }} 题</span>
      <span class="spacer" />
      <button class="btn btn-secondary" @click="store.cancelTask()">取消</button>
      <button class="btn btn-primary" :disabled="!canImport || store.importing" @click="doImport">
        {{ store.importing ? '导入中…' : `导入（${store.selectedCandidates.length}）` }}
      </button>
    </div>
  </div>
</template>

<style scoped>
.import-page { max-width: 768px; margin: 0 auto; padding-bottom: 96px; }
.spacer { flex: 1; }
.import-actions {
  position: sticky;
  bottom: var(--space-4);
  z-index: 20;
  display: flex;
  align-items: center;
  gap: var(--space-3);
  margin-top: var(--space-4);
  padding: var(--space-3) var(--space-4);
  background: var(--bg-card);
  border: var(--border-1);
  border-radius: var(--radius-lg);
  box-shadow: 0 4px 12px rgba(16, 24, 40, 0.12);
}
</style>
