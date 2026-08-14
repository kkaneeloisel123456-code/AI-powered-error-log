<script setup lang="ts">
/** 左栏列表项：状态色点 + 题干摘要（2 行截断）+ 学科/知识点/错因标签 + 最后复习时间。 */
import { computed } from 'vue'
import { ZH } from '@/constants/zh'
import { formatRelative } from '@/utils/format'
import type { MistakeListItem } from '@/api/types'

const props = defineProps<{ item: MistakeListItem; selected: boolean }>()
const emit = defineEmits<{ select: [] }>()

const statusLabel = computed(() => ZH.status[props.item.status as keyof typeof ZH.status] ?? props.item.status)
const errorTypeLabel = computed(() => ZH.errorTypes[props.item.error_type as keyof typeof ZH.errorTypes] ?? props.item.error_type)
</script>

<template>
  <div
    class="card mistake-card"
    :class="{ selected }"
    role="option"
    :aria-selected="selected"
    @click="emit('select')"
  >
    <div class="mistake-card-head">
      <span class="status-dot" :style="{ background: item.color }"></span>
      <span class="status-text">{{ statusLabel }}</span>
      <span class="spacer" />
      <span class="review-time">{{ formatRelative(item.last_reviewed_at) }}</span>
    </div>
    <p class="excerpt">{{ item.question_excerpt }}</p>
    <div class="chips">
      <span class="chip">{{ item.subject_name }}</span>
      <span v-if="item.knowledge_point" class="chip">{{ item.knowledge_point }}</span>
      <span class="chip">{{ errorTypeLabel }}</span>
      <span v-if="item.tags.length" class="chip">#{{ item.tags[0] }}{{ item.tags.length > 1 ? ` +${item.tags.length - 1}` : '' }}</span>
    </div>
  </div>
</template>

<style scoped>
.mistake-card {
  padding: var(--space-3);
  margin-bottom: var(--space-2);
  cursor: pointer;
  border-left: 2px solid transparent;
  transition: background var(--dur-hover) ease, border-color var(--dur-hover) ease;
}
.mistake-card:hover {
  background: var(--brand-8);
  border-color: var(--border);
}
.mistake-card.selected {
  background: var(--brand-8);
  border-left: 2px solid var(--brand);
}
.mistake-card-head {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  margin-bottom: var(--space-1);
}
.status-text {
  font-size: var(--fs-aux2);
  color: var(--text-secondary);
}
.spacer { flex: 1; }
.review-time {
  font-size: var(--fs-aux);
  color: var(--text-disabled);
}
.excerpt {
  font-size: var(--fs-body);
  line-height: var(--lh-body);
  margin-bottom: var(--space-2);
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  word-break: break-word;
}
.chips {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-1);
}
</style>
