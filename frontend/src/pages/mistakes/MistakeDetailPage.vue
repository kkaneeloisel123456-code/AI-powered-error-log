<script setup lang="ts">
/** 错题详情/编辑（移动端单栏钻取 + 直达链接 /mistakes/:id）。 */
import { onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ArrowLeft } from 'lucide-vue-next'
import { useMistakesStore } from '@/stores/mistakes'
import DetailPanel from '@/components/mistake/DetailPanel.vue'
import SkeletonList from '@/components/common/SkeletonList.vue'

const route = useRoute()
const router = useRouter()
const store = useMistakesStore()

onMounted(async () => {
  if (store.subjects.length === 0) await store.fetchSubjects()
  await store.fetchDetail(route.params.id as string)
})
</script>

<template>
  <div style="max-width: 768px; margin: 0 auto;">
    <button class="btn btn-text btn-sm" style="margin-bottom: var(--space-3);" @click="router.push('/mistakes')">
      <ArrowLeft :size="14" /> 返回错题本
    </button>
    <SkeletonList v-if="store.detailLoading" :rows="2" />
    <div v-else-if="store.detailError" class="card" style="padding: var(--space-4); color: var(--error);">{{ store.detailError }}</div>
    <DetailPanel
      v-else-if="store.detail"
      :mistake="store.detail"
      @deleted="router.replace('/mistakes')"
    />
  </div>
</template>
