<script setup lang="ts">
/** 颜色选择气泡（UI/UX 5.4）：
 * - Teleport 到 body，getBoundingClientRect 计算 fixed 定位，宽 240px；
 * - 4 个状态色（选中同步状态）+ 8 个自定义色板；
 * - 视口边缘自动翻转，点击外部 / Esc 关闭。 */
import { nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import { ZH } from '@/constants/zh'

const props = defineProps<{ anchor: HTMLElement | null; currentColor: string }>()
const emit = defineEmits<{ select: [color: string, status: string | null]; close: [] }>()

const STATUS_COLORS: Array<{ status: string; color: string; label: string }> = [
  { status: 'pending', color: '#6B7280', label: ZH.status.pending },
  { status: 'wrong', color: '#DC2626', label: ZH.status.wrong },
  { status: 'fixing', color: '#EA8C00', label: ZH.status.fixing },
  { status: 'mastered', color: '#16A34A', label: ZH.status.mastered },
]
const CUSTOM_COLORS = ['#2563EB', '#7C3AED', '#DB2777', '#0D9488', '#65A30D', '#D97706', '#475569', '#334155']

const popoverRef = ref<HTMLElement | null>(null)
const pos = ref({ top: 0, left: 0, flipY: false, flipX: false })
const WIDTH = 240
const HEIGHT = 208

function computePosition() {
  if (!props.anchor) return
  const rect = props.anchor.getBoundingClientRect()
  const vw = window.innerWidth
  const vh = window.innerHeight
  let left = rect.left
  let top = rect.bottom + 8
  const flipX = left + WIDTH > vw - 8
  const flipY = top + HEIGHT > vh - 8
  if (flipX) left = Math.max(8, rect.right - WIDTH)
  if (flipY) top = Math.max(8, rect.top - HEIGHT - 8)
  pos.value = { top, left, flipY, flipX }
}

function onClickOutside(e: MouseEvent) {
  if (popoverRef.value && !popoverRef.value.contains(e.target as Node) && props.anchor !== e.target) {
    emit('close')
  }
}

function onKeydown(e: KeyboardEvent) {
  if (e.key === 'Escape') emit('close')
}

onMounted(async () => {
  await nextTick()
  computePosition()
  window.addEventListener('resize', computePosition)
  document.addEventListener('mousedown', onClickOutside)
  window.addEventListener('keydown', onKeydown)
})
onBeforeUnmount(() => {
  window.removeEventListener('resize', computePosition)
  document.removeEventListener('mousedown', onClickOutside)
  window.removeEventListener('keydown', onKeydown)
})
</script>

<template>
  <Teleport to="body">
    <div
      ref="popoverRef"
      class="card color-popover"
      :style="{ top: `${pos.top}px`, left: `${pos.left}px` }"
      role="dialog"
      aria-label="选择颜色"
    >
      <div class="popover-group-label">状态色（会同步学习状态）</div>
      <div class="swatches">
        <button
          v-for="s in STATUS_COLORS"
          :key="s.status"
          class="swatch"
          :class="{ current: currentColor.toLowerCase() === s.color.toLowerCase() }"
          :style="{ background: s.color }"
          :title="s.label"
          :aria-label="`${s.label}（${s.status}）`"
          @click="emit('select', s.color, s.status)"
        ></button>
      </div>
      <div class="popover-group-label">自定义色（仅改颜色）</div>
      <div class="swatches">
        <button
          v-for="c in CUSTOM_COLORS"
          :key="c"
          class="swatch"
          :class="{ current: currentColor.toLowerCase() === c.toLowerCase() }"
          :style="{ background: c }"
          :aria-label="`自定义颜色 ${c}`"
          @click="emit('select', c, null)"
        ></button>
      </div>
    </div>
  </Teleport>
</template>

<style scoped>
.color-popover {
  position: fixed;
  width: 240px;
  padding: var(--space-3);
  z-index: 950;
  box-shadow: 0 4px 12px rgba(16, 24, 40, 0.14);
}
.popover-group-label {
  font-size: var(--fs-aux);
  color: var(--text-secondary);
  margin: var(--space-1) 0 var(--space-2);
}
.popover-group-label + .popover-group-label {
  margin-top: var(--space-3);
}
.swatches {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: var(--space-2);
}
.swatch {
  height: 32px;
  border-radius: var(--radius-md);
  border: 2px solid transparent;
  transition: transform var(--dur-hover) ease, border-color var(--dur-hover) ease;
}
.swatch:hover {
  transform: scale(1.08);
}
.swatch.current {
  border-color: var(--text-primary);
}
</style>
