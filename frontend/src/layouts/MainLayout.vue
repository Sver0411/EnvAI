<template>
  <div class="app-shell" :class="{ 'sidebar-collapsed': sidebarCollapsed }">
    <aside class="sidebar">
      <div class="brand" @click="router.push('/projects')">
        <div class="brand-mark"><span></span><span></span><span></span></div>
        <div><strong>EnvAI</strong><small>环保咨询工作台</small></div>
      </div>

      <button class="create-button" @click="router.push({ name: 'project-new' })">
        <el-icon><Plus /></el-icon><span>新建项目</span>
      </button>

      <nav class="nav-group">
        <p class="nav-label">工作空间</p>
        <router-link to="/projects" class="nav-item" :class="{ active: $route.path.startsWith('/projects') }">
          <el-icon><Grid /></el-icon><span>项目工作台</span>
        </router-link>
        <router-link to="/knowledge" class="nav-item" :class="{ active: $route.path === '/knowledge' }">
          <el-icon><Collection /></el-icon><span>专业知识库</span>
        </router-link>
        <button v-if="isPlatformAdmin" class="nav-item nav-button" @click="router.push('/admin')">
          <el-icon><DataAnalysis /></el-icon><span>平台运营</span>
        </button>
      </nav>

      <div class="account-area">
        <el-dropdown trigger="click" @command="onCommand">
          <button class="account-button">
            <span class="avatar">{{ avatarText }}</span>
            <span class="account-copy"><strong>{{ auth.user?.full_name || auth.user?.username }}</strong><small>{{ currentOrganization?.name || '个人工作区' }}</small></span>
            <el-icon class="more"><MoreFilled /></el-icon>
          </button>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item v-for="item in organizations" :key="item.id" :command="`org:${item.id}`" :disabled="item.id === organizationId">{{ item.name }}</el-dropdown-item>
              <el-dropdown-item divided command="logout"><el-icon><SwitchButton /></el-icon>退出登录</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </div>
    </aside>

    <section class="content-shell">
      <header class="topbar">
        <div class="topbar-left">
          <button class="menu-toggle" :aria-label="sidebarCollapsed ? '展开菜单' : '收起菜单'" :title="sidebarCollapsed ? '展开菜单' : '收起菜单'" @click="toggleSidebar"><el-icon><Expand v-if="sidebarCollapsed" /><Fold v-else /></el-icon></button>
          <div class="context">
          <span class="context-dot"></span>
          <span>{{ currentOrganization?.name || 'EnvAI 工作区' }}</span>
          </div>
        </div>
        <div class="topbar-actions">
          <span class="secure"><el-icon><Lock /></el-icon>企业数据已隔离</span>
          <button class="icon-button" title="帮助"><el-icon><QuestionFilled /></el-icon></button>
        </div>
      </header>
      <main class="main-content"><router-view /></main>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { Collection, DataAnalysis, Expand, Fold, Grid, Lock, MoreFilled, Plus, QuestionFilled, SwitchButton } from '@element-plus/icons-vue'
import { useAuthStore } from '../stores/auth'
import { listOrganizations } from '../api/tenant'
import type { Organization } from '../types'

const auth = useAuthStore()
const router = useRouter()
const organizations = ref<Organization[]>([])
const organizationId = ref<number | undefined>(Number(localStorage.getItem('envai_organization_id')) || undefined)
const sidebarCollapsed = ref(localStorage.getItem('envai_sidebar_collapsed') === '1')
const currentOrganization = computed(() => organizations.value.find((item) => item.id === organizationId.value))
const isPlatformAdmin = computed(() => ['platform_admin', 'platform_super_admin'].includes(auth.user?.platform_role || ''))
const avatarText = computed(() => (auth.user?.full_name || auth.user?.username || 'U').slice(0, 1).toUpperCase())

onMounted(async () => {
  organizations.value = await listOrganizations()
  if (!organizationId.value && organizations.value[0]) switchOrganization(organizations.value[0].id)
})

function switchOrganization(id: number) {
  organizationId.value = id
  localStorage.setItem('envai_organization_id', String(id))
  location.reload()
}

function toggleSidebar() {
  sidebarCollapsed.value = !sidebarCollapsed.value
  localStorage.setItem('envai_sidebar_collapsed', sidebarCollapsed.value ? '1' : '0')
}

function onCommand(command: string) {
  if (command.startsWith('org:')) return switchOrganization(Number(command.split(':')[1]))
  if (command === 'logout') {
    auth.logout()
    router.push({ name: 'login' })
  }
}
</script>

