<script setup lang="ts">
/** 二次确认弹窗（480px 居中，移动端底部抽屉，Esc 关闭）。 */
import { onBeforeUnmount, onMounted } from 'vue'
import { ZH } from '@/constants/zh'

const props = withDefaults(
  defineProps<{
    title: string
    message?: string
    confirmText?: string
    danger?: boolean
    loading?: boolean
  }>(),
  { message: '', confirmText: ZH.common.confirm, danger: false, loading: false },
)

const emit = defineEmits<{ confirm: []; cancel: [] }>()

function onKeydown(e: KeyboardEvent) {
  if (e.key === 'Escape') emit('cancel')
}
onMounted(() => window.addEventListener('keydown', onKeydown))
onBeforeUnmount(() => window.removeEventListener('keydown', onKeydown))
</script>

<template>
  <div class="dialog-mask" @click.self="emit('cancel')">
    <div class="dialog" role="dialog" :aria-label="props.title">
      <h3 class="dialog-title">{{ props.title }}</h3>
      <div v-if="props.message" class="dialog-body">{{ props.message }}</div>
      <slot />
      <div class="dialog-footer">
        <button class="btn btn-secondary" @click="emit('cancel')">{{ ZH.common.cancel }}</button>
        <button
          class="btn"
          :class="danger ? 'btn-primary' : 'btn-primary'"
          :style="danger ? { background: 'var(--error)' } : {}"
          :disabled="loading"
          @click="emit('confirm')"
        >
          {{ loading ? ZH.common.loading : props.confirmText }}
        </button>
      </div>
    </div>
  </div>
</template>
