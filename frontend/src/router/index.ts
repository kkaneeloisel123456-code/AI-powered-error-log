/** 路由表（UI/UX 5.1）。 */
import { createRouter, createWebHistory } from 'vue-router'
import { hasToken } from '@/api/client'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', name: 'home', component: () => import('@/pages/home/HomePage.vue') },
    { path: '/import', name: 'import', component: () => import('@/pages/import/ImportPage.vue') },
    { path: '/mistakes', name: 'mistakes', component: () => import('@/pages/mistakes/MistakesPage.vue') },
    { path: '/mistakes/:id', name: 'mistake-detail', component: () => import('@/pages/mistakes/MistakeDetailPage.vue') },
    { path: '/review', name: 'review', component: () => import('@/pages/review/ReviewPage.vue') },
    { path: '/review/answer', name: 'review-answer', component: () => import('@/pages/review/AnswerPage.vue') },
    { path: '/review/result/:sessionId', name: 'review-result', component: () => import('@/pages/review/ResultPage.vue') },
    { path: '/dashboard', name: 'dashboard', component: () => import('@/pages/dashboard/DashboardPage.vue') },
    { path: '/chat', name: 'chat', component: () => import('@/pages/chat/ChatPage.vue') },
    { path: '/help', name: 'help', component: () => import('@/pages/help/HelpPage.vue') },
    { path: '/settings', name: 'settings', component: () => import('@/pages/settings/SettingsPage.vue') },
    { path: '/login', name: 'login', component: () => import('@/pages/login/LoginPage.vue') },
  ],
})

// 鉴权守卫：未登录跳登录页；登录页在已登录时回首页
router.beforeEach((to) => {
  if (to.name !== 'login' && !hasToken()) return { name: 'login', query: { redirect: to.fullPath } }
  if (to.name === 'login' && hasToken()) return { name: 'home' }
})

export default router
