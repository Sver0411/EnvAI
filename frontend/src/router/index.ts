import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/login',
      name: 'login',
      component: () => import('../views/LoginView.vue'),
      meta: { public: true },
    },
    {
      path: '/register',
      name: 'register',
      component: () => import('../views/RegisterView.vue'),
      meta: { public: true },
    },
    {
      path: '/',
      component: () => import('../layouts/MainLayout.vue'),
      children: [
        {
          path: '',
          redirect: '/projects',
        },
        {
          path: 'projects',
          name: 'projects',
          component: () => import('../views/ProjectListView.vue'),
        },
        {
          path: 'projects/new',
          name: 'project-new',
          component: () => import('../views/ProjectCreateView.vue'),
        },
        {
          path: 'projects/:id',
          name: 'project-detail',
          component: () => import('../views/ProjectDetailView.vue'),
        },
        {
          path: 'knowledge',
          name: 'knowledge',
          component: () => import('../views/KnowledgeView.vue'),
        },
      ],
    },
    {
      path: '/admin',
      component: () => import('../layouts/AdminLayout.vue'),
      children: [
        { path: '', name: 'admin-dashboard', component: () => import('../views/AdminDashboardView.vue') },
        { path: 'organizations', name: 'admin-organizations', component: () => import('../views/AdminOrganizationsView.vue') },
      ],
      meta: { admin: true },
    },
  ],
})

router.beforeEach(async (to) => {
  const auth = useAuthStore()
  if (!to.meta.public && !auth.token) {
    return { name: 'login', query: { redirect: to.fullPath } }
  }
  if (to.meta.public && auth.token) {
    return { name: 'projects' }
  }
  if (to.meta.admin && !['platform_admin', 'platform_super_admin'].includes(auth.user?.platform_role || '')) {
    return { name: 'projects' }
  }
})

export default router
