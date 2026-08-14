<script setup lang="ts">
/** 阶段三逐题详情（UI/UX 4.5）：答对 1.5px 绿边框 / 答错 1.5px 红边框；
 * 默认答案摘要，点击展开完整 AI 解析；认可 / 不认可（重新批改）。 */
import { ref } from 'vue'
import { Check, X } from 'lucide-vue-next'
import type { ReviewReportItem } from '@/api/reviews'

const props = defineProps<{ item: ReviewReportItem; index: number }>()
const emit = defineEmits<{ regrade: [variantId: string] }>()

const expanded = ref(false)
const regrading = ref(false)

async function onRegrade() {
  regrading.value = true
  await emit('regrade', props.item.variant_id)
  regrading.value = false
}
</script>

<template>
  <div class="card result-item" :class="item.is_correct ? 'correct' : 'wrong'">
    <button class="item-head" @click="expanded = !expanded">
      <span class="verdict-icon" :style="{ background: item.is_correct ? 'var(--status-mastered)' : 'var(--status-wrong)' }">
        <Check v-if="item.is_correct" :size="14" color="#fff" />
        <X v-else :size="14" color="#fff" />
      </span>
      <span class="num">第 {{ index + 1 }} 题</span>
      <span :style="{ color: item.is_correct ? 'var(--status-mastered)' : 'var(--status-wrong)', fontWeight: 600 }">
        {{ item.is_correct ? '答对' : '答错' }}
      </span>
      <span class="excerpt">{{ item.question_excerpt }}</span>
      <span class="spacer" />
      <span class="answer-summary num">
        我的答案 {{ item.my_answer || '（未作答）' }}
        <template v-if="!item.is_correct"> / 正确答案 {{ item.correct_answer }}</template>
      </span>
      <span class="chevron" :class="{ open: expanded }">▾</span>
    </button>
    <div v-show="expanded" class="item-body">
      <div class="kv"><span class="kv-key">AI 解析</span></div>
      <p class="analysis">{{ item.analysis || '暂无解析' }}</p>
      <div class="kv"><span class="kv-key">错因建议</span><span>{{ item.error_type === 'none' ? '无' : item.error_type }}</span></div>
      <div class="kv"><span class="kv-key">关联知识点</span><span>{{ item.knowledge_point || '—' }}</span></div>
      <div class="item-actions">
        <span class="spacer" />
        <button class="btn btn-text btn-sm">认可</button>
        <button class="btn btn-secondary btn-sm" :disabled="regrading" @click="onRegrade">
          {{ regrading ? '重新批改中…' : '不认可，重新批改' }}
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.result-item {
  margin-bottom: var(--space-3);
  overflow: hidden;
}
.result-item.correct { border: 1.5px solid var(--status-mastered); }
.result-item.wrong { border: 1.5px solid var(--status-wrong); }
.item-head {
  width: 100%;
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-3) var(--space-4);
  cursor: pointer;
  text-align: left;
  font-size: var(--fs-body);
}
.item-head:hover { background: var(--bg-subtle); }
.verdict-icon {
  width: 22px;
  height: 22px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.excerpt {
  color: var(--text-secondary);
  font-size: var(--fs-aux2);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 40%;
}
.spacer { flex: 1; }
.answer-summary { font-size: var(--fs-aux2); color: var(--text-secondary); }
.chevron { color: var(--text-secondary); transition: transform var(--dur-collapse) ease; }
.chevron.open { transform: rotate(180deg); }
.item-body {
  border-top: var(--border-1);
  padding: var(--space-4);
}
.kv { display: flex; gap: var(--space-2); font-size: var(--fs-aux2); margin-bottom: var(--space-2); }
.kv-key { color: var(--text-secondary); flex-shrink: 0; }
.analysis {
  white-space: pre-wrap;
  word-break: break-word;
  margin-bottom: var(--space-3);
  line-height: var(--lh-body);
}
.item-actions { display: flex; align-items: center; }
</style>
