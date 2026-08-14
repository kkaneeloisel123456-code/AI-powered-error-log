<script setup lang="ts">
/** 全局应用外壳（UI/UX 3.1）：左侧导航 + 顶栏 + 内容区；<768px 底部导航。 */
import GlobalNav from './GlobalNav.vue'
import Topbar from './Topbar.vue'
import BottomNav from './BottomNav.vue'
</script>

<template>
  <div class="app-shell">
    <GlobalNav />
    <div class="app-main">
      <Topbar />
      <main class="app-content">
        <RouterView />
      </main>
    </div>
    <BottomNav />
  </div>
</template>
