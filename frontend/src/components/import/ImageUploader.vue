<script setup lang="ts">
/** 上传区（UI/UX 4.4）：拖拽虚线框 + 点击上传 + Ctrl+V 粘贴；EX-01/02 前端校验。 */
import { ref } from 'vue'
import { ImagePlus } from 'lucide-vue-next'
import { compressImage } from '@/utils/compressImage'
import { ZH } from '@/constants/zh'

const emit = defineEmits<{ upload: [file: File]; error: [message: string] }>()

const dragging = ref(false)
const errorMsg = ref('')

const ALLOWED = /\.(jpe?g|png|webp|heic)$/i

function validate(file: File): string | null {
  if (!ALLOWED.test(file.name)) return ZH.errors.uploadFormat
  if (file.size > 10 * 1024 * 1024) return null // 交给 compress 再判定
  return null
}

async function handleFile(file: File) {
  errorMsg.value = ''
  const invalid = validate(file)
  if (invalid && file.size <= 10 * 1024 * 1024) {
    errorMsg.value = invalid
    emit('error', invalid)
    return
  }
  try {
    const processed = await compressImage(file)
    if (processed.size > 10 * 1024 * 1024) {
      errorMsg.value = ZH.errors.uploadTooLarge
      emit('error', ZH.errors.uploadTooLarge)
      return
    }
    emit('upload', processed)
  } catch {
    errorMsg.value = ZH.errors.uploadTooLarge
    emit('error', ZH.errors.uploadTooLarge)
  }
}

function onDrop(e: DragEvent) {
  dragging.value = false
  const file = e.dataTransfer?.files?.[0]
  if (file) void handleFile(file)
}

function onPaste(e: ClipboardEvent) {
  const file = e.clipboardData?.files?.[0]
  if (file && file.type.startsWith('image/')) {
    void handleFile(file)
  }
}
</script>

<template>
  <div
    class="uploader"
    :class="{ dragging }"
    role="button"
    tabindex="0"
    aria-label="上传错题图片"
    @dragover.prevent="dragging = true"
    @dragleave="dragging = false"
    @drop.prevent="onDrop"
    @paste="onPaste"
    @keydown.enter="($refs.fileInput as HTMLInputElement).click()"
    @click="($refs.fileInput as HTMLInputElement).click()"
  >
    <input
      ref="fileInput"
      type="file"
      accept=".jpg,.jpeg,.png,.webp,.heic"
      hidden
      @change="($event.target as HTMLInputElement).files?.[0] && handleFile(($event.target as HTMLInputElement).files![0])"
    />
    <div class="uploader-icon"><ImagePlus :size="28" :stroke-width="1.5" /></div>
    <p class="uploader-title">拖拽图片到这里，或点击上传</p>
    <p class="uploader-hint">支持拍照 / 截图 / Ctrl+V 粘贴</p>
    <p class="uploader-hint">支持 JPG / PNG / WebP / HEIC，≤10MB</p>
  </div>
  <div v-if="errorMsg" class="field-error" style="margin-top: var(--space-2);">{{ errorMsg }}</div>
</template>

<style scoped>
.uploader {
  border: 2px dashed var(--border);
  border-radius: var(--radius-lg);
  padding: var(--space-6) var(--space-4);
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space-2);
  cursor: pointer;
  text-align: center;
  transition: border-color var(--dur-hover) ease, background var(--dur-hover) ease;
}
.uploader:hover,
.uploader.dragging {
  border-color: var(--brand);
  background: var(--brand-8);
}
.uploader-icon {
  width: 56px;
  height: 56px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--bg-subtle);
  color: var(--brand);
  margin-bottom: var(--space-2);
}
.uploader-title { font-size: var(--fs-body-lg); font-weight: 500; }
.uploader-hint { font-size: var(--fs-aux2); color: var(--text-secondary); }
</style>
