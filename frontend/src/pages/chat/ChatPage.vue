<script setup lang="ts">
/** AI 答疑页（UI/UX 3.3 / 4.3）：260px 会话历史 + 问答区（消息流 max 760px）；
 * SSE 流式、停止/继续、加入错题本、专注舱切换；移动端历史收抽屉。 */
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Bot, Moon, Sparkles } from 'lucide-vue-next'
import { useChatStore } from '@/stores/chat'
import { disableCockpit, enableCockpit, isCockpitEnabled } from '@/utils/cockpit'
import { ZH } from '@/constants/zh'
import ChatHistory from '@/components/chat/ChatHistory.vue'
import MessageBubble from '@/components/chat/MessageBubble.vue'
import ChatInput from '@/components/chat/ChatInput.vue'
import AddMistakeDialog from '@/components/chat/AddMistakeDialog.vue'

const store = useChatStore()
const route = useRoute()
const router = useRouter()

const cockpit = ref(false)
const draftMessageId = ref<string | null>(null)
const exampleQuestions = [
  '这道题为什么选 C？',
  '帮我推导一下动能定理',
  '函数单调性怎么判断？',
]

onMounted(async () => {
  await store.fetchConversations()
  const convId = route.query.conversationId as string | undefined
  await store.openConversation(convId ?? null)
  cockpit.value = isCockpitEnabled()
  if (cockpit.value) enableCockpit()
})

onBeforeUnmount(() => {
  store.stop()
  if (cockpit.value) disableCockpit()
})

function toggleCockpit() {
  cockpit.value = !cockpit.value
  if (cockpit.value) enableCockpit()
  else disableCockpit()
}

const currentTitle = computed(() => {
  const conv = store.conversations.find((c) => c.id === store.conversationId)
  return conv?.title ?? '新对话'
})

async function onSend(content: string) {
  await store.send(content)
}

async function addToMistake(messageId: string) {
  draftMessageId.value = messageId
  await store.extractToDraft(messageId)
}

function onDraftSaved() {
  draftMessageId.value = null
  store.draft = null
  router.push('/mistakes')
}
</script>

<template>
  <div class="chat-page">
    <!-- 顶部栏 -->
    <div class="chat-topbar">
      <h1 style="font-size: var(--fs-page-title); font-weight: 600; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">{{ currentTitle }}</h1>
      <span class="spacer" />
      <button class="btn btn-icon" :title="cockpit ? '退出专注舱' : '进入专注舱'" @click="toggleCockpit"><Moon :size="16" :stroke-width="1.5" /></button>
    </div>

    <div class="grid-chat">
      <!-- 左栏：会话历史 -->
      <aside class="chat-side"><ChatHistory /></aside>

      <!-- 右栏：问答区 -->
      <div class="chat-main">
        <div class="chat-stream">
          <!-- 错误提示（EX-06 兜底文案） -->
          <div v-if="store.error" class="chat-error">
            {{ store.error }}
            <button class="btn btn-text btn-sm" @click="store.error = null">关闭</button>
          </div>
          <!-- 空状态：示例提问 chips -->
          <div v-if="store.messages.length === 0" class="chat-empty">
            <div class="empty-icon" style="width: 56px; height: 56px; border-radius: 50%; background: var(--gradient-ai); color: #fff; display: flex; align-items: center; justify-content: center;">
              <Bot :size="26" :stroke-width="1.5" />
            </div>
            <h3 style="font-weight: 600;">{{ ZH.emptyStates.startChat }}</h3>
            <p style="color: var(--text-secondary); font-size: var(--fs-aux2);">提问学科问题，AI 流式讲解后可一键加入错题本</p>
            <div style="display: flex; flex-wrap: wrap; gap: var(--space-2); justify-content: center;">
              <button v-for="q in exampleQuestions" :key="q" class="chip clickable" @click="onSend(q)"><Sparkles :size="12" /> {{ q }}</button>
            </div>
          </div>
          <MessageBubble
            v-for="m in store.messages"
            :key="m.id"
            :message="m"
            :streaming="m.streaming ?? false"
            @continue="store.continueLast()"
            @add-to-mistake="addToMistake(m.id)"
          />
        </div>
        <ChatInput
          :sending="store.sending"
          :streaming="store.streaming"
          @send="onSend"
          @stop="store.stop()"
        />
      </div>
    </div>

    <AddMistakeDialog
      v-if="store.draft || store.draftLoading"
      :draft="store.draft!"
      :loading="store.draftLoading"
      @close="store.draft = null; draftMessageId = null"
      @saved="onDraftSaved"
    />
  </div>
</template>

<style scoped>
.chat-page { display: flex; flex-direction: column; height: calc(100vh - var(--topbar-height) - 48px); }
.chat-topbar {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  margin-bottom: var(--space-3);
}
.spacer { flex: 1; }
/* UI/UX 3.3：260px 历史 + 问答，消息流居中 max 760px */
.grid-chat {
  display: grid;
  grid-template-columns: 260px minmax(0, 1fr);
  gap: var(--space-4);
  flex: 1;
  min-height: 0;
}
.chat-side { min-height: 0; overflow: hidden; }
.chat-main {
  display: flex;
  flex-direction: column;
  min-width: 0;
  min-height: 0;
}
.chat-stream {
  flex: 1;
  overflow-y: auto;
  max-width: 760px;
  width: 100%;
  margin: 0 auto;
  padding-right: var(--space-1);
}
.chat-error {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-2);
  background: var(--status-wrong-8);
  color: var(--error);
  border: 1px solid var(--error);
  border-radius: var(--radius-md);
  padding: var(--space-2) var(--space-3);
  font-size: var(--fs-aux2);
  margin-bottom: var(--space-3);
}
.chat-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-6) var(--space-4);
  text-align: center;
}

/* 平板：220px（UI/UX 9.3） */
@media (max-width: 1199px) {
  .grid-chat { grid-template-columns: 220px minmax(0, 1fr); }
}
/* 移动：单栏，历史抽屉收起（移动端 MVP：隐藏左栏，全屏问答） */
@media (max-width: 767px) {
  .grid-chat { grid-template-columns: minmax(0, 1fr); }
  .chat-side { display: none; }
  .chat-page { height: calc(100vh - var(--topbar-height) - var(--space-4)); }
}
</style>
