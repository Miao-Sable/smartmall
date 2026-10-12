import { createRouter, createWebHistory } from 'vue-router'
import { useUserStore } from '@/stores/user'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', name: 'home', component: () => import('@/pages/HomePage.vue'), meta: { title: '首页', tabbar: true } },
    { path: '/scan', name: 'scan', component: () => import('@/pages/ScanPage.vue'), meta: { title: '扫码', tabbar: true, requiresAuth: true } },
    { path: '/history', name: 'history', component: () => import('@/pages/HistoryPage.vue'), meta: { title: '扫描历史', tabbar: true, requiresAuth: true } },
    { path: '/profile', name: 'profile', component: () => import('@/pages/ProfilePage.vue'), meta: { title: '我的', tabbar: true } },
    { path: '/profile/setup', name: 'profile-setup', component: () => import('@/pages/ProfileSetupPage.vue'), meta: { title: '档案设置', requiresAuth: true } },
    { path: '/shopping-list', name: 'shopping-list', component: () => import('@/pages/ShoppingListPage.vue'), meta: { title: '购物清单预检', requiresAuth: true } },
    { path: '/product/:barcode', name: 'product', component: () => import('@/pages/ProductDetailPage.vue'), meta: { title: '商品详情' } },
    { path: '/login', name: 'login', component: () => import('@/pages/LoginPage.vue'), meta: { title: '登录' } },
    { path: '/register', name: 'register', component: () => import('@/pages/RegisterPage.vue'), meta: { title: '注册' } },
    { path: '/privacy', name: 'privacy', component: () => import('@/pages/PrivacyPage.vue'), meta: { title: '隐私与免责声明' } },
  ],
})

// 登录守卫：未登录不可扫码 / 查看历史 / 设置档案
router.beforeEach((to) => {
  const userStore = useUserStore()
  if (to.meta.requiresAuth && !userStore.isLoggedIn) {
    return { name: 'login', query: { redirect: to.fullPath } }
  }
})

router.afterEach((to) => {
  document.title = `${String(to.meta.title ?? '智慧购物')} · 智慧购物`
})

export default router
