<script setup lang="ts">
/** 登录页：单用户启动引导（T-M1-01）。首次自动揭示 Token，之后凭 Token 进入。 */
import { onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { BookOpen } from 'lucide-vue-next'
import { request, setToken } from '@/api/client'
import { ZH } from '@/constants/zh'

const router = useRouter()
const route = useRoute()

const tokenInput = ref('')
const errorMsg = ref('')
const loading = ref(false)
const revealedToken = ref<string | null>(null)

onMounted(async () => {
  // 首次进入：向本地服务揭示 Token（仅一次）
  try {
    const resp = await request<{ token: string | null; token_masked: string }>('/auth/setup', { method: 'POST' })
    if (resp.token) revealedToken.value = resp.token
  } catch {
    /* 后端不可用时保持登录页可重试 */
  }
})

async function submit() {
  errorMsg.value = ''
  const token = tokenInput.value.trim()
  if (!token) {
    errorMsg.value = '请输入本地访问令牌'
    return
  }
  loading.value = true
  try {
    await request('/auth/verify-token', { method: 'POST', body: JSON.stringify({ token }) })
    setToken(token)
    router.replace((route.query.redirect as string) || '/')
  } catch (err) {
    errorMsg.value = (err as Error).message
  } finally {
    loading.value = false
  }
}

async function useRevealed() {
  if (!revealedToken.value) return
  tokenInput.value = revealedToken.value
  await submit()
}
</script>

<template>
  <div class="login-page" style="min-height: 100vh; display: flex; align-items: center; justify-content: center; background: var(--bg-page); padding: var(--space-4);">
    <div class="card" style="width: 400px; max-width: 100%; padding: var(--space-6);">
      <div style="display: flex; align-items: center; gap: var(--space-3); margin-bottom: var(--space-5);">
        <span class="logo-mark" style="width: 36px; height: 36px; border-radius: var(--radius-md); background: var(--gradient-ai); color: #fff; display: flex; align-items: center; justify-content: center;">
          <BookOpen :size="18" />
        </span>
        <div>
          <div style="font-size: var(--fs-page-title); font-weight: 600;">{{ ZH.app.name }}</div>
          <div style="font-size: var(--fs-aux2); color: var(--text-secondary);">{{ ZH.app.subtitle }} · 数据本地存储</div>
        </div>
      </div>

      <div v-if="revealedToken" class="card" style="background: var(--bg-subtle); border: var(--border-1); padding: var(--space-4); margin-bottom: var(--space-4);">
        <div style="font-size: var(--fs-aux2); color: var(--text-secondary); margin-bottom: var(--space-2);">首次启动 · 请保存你的本地访问令牌：</div>
        <code class="num" style="font-size: var(--fs-aux2); word-break: break-all; color: var(--text-primary);">{{ revealedToken }}</code>
        <button class="btn btn-primary" style="width: 100%; margin-top: var(--space-3);" @click="useRevealed">使用此令牌进入</button>
      </div>

      <div class="field">
        <label class="field-label" for="token-input">本地访问令牌</label>
        <input
          id="token-input"
          v-model="tokenInput"
          class="input num"
          type="password"
          placeholder="粘贴令牌（见 data/auth/token.key）"
          @keydown.enter="submit"
        />
        <div v-if="errorMsg" class="field-error">{{ errorMsg }}</div>
      </div>
      <button class="btn btn-primary" style="width: 100%; margin-top: var(--space-4);" :disabled="loading" @click="submit">
        {{ loading ? ZH.common.loading : '进入 Recall' }}
      </button>
      <p style="font-size: var(--fs-aux); color: var(--text-disabled); margin-top: var(--space-4); text-align: center;">
        全部数据仅存于本机 · 令牌文件位于 data/auth/token.key
      </p>
    </div>
  </div>
</template>
