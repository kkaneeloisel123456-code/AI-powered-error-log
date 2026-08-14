<script setup lang="ts">
/** 错题集主页（UI/UX 3.2 / 4.2）：260px 列表 + 详情双栏。
 * - 分页 + 滚动加载；空状态（无错题本引导 / 三入口 / 无结果清除筛选）；
 * - 勾选浮现批量操作（批量删除/改状态/打标签）；
 * - 选中态与筛选同步到 URL query，切回恢复。 */
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { BookOpen, Bot, FileInput, Tags, Trash2 } from 'lucide-vue-next'
import { useMistakesStore } from '@/stores/mistakes'
import { useInfiniteScroll } from '@/utils/useInfiniteScroll'
import { exportMarkdown, exportPdf, needsBatchWarning } from '@/utils/export'
import { ZH } from '@/constants/zh'
import { toast } from '@/components/common/toast'
import MistakeCard from '@/components/mistake/MistakeCard.vue'
import DetailPanel from '@/components/mistake/DetailPanel.vue'
import FilterBar from '@/components/mistake/FilterBar.vue'
import SkeletonList from '@/components/common/SkeletonList.vue'
import EmptyState from '@/components/common/EmptyState.vue'
import ConfirmDialog from '@/components/common/ConfirmDialog.vue'
import ColorPickerPopover from '@/components/mistake/ColorPickerPopover.vue'

const store = useMistakesStore()
const route = useRoute()
const router = useRouter()

const sentinel = ref<HTMLElement | null>(null)
const batchDeleteOpen = ref(false)
const batchStatusAnchor = ref<HTMLElement | null>(null)
const batchStatusOpen = ref(false)
const tagDialogOpen = ref(false)
const tagInput = ref('')
const exportMenuOpen = ref(false)
const exportDialog = ref<{ kind: 'md' | 'pdf' } | null>(null)

const selectedDetail = computed(() => store.detail)
const showGuide = computed(() => !store.loading && !store.error && store.items.length === 0 && !store.filtersActive && !store.notebookCreated && store.total === 0)
const showThreeEntries = computed(() => !store.loading && !store.error && store.items.length === 0 && !store.filtersActive && store.notebookCreated && store.total === 0)
const showNoResult = computed(() => !store.loading && !store.error && store.items.length === 0 && store.filtersActive)

useInfiniteScroll(sentinel, {
  hasMore: () => store.hasMore,
  loading: () => store.loadingMore,
  onLoadMore: () => void store.loadMore(),
})

onMounted(async () => {
  store.applyFiltersFromQuery(route.query)
  await Promise.all([store.fetchSubjects(), store.fetchList(true)])
  const id = route.query.id as string | undefined
  if (id) void selectMistake(id)
})

watch(
  () => route.query.q,
  (q) => {
    if (typeof q === 'string') {
      store.setFilter({ q })
      void store.fetchList(true)
    }
  },
)

async function selectMistake(id: string, mobile = false) {
  if (mobile) {
    router.push(`/mistakes/${id}`)
    return
  }
  await router.replace({ path: '/mistakes', query: { ...route.query, id } })
  void store.fetchDetail(id)
}

function closeDetail() {
  void router.replace({ path: '/mistakes', query: { ...route.query, id: undefined } })
  store.detail = null
}

async function doBatchStatus(color: string, status: string | null) {
  batchStatusOpen.value = false
  try {
    // 状态色：同步状态 + 颜色；自定义色：仅改颜色
    await store.batchOp(status ? 'set_status' : 'set_color', status ?? color)
    toast.success('批量更新完成')
  } catch (err) {
    toast.error((err as Error).message)
  }
}

async function confirmBatchDelete() {
  try {
    await store.batchOp('delete')
    batchDeleteOpen.value = false
    toast.success('已批量删除')
  } catch (err) {
    toast.error((err as Error).message)
  }
}

async function addTags() {
  const value = tagInput.value.trim()
  if (!value) return
  try {
    await store.batchOp('add_tags', value)
    tagDialogOpen.value = false
    tagInput.value = ''
    toast.success('已添加标签')
  } catch (err) {
    toast.error((err as Error).message)
  }
}

function requestExport(kind: 'md' | 'pdf') {
  exportMenuOpen.value = false
  // EX-09 / PRD 7.7-23：超过 200 题提示分批导出，同时允许继续生成
  if (needsBatchWarning(store.total)) {
    exportDialog.value = { kind }
  } else {
    void doExport(kind)
  }
}

