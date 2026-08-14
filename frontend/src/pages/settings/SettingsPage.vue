<script setup lang="ts">
/** 设置页（UI/UX 4.8）：单栏 768px。
 * 学科管理 / AI API 配置（掩码 + 测试连接）/ 主题切换 / 数据流向开关 / 令牌信息。
 * 备份恢复在 M4 落地。 */
import { onMounted, reactive, ref } from 'vue'
import { KeyRound, PlugZap, Plus, Trash2 } from 'lucide-vue-next'
import { settingsApi } from '@/api/settings'
import { subjectsApi } from '@/api/subjects'
import type { SettingsView, Subject } from '@/api/types'
import { useThemeStore } from '@/stores/theme'
import { toast } from '@/components/common/toast'
import PageHeader from '@/components/common/PageHeader.vue'
import ConfirmDialog from '@/components/common/ConfirmDialog.vue'

const themeStore = useThemeStore()
const settings = ref<SettingsView | null>(null)
const subjects = ref<Subject[]>([])
const loading = ref(true)

const aiForm = reactive({ api_key: '', base_url: '', model: '' })
const testing = ref(false)
const testResult = ref<{ ok: boolean; message: string; latency_ms: number } | null>(null)
const newSubjectName = ref('')
const deleteTarget = ref<Subject | null>(null)

onMounted(async () => {
  await Promise.all([loadSettings(), loadSubjects()])
  loading.value = false
})

async function loadSettings() {
  settings.value = await settingsApi.get()
  aiForm.base_url = settings.value.ai.base_url
  aiForm.model = settings.value.ai.model
}

async function loadSubjects() {
  subjects.value = await subjectsApi.list()
}

async function saveAiConfig() {
  if (!settings.value) return
  const payload: Record<string, unknown> = {
    ai: { base_url: aiForm.base_url, model: aiForm.model },
  }
  if (aiForm.api_key.trim()) payload.api_key = aiForm.api_key.trim()
  settings.value = await settingsApi.update(payload)
  aiForm.api_key = ''
  toast.success('AI 配置已保存')
}

async function testConnection() {
  testing.value = true
  testResult.value = null
  try {
    const resp = await settingsApi.testAi({
      base_url: aiForm.base_url,
      model: aiForm.model,
      api_key: aiForm.api_key.trim() || undefined,
    })
    testResult.value = { ok: resp.ok, message: resp.message, latency_ms: resp.latency_ms }
  } catch (err) {
    testResult.value = { ok: false, message: (err as Error).message, latency_ms: 0 }
  } finally {
    testing.value = false
  }
}

async function addSubject() {
  const name = newSubjectName.value.trim()
  if (!name) return
  try {
    await subjectsApi.create(name)
    newSubjectName.value = ''
    await loadSubjects()
    toast.success('学科已添加')
  } catch (err) {
    toast.error((err as Error).message)
  }
}

async function confirmDeleteSubject() {
  if (!deleteTarget.value) return
  try {
    await subjectsApi.remove(deleteTarget.value.id)
    deleteTarget.value = null
    await loadSubjects()
    toast.success('学科已删除')
  } catch (err) {
    deleteTarget.value = null
    toast.error((err as Error).message)
  }
}

async function togglePrivacy(key: 'send_question_to_ai' | 'lan_enabled', value: boolean) {
  if (!settings.value) return
  settings.value = await settingsApi.update({ privacy: { ...settings.value.privacy, [key]: value } })
}

const backingUp = ref(false)
const restoreConfirm = ref<File | null>(null)

async function downloadBackup() {
  backingUp.value = true
  try {
    const { getToken } = await import('@/api/client')
    const resp = await fetch('/api/v1/settings/backup', {
      headers: { Authorization: `Bearer ${getToken()}` },
    })
    if (!resp.ok) throw new Error('备份生成失败')
    const blob = await resp.blob()
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `Recall_backup_${new Date().toISOString().slice(0, 10)}.zip`
    a.click()
    URL.revokeObjectURL(url)
    toast.success('备份包已下载')
  } catch (err) {
    toast.error((err as Error).message)
  } finally {
    backingUp.value = false
  }
}

function onRestoreFile(e: Event) {
  const file = (e.target as HTMLInputElement).files?.[0]
  if (file) restoreConfirm.value = file
  ;(e.target as HTMLInputElement).value = ''
}

