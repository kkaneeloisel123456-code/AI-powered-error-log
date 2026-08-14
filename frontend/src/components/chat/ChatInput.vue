<script setup lang="ts">
/** 底部输入区（UI/UX 4.3）：自适应 textarea（min 48px、max 160px）、Ctrl+Enter 发送、空输入禁发。 */
import { ref } from 'vue'
import { SendHorizontal, Square } from 'lucide-vue-next'

const props = defineProps<{ sending: boolean; streaming: boolean }>()
const emit = defineEmits<{ send: [content: string]; stop: [] }>()

const text = ref('')
const textareaRef = ref<HTMLTextAreaElement | null>(null)

function submit() {
  const content = text.value.trim()
  if (!content || props.sending) return
  emit('send', content)
  text.value = ''
  if (textareaRef.value) textareaRef.value.style.height = ''
}

function onKeydown(e: KeyboardEvent) {
  // Ctrl+Enter 发送（UI/UX 5.4 快捷键）
  if (e.key === 'Enter' && (e.ctrlKey || e.metaKey) && !e.shiftKey) {
    e.preventDefault()
    submit()
  }
}

function autoGrow() {
  const el = textareaRef.value
  if (!el) return
  el.style.height = ''
  el.style.height = `${Math.min(Math.max(el.scrollHeight, 48), 160)}px`
}
</script>

<template>
  <div class="chat-input">
    <textarea
      ref="textareaRef"
      v-model="text"
      class="textarea"
      style="min-height: 48px; max-height: 160px;"
      placeholder="输入你的问题…（Ctrl+Enter 发送；图片不发送，仅题干文本发送至 AI）"
      aria-label="输入问题"
      @keydown="onKeydown"
      @input="autoGrow"
    ></textarea>
    <button
      v-if="streaming"
      class="btn btn-secondary"
      aria-label="停止生成"
      @click="emit('stop')"
    ><Square :size="14" /> 停止</button>
    <button
      v-else
      class="btn btn-primary"
      :disabled="!text.trim() || sending"
      aria-label="发送"
      @click="submit"
    ><SendHorizontal :size="15" /> 发送</button>
  </div>
</template>

<style scoped>
.chat-input {
  display: flex;
  align-items: flex-end;
  gap: var(--space-2);
  padding: var(--space-3) 0;
  border-top: var(--border-1);
}
.chat-input .textarea { flex: 1; }
</style>
