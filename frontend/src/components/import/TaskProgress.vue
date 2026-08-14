<script setup lang="ts">
/** OCR 任务阶段条（UI/UX 7.2）：识别中 / 拆题中 / 待确认；失败步骤变红（EX-03 兜底入口）。 */
import { computed } from 'vue'
import { ImageOff, RefreshCw, FileText } from 'lucide-vue-next'
import { ZH } from '@/constants/zh'

const props = defineProps<{ status: string | null; error: string | null }>()
const emit = defineEmits<{ retry: []; reset: []; toText: [] }>()

const STEPS = [
  { key: 'ocr_running', label: '识别中' },
  { key: 'splitting', label: '拆题中' },
  { key: 'awaiting_confirm', label: '待确认' },
]

const currentIdx = computed(() => {
  const map: Record<string, number> = { uploaded: 0, queued: 0, ocr_running: 0, splitting: 1, awaiting_confirm: 2, done: 3 }
  return map[props.status ?? ''] ?? 0
})
</script>

<template>
  <div class="card" style="padding: var(--space-4);">
    <template v-if="status !== 'failed'">
      <div class="steps">
        <template v-for="(step, i) in STEPS" :key="step.key">
          <div class="step" :class="{ active: i <= currentIdx, current: i === currentIdx }">
            <span class="step-dot">{{ i < currentIdx ? '✓' : i + 1 }}</span>
            <span class="step-label">{{ step.label }}</span>
          </div>
          <div v-if="i < STEPS.length - 1" class="step-line" :class="{ filled: i < currentIdx }"></div>
        </template>
      </div>
      <div class="progress-track">
        <div class="progress-fill" :style="{ width: `${Math.max(props.status ? 10 : 0, currentIdx / STEPS.length * 100)}%` }"></div>
      </div>
    </template>
    <div v-else class="task-error">
      <div class="task-error-head">
        <ImageOff :size="18" style="color: var(--error);" />
        <span style="color: var(--error); font-weight: 500;">{{ error || ZH.errors.ocrFailed }}</span>
      </div>
      <p style="color: var(--text-secondary); font-size: var(--fs-aux2); margin: var(--space-2) 0;">{{ ZH.errors.ocrFailed }}</p>
      <div style="display: flex; gap: var(--space-2); flex-wrap: wrap;">
        <button class="btn btn-primary btn-sm" @click="emit('retry')"><RefreshCw :size="14" /> 重试</button>
        <button class="btn btn-secondary btn-sm" @click="emit('reset')">重新拍照 / 换图</button>
        <button class="btn btn-text btn-sm" @click="emit('toText')"><FileText :size="14" /> 改用文本录入</button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.steps {
  display: flex;
  align-items: center;
  margin-bottom: var(--space-3);
}
.step {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  font-size: var(--fs-aux2);
  color: var(--text-disabled);
}
.step.active { color: var(--text-primary); }
.step.current .step-dot { background: var(--brand); border-color: var(--brand); color: #fff; }
.step-dot {
  width: 22px;
  height: 22px;
  border-radius: 50%;
  border: 1px solid var(--border);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: var(--fs-aux);
  background: var(--bg-card);
}
.step-line {
  flex: 1;
  height: 2px;
  background: var(--border);
  margin: 0 var(--space-2);
}
.step-line.filled { background: var(--brand); }
.progress-track {
  height: 4px;
  border-radius: 2px;
  background: var(--bg-subtle);
  overflow: hidden;
}
.progress-fill {
  height: 100%;
  background: var(--brand);
  border-radius: 2px;
  transition: width var(--dur-collapse) ease;
}
.task-error-head {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}
</style>
