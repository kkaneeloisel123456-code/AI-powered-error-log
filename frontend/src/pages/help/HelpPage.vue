<script setup lang="ts">
/** 帮助中心（UI/UX 3.7 / 4.7）：220px 左栏导航 + 内容 760px；
 * 新手引导 4 步、FAQ 手风琴（同时只展开一项）、快捷键表、意见反馈、版本信息与数据流向说明。 */
import { onMounted, ref } from 'vue'
import { BookOpen, GraduationCap, LayoutDashboard, FileInput } from 'lucide-vue-next'
import { ZH } from '@/constants/zh'
import { settingsApi } from '@/api/settings'
import { toast } from '@/components/common/toast'

type SectionKey = 'guide' | 'faq' | 'shortcuts' | 'feedback' | 'about'

const section = ref<SectionKey>('guide')
const openFaq = ref<string | null>('faq-1')
const feedbackText = ref('')
const version = ref('')
const sections: Array<{ key: SectionKey; label: string }> = [
  { key: 'guide', label: '新手引导' },
  { key: 'faq', label: '常见问题' },
  { key: 'shortcuts', label: '快捷键' },
  { key: 'feedback', label: '意见反馈' },
  { key: 'about', label: '版本信息' },
]

const guideSteps = [
  { icon: FileInput, title: '录入', desc: '拍照 / 截图 / 粘贴或文本录入，AI 自动拆题与归档', to: '/import' },
  { icon: BookOpen, title: '归档', desc: '确认候选题导入错题本，新错题次日进入复习计划', to: '/mistakes' },
  { icon: GraduationCap, title: '复习', desc: '一键复习生成变体题，AI 批改并更新 SM-2 计划', to: '/review' },
  { icon: LayoutDashboard, title: '看板', desc: '数据看板呈现趋势、薄弱点与知识图谱', to: '/dashboard' },
]

const faqs = [
  { id: 'faq-1', q: '录入失败怎么办？', a: '请确认图片为 JPG / PNG / WebP / HEIC 且 ≤10MB，题目完整、光线充足。仍失败可改用文本录入（录入页顶部切换）。' },
  { id: 'faq-2', q: '对图片有什么要求？', a: '单图 ≤10MB；分辨率 ≥800px 更佳；多题同图可一次拆分。图片默认本地处理，不上传第三方。' },
  { id: 'faq-3', q: '复习计划是怎么安排的？', a: '采用 SM-2 间隔复习算法：新错题次日复习；答对间隔按掌握因子拉长；答错重置为 1 天后重现。' },
  { id: 'faq-4', q: 'AI 对话失败 / 批改失败？', a: '未配置 API Key 时运行于演示模式（mock）。真实 AI 需在「设置 → AI API 配置」填写 DeepSeek Key；服务不可用时已录数据不丢失，批改可稍后重试。' },
  { id: 'faq-5', q: '数据存在哪里？', a: '全部数据保存在本机 data/ 目录（SQLite + 原图 + 备份）。设置页可一键下载备份包。' },
  { id: 'faq-6', q: '如何备份与恢复？', a: '设置 → 数据备份 / 恢复：下载备份包；恢复前系统校验格式，恢复后需重启服务。' },
  { id: 'faq-7', q: 'API Key 怎么配置？', a: '设置 → AI API 配置：粘贴 DeepSeek Key（仅本机加密存储，界面只显示掩码），点「测试连接」验证后保存。' },
]

const shortcutRows = Object.entries(ZH.shortcuts)

onMounted(async () => {
  try {
    const s = await settingsApi.get()
    version.value = s.version
  } catch { /* 忽略 */ }
})

async function submitFeedback() {
  if (!feedbackText.value.trim()) {
    toast.error('请输入反馈内容')
    return
  }
  toast.success('感谢反馈！本地版暂不上传，建议记录在项目 issue 中')
  feedbackText.value = ''
}
</script>

