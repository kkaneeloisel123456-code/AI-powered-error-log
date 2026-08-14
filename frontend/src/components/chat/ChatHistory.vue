<script setup lang="ts">
/** 会话历史（260px 左栏，UI/UX 4.3）：标题/更新时间/消息数，悬停显示 重命名/清空/删除，搜索。 */
import { ref } from 'vue'
import { MessageSquarePlus, Pencil, Search, Trash2, X } from 'lucide-vue-next'
import { useChatStore } from '@/stores/chat'
import { ZH } from '@/constants/zh'
import { formatRelative } from '@/utils/format'
import { toast } from '@/components/common/toast'
import ConfirmDialog from '@/components/common/ConfirmDialog.vue'

const store = useChatStore()
const searchOpen = ref(false)
const searchText = ref('')
const renameId = ref<string | null>(null)
const renameText = ref('')
const deleteId = ref<string | null>(null)
const clearId = ref<string | null>(null)

async function newConversation() {
  await store.openConversation(null)
}

async function search() {
  await store.fetchConversations(searchText.value.trim() || undefined)
}

async function saveRename() {
  if (!renameId.value || !renameText.value.trim()) return
  const { chatApi } = await import('@/api/chat')
  await chatApi.updateConversation(renameId.value, { title: renameText.value.trim() })
  await store.fetchConversations()
  renameId.value = null
  toast.success('已重命名')
}

async function clearConversation(id: string) {
  const { chatApi } = await import('@/api/chat')
  await chatApi.clearConversation(id)
  clearId.value = null
  if (store.conversationId === id) store.messages = []
  await store.fetchConversations()
  toast.success('已清空')
}
</script>

<template>
  <div class="chat-history">
    <div class="history-head">
      <button class="btn btn-primary btn-sm" style="flex: 1;" @click="newConversation">
        <MessageSquarePlus :size="14" /> 新建对话
      </button>
      <button class="btn btn-icon" :title="'搜索历史'" @click="searchOpen = !searchOpen"><Search :size="15" :stroke-width="1.5" /></button>
    </div>
    <div v-if="searchOpen" class="history-search">
      <input v-model="searchText" class="input" placeholder="搜索会话标题" @keydown.enter="search" />
    </div>
    <div class="history-list">
      <div v-if="store.conversations.length === 0" class="history-empty">
        <p>{{ ZH.emptyStates.noConversation }}</p>
        <button class="btn btn-primary btn-sm" @click="newConversation">{{ ZH.emptyStates.startChat }}</button>
      </div>
      <div
        v-for="c in store.conversations"
        :key="c.id"
        class="history-item"
        :class="{ active: c.id === store.conversationId }"
        @click="store.openConversation(c.id)"
      >
        <div class="history-info">
          <div class="history-title">{{ c.title }}</div>
          <div class="history-meta num">{{ formatRelative(c.updated_at) }} · {{ c.message_count }} 条</div>
        </div>
        <div class="history-actions">
          <button class="btn btn-icon" style="width: 24px; height: 24px; min-width: 24px; min-height: 24px;" title="重命名" @click.stop="renameId = c.id; renameText = c.title"><Pencil :size="13" /></button>
          <button class="btn btn-icon" style="width: 24px; height: 24px; min-width: 24px; min-height: 24px;" title="清空" @click.stop="clearId = c.id"><X :size="13" /></button>
          <button class="btn btn-icon" style="width: 24px; height: 24px; min-width: 24px; min-height: 24px;" title="删除" @click.stop="deleteId = c.id"><Trash2 :size="13" /></button>
        </div>
      </div>
    </div>

    <ConfirmDialog
      v-if="renameId"
      title="重命名会话"
      confirm-text="保存"
      @confirm="saveRename"
      @cancel="renameId = null"
    >
      <input v-model="renameText" class="input" style="margin-bottom: var(--space-3);" @keydown.enter="saveRename" />
    </ConfirmDialog>
    <ConfirmDialog
      v-if="deleteId"
      title="删除会话？"
      message="会话与其消息将被移除，错题本数据不受影响。"
      confirm-text="删除"
      danger
      @confirm="store.removeConversation(deleteId); deleteId = null"
      @cancel="deleteId = null"
    />
    <ConfirmDialog
      v-if="clearId"
      title="清空会话消息？"
      message="该会话的全部消息将被移除，会话保留。"
      confirm-text="清空"
      danger
      @confirm="clearConversation(clearId)"
      @cancel="clearId = null"
    />
  </div>
</template>

<style scoped>
.chat-history {
  display: flex;
  flex-direction: column;
  height: 100%;
  gap: var(--space-2);
  border-right: var(--border-1);
  padding-right: var(--space-3);
}
.history-head { display: flex; gap: var(--space-2); align-items: center; }
.history-search { margin-bottom: var(--space-1); }
.history-list { flex: 1; overflow-y: auto; display: flex; flex-direction: column; gap: var(--space-1); }
.history-empty {
  text-align: center;
  color: var(--text-secondary);
  font-size: var(--fs-aux2);
  padding: var(--space-4) var(--space-2);
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
  align-items: center;
}
.history-item {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-2) var(--space-3);
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: background var(--dur-hover) ease;
}
.history-item:hover { background: var(--brand-8); }
.history-item.active { background: var(--brand-8); color: var(--brand); }
.history-info { flex: 1; min-width: 0; }
.history-title {
  font-size: var(--fs-aux2);
  font-weight: 500;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.history-meta { font-size: var(--fs-aux); color: var(--text-disabled); }
.history-actions { display: none; gap: 2px; }
.history-item:hover .history-actions { display: flex; }
</style>
