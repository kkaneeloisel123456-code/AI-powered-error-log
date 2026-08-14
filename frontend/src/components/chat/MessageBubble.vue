<script setup lang="ts">
/** 消息气泡（UI/UX 4.3）：用户右侧品牌 8% 底，AI 左侧白卡；流式打字光标；
 * 完成后「继续生成 / 加入错题本」。 */
import { computed } from 'vue'
import { BookPlus, Play } from 'lucide-vue-next'
import { renderMarkdown } from '@/utils/markdown'
import type { UIMessage } from '@/stores/chat'

const props = defineProps<{ message: UIMessage; streaming: boolean }>()
const emit = defineEmits<{ continue: []; addToMistake: [] }>()

const isUser = computed(() => props.message.role === 'user')
const html = computed(() => (props.message.role === 'assistant' ? renderMarkdown(props.message.content) : ''))
const canContinue = computed(() => props.message.role === 'assistant' && !props.streaming && props.message.content && props.message.content !== '（已停止）' && props.message.content !== '（生成中断）')
</script>

<template>
  <div class="bubble-row" :class="{ user: isUser }">
    <div class="bubble" :class="{ user: isUser }">
      <template v-if="isUser">
        <span class="bubble-text">{{ message.content }}</span>
      </template>
      <template v-else>
        <div class="markdown-body" v-html="html"></div>
        <span v-if="streaming" class="typing-cursor"></span>
      </template>
    </div>
    <div v-if="message.role === 'assistant' && !streaming" class="bubble-actions">
      <button v-if="canContinue" class="btn btn-text btn-sm" @click="emit('continue')"><Play :size="13" /> 继续生成</button>
      <button class="btn btn-text btn-sm" @click="emit('addToMistake')"><BookPlus :size="13" /> 加入错题本</button>
    </div>
  </div>
</template>

<style scoped>
.bubble-row {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  margin-bottom: var(--space-4);
}
.bubble-row.user { align-items: flex-end; }
.bubble {
  max-width: 85%;
  padding: var(--space-3) var(--space-4);
  border-radius: var(--radius-lg);
  background: var(--bg-card);
  border: var(--border-1);
  font-size: var(--fs-body);
  line-height: var(--lh-body);
  word-break: break-word;
}
.bubble.user {
  background: var(--brand-8);
  border: none;
  border-top-right-radius: var(--radius-sm);
}
.bubble:not(.user) { border-top-left-radius: var(--radius-sm); }
.bubble-text { white-space: pre-wrap; }
.bubble-actions {
  display: flex;
  gap: var(--space-1);
  margin-top: var(--space-1);
  padding-left: var(--space-2);
}
</style>
