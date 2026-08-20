<template>
  <div class="page-container dashboard">
    <section class="hero">
      <div>
        <h1 class="page-title">下午好，{{ displayName }}</h1>
      </div>
      <el-button type="primary" size="large" @click="router.push({ name: 'project-new' })"><el-icon><Plus /></el-icon>创建新项目</el-button>
    </section>

    <section class="metrics">
      <article class="metric surface"><div class="metric-icon blue"><el-icon><Folder /></el-icon></div><div><span>全部项目</span><strong>{{ total }}</strong></div></article>
      <article class="metric surface"><div class="metric-icon amber"><el-icon><EditPen /></el-icon></div><div><span>编制进行中</span><strong>{{ inProgressCount }}</strong></div></article>
      <article class="metric surface"><div class="metric-icon green"><el-icon><CircleCheck /></el-icon></div><div><span>已完成</span><strong>{{ completedCount }}</strong></div></article>
      <article class="metric surface"><div class="metric-icon violet"><el-icon><Files /></el-icon></div><div><span>本页企业</span><strong>{{ companyCount }}</strong></div></article>
    </section>

    <section class="project-section">
      <div class="section-head">
        <div><h2 class="section-title">最近项目</h2><p class="section-copy">{{ total }} 个项目</p></div>
        <div class="filters"><el-input v-model="keyword" clearable placeholder="搜索项目或企业" :prefix-icon="Search" /><el-select v-model="statusFilter" style="width: 132px"><el-option label="全部状态" value="all" /><el-option label="进行中" value="active" /><el-option label="已完成" value="completed" /></el-select></div>
      </div>

      <div v-loading="loading" class="project-grid">
        <article v-for="project in filteredProjects" :key="project.id" class="project-card surface" @click="openProject(project.id)">
          <div class="card-top"><div class="project-symbol" :class="project.project_type"><el-icon><Document /></el-icon></div><div class="card-actions"><button class="delete-button" title="删除项目" aria-label="删除项目" @click.stop="onDelete(project.id)"><el-icon><Delete /></el-icon></button><el-dropdown trigger="click" @click.stop><button class="more-button" title="更多操作" aria-label="更多操作"><el-icon><MoreFilled /></el-icon></button><template #dropdown><el-dropdown-menu><el-dropdown-item @click="openProject(project.id)">打开项目</el-dropdown-item><el-dropdown-item @click="openWriting(project.id)">进入报告编制</el-dropdown-item><el-dropdown-item divided @click="onDelete(project.id)">删除项目</el-dropdown-item></el-dropdown-menu></template></el-dropdown></div></div>
          <div class="project-type">{{ typeLabel(project.project_type) }}</div>
          <h3>{{ project.name }}</h3>
          <p class="company">{{ project.company_name || '企业名称待补充' }}</p>
          <div class="progress-row"><span>项目进度</span><strong>{{ progress(project.status) }}%</strong></div>
          <el-progress :percentage="progress(project.status)" :show-text="false" :stroke-width="5" />
          <footer><el-tag :type="statusType(project.status)" effect="light">{{ statusLabel(project.status) }}</el-tag><span>{{ friendlyDate(project.updated_at || project.created_at) }}</span><button class="go"><el-icon><ArrowRight /></el-icon></button></footer>
        </article>
        <button class="new-card" @click="router.push({ name: 'project-new' })"><span><el-icon><Plus /></el-icon></span><strong>创建新项目</strong></button>
      </div>
      <el-empty v-if="!loading && projects.length && !filteredProjects.length" description="没有找到匹配的项目" />
      <el-pagination v-if="total > pageSize" class="pagination" layout="prev, pager, next" :total="total" :page-size="pageSize" :current-page="page" @current-change="onPageChange" />
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { ArrowRight, CircleCheck, Delete, Document, EditPen, Files, Folder, MoreFilled, Plus, Search } from '@element-plus/icons-vue'
import { projectApi } from '../api/projects'
import { useAuthStore } from '../stores/auth'
import type { Project, ProjectStatus, ProjectType } from '../types'

