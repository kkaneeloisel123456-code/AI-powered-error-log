<script setup lang="ts">
/** 候选题卡片（UI/UX 4.4）：勾选 + 题干/选项/答案/解析可编辑 + 低置信字段高亮（EX-04）+ 删除。 */
import { computed } from 'vue'
import { AlertTriangle, Trash2 } from 'lucide-vue-next'
import type { ImportCandidate } from '@/stores/importTask'

const props = defineProps<{ candidate: ImportCandidate; index: number }>()
const emit = defineEmits<{
  toggle: [index: number]
  update: [index: number, patch: Partial<ImportCandidate>]
  remove: [index: number]
}>()

const optionsText = computed({
  get: () => props.candidate.options.join('\n'),
  set: (v: string) => emit('update', props.index, { options: v.split('\n').map((s) => s.trim()).filter(Boolean) }),
})

const lowFields = computed(() => ({
  question_text: props.candidate.confidence_fields.includes('question_text'),
  answer: props.candidate.confidence_fields.includes('answer'),
  analysis: props.candidate.confidence_fields.includes('analysis'),
}))
</script>

<template>
  <div class="card candidate-card">
    <div class="candidate-head">
      <label class="check">
        <input
          type="checkbox"
          :checked="candidate.selected"
          @change="emit('toggle', index)"
        />
        <span>第 {{ index + 1 }} 题</span>
      </label>
      <span v-if="candidate.knowledge_point" class="chip">{{ candidate.knowledge_point }}</span>
      <span class="spacer" />
      <button class="btn btn-danger btn-sm" aria-label="删除该题" @click="emit('remove', index)">
        <Trash2 :size="14" />
      </button>
    </div>
    <div class="field">
      <label class="field-label">
        题干
        <span v-if="lowFields.question_text" class="confirm-badge"><AlertTriangle :size="12" /> 请确认</span>
      </label>
      <textarea
        class="textarea"
        :class="{ 'low-confidence': lowFields.question_text }"
        :value="candidate.question_text"
        @input="emit('update', index, { question_text: ($event.target as HTMLTextAreaElement).value })"
      ></textarea>
    </div>
    <div class="field">
      <label class="field-label">选项（每行一个）</label>
      <textarea v-model="optionsText" class="textarea" style="min-height: 64px;"></textarea>
    </div>
    <div class="candidate-row">
      <div class="field" style="flex: 1;">
        <label class="field-label">
          答案
          <span v-if="lowFields.answer" class="confirm-badge"><AlertTriangle :size="12" /> 请确认</span>
        </label>
        <input
          class="input"
          :class="{ 'low-confidence': lowFields.answer }"
          :value="candidate.answer"
          placeholder="如：C（缺答案将影响后续复习）"
          @input="emit('update', index, { answer: ($event.target as HTMLInputElement).value })"
        />
      </div>
      <div class="field" style="flex: 2;">
        <label class="field-label">
          解析
          <span v-if="lowFields.analysis" class="confirm-badge"><AlertTriangle :size="12" /> 请确认</span>
        </label>
        <input
          class="input"
          :class="{ 'low-confidence': lowFields.analysis }"
          :value="candidate.analysis"
          placeholder="AI 解析（可修改）"
          @input="emit('update', index, { analysis: ($event.target as HTMLInputElement).value })"
        />
      </div>
    </div>
  </div>
</template>

<style scoped>
.candidate-card {
  padding: var(--space-4);
  margin-bottom: var(--space-3);
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}
.candidate-head {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}
.check {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  font-weight: 600;
  cursor: pointer;
  font-size: var(--fs-body);
}
.spacer { flex: 1; }
.candidate-row { display: flex; gap: var(--space-3); }
.confirm-badge {
  display: inline-flex;
  align-items: center;
  gap: 2px;
  margin-left: var(--space-2);
  color: var(--warning);
  font-weight: 500;
}
/* EX-04：低置信字段黄色高亮（--warning 背景） */
.low-confidence {
  background: rgba(234, 140, 0, 0.08);
  border-color: var(--warning);
}
</style>
