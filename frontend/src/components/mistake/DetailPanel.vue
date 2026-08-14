<script setup lang="ts">
/** 右栏详情/编辑区：
 * - 题目区 border-left 3px 蓝（var(--brand)）；
 * - 解析区 border-left 3px 绿（var(--brand-secondary)），可折叠；
 * - 元信息行：状态色点（点击弹出颜色气泡）、标签、来源、复习统计、掌握度；
 * - 操作区：编辑 / 删除（二次确认）/ 复制 / 加入复习（M3）/ 导出（M4）。 */
import { computed, onMounted, ref } from 'vue'
import { CalendarClock, Check, Copy, GraduationCap, Pencil, Trash2 } from 'lucide-vue-next'
import { subjectsApi } from '@/api/subjects'
import type { MistakeDetail } from '@/api/types'
import { ZH } from '@/constants/zh'
import { useMistakesStore } from '@/stores/mistakes'
import { formatDate, formatRelative, percent } from '@/utils/format'
import { toast } from '@/components/common/toast'
import ConfirmDialog from '@/components/common/ConfirmDialog.vue'
import ColorPickerPopover from './ColorPickerPopover.vue'

const props = defineProps<{ mistake: MistakeDetail; mobile?: boolean }>()
const emit = defineEmits<{ changed: [m: MistakeDetail]; deleted: [] }>()

const store = useMistakesStore()

const analysisOpen = ref(true)
const editing = ref(false)
const deleting = ref(false)
const colorAnchor = ref<HTMLElement | null>(null)
const colorPickerOpen = ref(false)

// 编辑表单
const form = ref({ question_text: '', optionsText: '', answer_text: '', analysis: '', subject_id: 0, kp_id: null as number | null, error_type: 'other', tagsText: '', note: '' })
const kpOptions = ref<Array<{ id: number; name: string }>>([])
const formError = ref('')

const statusLabel = computed(() => ZH.status[props.mistake.status as keyof typeof ZH.status] ?? props.mistake.status)
const errorTypeLabel = computed(() => ZH.errorTypes[props.mistake.error_type as keyof typeof ZH.errorTypes] ?? props.mistake.error_type)
const sourceLabel = computed(() => ZH.source[props.mistake.source as keyof typeof ZH.source] ?? props.mistake.source)

onMounted(() => {
  if (props.mistake.subject_id) void loadKps(props.mistake.subject_id)
})

async function loadKps(subjectId: number) {
  kpOptions.value = await subjectsApi.knowledgePoints(subjectId)
}

function startEdit() {
  form.value = {
    question_text: props.mistake.question_text,
    optionsText: props.mistake.options.join('\n'),
    answer_text: props.mistake.answer_text,
    analysis: props.mistake.analysis,
    subject_id: props.mistake.subject_id,
    kp_id: props.mistake.kp_id,
    error_type: props.mistake.error_type,
    tagsText: props.mistake.tags.join(', '),
    note: props.mistake.note,
  }
  editing.value = true
}

async function saveEdit() {
  if (!form.value.question_text.trim()) {
    formError.value = ZH.errors.emptyQuestion
    return
  }
  formError.value = ''
  const payload: Record<string, unknown> = {
    question_text: form.value.question_text,
    options: form.value.optionsText.split('\n').map((s) => s.trim()).filter(Boolean),
    answer_text: form.value.answer_text,
    analysis: form.value.analysis,
    subject_id: form.value.subject_id,
    kp_id: form.value.kp_id,
    error_type: form.value.error_type,
    tags: form.value.tagsText.split(/[,，]/).map((s) => s.trim()).filter(Boolean),
    note: form.value.note,
  }
  try {
    const updated = await store.updateMistake(props.mistake.id, payload)
    editing.value = false
    emit('changed', updated)
    toast.success('已保存')
  } catch (err) {
    formError.value = (err as Error).message
  }
}

async function confirmDelete() {
  try {
    await store.removeMistake(props.mistake.id)
    deleting.value = false
    emit('deleted')
    toast.success('已删除')
  } catch (err) {
    toast.error((err as Error).message)
  }
}

async function pickColor(color: string, status: string | null) {
  colorPickerOpen.value = false
  try {
    const updated = await store.updateMistake(props.mistake.id, status ? { color, status } : { color })
    emit('changed', updated)
  } catch (err) {
    toast.error((err as Error).message)
  }
}

async function copyQuestion() {
  const text = [props.mistake.question_text, ...props.mistake.options].join('\n')
  await navigator.clipboard.writeText(text)
  toast.success(ZH.common.copied)
}