<template>
  <div class="grid-help">
    <!-- 左栏导航 220px -->
    <aside class="help-nav">
      <button
        v-for="s in sections"
        :key="s.key"
        class="help-nav-item"
        :class="{ active: section === s.key }"
        @click="section = s.key"
      >{{ s.label }}</button>
    </aside>

    <!-- 右栏内容 max 760px -->
    <div class="help-content">
      <!-- 新手引导 -->
      <template v-if="section === 'guide'">
        <h2 style="font-size: var(--fs-page-title); font-weight: 600; margin-bottom: var(--space-4);">新手引导</h2>
        <div class="guide-steps">
          <RouterLink v-for="(step, i) in guideSteps" :key="step.title" :to="step.to" class="card guide-step" style="color: inherit;">
            <div class="guide-num num">{{ i + 1 }}</div>
            <component :is="step.icon" :size="20" :stroke-width="1.5" style="color: var(--brand);" />
            <div>
              <div style="font-weight: 600;">{{ step.title }}</div>
              <div style="font-size: var(--fs-aux2); color: var(--text-secondary);">{{ step.desc }}</div>
            </div>
          </RouterLink>
        </div>
      </template>

      <!-- FAQ 手风琴 -->
      <template v-else-if="section === 'faq'">
        <h2 style="font-size: var(--fs-page-title); font-weight: 600; margin-bottom: var(--space-4);">常见问题</h2>
        <div class="card">
          <div v-for="faq in faqs" :key="faq.id" class="faq-item">
            <button class="faq-q" @click="openFaq = openFaq === faq.id ? null : faq.id">
              <span>{{ faq.q }}</span>
              <span class="chevron" :class="{ open: openFaq === faq.id }">▾</span>
            </button>
            <div v-show="openFaq === faq.id" class="faq-a">{{ faq.a }}</div>
          </div>
        </div>
      </template>

      <!-- 快捷键 -->
      <template v-else-if="section === 'shortcuts'">
        <h2 style="font-size: var(--fs-page-title); font-weight: 600; margin-bottom: var(--space-4);">快捷键</h2>
        <div class="card shortcut-table">
          <div v-for="[key, desc] in shortcutRows" :key="key" class="shortcut-row">
            <kbd class="num">{{ key }}</kbd>
            <span>{{ desc }}</span>
          </div>
        </div>
      </template>

      <!-- 意见反馈 -->
      <template v-else-if="section === 'feedback'">
        <h2 style="font-size: var(--fs-page-title); font-weight: 600; margin-bottom: var(--space-4);">意见反馈</h2>
        <div class="card" style="padding: var(--space-4);">
          <textarea v-model="feedbackText" class="textarea" placeholder="遇到的问题或改进建议…"></textarea>
          <div style="display: flex; justify-content: flex-end; margin-top: var(--space-3);">
            <button class="btn btn-primary btn-sm" @click="submitFeedback">提交反馈</button>
          </div>
        </div>
      </template>

      <!-- 版本信息 -->
      <template v-else>
        <h2 style="font-size: var(--fs-page-title); font-weight: 600; margin-bottom: var(--space-4);">版本信息</h2>
        <div class="card" style="padding: var(--space-4); font-size: var(--fs-body); line-height: var(--lh-body);">
          <p>Recall - AI 智能错题本 v{{ version || '0.5.0' }}（MVP）</p>
          <p style="color: var(--text-secondary); font-size: var(--fs-aux2); margin-top: var(--space-3);">
            数据流向说明：全部数据本地存储（data/ 目录）；图片由本地 OCR 处理，默认不上传；
            仅题干文本与必要上下文发送至 DeepSeek API，可在「设置 → 隐私与数据流向」关闭；
            服务默认仅监听 127.0.0.1，局域网访问需显式开启。
          </p>
        </div>
      </template>
    </div>
  </div>
</template>

<style scoped>
/* UI/UX 3.7：220px 导航 + 内容，max 1080px 居中 */
.grid-help {
  display: grid;
  grid-template-columns: 220px minmax(0, 1fr);
  gap: var(--space-5);
  max-width: 1080px;
  margin: 0 auto;
}
.help-nav { display: flex; flex-direction: column; gap: var(--space-1); }
.help-nav-item {
  padding: var(--space-2) var(--space-3);
  border-radius: var(--radius-md);
  text-align: left;
  color: var(--text-secondary);
  transition: background var(--dur-hover) ease, color var(--dur-hover) ease;
}
.help-nav-item:hover { background: var(--bg-subtle); color: var(--text-primary); }
.help-nav-item.active { background: var(--brand-8); color: var(--brand); font-weight: 500; }
.help-content { max-width: 760px; }
.guide-steps { display: flex; flex-direction: column; gap: var(--space-3); }
.guide-step {
  display: flex;
  align-items: center;
  gap: var(--space-4);
  padding: var(--space-4);
}
.guide-num {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background: var(--gradient-ai);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: var(--fs-aux2);
  flex-shrink: 0;
}
.faq-item { border-bottom: var(--border-1); }
.faq-item:last-child { border-bottom: none; }
.faq-q {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-2);
  padding: var(--space-3) var(--space-4);
  font-size: var(--fs-body);
  font-weight: 500;
  text-align: left;
}
.faq-q:hover { color: var(--brand); }
.chevron { color: var(--text-secondary); transition: transform var(--dur-collapse) ease; }
.chevron.open { transform: rotate(180deg); }
.faq-a {
  padding: 0 var(--space-4) var(--space-3);
  color: var(--text-secondary);
  font-size: var(--fs-aux2);
  line-height: var(--lh-body);
}
.shortcut-table { padding: var(--space-2); }
.shortcut-row {
  display: flex;
  align-items: center;
  gap: var(--space-4);
  padding: var(--space-3) var(--space-4);
  border-bottom: var(--border-1);
}
.shortcut-row:last-child { border-bottom: none; }
kbd {
  font-family: var(--font-mono);
  font-size: var(--fs-aux2);
  background: var(--bg-subtle);
  border: var(--border-1);
  border-radius: var(--radius-sm);
  padding: 2px 8px;
  min-width: 72px;
  text-align: center;
}

/* 平板：导航变顶部横向 Tab（UI/UX 9.3） */
@media (max-width: 1199px) {
  .grid-help { grid-template-columns: minmax(0, 1fr); }
  .help-nav { flex-direction: row; flex-wrap: wrap; margin-bottom: var(--space-3); }
  .help-nav-item { border: var(--border-1); }
}
/* 移动：手风琴导航 + FAQ 单列 */
@media (max-width: 767px) {
  .help-nav { flex-direction: column; }
}
</style>
