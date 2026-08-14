<script setup lang="ts">
/** 加入错题本草稿弹窗（PRD 5.1.3 / T-M5-03）：题干 + AI 解析预填，缺答案提示补充，确认后入库。 */
import { computed, ref, watch } from 'vue'
import { AlertTriangle } from 'lucide-vue-next'
import { mistakesApi } from '@/api/mistakes'
import { subjectsApi } from '@/api/subjects'
import type { ExtractDraft } from '@/api/chat'
import type { Subject } from '@/api/types'
import { toast } from '@/components/common/toast'
import ConfirmDialog from '@/components/common/ConfirmDialog.vue'

const props = defineProps<{ draft: ExtractDraft; loading: boolean }>()
const emit = defineEmits<{ close: []; saved: [mistakeId: string] }>()

const questionText = ref('')
const optionsText = ref('')
const answer = ref('')
const analysis = ref('')
const subjectId = ref<number | null>(null)
const subjects = ref<Subject[]>([])
const missingAnswerWarn = ref(false)
const saving = ref(false)

const hasAnswer = computed(() => answer.value.trim() !== '')

watch(
  () => props.draft,
  async (d) => {
    if (!d) return
    questionText.value = d.question_text
    optionsText.value = d.options.join('\n')
    answer.value = d.answer
    analysis.value = d.analysis
    if (!subjects.value.length) subjects.value = await subjectsApi.list()
    if (subjects.value.length) subjectId.value = subjects.value[0].id
  },
  { immediate: true },
)

async function save() {
  // PRD 5.1.3：缺少答案时提示用户补充
  if (!hasAnswer.value) {
    missingAnswerWarn.value = true
    return
  }
  if (!questionText.value.trim()) {
    toast.error('题干不能为空')
    return
  }
  saving.value = true
  try {
    const created = await mistakesApi.create({
      question_text: questionText.value.trim(),
      options: optionsText.value.split('\n').map((s) => s.trim()).filter(Boolean),
      answer_text: answer.value.trim(),
      analysis: analysis.value.trim(),
      subject_id: subjectId.value ?? subjects.value[0]?.id ?? 0,
      source: 'chat',
    })
    toast.success('已加入错题本，明日进入复习计划')
    emit('saved', created.id)
  } catch (err) {
    toast.error((err as Error).message)
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <ConfirmDialog
    v-if="draft"
    title="加入错题本"
    :message="loading ? '正在提取题目草稿…' : 'AI 已生成题目草稿，可编辑后确认入库。'"
    :confirm-text="saving ? '保存中…' : '确认归档'"
    @confirm="save"
    @cancel="emit('close')"
  >
    <template v-if="!loading">
      <div class="field" style="margin-bottom: var(--space-3);">
        <label class="field-label" for="draft-question">题干</label>
        <textarea id="draft-question" v-model="questionText" class="textarea" rows="3"></textarea>
      </div>
      <div class="field" style="margin-bottom: var(--space-3);">
        <label class="field-label" for="draft-options">选项（每行一个）</label>
        <textarea id="draft-options" v-model="optionsText" class="textarea" style="min-height: 56px;"></textarea>
      </div>
      <div class="draft-row">
        <div class="field" style="flex: 1;">
          <label class="field-label" for="draft-answer">答案 *</label>
          <input id="draft-answer" v-model="answer" class="input" :class="{ invalid: missingAnswerWarn && !hasAnswer }" placeholder="缺少答案，请补充" />
          <span v-if="missingAnswerWarn && !hasAnswer" class="field-error"><AlertTriangle :size="12" style="vertical-align: -2px;" /> 请补充答案后再归档</span>
        </div>
        <div class="field" style="flex: 1;">
          <label class="field-label" for="draft-subject">学科</label>
          <select id="draft-subject" v-model="subjectId" class="select">
            <option v-for="s in subjects" :key="s.id" :value="s.id">{{ s.name }}</option>
          </select>
        </div>
      </div>
      <div class="field">
        <label class="field-label" for="draft-analysis">AI 解析（预填）</label>
        <textarea id="draft-analysis" v-model="analysis" class="textarea" style="min-height: 56px;"></textarea>
      </div>
    </template>
  </ConfirmDialog>
</template>

<style scoped>
.draft-row { display: flex; gap: var(--space-3); margin-bottom: var(--space-3); }
</style>