async function changeSubject(subjectId: number) {
  form.value.subject_id = subjectId
  form.value.kp_id = null
  await loadKps(subjectId)
}
</script>

<template>
  <div class="card detail-panel">
    <!-- 题目区：蓝色左边框 -->
    <section class="section problem-section">
      <div class="section-head">
        <span class="section-badge" :style="{ background: mistake.color }"></span>
        <span class="section-title">题目</span>
        <span class="spacer" />
        <span class="chip">{{ sourceLabel }}</span>
      </div>
      <template v-if="!editing">
        <p class="question-text">{{ mistake.question_text }}</p>
        <ul v-if="mistake.options.length" class="options">
          <li v-for="(opt, i) in mistake.options" :key="i">
            <span class="opt-key num">{{ String.fromCharCode(65 + i) }}.</span>{{ opt }}
          </li>
        </ul>
        <div v-if="mistake.source_image_url" class="source-image">
          <img :src="mistake.source_image_url" alt="原题图片" loading="lazy" />
        </div>
      </template>
      <div v-else class="edit-form">
        <div class="field">
          <label class="field-label" for="edit-question">题干 *</label>
          <textarea id="edit-question" v-model="form.question_text" class="textarea"></textarea>
        </div>
        <div class="field">
          <label class="field-label" for="edit-options">选项（每行一个）</label>
          <textarea id="edit-options" v-model="form.optionsText" class="textarea" style="min-height: 64px;"></textarea>
        </div>
        <div class="field">
          <label class="field-label" for="edit-answer">答案</label>
          <input id="edit-answer" v-model="form.answer_text" class="input" />
        </div>
      </div>
    </section>

    <!-- 解析区：绿色左边框，可折叠 -->
    <section class="section analysis-section">
      <button class="section-head analysis-toggle" @click="analysisOpen = !analysisOpen">
        <span class="section-title">解析</span>
        <span class="spacer" />
        <span class="chevron" :class="{ open: analysisOpen }">▾</span>
      </button>
      <div v-show="analysisOpen" class="analysis-body">
        <template v-if="!editing">
          <div class="kv">
            <span class="kv-key">正确答案</span>
            <span class="num">{{ mistake.answer_text || '—' }}</span>
          </div>
          <div class="kv">
            <span class="kv-key">AI 解析</span>
          </div>
          <p class="analysis-text">{{ mistake.analysis || '暂无解析' }}</p>
          <div class="kv">
            <span class="kv-key">错因建议</span>
            <span>{{ errorTypeLabel }}</span>
          </div>
          <div class="kv">
            <span class="kv-key">关联知识点</span>
            <span>{{ mistake.knowledge_point || '—' }}</span>
          </div>
        </template>
        <div v-else class="edit-form">
          <div class="field">
            <label class="field-label" for="edit-analysis">AI 解析</label>
            <textarea id="edit-analysis" v-model="form.analysis" class="textarea"></textarea>
          </div>
          <div class="field-row">
            <div class="field" style="flex: 1;">
              <label class="field-label" for="edit-subject">学科</label>
              <select id="edit-subject" v-model="form.subject_id" class="select" @change="changeSubject(form.subject_id)">
                <option v-for="s in store.subjects" :key="s.id" :value="s.id">{{ s.name }}</option>
              </select>
            </div>
            <div class="field" style="flex: 1;">
              <label class="field-label" for="edit-kp">知识点</label>
              <select id="edit-kp" v-model="form.kp_id" class="select">
                <option :value="null">未分类</option>
                <option v-for="kp in kpOptions" :key="kp.id" :value="kp.id">{{ kp.name }}</option>
              </select>
            </div>
          </div>
          <div class="field-row">
            <div class="field" style="flex: 1;">
              <label class="field-label" for="edit-error">错因</label>
              <select id="edit-error" v-model="form.error_type" class="select">
                <option v-for="(label, key) in ZH.errorTypes" :key="key" :value="key">{{ label }}</option>
              </select>
            </div>
            <div class="field" style="flex: 1;">
              <label class="field-label" for="edit-tags">标签（逗号分隔）</label>
              <input id="edit-tags" v-model="form.tagsText" class="input" />
            </div>
          </div>
          <div class="field">
            <label class="field-label" for="edit-note">备注</label>
            <textarea id="edit-note" v-model="form.note" class="textarea" style="min-height: 48px;"></textarea>
          </div>
        </div>
      </div>
    </section>

    <!-- 元信息行 -->
    <section class="meta-row">
      <button ref="colorAnchor" class="meta-item" aria-label="修改状态颜色" @click="colorPickerOpen = !colorPickerOpen">
        <span class="status-dot" :style="{ background: mistake.color }"></span>
        <span>{{ statusLabel }}</span>
      </button>
      <span v-for="tag in mistake.tags" :key="tag" class="chip">#{{ tag }}</span>
      <span class="meta-item"><CalendarClock :size="14" /> 复习 {{ mistake.review_count }} 次</span>
      <span class="meta-item">掌握度 {{ percent(mistake.mastery) }}</span>
      <span class="spacer" />
      <span class="meta-time">{{ formatRelative(mistake.last_reviewed_at) }} · 创建于 {{ formatDate(mistake.created_at) }}</span>
    </section>

    <!-- 操作区 -->
    <section class="actions">
      <template v-if="!editing">
        <button class="btn btn-secondary btn-sm" @click="startEdit"><Pencil :size="14" /> 编辑</button>
        <button class="btn btn-secondary btn-sm" @click="copyQuestion"><Copy :size="14" /> 复制</button>
        <button class="btn btn-secondary btn-sm" @click="$router.push({ path: '/review', query: { ids: mistake.id } })"><GraduationCap :size="14" /> 加入复习</button>
        <span class="spacer" />
        <button class="btn btn-danger btn-sm" @click="deleting = true"><Trash2 :size="14" /> 删除</button>
      </template>
      <template v-else>
        <div v-if="formError" class="field-error" style="flex: 1;">{{ formError }}</div>
        <span class="spacer" />
        <button class="btn btn-secondary btn-sm" @click="editing = false">取消</button>
        <button class="btn btn-primary btn-sm" @click="saveEdit"><Check :size="14" /> 保存</button>
      </template>
    </section>

    <ColorPickerPopover
      v-if="colorPickerOpen"
      :anchor="colorAnchor"
      :current-color="mistake.color"
      @select="pickColor"
      @close="colorPickerOpen = false"
    />

    <ConfirmDialog
      v-if="deleting"
      title="删除这道错题？"
      message="错题与其复习计划将一并移除，历史复习记录保留。此操作不可撤销。"
      confirm-text="删除"
      danger
      @confirm="confirmDelete"
      @cancel="deleting = false"
    />
  </div>