async function doExport(kind: 'md' | 'pdf') {
  exportDialog.value = null
  const filters = { ...store.filters }
  try {
    if (kind === 'md') {
      await exportMarkdown(filters)
      toast.success('已导出 Markdown')
    } else {
      exportPdf(filters)
      toast.info('已打开打印预览，选择「另存为 PDF」即可')
    }
  } catch (err) {
    toast.error((err as Error).message || ZH.errors.exportFailed)
  }
}
</script>

<template>
  <div class="mistakes-page">
    <!-- 顶部工具栏：面包屑 + 新建 + 批量操作 -->
    <div class="page-toolbar">
      <h1 style="font-size: var(--fs-page-title); font-weight: 600;">错题本</h1>
      <span class="hit-count">共 {{ store.total }} 题</span>
      <span class="spacer" />
      <template v-if="store.selectedCount > 0">
        <span style="color: var(--text-secondary); font-size: var(--fs-aux2);">已选 {{ store.selectedCount }} 题</span>
        <button ref="batchStatusAnchor" class="btn btn-secondary btn-sm" @click="batchStatusOpen = !batchStatusOpen">批量改状态</button>
        <button class="btn btn-secondary btn-sm" @click="tagDialogOpen = true"><Tags :size="14" /> 批量打标签</button>
        <button class="btn btn-danger btn-sm" @click="batchDeleteOpen = true"><Trash2 :size="14" /> 批量删除</button>
        <button class="btn btn-text btn-sm" @click="store.clearSelection()">取消选择</button>
      </template>
      <button v-else class="btn btn-primary btn-sm" @click="router.push('/import')">录入错题</button>
      <div style="position: relative;">
        <button class="btn btn-secondary btn-sm" @click="exportMenuOpen = !exportMenuOpen">导出</button>
        <div v-if="exportMenuOpen" class="card export-menu">
          <button class="export-item" @click="requestExport('md')">导出 Markdown（.md）</button>
          <button class="export-item" @click="requestExport('pdf')">导出 PDF（打印预览）</button>
        </div>
      </div>
    </div>

    <!-- 错误态 -->
    <div v-if="store.error" class="card" style="padding: var(--space-4); display: flex; align-items: center; gap: var(--space-3);">
      <span style="color: var(--error);">{{ store.error }}</span>
      <span class="spacer" />
      <button class="btn btn-secondary btn-sm" @click="store.fetchList(true)">重试</button>
    </div>

    <div class="grid-mistakes">
      <!-- 左栏：260px 列表 -->
      <div class="list-panel">
        <FilterBar />
        <SkeletonList v-if="store.loading" />
        <template v-else>
          <div class="select-all-row">
            <label style="display: flex; align-items: center; gap: var(--space-2); font-size: var(--fs-aux2); color: var(--text-secondary); cursor: pointer;">
              <input type="checkbox" :checked="store.selectedCount === store.items.length && store.items.length > 0" @change="store.selectAllVisible(($event.target as HTMLInputElement).checked)" />
              全选本页
            </label>
          </div>
          <div v-if="store.items.length" class="mistake-list">
            <MistakeCard
              v-for="item in store.items"
              :key="item.id"
              :item="item"
              :selected="item.id === selectedDetail?.id"
              @select="selectMistake(item.id)"
            />
            <div ref="sentinel" style="height: 1px;"></div>
            <div v-if="store.loadingMore" style="padding: var(--space-2);">
              <SkeletonList :rows="3" />
            </div>
          </div>
          <!-- 空状态 -->
          <EmptyState v-else-if="showGuide" :title="ZH.emptyStates.noNotebookTitle" :desc="ZH.emptyStates.noNotebookDesc">
            <button class="btn btn-primary" @click="router.push('/import')">{{ ZH.emptyStates.noNotebookAction }}</button>
          </EmptyState>
          <EmptyState v-else-if="showThreeEntries" :title="ZH.emptyStates.emptyNotebookTitle">
            <div style="display: flex; gap: var(--space-3); flex-wrap: wrap; justify-content: center;">
              <button v-for="(entry, key) in ZH.emptyStates.emptyNotebookEntries" :key="key" class="card entry-card" @click="router.push(key === 'chat' ? '/chat' : `/import?mode=${key === 'image' ? 'image' : 'text'}`)">
                <Bot v-if="key === 'chat'" :size="22" :stroke-width="1.5" style="color: var(--brand);" />
                <FileInput v-else-if="key === 'image'" :size="22" :stroke-width="1.5" style="color: var(--brand);" />
                <BookOpen v-else :size="22" :stroke-width="1.5" style="color: var(--brand);" />
                <div style="font-weight: 600; font-size: var(--fs-body);">{{ entry.title }}</div>
                <div style="font-size: var(--fs-aux2); color: var(--text-secondary);">{{ entry.desc }}</div>
              </button>
            </div>
          </EmptyState>
          <EmptyState v-else-if="showNoResult" :title="ZH.common.noResult">
            <button class="btn btn-secondary" @click="store.resetFilters(); store.fetchList(true)">{{ ZH.common.clearFilters }}</button>
          </EmptyState>
        </template>
      </div>

      <!-- 右栏：详情 -->
      <div class="detail-panel-area">
        <SkeletonList v-if="store.detailLoading" :rows="2" />
        <div v-else-if="store.detailError" class="card" style="padding: var(--space-4); color: var(--error);">
          {{ store.detailError }}
          <button class="btn btn-secondary btn-sm" style="margin-left: var(--space-3);" @click="store.detail && store.fetchDetail(store.detail.id)">重试</button>
        </div>
        <DetailPanel
          v-else-if="selectedDetail"
          :mistake="selectedDetail"
          @deleted="closeDetail"
        />
        <EmptyState v-else title="选择左侧错题查看详情" desc="或点击顶部「录入错题」新增" />
      </div>
    </div>

    <ConfirmDialog
      v-if="batchDeleteOpen"
      title="批量删除错题？"
      :message="`将删除选中的 ${store.selectedCount} 道错题及其复习计划，历史复习记录保留。此操作不可撤销。`"
      confirm-text="删除"
      danger
      @confirm="confirmBatchDelete"
      @cancel="batchDeleteOpen = false"
    />
    <ColorPickerPopover
      v-if="batchStatusOpen"
      :anchor="batchStatusAnchor"
      :current-color="'#6B7280'"
      @select="doBatchStatus"
      @close="batchStatusOpen = false"
    />
    <ConfirmDialog
      v-if="tagDialogOpen"
      title="批量打标签"
      :message="`为选中的 ${store.selectedCount} 道题添加标签`"
      confirm-text="添加"
      @confirm="addTags"
      @cancel="tagDialogOpen = false"
    >
      <input v-model="tagInput" class="input" placeholder="标签名，如：期中" style="margin-bottom: var(--space-3);" @keydown.enter="addTags" />
    </ConfirmDialog>

    <!-- EX-09 / PRD 7.7-23：超 200 题提示分批，允许继续 -->
    <ConfirmDialog
      v-if="exportDialog"
      title="导出范围较大"
      :message="`当前共 ${store.total} 题，超过 200 题建议分批导出以避免渲染卡顿。`"
      :confirm-text="`继续导出（${store.total} 题）`"
      @confirm="doExport(exportDialog.kind)"
      @cancel="exportDialog = null"
    />
  </div>