async function confirmRestore() {
  if (!restoreConfirm.value) return
  try {
    const { getToken } = await import('@/api/client')
    const form = new FormData()
    form.append('file', restoreConfirm.value)
    const resp = await fetch('/api/v1/settings/backup/restore', {
      method: 'POST',
      headers: { Authorization: `Bearer ${getToken()}` },
      body: form,
    })
    const body = await resp.json().catch(() => null)
    if (!resp.ok) throw new Error(body?.message ?? '恢复失败')
    restoreConfirm.value = null
    toast.success('恢复完成，请重启服务后生效')
  } catch (err) {
    restoreConfirm.value = null
    toast.error((err as Error).message)
  }
}
</script>

<template>
  <div style="max-width: 768px; margin: 0 auto;">
    <PageHeader title="设置" />

    <div v-if="loading"><div class="skeleton" style="height: 120px;"></div></div>
    <template v-else-if="settings">
      <!-- 学科管理 -->
      <section class="card settings-card">
        <h2 class="card-title">学科管理</h2>
        <div class="subject-list">
          <div v-for="s in subjects" :key="s.id" class="subject-row">
            <span>{{ s.name }}</span>
            <span class="count num">{{ s.mistake_count }} 题</span>
            <button class="btn btn-danger btn-sm" aria-label="删除学科" @click="deleteTarget = s"><Trash2 :size="14" /></button>
          </div>
        </div>
        <div class="add-row">
          <input v-model="newSubjectName" class="input" placeholder="新学科名称" @keydown.enter="addSubject" />
          <button class="btn btn-secondary btn-sm" @click="addSubject"><Plus :size="14" /> 添加学科</button>
        </div>
      </section>

      <!-- AI API 配置 -->
      <section class="card settings-card">
        <h2 class="card-title"><KeyRound :size="16" /> AI API 配置（DeepSeek）</h2>
        <p v-if="settings.ai.mock" class="hint">当前为演示模式（mock）。配置 API Key 并关闭 mock 后启用真实 AI。</p>
        <div class="field">
          <label class="field-label" for="ai-key">API Key
            <template v-if="settings.ai.has_api_key">（已配置：{{ settings.ai.api_key_masked }}）</template>
          </label>
          <input id="ai-key" v-model="aiForm.api_key" class="input num" type="password" placeholder="sk-…（留空则不变）" />
        </div>
        <div class="form-row">
          <div class="field" style="flex: 2;">
            <label class="field-label" for="ai-base">Base URL</label>
            <input id="ai-base" v-model="aiForm.base_url" class="input num" />
          </div>
          <div class="field" style="flex: 1;">
            <label class="field-label" for="ai-model">模型</label>
            <input id="ai-model" v-model="aiForm.model" class="input num" />
          </div>
        </div>
        <div class="row-actions">
          <button class="btn btn-secondary btn-sm" :disabled="testing" @click="testConnection">
            <PlugZap :size="14" /> {{ testing ? '测试中…' : '测试连接' }}
          </button>
          <span v-if="testResult" :style="{ color: testResult.ok ? 'var(--status-mastered)' : 'var(--error)', fontSize: 'var(--fs-aux2)' }">
            {{ testResult.message }}<template v-if="testResult.ok">（{{ testResult.latency_ms }}ms）</template>
          </span>
          <span class="spacer" />
          <button class="btn btn-primary btn-sm" @click="saveAiConfig">保存</button>
        </div>
      </section>

      <!-- 隐私与数据流向 -->
      <section class="card settings-card">
        <h2 class="card-title">隐私与数据流向</h2>
        <div class="switch-row">
          <div>
            <div>允许向 AI 发送题干文本</div>
            <div class="hint">关闭后 AI 补全 / 批改 / 答疑将不可用；图片始终本地处理，不上传</div>
          </div>
          <button
            class="switch"
            :class="{ on: settings.privacy.send_question_to_ai }"
            role="switch"
            :aria-checked="settings.privacy.send_question_to_ai"
            @click="togglePrivacy('send_question_to_ai', !settings.privacy.send_question_to_ai)"
          ><span class="knob"></span></button>
        </div>
        <div class="switch-row">
          <div>
            <div>局域网访问</div>
            <div class="hint">默认仅本机（127.0.0.1）可访问；开启需重启后端并监听 0.0.0.0</div>
          </div>
          <button
            class="switch"
            :class="{ on: settings.privacy.lan_enabled }"
            role="switch"
            :aria-checked="settings.privacy.lan_enabled"
            @click="togglePrivacy('lan_enabled', !settings.privacy.lan_enabled)"
          ><span class="knob"></span></button>
        </div>
      </section>

      <!-- 数据备份 / 恢复 -->
      <section class="card settings-card">
        <h2 class="card-title">数据备份 / 恢复</h2>
        <p class="hint">备份包包含 SQLite 数据库与全部原题图片；恢复前会做格式校验，恢复后需重启服务生效。</p>
        <div class="row-actions">
          <button class="btn btn-secondary btn-sm" :disabled="backingUp" @click="downloadBackup">
            {{ backingUp ? '打包中…' : '下载备份包' }}
          </button>
          <label class="btn btn-secondary btn-sm" style="cursor: pointer;">
            选择备份包恢复
            <input type="file" accept=".zip" hidden @change="onRestoreFile" />
          </label>
          <span class="spacer" />
        </div>
      </section>

      <!-- 主题 -->
      <section class="card settings-card">
        <h2 class="card-title">主题</h2>
        <div class="segmented">
          <button :class="{ active: themeStore.theme === 'light' }" @click="themeStore.set('light')">亮色</button>
          <button :class="{ active: themeStore.theme === 'dark' }" @click="themeStore.set('dark')">暗色</button>
        </div>
      </section>

      <!-- 令牌信息 -->
      <section class="card settings-card">
        <h2 class="card-title">本地访问令牌</h2>
        <p class="hint">当前令牌掩码：<code class="num">{{ settings.token_masked }}</code>。令牌文件位于 data/auth/token.key，请勿外泄。</p>
        <p class="hint">版本 {{ settings.version }} · 数据目录 data/（SQLite + 图片 + 备份）</p>
      </section>
    </template>

    <ConfirmDialog
      v-if="deleteTarget"
      title="删除学科？"
      :message="`学科「${deleteTarget.name}」及其知识树将被删除。该学科下已有错题时无法删除。`"
      confirm-text="删除"
      danger
      @confirm="confirmDeleteSubject"
      @cancel="deleteTarget = null"
    />
    <ConfirmDialog
      v-if="restoreConfirm"
      title="恢复备份？"
      :message="`将用备份包「${restoreConfirm.name}」覆盖当前数据库与图片，恢复后需重启服务。建议先下载当前备份。`"
      confirm-text="确认恢复"
      danger
      @confirm="confirmRestore"
      @cancel="restoreConfirm = null"
    />
  </div>