</template>

<style scoped>
.detail-panel { overflow: visible; }
.section {
  padding: var(--space-4) var(--space-4) var(--space-4) var(--space-5);
  border-bottom: var(--border-1);
}
.problem-section {
  border-left: 3px solid var(--brand);
  border-radius: var(--radius-lg) var(--radius-lg) 0 0;
}
.analysis-section {
  border-left: 3px solid var(--brand-secondary);
}
.section-head {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  margin-bottom: var(--space-3);
}
.section-title {
  font-size: var(--fs-card-title);
  font-weight: 600;
}
.spacer { flex: 1; }
.question-text {
  font-size: var(--fs-body-lg);
  line-height: var(--lh-body);
  white-space: pre-wrap;
  word-break: break-word;
  margin-bottom: var(--space-3);
}
.options {
  list-style: none;
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  margin-bottom: var(--space-2);
}
.options li { display: flex; gap: var(--space-2); }
.opt-key {
  font-weight: 600;
  flex-shrink: 0;
}
.source-image img {
  max-width: 240px;
  max-height: 160px;
  border-radius: var(--radius-md);
  border: var(--border-1);
  margin-top: var(--space-2);
}
.analysis-toggle { width: 100%; border: none; background: none; cursor: pointer; }
.chevron { color: var(--text-secondary); transition: transform var(--dur-collapse) ease; font-size: var(--fs-aux2); }
.chevron.open { transform: rotate(180deg); }
.kv {
  display: flex;
  gap: var(--space-2);
  font-size: var(--fs-aux2);
  margin-bottom: var(--space-2);
}
.kv-key { color: var(--text-secondary); flex-shrink: 0; }
.analysis-text {
  white-space: pre-wrap;
  word-break: break-word;
  margin-bottom: var(--space-3);
  line-height: var(--lh-body);
}
.meta-row {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: var(--space-2);
  padding: var(--space-3) var(--space-5);
  border-bottom: var(--border-1);
}
.meta-item {
  display: inline-flex;
  align-items: center;
  gap: var(--space-1);
  font-size: var(--fs-aux2);
  color: var(--text-secondary);
  border-radius: var(--radius-sm);
  padding: 2px var(--space-1);
}
button.meta-item:hover { background: var(--bg-subtle); color: var(--text-primary); }
.meta-time { font-size: var(--fs-aux); color: var(--text-disabled); }
.actions {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-3) var(--space-5);
}
.edit-form {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}
.field-row {
  display: flex;
  gap: var(--space-3);
}
</style>