<style scoped>
.app-shell { min-height: 100vh; }
.sidebar { position: fixed; inset: 0 auto 0 0; z-index: 20; width: 252px; padding: 22px 16px 16px; display: flex; flex-direction: column; background: rgba(250, 250, 252, .82); border-right: 1px solid rgba(0,0,0,.07); backdrop-filter: saturate(180%) blur(28px); }
.brand { display: flex; align-items: center; gap: 11px; height: 52px; padding: 0 10px; cursor: pointer; }
.brand-mark { position: relative; width: 34px; height: 34px; border-radius: 11px; background: linear-gradient(145deg, #0b84ff, #0057c7); box-shadow: 0 7px 18px rgba(0,113,227,.25); overflow: hidden; }
.brand-mark span { position: absolute; bottom: 8px; width: 5px; border-radius: 5px; background: white; }
.brand-mark span:nth-child(1) { left: 8px; height: 9px; opacity: .65; }.brand-mark span:nth-child(2) { left: 15px; height: 15px; opacity: .82; }.brand-mark span:nth-child(3) { left: 22px; height: 21px; }
.brand strong { display: block; font-size: 18px; letter-spacing: -.03em; }.brand small { display: block; margin-top: 1px; color: #86868b; font-size: 10px; }
.create-button { width: 100%; height: 45px; margin: 20px 0 18px; display: flex; align-items: center; justify-content: center; gap: 8px; color: white; border: 0; border-radius: 14px; background: #0071e3; box-shadow: 0 8px 20px rgba(0,113,227,.2); cursor: pointer; font-weight: 650; transition: .2s ease; }
.create-button:hover { transform: translateY(-1px); background: #0077ed; }
.nav-label { margin: 12px 12px 8px; color: #98989d; font-size: 10px; font-weight: 700; letter-spacing: .09em; text-transform: uppercase; }
.nav-item { width: 100%; min-height: 44px; margin: 3px 0; padding: 0 13px; display: flex; align-items: center; gap: 11px; color: #515154; border-radius: 13px; font-size: 14px; font-weight: 600; transition: .18s; }
.nav-item:hover { background: rgba(0,0,0,.045); }.nav-item.active { color: #0068d1; background: #e8f2ff; }.nav-item .el-icon { font-size: 18px; }
.nav-button { border: 0; background: transparent; cursor: pointer; text-align: left; }
.account-area { margin-top: auto; padding-top: 12px; border-top: 1px solid rgba(0,0,0,.06); }.account-area :deep(.el-dropdown) { width: 100%; }
.account-button { width: 100%; padding: 7px 6px; display: flex; align-items: center; gap: 10px; border: 0; border-radius: 13px; background: transparent; cursor: pointer; }.account-button:hover { background: rgba(0,0,0,.045); }
.avatar { flex: 0 0 34px; width: 34px; height: 34px; display: grid; place-items: center; border-radius: 50%; color: white; background: linear-gradient(145deg,#555,#1d1d1f); font-size: 13px; font-weight: 700; }
.account-copy { min-width: 0; flex: 1; text-align: left; }.account-copy strong,.account-copy small { display: block; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }.account-copy strong { font-size: 12px; }.account-copy small { margin-top: 3px; color: #86868b; font-size: 10px; }.more { color: #86868b; }
.content-shell { min-height: 100vh; margin-left: 252px; transition: margin-left .22s ease; }.topbar { position: static; height: 64px; padding: 0 34px; display: flex; align-items: center; justify-content: space-between; border-bottom: 1px solid rgba(0,0,0,.055); background: #f5f5f7; }.topbar-left { display: flex; align-items: center; gap: 13px; }.menu-toggle { width: 36px; height: 36px; display: grid; place-items: center; border: 1px solid rgba(0,0,0,.08); border-radius: 11px; color: #515154; background: rgba(255,255,255,.78); cursor: pointer; transition: .18s ease; }.menu-toggle:hover { color: #0068d1; background: #e8f2ff; }
.context { display: flex; align-items: center; gap: 8px; color: #515154; font-size: 13px; font-weight: 600; }.context-dot { width: 7px; height: 7px; border-radius: 50%; background: #34c759; box-shadow: 0 0 0 4px rgba(52,199,89,.12); }
.topbar-actions { display: flex; align-items: center; gap: 12px; }.secure { display: flex; align-items: center; gap: 5px; color: #86868b; font-size: 11px; }.icon-button { width: 34px; height: 34px; display: grid; place-items: center; border: 1px solid rgba(0,0,0,.07); border-radius: 50%; background: rgba(255,255,255,.72); color: #515154; cursor: pointer; }
@media (max-width: 1100px) { .sidebar { width: 76px; padding: 18px 10px; }.brand > div:last-child,.create-button span,.nav-item span,.nav-label,.account-copy,.more { display:none; }.brand { justify-content:center; padding:0; }.create-button { width:48px; margin-left:auto; margin-right:auto; }.nav-item { justify-content:center; padding:0; }.content-shell { margin-left:76px; }.topbar { padding:0 18px; }.secure { display:none; } }
.app-shell.sidebar-collapsed .sidebar { width: 76px; padding: 18px 10px; }
.app-shell.sidebar-collapsed .brand { justify-content: center; padding: 0; }
.app-shell.sidebar-collapsed .brand > div:last-child,
.app-shell.sidebar-collapsed .create-button span,
.app-shell.sidebar-collapsed .nav-item span,
.app-shell.sidebar-collapsed .nav-label,
.app-shell.sidebar-collapsed .account-copy,
.app-shell.sidebar-collapsed .more { display: none; }
.app-shell.sidebar-collapsed .create-button { width: 48px; margin-left: auto; margin-right: auto; }
.app-shell.sidebar-collapsed .nav-item { justify-content: center; padding: 0; }
.app-shell.sidebar-collapsed .content-shell { margin-left: 76px; }
@media (max-width: 640px) { .context { font-size: 12px; }.topbar { padding: 0 12px; }.topbar-actions .icon-button { display: none; } }
</style>
