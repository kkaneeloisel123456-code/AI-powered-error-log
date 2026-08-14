<script setup lang="ts">
/** 筛选折叠条（UI/UX 4.2）：学科/状态/颜色/错因/录入方式/标签/日期范围 + 排序。 */
import { ref } from 'vue'
import { ChevronDown, ChevronUp, RotateCcw } from 'lucide-vue-next'
import { useMistakesStore } from '@/stores/mistakes'
import { ZH } from '@/constants/zh'

const store = useMistakesStore()
const open = ref(false)

const SORT_OPTIONS = [
  { value: 'created_at', label: '创建时间' },
  { value: 'last_reviewed_at', label: '最后复习时间' },
  { value: 'mastery', label: '掌握度' },
  { value: 'review_count', label: '复习次数' },
  { value: 'due_date', label: '到期时间' },
]

const STATUS_OPTIONS = (Object.keys(ZH.status) as Array<keyof typeof ZH.status>).map((k) => ({
  value: k,
  label: ZH.status[k],
}))
const ERROR_OPTIONS = (Object.keys(ZH.errorTypes) as Array<keyof typeof ZH.errorTypes>).map((k) => ({
  value: k,
  label: ZH.errorTypes[k],
}))

async function apply() {
  await store.fetchList(true)
}

function clearAll() {
  store.resetFilters()
  void apply()
}
</script>

<template>
  <div class="card filter-bar">
    <button class="filter-toggle" @click="open = !open">
      <span>筛选<template v-if="store.filtersActive"> · 已启用</template></span>
      <span class="spacer" />
      <ChevronDown v-if="!open" :size="16" />
      <ChevronUp v-else :size="16" />
    </button>
    <div v-show="open" class="filter-body">
      <div class="filter-grid">
        <div class="field">
          <label class="field-label" for="f-subject">学科</label>
          <select id="f-subject" v-model="store.filters.subject_id" class="select" @change="apply">
            <option :value="undefined">全部</option>
            <option v-for="s in store.subjects" :key="s.id" :value="s.id">{{ s.name }}</option>
          </select>
        </div>
        <div class="field">
          <label class="field-label" for="f-status">状态</label>
          <select id="f-status" v-model="store.filters.status" class="select" @change="apply">
            <option :value="undefined">全部</option>
            <option v-for="s in STATUS_OPTIONS" :key="s.value" :value="s.value">{{ s.label }}</option>
          </select>
        </div>
        <div class="field">
          <label class="field-label" for="f-error">错因</label>
          <select id="f-error" v-model="store.filters.error_type" class="select" @change="apply">
            <option :value="undefined">全部</option>
            <option v-for="e in ERROR_OPTIONS" :key="e.value" :value="e.value">{{ e.label }}</option>
          </select>
        </div>
        <div class="field">
          <label class="field-label" for="f-source">录入方式</label>
          <select id="f-source" v-model="store.filters.source" class="select" @change="apply">
            <option :value="undefined">全部</option>
            <option value="image">{{ ZH.source.image }}</option>
            <option value="text">{{ ZH.source.text }}</option>
            <option value="chat">{{ ZH.source.chat }}</option>
          </select>
        </div>
        <div class="field">
          <label class="field-label" for="f-tags">标签</label>
          <input id="f-tags" v-model="store.filters.tags" class="input" placeholder="如：周测" @keydown.enter="apply" />
        </div>
        <div class="field">
          <label class="field-label" for="f-date">开始日期</label>
          <input id="f-date" v-model="store.filters.date_from" type="date" class="input" @change="apply" />
        </div>
        <div class="field">
          <label class="field-label" for="f-date2">结束日期</label>
          <input id="f-date2" v-model="store.filters.date_to" type="date" class="input" @change="apply" />
        </div>
        <div class="field">
          <label class="field-label" for="f-sort">排序</label>
          <select id="f-sort" v-model="store.filters.sort" class="select" @change="apply">
            <option v-for="s in SORT_OPTIONS" :key="s.value" :value="s.value">{{ s.label }}</option>
          </select>
        </div>
      </div>
      <div class="filter-actions">
        <button class="btn btn-text btn-sm" @click="clearAll"><RotateCcw :size="14" /> 清除筛选条件</button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.filter-bar { margin-bottom: var(--space-3); }
.filter-toggle {
  width: 100%;
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-2) var(--space-3);
  font-size: var(--fs-aux2);
  color: var(--text-secondary);
}
.filter-toggle:hover { color: var(--text-primary); }
.spacer { flex: 1; }
.filter-body {
  padding: 0 var(--space-3) var(--space-3);
  border-top: var(--border-1);
  padding-top: var(--space-3);
}
.filter-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
  gap: var(--space-3);
}
.filter-actions {
  margin-top: var(--space-3);
  display: flex;
  justify-content: flex-end;
}
</style>