const router = useRouter(); const auth = useAuthStore()
const projects = ref<Project[]>([]); const total = ref(0); const page = ref(1); const pageSize = 12; const loading = ref(false); const keyword = ref(''); const statusFilter = ref('all')
const displayName = computed(() => auth.user?.full_name || auth.user?.username || '顾问')
const completedCount = computed(() => projects.value.filter((item) => item.status === 'completed').length)
const inProgressCount = computed(() => projects.value.filter((item) => item.status !== 'completed').length)
const companyCount = computed(() => new Set(projects.value.map((item) => item.company_name).filter(Boolean)).size)
const filteredProjects = computed(() => projects.value.filter((item) => {
  const matchesText = !keyword.value || `${item.name}${item.company_name || ''}`.toLowerCase().includes(keyword.value.toLowerCase())
  const matchesStatus = statusFilter.value === 'all' || (statusFilter.value === 'completed' ? item.status === 'completed' : item.status !== 'completed')
  return matchesText && matchesStatus
}))
const typeLabels: Record<ProjectType, string> = { environmental_impact: '环境影响评价', emergency_response: '突发环境事件应急预案', risk_assessment: '环境风险评估', other: '环保咨询报告' }
const statusLabels: Record<ProjectStatus, string> = { draft: '刚刚创建', collecting_data: '准备资料', analyzing: '整理企业数据', generating: '报告编制中', reviewing: '审核中', completed: '已完成' }
const progressMap: Record<ProjectStatus, number> = { draft: 8, collecting_data: 28, analyzing: 48, generating: 68, reviewing: 86, completed: 100 }
const typeLabel = (value: string) => typeLabels[value as ProjectType] || '环保咨询报告'
const statusLabel = (value: string) => statusLabels[value as ProjectStatus] || '进行中'
const statusType = (value: string) => value === 'completed' ? 'success' : ['generating', 'analyzing'].includes(value) ? 'primary' : 'warning'
const progress = (value: string) => progressMap[value as ProjectStatus] || 10
const friendlyDate = (value: string) => `更新于 ${new Date(value).toLocaleDateString('zh-CN', { month: 'numeric', day: 'numeric' })}`
const openProject = (id: number) => router.push(`/projects/${id}`)
const openWriting = (id: number) => router.push({ path: `/projects/${id}`, query: { tab: 'writing' } })

async function load() { loading.value = true; try { const data = await projectApi.list({ page: page.value, page_size: pageSize }); projects.value = data.items; total.value = data.total } catch (e) { ElMessage.error((e as Error).message) } finally { loading.value = false } }
function onPageChange(value: number) { page.value = value; load() }
async function onDelete(id: number) {
  try {
    await ElMessageBox.confirm('删除后无法恢复，确认删除这个项目吗？', '删除项目', { type: 'warning', confirmButtonText: '确认删除', cancelButtonText: '取消' })
    await projectApi.remove(id)
    ElMessage.success('项目已删除')
    await load()
  } catch (error) {
    if (error === 'cancel' || error === 'close') return
    ElMessage.error(error instanceof Error ? error.message : '项目删除失败，请稍后重试')
  }
}
onMounted(load)
</script>

