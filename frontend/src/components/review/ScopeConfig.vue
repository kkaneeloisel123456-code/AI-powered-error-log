<script setup lang="ts">
/** 阶段一「选范围」（UI/UX 4.5）：学科 chips（必选）、题数 5/10/15、难度、范围；手动选题展开列表。 */
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { mistakesApi } from '@/api/mistakes'
import { useMistakesStore } from '@/stores/mistakes'
import { useReviewStore } from '@/stores/review'

const router = useRouter()
const mistakesStore = useMistakesStore()
const reviewStore = useReviewStore()

const selectedSubjects = ref<number[]>([])
const count = ref(5)
const difficulty = ref('auto')
const scope = ref('due')
const manualIds = ref<string[]>([])
const manualOptions = ref<Array<{ id: string; excerpt: string }>>([])
const manualLoading = ref(false)
const errorMsg = ref('')
const creating = ref(false)

const counts = [5, 10, 15]
const difficulties = [
  { value: 'auto', label: '自适应' },
  { value: 'easy', label: '易' },
  { value: 'medium', label: '中' },
  { value: 'hard', label: '难' },
]
const scopes = [
  { value: 'due', label: '今日到期' },
  { value: 'all', label: '全部' },
  { value: 'weak', label: '薄弱知识点' },
  { value: 'manual', label: '手动选题' },
]

const canStart = computed(() => selectedSubjects.value.length > 0 && (scope.value !== 'manual' || manualIds.value.length > 0))

onMounted(async () => {
  if (mistakesStore.subjects.length === 0) await mistakesStore.fetchSubjects()
  if (reviewStore.config) {
    // 从首页一键复习带入
    selectedSubjects.value = reviewStore.config.subject_ids
    count.value = reviewStore.config.count
    difficulty.value = reviewStore.config.difficulty
    scope.value = reviewStore.config.scope
  }
})

function toggleSubject(id: number) {
  const idx = selectedSubjects.value.indexOf(id)
  if (idx >= 0) selectedSubjects.value.splice(idx, 1)
  else selectedSubjects.value.push(id)
}

async function loadManualOptions() {
  manualLoading.value = true
  try {
    const resp = await mistakesApi.list({ sort: 'created_at', order: 'desc' }, 1, 100)
    manualOptions.value = resp.items.map((it) => ({ id: it.id, excerpt: it.question_excerpt }))
  } finally {
    manualLoading.value = false
  }
}

async function start() {
  if (!canStart.value) {
    errorMsg.value = '请至少选择一个学科'
    return
  }
  errorMsg.value = ''
  creating.value = true
  try {
    await reviewStore.createSession({
      subject_ids: selectedSubjects.value,
      count: count.value,
      difficulty: difficulty.value,
      scope: scope.value,
      mistake_ids: scope.value === 'manual' ? manualIds.value : [],
    })
    router.push('/review/answer')
  } catch (err) {
    errorMsg.value = (err as Error).message
  } finally {
    creating.value = false
  }
}
</script>

<template>
  <div class="card" style="padding: var(--space-5);">
    <div class="field" style="margin-bottom: var(--space-4);">
      <label class="field-label">学科（必选，可多选）</label>
      <div class="subject-chips">
        <button
          v-for="s in mistakesStore.subjects.filter((s) => s.is_active)"
          :key="s.id"
          class="chip clickable"
          :class="{ 'chip-selected': selectedSubjects.includes(s.id) }"
          @click="toggleSubject(s.id)"
        >
          {{ s.name }}<span v-if="s.mistake_count" class="num"> {{ s.mistake_count }}</span>
        </button>
      </div>
    </div>

    <div class="field" style="margin-bottom: var(--space-4);">
      <label class="field-label">题数</label>
      <div class="segmented">
        <button v-for="c in counts" :key="c" :class="{ active: count === c }" @click="count = c">{{ c }}</button>
      </div>
    </div>

    <div class="field" style="margin-bottom: var(--space-4);">
      <label class="field-label">难度</label>
      <div class="segmented">
        <button v-for="d in difficulties" :key="d.value" :class="{ active: difficulty === d.value }" @click="difficulty = d.value">{{ d.label }}</button>
      </div>
    </div>

    <div class="field" style="margin-bottom: var(--space-4);">
      <label class="field-label">复习范围</label>
      <div class="segmented" style="flex-wrap: wrap;">
        <button
          v-for="s in scopes"
          :key="s.value"
          :class="{ active: scope === s.value }"
          @click="scope = s.value; if (s.value === 'manual') loadManualOptions()"
        >{{ s.label }}</button>
      </div>
    </div>

    <!-- 手动选题多选列表 -->
    <div v-if="scope === 'manual'" class="manual-list">
      <div v-if="manualLoading" class="skeleton" style="height: 64px;"></div>
      <label v-for="opt in manualOptions" :key="opt.id" class="manual-row">
        <input
          type="checkbox"
          :checked="manualIds.includes(opt.id)"
          @change="($event.target as HTMLInputElement).checked ? manualIds.push(opt.id) : (manualIds = manualIds.filter((i) => i !== opt.id))"
        />
        <span>{{ opt.excerpt }}</span>
      </label>
    </div>

    <div v-if="errorMsg" class="field-error" style="margin-bottom: var(--space-3);">{{ errorMsg }}</div>

    <div style="display: flex; gap: var(--space-2); justify-content: flex-end;">
      <button class="btn btn-secondary" @click="router.push('/')">返回</button>
      <button class="btn btn-primary" :disabled="!canStart || creating" @click="start">
        {{ creating ? '生成中…' : '开始复习' }}
      </button>
    </div>
  </div>
</template>

<style scoped>
.subject-chips { display: flex; flex-wrap: wrap; gap: var(--space-2); }
.chip-selected {
  background: var(--brand-8);
  color: var(--brand);
  outline: 1px solid var(--brand);
}
.manual-list {
  margin-bottom: var(--space-3);
  max-height: 240px;
  overflow-y: auto;
  border: var(--border-1);
  border-radius: var(--radius-md);
  padding: var(--space-2);
}
.manual-row {
  display: flex;
  gap: var(--space-2);
  align-items: flex-start;
  padding: var(--space-2);
  font-size: var(--fs-aux2);
  cursor: pointer;
  border-radius: var(--radius-sm);
}
.manual-row:hover { background: var(--bg-subtle); }
.manual-row span {
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
</style>
