<script setup lang="ts">
/** 文本录入表单（UI/UX 4.4 / PRD 5.1.2）：
 * 题干必填（EX-07 拦截）→「识别并归档」AI 补全学科/知识点/错因（可修改）→ 确认入库；
 * 「直接保存」跳过 AI。 */
import { computed, onMounted, reactive, ref } from 'vue'
import { Sparkles, ClipboardPaste } from 'lucide-vue-next'
import { importApi } from '@/api/import'
import { mistakesApi } from '@/api/mistakes'
import { subjectsApi } from '@/api/subjects'
import type { KnowledgePoint, Subject } from '@/api/types'
import { ZH } from '@/constants/zh'
import { toast } from '@/components/common/toast'

const emit = defineEmits<{ saved: [] }>()

const form = reactive({ question_text: '', optionsText: '', answer_text: '', analysis: '' })
const errorMsg = ref('')
const aiLoading = ref(false)
const suggested = ref(false)
const saving = ref(false)
const subjects = ref<Subject[]>([])
const kps = ref<KnowledgePoint[]>([])

const arch = reactive({ subject_id: null as number | null, kp_id: null as number | null, error_type: 'other' })

const kpOptions = computed(() => kps.value.filter((kp) => kp.subject_id === arch.subject_id))

onMounted(async () => {
  subjects.value = await subjectsApi.list()
})

async function pasteFromClipboard() {
  try {
    const text = await navigator.clipboard.readText()
    if (!form.question_text) form.question_text = text
    else form.question_text += `\n${text}`
  } catch {
    toast.error('无法读取剪贴板，请手动粘贴（Ctrl+V）')
  }
}

async function suggest() {
  if (!form.question_text.trim()) {
    errorMsg.value = ZH.errors.emptyQuestion
    return
  }
  errorMsg.value = ''
  aiLoading.value = true
  try {
    const resp = await importApi.textSuggest({
      question_text: form.question_text,
      options: form.optionsText.split('\n').map((s) => s.trim()).filter(Boolean),
      answer_text: form.answer_text,
      analysis: form.analysis,
    })
    arch.subject_id = resp.subject_id
    arch.kp_id = resp.kp_id
    arch.error_type = resp.error_type
    if (resp.subject_id) {
      kps.value = await subjectsApi.knowledgePoints(resp.subject_id)
    }
    suggested.value = true
    if (resp.mock) toast.info('演示模式：AI 归档为本地模拟结果')
  } catch (err) {
    errorMsg.value = (err as Error).message
  } finally {
    aiLoading.value = false
  }
}

async function save(useAi: boolean) {
  if (!form.question_text.trim()) {
    errorMsg.value = ZH.errors.emptyQuestion
    return
  }
  if (useAi && !suggested.value) {
    await suggest()
    if (!suggested.value) return
  }
  errorMsg.value = ''
  saving.value = true
  try {
    await mistakesApi.create({
      question_text: form.question_text.trim(),
      options: form.optionsText.split('\n').map((s) => s.trim()).filter(Boolean),
      answer_text: form.answer_text.trim(),
      analysis: form.analysis.trim(),
      subject_id: arch.subject_id ?? subjects.value[0]?.id ?? 0,
      kp_id: arch.kp_id,
      error_type: useAi ? arch.error_type : 'other',
      source: 'text',
    })
    toast.success('已归档到错题本，明日进入复习计划')
    form.question_text = ''
    form.optionsText = ''
    form.answer_text = ''
    form.analysis = ''
    suggested.value = false
    emit('saved')
  } catch (err) {
    errorMsg.value = (err as Error).message
  } finally {
    saving.value = false
  }
}

function changeSubject() {
  arch.kp_id = null
  if (arch.subject_id) void subjectsApi.knowledgePoints(arch.subject_id).then((rows) => (kps.value = rows))
}
</script>

<template>
  <div class="card" style="padding: var(--space-5);">
    <div style="display: flex; align-items: center; gap: var(--space-2); margin-bottom: var(--space-4);">
      <span style="font-size: var(--fs-card-title); font-weight: 600;">文本录入</span>
      <button class="btn btn-text btn-sm" @click="pasteFromClipboard"><ClipboardPaste :size="14" /> 从剪贴板粘贴</button>
    </div>
    <div class="field" style="margin-bottom: var(--space-3);">
      <label class="field-label" for="ti-question">题干 *</label>
      <textarea id="ti-question" v-model="form.question_text" class="textarea" :class="{ invalid: !!errorMsg }" placeholder="粘贴或输入题干内容"></textarea>
    </div>
    <div class="field" style="margin-bottom: var(--space-3);">
      <label class="field-label" for="ti-options">选项（每行一个，如 A. 2m）</label>
      <textarea id="ti-options" v-model="form.optionsText" class="textarea" style="min-height: 64px;"></textarea>
    </div>
    <div class="form-row" style="margin-bottom: var(--space-3);">
      <div class="field" style="flex: 1;">
        <label class="field-label" for="ti-answer">答案</label>
        <input id="ti-answer" v-model="form.answer_text" class="input" placeholder="如：C" />
      </div>
      <div class="field" style="flex: 2;">
        <label class="field-label" for="ti-analysis">解析</label>
        <input id="ti-analysis" v-model="form.analysis" class="input" placeholder="可留空，由 AI 补全" />
      </div>
    </div>

    <!-- AI 补全归档字段（可编辑下拉） -->
    <div v-if="suggested" class="card" style="background: var(--bg-subtle); border: var(--border-1); padding: var(--space-3); margin-bottom: var(--space-3);">
      <div style="display: flex; align-items: center; gap: var(--space-2); font-size: var(--fs-aux2); color: var(--text-secondary); margin-bottom: var(--space-2);">
        <Sparkles :size="14" style="color: var(--brand);" /> AI 已补全归档字段，确认或修改：
      </div>
      <div class="form-row">
        <div class="field" style="flex: 1;">
          <label class="field-label" for="ti-subject">学科</label>
          <select id="ti-subject" v-model="arch.subject_id" class="select" @change="changeSubject">
            <option v-for="s in subjects" :key="s.id" :value="s.id">{{ s.name }}</option>
          </select>
        </div>
        <div class="field" style="flex: 1;">
          <label class="field-label" for="ti-kp">知识点</label>
          <select id="ti-kp" v-model="arch.kp_id" class="select">
            <option :value="null">未分类</option>
            <option v-for="kp in kpOptions" :key="kp.id" :value="kp.id">{{ kp.name }}</option>
          </select>
        </div>
        <div class="field" style="flex: 1;">
          <label class="field-label" for="ti-error">错因</label>
          <select id="ti-error" v-model="arch.error_type" class="select">
            <option v-for="(label, key) in ZH.errorTypes" :key="key" :value="key">{{ label }}</option>
          </select>
        </div>
      </div>
    </div>

    <div v-if="errorMsg" class="field-error" style="margin-bottom: var(--space-3);">{{ errorMsg }}</div>

    <div style="display: flex; gap: var(--space-2); justify-content: flex-end;">
      <button class="btn btn-primary" :disabled="saving || aiLoading" @click="save(false)">直接保存</button>
      <button class="btn btn-secondary" :disabled="saving || aiLoading" @click="save(true)">
        <Sparkles :size="14" /> {{ aiLoading ? 'AI 识别中…' : '识别并归档' }}
      </button>
    </div>
  </div>
</template>

<style scoped>
.form-row { display: flex; gap: var(--space-3); }
</style>
