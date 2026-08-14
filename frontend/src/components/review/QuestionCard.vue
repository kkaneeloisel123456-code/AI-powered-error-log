<script setup lang="ts">
/** 阶段二题目卡（UI/UX 4.5）：AI 变体标识、题干、选项点选/文本输入、不确定勾选、换一题（剩 N 次）。 */
import { computed } from 'vue'
import { RefreshCw, Sparkles } from 'lucide-vue-next'
import type { Variant } from '@/api/reviews'

const props = defineProps<{
  variant: Variant
  index: number
  total: number
  answer: { answer: string; unsure: boolean } | undefined
  replaceLeft: number
  replacing: boolean
}>()

const emit = defineEmits<{ answer: [answer: string, unsure: boolean]; replace: [] }>()

const isChoice = computed(() => props.variant.options.length > 0)
const inputAnswer = computed({
  get: () => props.answer?.answer ?? '',
  set: (v: string) => emit('answer', v, props.answer?.unsure ?? false),
})
const unsure = computed({
  get: () => props.answer?.unsure ?? false,
  set: (v: boolean) => emit('answer', props.answer?.answer ?? '', v),
})
</script>

<template>
  <div class="card question-card">
    <div class="card-head">
      <span class="chip" style="color: var(--brand);"><Sparkles :size="12" /> AI 变体</span>
      <span class="num" style="color: var(--text-secondary); font-size: var(--fs-aux2);">第 {{ index + 1 }} / {{ total }} 题</span>
      <span class="spacer" />
      <button class="btn btn-text btn-sm" :disabled="replaceLeft <= 0 || replacing" @click="emit('replace')">
        <RefreshCw :size="14" /> {{ replacing ? '生成中…' : `换一题（剩 ${replaceLeft} 次）` }}
      </button>
    </div>
    <p class="question-text">{{ variant.question_text }}</p>

    <!-- 选择题：单选点选 -->
    <div v-if="isChoice" class="options" role="radiogroup">
      <label
        v-for="(opt, i) in variant.options"
        :key="i"
        class="option-row"
        :class="{ picked: inputAnswer === String.fromCharCode(65 + i) }"
      >
        <input
          type="radio"
          name="answer"
          :checked="inputAnswer === String.fromCharCode(65 + i)"
          @change="inputAnswer = String.fromCharCode(65 + i)"
        />
        <span>{{ opt }}</span>
      </label>
    </div>
    <!-- 解答题：文本输入 -->
    <div v-else class="field">
      <label class="field-label" for="answer-input">作答（文本）</label>
      <textarea id="answer-input" v-model="inputAnswer" class="textarea" placeholder="输入你的答案…"></textarea>
    </div>

    <label class="unsure-row">
      <input type="checkbox" v-model="unsure" />
      <span>不确定（标记后批改质量分降档）</span>
    </label>
  </div>
</template>

<style scoped>
.question-card { padding: var(--space-5); margin-bottom: var(--space-4); }
.card-head {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  margin-bottom: var(--space-3);
}
.spacer { flex: 1; }
.question-text {
  font-size: var(--fs-body-lg);
  line-height: var(--lh-body);
  white-space: pre-wrap;
  word-break: break-word;
  margin-bottom: var(--space-4);
}
.options { display: flex; flex-direction: column; gap: var(--space-2); margin-bottom: var(--space-3); }
.option-row {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-3);
  border: var(--border-1);
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: border-color var(--dur-hover) ease, background var(--dur-hover) ease;
}
.option-row:hover { border-color: var(--text-disabled); }
.option-row.picked {
  border-color: var(--brand);
  background: var(--brand-8);
}
.unsure-row {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  font-size: var(--fs-aux2);
  color: var(--text-secondary);
  cursor: pointer;
  margin-top: var(--space-3);
}
</style>
