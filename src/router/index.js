import { createRouter, createWebHistory } from 'vue-router'
import DashboardView from '../views/DashboardView.vue'
import TransactionsView from '../views/TransactionsView.vue'
import BucketsView from '../views/BucketsView.vue'
import InsightsView from '../views/InsightsView.vue'
import AuthView from '../views/AuthView.vue'
import useFinanceData from '../composables/useFinanceData'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/auth',
      name: 'auth',
      component: AuthView,
      meta: { public: true },
    },
    {
      path: '/',
      name: 'dashboard',
      component: DashboardView,
      meta: { requiresAuth: true },
    },
    {
      path: '/transactions',
      name: 'transactions',
      component: TransactionsView,
      meta: { requiresAuth: true },
    },
    {
      path: '/buckets',
      name: 'buckets',
      component: BucketsView,
      meta: { requiresAuth: true },
    },
    {
      path: '/insights',
      name: 'insights',
      component: InsightsView,
      meta: { requiresAuth: true },
    },
  ],
})

router.beforeEach((to) => {
  const { isAuthenticated } = useFinanceData()

  if (to.meta.requiresAuth && !isAuthenticated.value) {
    return { name: 'auth' }
  }

  if (to.name === 'auth' && isAuthenticated.value) {
    return { name: 'dashboard' }
  }

  return true
})

export default router