</template>

<style scoped>
.settings-card {
  padding: var(--space-4) var(--space-5);
  margin-bottom: var(--space-4);
}
.card-title {
  font-size: var(--fs-card-title);
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: var(--space-2);
  margin-bottom: var(--space-3);
}
.hint {
  font-size: var(--fs-aux2);
  color: var(--text-secondary);
  margin-bottom: var(--space-3);
}
.subject-list { display: flex; flex-direction: column; margin-bottom: var(--space-3); }
.subject-row {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-2) 0;
  border-bottom: var(--border-1);
}
.subject-row:last-child { border-bottom: none; }
.subject-row .count { color: var(--text-secondary); font-size: var(--fs-aux2); flex: 1; }
.add-row { display: flex; gap: var(--space-2); }
.form-row { display: flex; gap: var(--space-3); margin-bottom: var(--space-3); }
.row-actions { display: flex; align-items: center; gap: var(--space-3); }
.spacer { flex: 1; }
.switch-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-3);
  padding: var(--space-3) 0;
  border-bottom: var(--border-1);
  font-size: var(--fs-body);
}
.switch-row:last-child { border-bottom: none; }
.switch {
  width: 44px;
  height: 24px;
  border-radius: 12px;
  background: var(--border);
  position: relative;
  transition: background var(--dur-hover) ease;
  flex-shrink: 0;
}
.switch.on { background: var(--brand); }
.switch .knob {
  position: absolute;
  top: 2px;
  left: 2px;
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: #fff;
  transition: transform var(--dur-hover) ease;
}
.switch.on .knob { transform: translateX(20px); }
</style>