<style scoped>
.hero { display:flex; align-items:flex-end; justify-content:space-between; gap:24px; padding: 15px 0 29px; }.hero :deep(.el-button){padding:0 23px;height:48px}.metrics{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin-bottom:18px}.metric{display:flex;align-items:center;gap:15px;padding:18px 20px}.metric-icon{width:44px;height:44px;display:grid;place-items:center;border-radius:14px;font-size:20px}.metric-icon.blue{color:#0071e3;background:#e8f2ff}.metric-icon.amber{color:#e57c00;background:#fff2dc}.metric-icon.green{color:#1d9d43;background:#e9f9ed}.metric-icon.violet{color:#7d47d9;background:#f1eaff}.metric span{display:block;color:#86868b;font-size:12px}.metric strong{display:block;margin-top:3px;font-size:24px;letter-spacing:-.04em}.quick-start{display:flex;align-items:center;gap:22px;padding:18px 20px;margin-bottom:34px;background:linear-gradient(110deg,rgba(255,255,255,.95),rgba(235,246,255,.9))}.quick-copy{display:flex;align-items:center;gap:12px;min-width:290px}.spark{width:38px;height:38px;display:grid;place-items:center;border-radius:12px;color:#0071e3;background:white;box-shadow:0 6px 16px rgba(0,0,0,.06)}.quick-copy strong{font-size:14px}.quick-copy p{margin:4px 0 0;color:#6e6e73;font-size:11px}.quick-flow{flex:1;display:flex;align-items:center;justify-content:center}.quick-flow span{display:flex;align-items:center;gap:6px;color:#515154;font-size:12px;white-space:nowrap}.quick-flow b{width:22px;height:22px;display:grid;place-items:center;border-radius:50%;color:#0071e3;background:#e8f2ff;font-size:10px}.quick-flow i{width:34px;height:1px;margin:0 8px;background:#d2d2d7}.section-head{display:flex;align-items:flex-end;justify-content:space-between;gap:20px;margin-bottom:18px}.filters{display:flex;gap:10px}.filters :deep(.el-input){width:240px}.project-grid{min-height:260px;display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:16px}.project-card{padding:20px;cursor:pointer;transition:.24s ease}.project-card:hover{transform:translateY(-3px);box-shadow:0 20px 50px rgba(0,0,0,.09)}.card-top{display:flex;justify-content:space-between}.card-actions{display:flex;align-items:center;gap:4px}.project-symbol{width:43px;height:43px;display:grid;place-items:center;border-radius:14px;color:#0071e3;background:#e8f2ff;font-size:20px}.project-symbol.emergency_response{color:#e57c00;background:#fff2dc}.project-symbol.risk_assessment{color:#7d47d9;background:#f1eaff}.more-button,.delete-button{width:32px;height:32px;border:0;border-radius:50%;background:transparent;color:#86868b;cursor:pointer}.more-button:hover{background:#f0f0f2}.delete-button:hover{color:#d70015;background:#fff0ef}.project-type{margin-top:17px;color:#0071e3;font-size:11px;font-weight:700}.project-card h3{height:48px;margin:6px 0 5px;overflow:hidden;font-size:18px;line-height:1.35;letter-spacing:-.02em}.company{height:20px;margin:0 0 20px;overflow:hidden;color:#6e6e73;font-size:12px;white-space:nowrap;text-overflow:ellipsis}.progress-row{display:flex;justify-content:space-between;margin-bottom:8px;color:#6e6e73;font-size:11px}.progress-row strong{color:#515154}.project-card footer{display:flex;align-items:center;gap:9px;margin-top:18px;padding-top:15px;border-top:1px solid rgba(0,0,0,.06)}.project-card footer>span{color:#86868b;font-size:10px}.go{width:29px;height:29px;margin-left:auto;display:grid;place-items:center;border:0;border-radius:50%;color:#0071e3;background:#e8f2ff;cursor:pointer}.new-card{min-height:280px;display:flex;flex-direction:column;align-items:center;justify-content:center;border:1.5px dashed #c7c7cc;border-radius:22px;background:rgba(255,255,255,.35);color:#515154;cursor:pointer;transition:.2s}.new-card:hover{border-color:#0071e3;background:#f8fbff}.new-card span{width:45px;height:45px;display:grid;place-items:center;margin-bottom:12px;border-radius:50%;color:#0071e3;background:#e8f2ff;font-size:18px}.new-card small{margin-top:5px;color:#86868b}.pagination{justify-content:center;margin-top:25px}@media(max-width:1150px){.metrics{grid-template-columns:repeat(2,1fr)}.project-grid{grid-template-columns:repeat(2,1fr)}.quick-flow{display:none}}@media(max-width:700px){.hero,.section-head{align-items:flex-start;flex-direction:column}.project-grid{grid-template-columns:1fr}.metrics{grid-template-columns:1fr 1fr}.quick-start{align-items:flex-start;flex-direction:column}.filters{width:100%;flex-direction:column}.filters :deep(.el-input){width:100%}}
</style>