</template>

<style scoped>
.mistakes-page { display: flex; flex-direction: column; gap: var(--space-3); }
.page-toolbar {
  display: flex;
  align-items: center;
  gap: var(--space-3);
}
.hit-count { font-size: var(--fs-aux2); color: var(--text-secondary); }
.spacer { flex: 1; }

/* UI/UX 3.2：双栏 260px + 详情，左栏 sticky 滚动 */
.grid-mistakes {
  display: grid;
  grid-template-columns: 260px minmax(0, 1fr);
  gap: var(--space-4);
  align-items: start;
}
.list-panel {
  position: sticky;
  top: calc(var(--topbar-height) + var(--space-3));
  max-height: calc(100vh - var(--topbar-height) - 96px);
  overflow-y: auto;
  padding-right: var(--space-1);
}
.detail-panel-area { min-width: 0; }
.select-all-row {
  padding: 0 var(--space-1) var(--space-2);
}
.entry-card {
  width: 200px;
  padding: var(--space-4);
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space-2);
  cursor: pointer;
  text-align: center;
  color: var(--text-primary);
}
.entry-card:hover { border-color: var(--brand); }
.export-menu {
  position: absolute;
  right: 0;
  top: calc(100% + var(--space-1));
  z-index: 60;
  min-width: 200px;
  padding: var(--space-1);
  box-shadow: 0 4px 12px rgba(16, 24, 40, 0.14);
}
.export-item {
  width: 100%;
  display: block;
  padding: var(--space-2) var(--space-3);
  font-size: var(--fs-aux2);
  text-align: left;
  border-radius: var(--radius-sm);
}
.export-item:hover { background: var(--brand-8); color: var(--brand); }

/* 平板：左栏 220px（UI/UX 9.3） */
@media (max-width: 1199px) {
  .grid-mistakes { grid-template-columns: 220px minmax(0, 1fr); }
}
/* 移动：单栏钻取 */
@media (max-width: 767px) {
  .grid-mistakes { grid-template-columns: minmax(0, 1fr); }
  .list-panel { position: static; max-height: none; overflow: visible; }
}
</style>
