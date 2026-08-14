/** 录入任务 store（T-M2-02/M2-04）：
 * - 识图模式：上传 -> OCR 任务轮询（状态机）-> 候选题勾选/编辑/删除 -> 导入
 * - 草稿持久化：localStorage，离开后可「继续上次导入」（UI/UX 7.4） */
import { defineStore } from 'pinia'
import { importApi } from '@/api/import'
import type { Candidate } from '@/api/import'

const DRAFT_KEY = 'recall-import-draft'

export interface ImportCandidate extends Candidate {
  selected: boolean
}

interface Draft {
  taskId: string
  candidates: ImportCandidate[]
  savedAt: string
}

interface State {
  mode: 'image' | 'text'
  taskId: string | null
  taskStatus: string | null
  progress: { phase: string; percent: number } | null
  taskError: string | null
  candidates: ImportCandidate[]
  uploading: boolean
  importing: boolean
  pollTimer: number | null
}

function readDraft(): Draft | null {
  try {
    const raw = localStorage.getItem(DRAFT_KEY)
    return raw ? (JSON.parse(raw) as Draft) : null
  } catch {
    return null
  }
}

export const useImportStore = defineStore('importTask', {
  state: (): State => ({
    mode: 'image',
    taskId: null,
    taskStatus: null,
    progress: null,
    taskError: null,
    candidates: [],
    uploading: false,
    importing: false,
    pollTimer: null,
  }),
  getters: {
    selectedCandidates: (state) => state.candidates.filter((c) => c.selected),
    hasDraft: () => !!readDraft(),
    draft: () => readDraft(),
  },
  actions: {
    setMode(mode: 'image' | 'text') {
      this.mode = mode
    },
    async upload(file: File, clientId: string) {
      this.uploading = true
      this.taskError = null
      try {
        const resp = await importApi.upload(file, clientId)
        this.taskId = resp.task_id
        this.taskStatus = resp.status
        this.progress = resp.progress
        this.startPolling(resp.task_id)
      } catch (err) {
        this.taskError = (err as Error).message
      } finally {
        this.uploading = false
      }
    },
    startPolling(taskId: string) {
      this.stopPolling()
      this.pollTimer = window.setInterval(() => void this.poll(taskId), 1000)
    },
    async poll(taskId: string) {
      try {
        const task = await importApi.getTask(taskId)
        this.taskStatus = task.status
        this.progress = task.progress
        this.taskError = task.error
        if (task.status === 'awaiting_confirm') {
          this.stopPolling()
          const resp = await importApi.getCandidates(taskId)
          this.candidates = resp.candidates.map((c) => ({ ...c, selected: true }))
          this.persistDraft()
        } else if (task.status === 'failed') {
          this.stopPolling()
        } else if (task.status === 'done') {
          this.stopPolling()
          this.resetTask()
        }
      } catch (err) {
        this.stopPolling()
        this.taskError = (err as Error).message
      }
    },
    stopPolling() {
      if (this.pollTimer !== null) {
        clearInterval(this.pollTimer)
        this.pollTimer = null
      }
    },
    async retry() {
      if (!this.taskId) return
      this.taskError = null
      const task = await importApi.retryTask(this.taskId)
      this.taskStatus = task.status
      this.startPolling(this.taskId)
    },
    toggleCandidate(idx: number) {
      this.candidates[idx].selected = !this.candidates[idx].selected
      this.persistDraft()
    },
    updateCandidate(idx: number, patch: Partial<ImportCandidate>) {
      Object.assign(this.candidates[idx], patch)
      // 手动修改后清除该字段的置信度标记
      const fieldMap: Record<string, string> = {
        question_text: 'question_text',
        answer: 'answer',
        analysis: 'analysis',
      }
      for (const [key, field] of Object.entries(fieldMap)) {
        if (patch[key as keyof ImportCandidate] !== undefined) {
          this.candidates[idx].confidence_fields = this.candidates[idx].confidence_fields.filter((f) => f !== field)
        }
      }
      this.persistDraft()
    },
    removeCandidate(idx: number) {
      this.candidates.splice(idx, 1)
      this.persistDraft()
    },
    async importSelected() {
      if (!this.selectedCandidates.length) return null
      this.importing = true
      try {
        const result = await importApi.importCandidates(
          this.selectedCandidates.map(({ selected: _s, ...c }) => c),
          this.taskId ?? undefined,
        )
        this.clearDraft()
        this.resetTask()
        return result
      } finally {
        this.importing = false
      }
    },
    cancelTask() {
      if (this.taskId) void importApi.cancelTask(this.taskId).catch(() => {})
      this.stopPolling()
      this.resetTask()
      this.clearDraft()
    },
    resetTask() {
      this.taskId = null
      this.taskStatus = null
      this.progress = null
      this.taskError = null
      this.candidates = []
    },
    persistDraft() {
      if (!this.taskId || !this.candidates.length) return
      localStorage.setItem(DRAFT_KEY, JSON.stringify({
        taskId: this.taskId,
        candidates: this.candidates,
        savedAt: new Date().toISOString(),
      }))
    },
    clearDraft() {
      localStorage.removeItem(DRAFT_KEY)
    },
    restoreDraft() {
      const draft = readDraft()
      if (!draft) return
      this.taskId = draft.taskId
      this.taskStatus = 'awaiting_confirm'
      this.candidates = draft.candidates
      this.progress = { phase: 'awaiting_confirm', percent: 70 }
      void importApi.getCandidates(draft.taskId).then((resp) => {
        // 服务端候选为准，保留本地勾选与编辑
        const saved = new Map(draft.candidates.map((c) => [c.question_text, c]))
        this.candidates = resp.candidates.map((c) => {
          const local = saved.get(c.question_text)
          return local ? { ...local } : { ...c, selected: true }
        })
      }).catch(() => { /* 任务已清理则丢弃草稿 */ this.clearDraft(); this.resetTask() })
    },
  },
})
