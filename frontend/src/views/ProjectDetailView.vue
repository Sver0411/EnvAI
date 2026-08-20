<template>
  <div class="page-container project-page" :class="{ 'report-mode': activeTab === 'writing' }" v-loading="loading">
    <button class="back-link" @click="router.push('/projects')"><el-icon><ArrowLeft /></el-icon>全部项目</button>
    <section class="project-hero">
      <div class="project-title-wrap"><div class="project-badge"><el-icon><Document /></el-icon></div><div><div class="project-meta"><span>项目 #{{ projectId }}</span><i></i><span>{{ projectTypeLabel(project?.project_type) }}</span></div><h1>{{ project?.name || '加载项目中…' }}</h1><p>{{ project?.company_name || '企业名称待补充' }}</p></div></div>
      <div class="hero-actions"><el-tag :type="projectStatusType(project?.status)" effect="light" size="large">{{ projectStatusLabel(project?.status) }}</el-tag><el-button type="primary" size="large" @click="activeTab = 'writing'">打开报告<el-icon><ArrowRight /></el-icon></el-button></div>
    </section>

    <nav class="project-nav surface" aria-label="项目工作区">
      <button v-for="item in projectNavigation" :key="item.key" :class="{ active: activeTab === item.key }" @click="activeTab = item.key">
        <el-icon><component :is="item.icon" /></el-icon><span>{{ item.label }}</span>
        <small v-if="item.count !== undefined">{{ item.count }}</small>
      </button>
    </nav>

    <div class="workspace-content">
      <section v-show="activeTab === 'info'" class="workspace-section">
        <section class="surface content-panel info-panel">
          <div class="panel-heading"><div><h2>项目概览</h2></div></div>
          <el-form :model="form" label-width="100px" style="max-width: 640px">
            <el-form-item label="项目名称">
              <el-input v-model="form.name" />
            </el-form-item>
            <el-form-item label="项目类型">
              <el-select v-model="form.project_type" style="width: 100%">
                <el-option label="环评" value="environmental_impact" />
                <el-option label="应急预案" value="emergency_response" />
                <el-option label="风险评估" value="risk_assessment" />
                <el-option label="其他" value="other" />
              </el-select>
            </el-form-item>
            <el-form-item label="企业名称">
              <el-input v-model="form.company_name" />
            </el-form-item>
            <el-form-item label="状态">
              <el-select v-model="form.status" style="width: 100%">
                <el-option label="草稿" value="draft" />
                <el-option label="资料收集" value="collecting_data" />
                <el-option label="分析中" value="analyzing" />
                <el-option label="生成中" value="generating" />
                <el-option label="审核中" value="reviewing" />
                <el-option label="已完成" value="completed" />
              </el-select>
            </el-form-item>
            <el-form-item label="描述">
              <el-input v-model="form.description" type="textarea" :rows="3" />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" :loading="saving" @click="onSaveProject">保存</el-button>
            </el-form-item>
          </el-form>

          <el-descriptions title="元数据" :column="2" border>
            <el-descriptions-item label="创建时间">{{ project?.created_at }}</el-descriptions-item>
            <el-descriptions-item label="更新时间">{{ project?.updated_at }}</el-descriptions-item>
            <el-descriptions-item label="项目编号">#{{ project?.id }}</el-descriptions-item>
          </el-descriptions>
        </section>
      </section>

      <section v-show="activeTab === 'profile'" class="workspace-section">
        <div class="workspace-heading"><div><h2>企业信息</h2></div><el-button type="primary" :loading="savingProfile" @click="onSaveProfile">保存更改</el-button></div>
        <section class="surface content-panel profile-panel">
          <el-form :model="profileForm" label-width="120px" style="max-width: 720px">
            <el-divider content-position="left">企业基本信息</el-divider>
            <el-form-item label="企业名称">
              <el-input v-model="profileForm.company_name" />
            </el-form-item>
            <el-form-item label="统一社会信用代码">
              <el-input v-model="profileForm.credit_code" />
            </el-form-item>
            <el-form-item label="法定代表人">
              <el-input v-model="profileForm.legal_representative" />
            </el-form-item>
            <el-form-item label="联系人 / 电话">
              <el-input v-model="profileForm.contact_name" placeholder="联系人" style="width: 48%; margin-right: 4%" />
              <el-input v-model="profileForm.contact_phone" placeholder="电话" style="width: 48%" />
            </el-form-item>
            <el-form-item label="项目地址">
              <el-input v-model="profileForm.project_address" />
            </el-form-item>
            <el-form-item label="行业类别">
              <el-input v-model="profileForm.industry_category" />
            </el-form-item>
            <el-form-item label="占地面积 / 建筑面积">
              <el-input v-model="profileForm.land_area" placeholder="如 12000 m²" style="width: 48%; margin-right: 4%" />
              <el-input v-model="profileForm.building_area" placeholder="如 8600 m²" style="width: 48%" />
            </el-form-item>

            <el-divider content-position="left">生产信息</el-divider>
            <el-form-item label="产品">
              <el-input v-model="profileForm.products" placeholder="主要产品" />
            </el-form-item>
            <el-form-item label="年产量">
              <el-input v-model="profileForm.annual_output" placeholder="如 5000 t/a" />
            </el-form-item>
            <el-form-item label="生产工艺">
              <el-input v-model="profileForm.production_process" type="textarea" :rows="3" placeholder="工艺描述" />
            </el-form-item>

            <el-divider content-position="left">原辅材料</el-divider>
            <div v-for="(m, i) in profileForm.raw_materials" :key="i" class="material-row">
              <el-input v-model="m.name" placeholder="名称" />
              <el-input v-model="m.annual_usage" placeholder="年用量" />
              <el-input v-model="m.unit" placeholder="单位(t/a)" />
              <el-input v-model="m.max_storage" placeholder="最大储量" />
              <el-input v-model="m.storage_location" placeholder="存放位置" />
              <el-input v-model="m.cas_number" placeholder="CAS号" />
              <el-button type="danger" link @click="removeMaterial(i)">删除</el-button>
            </div>
            <el-button @click="addMaterial" style="margin-bottom: 16px">+ 添加原辅材料</el-button>

          </el-form>
        </section>
      </section>

      <section v-show="activeTab === 'files'" class="workspace-section">
        <div class="workspace-heading"><div><h2>资料文件</h2><p>{{ files.length }} 份项目资料</p></div></div>
        <section class="surface content-panel files-panel">
          <el-upload
            drag
            :auto-upload="false"
            :limit="10"
            multiple
            accept=".pdf,.doc,.docx,.xls,.xlsx,.png,.jpg,.jpeg"
            :on-change="onFileChange"
            :on-remove="onFileRemove"
            :file-list="fileList"
          >
            <el-icon class="upload-icon"><UploadFilled /></el-icon>
            <div class="upload-title">拖放项目资料到这里</div>
            <div class="upload-copy">或点击选择本地文件</div>
            <template #tip>
              <div class="el-upload__tip">支持 PDF / DOCX / XLSX / XLS / PNG / JPG / JPEG；单个文件最大 20 MB</div>
            </template>
          </el-upload>
          <el-button type="success" :loading="uploading" :disabled="pendingFiles.length === 0" @click="onUpload" style="margin-top: 12px">
            上传文件
          </el-button>

          <el-table :data="files" border style="margin-top: 16px">
            <el-table-column prop="filename" label="文件名" min-width="200" />
            <el-table-column prop="file_type" label="类型" width="100" />
            <el-table-column prop="file_size" label="大小(KB)" width="110">
              <template #default="{ row }">{{ (row.file_size / 1024).toFixed(1) }}</template>
            </el-table-column>
            <el-table-column prop="parse_status" label="解析状态" width="120">
              <template #default="{ row }">
                <el-tag :type="parseStatusType(row.parse_status)">
                  {{ parseStatusLabel(row.parse_status) }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="created_at" label="上传时间" width="180" />
            <el-table-column label="操作" width="150">
              <template #default="{ row }">
                <el-button link type="primary" @click="onDownload(row)">下载</el-button>
                <el-button link type="primary" :loading="parsingFileId === row.id" @click="onParse(row)">
                  {{ row.parse_status === 'parsed' ? '重新解析' : '解析' }}
                </el-button>
                <el-button link type="success" :disabled="row.parse_status !== 'parsed'" @click="onViewParsed(row)">
                  查看
                </el-button>
                <el-popconfirm title="确认删除此文件？" @confirm="onDeleteFile(row.id)">
                  <template #reference>
                    <el-button link type="danger">删除</el-button>
                  </template>
                </el-popconfirm>
              </template>
            </el-table-column>
          </el-table>
        </section>
      </section>
      <section v-show="activeTab === 'structured'" class="workspace-section">
        <ProjectStructuredDataView :project-id="projectId" />
      </section>
      <section v-show="activeTab === 'writing'" class="workspace-section writing-section">
        <DocumentWritingView :project-id="projectId" />
      </section>
    </div>

    <el-dialog v-model="parsedDialogVisible" :title="`解析结果：${selectedParsedFile?.filename || ''}`" width="80%">
      <el-descriptions v-if="selectedParsed" :column="3" border>
        <el-descriptions-item label="Parser">{{ selectedParsed.parser_name }}</el-descriptions-item>
        <el-descriptions-item label="版本">{{ selectedParsed.parser_version }}</el-descriptions-item>
        <el-descriptions-item label="解析时间">{{ selectedParsed.parsed_at }}</el-descriptions-item>
      </el-descriptions>
      <el-alert
        v-for="warning in selectedParsed?.warnings || []"
        :key="warning"
        :title="parseWarningLabel(warning)"
        type="warning"
        show-icon
        style="margin-top: 12px"
      />
      <el-tabs v-if="selectedParsed" style="margin-top: 16px">
        <el-tab-pane label="纯文本">
          <pre class="parsed-text">{{ selectedParsed.plain_text || '（无文本层，可能需要 OCR）' }}</pre>
        </el-tab-pane>
        <el-tab-pane label="结构化数据">
          <pre class="parsed-text">{{ formatStructuredContent(selectedParsed.structured_content) }}</pre>
        </el-tab-pane>
        <el-tab-pane label="元数据">
          <pre class="parsed-text">{{ formatStructuredContent(selectedParsed.metadata) }}</pre>
        </el-tab-pane>
      </el-tabs>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, markRaw, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, type UploadFile, type UploadFiles } from 'element-plus'
import { ArrowLeft, ArrowRight, Collection, DataAnalysis, Document, Files, OfficeBuilding, UploadFilled } from '@element-plus/icons-vue'
import { projectApi } from '../api/projects'
import type { CompanyProfile, ParsedDocument, Project, ProjectFile, RawMaterial } from '../types'
import ProjectStructuredDataView from './ProjectStructuredDataView.vue'
import DocumentWritingView from './DocumentWritingView.vue'

const route = useRoute()
const router = useRouter()
const projectId = Number(route.params.id)

const loading = ref(false)
const saving = ref(false)
const savingProfile = ref(false)
const uploading = ref(false)
const activeTab = ref(String(route.query.tab || 'info'))

const project = ref<Project | null>(null)
const form = reactive({ name: '', project_type: 'other', company_name: '', status: 'draft', description: '' })

const profileForm = reactive<CompanyProfile>({
  id: 0,
  project_id: projectId,
  company_name: '',
  credit_code: '',
  legal_representative: '',
  contact_name: '',
  contact_phone: '',
  project_address: '',
  industry_category: '',
  land_area: '',
  building_area: '',
  products: '',
  annual_output: '',
  production_process: '',
  equipment: null,
  raw_materials: [],
  pollution_control: null,
  risk_substances: null,
  created_at: '',
  updated_at: '',
})

const files = ref<ProjectFile[]>([])
const pendingFiles = ref<UploadFile[]>([])
const fileList = ref<UploadFile[]>([])
const parsingFileId = ref<number | null>(null)
const parsedDialogVisible = ref(false)
const selectedParsed = ref<ParsedDocument | null>(null)
const selectedParsedFile = ref<ProjectFile | null>(null)

const projectNavigation = computed(() => [
  { key: 'info', label: '概览', icon: markRaw(Document) },
  { key: 'profile', label: '企业信息', icon: markRaw(OfficeBuilding) },
  { key: 'files', label: '项目资料', icon: markRaw(Files), count: files.value.length },
  { key: 'structured', label: '数据校对', icon: markRaw(DataAnalysis) },
  { key: 'writing', label: '报告', icon: markRaw(Collection) },
])

function projectTypeLabel(type?: string) { return ({ environmental_impact: '环境影响评价', emergency_response: '突发环境事件应急预案', risk_assessment: '环境风险评估', other: '环保咨询报告' } as Record<string, string>)[type || ''] || '环保咨询项目' }
function projectStatusLabel(status?: string) { return ({ draft: '刚刚创建', collecting_data: '正在准备资料', analyzing: '正在确认数据', generating: '正在编制', reviewing: '正在审核', completed: '已完成' } as Record<string, string>)[status || ''] || '进行中' }
function projectStatusType(status?: string) { return status === 'completed' ? 'success' : ['generating', 'analyzing'].includes(status || '') ? 'primary' : 'warning' }

const parseStatusLabels: Record<ProjectFile['parse_status'], string> = {
  uploaded: '未解析',
  parsing: '解析中',
  parsed: '解析成功',
  failed: '解析失败',
}

function parseStatusLabel(status: ProjectFile['parse_status']) {
  return parseStatusLabels[status] || status
}

function parseStatusType(status: ProjectFile['parse_status']) {
  return status === 'parsed' ? 'success' : status === 'failed' ? 'danger' : status === 'parsing' ? 'warning' : 'info'
}

function parseWarningLabel(warning: string) {
  if (warning === 'possible_scanned_pdf') return '该 PDF 可能是扫描版，当前未配置 OCR。'
  if (warning === 'ocr_not_configured') return '图片已读取元数据，但当前未配置 OCR。'
  return warning
}

async function load() {
  loading.value = true
  try {
    const p = await projectApi.get(projectId)
    project.value = p
    Object.assign(form, {
      name: p.name,
      project_type: p.project_type,
      company_name: p.company_name || '',
      status: p.status,
      description: p.description || '',
    })
    await loadProfile()
    await loadFiles()
  } catch (e) {
    ElMessage.error((e as Error).message)
  } finally {
    loading.value = false
  }
}

async function loadProfile() {
  try {
    const profile = await projectApi.getProfile(projectId)
    Object.assign(profileForm, profile)
  } catch {
    // 尚未填写，保持空表单
  }
}

async function loadFiles() {
  files.value = await projectApi.listFiles(projectId)
}

async function onSaveProject() {
  saving.value = true
  try {
    const updated = await projectApi.update(projectId, {
      name: form.name,
      project_type: form.project_type as Project['project_type'],
      company_name: form.company_name || undefined,
      status: form.status as Project['status'],
      description: form.description || undefined,
    })
    project.value = updated
    ElMessage.success('已保存')
  } catch (e) {
    ElMessage.error((e as Error).message)
  } finally {
    saving.value = false
  }
}

function addMaterial() {
  profileForm.raw_materials = profileForm.raw_materials || []
  profileForm.raw_materials.push({
    name: '',
    annual_usage: '',
    unit: 't/a',
    max_storage: '',
    storage_location: '',
    cas_number: '',
  })
}

function removeMaterial(i: number) {
  profileForm.raw_materials?.splice(i, 1)
}

async function onSaveProfile() {
  savingProfile.value = true
  try {
    await projectApi.saveProfile(projectId, { ...profileForm })
    ElMessage.success('企业资料已保存')
    await loadProfile()
  } catch (e) {
    ElMessage.error((e as Error).message)
  } finally {
    savingProfile.value = false
  }
}

function onFileChange(_file: UploadFile, uploadFiles: UploadFiles) {
  pendingFiles.value = uploadFiles
  fileList.value = uploadFiles
}

function onFileRemove(_file: UploadFile, uploadFiles: UploadFiles) {
  pendingFiles.value = uploadFiles
  fileList.value = uploadFiles
}

async function onUpload() {
  if (pendingFiles.value.length === 0) return
  uploading.value = true
  try {
    const rawFiles = pendingFiles.value.flatMap((file) => (file.raw ? [file.raw] : []))
    await projectApi.uploadFiles(projectId, rawFiles)
    pendingFiles.value = []
    fileList.value = []
    await loadFiles()
    ElMessage.success('上传成功')
  } catch (e) {
    ElMessage.error((e as Error).message || '上传失败')
  } finally {
    uploading.value = false
  }
}

async function onDownload(file: ProjectFile) {
  try {
    const blob = await projectApi.downloadFile(projectId, file.id)
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = file.filename
    link.click()
    URL.revokeObjectURL(url)
  } catch (e) {
    ElMessage.error((e as Error).message || '下载失败')
  }
}

async function onDeleteFile(fileId: number) {
  try {
    await projectApi.removeFile(projectId, fileId)
    await loadFiles()
    ElMessage.success('文件已删除')
  } catch (e) {
    ElMessage.error((e as Error).message || '删除失败')
  }
}

async function onParse(file: ProjectFile) {
  parsingFileId.value = file.id
  try {
    const status = await projectApi.parseFile(projectId, file.id)
    await loadFiles()
    if (status.status === 'parsed') ElMessage.success('文件解析成功')
    else ElMessage.warning(status.error_message || '文件解析失败')
  } catch (e) {
    ElMessage.error((e as Error).message || '解析失败')
  } finally {
    parsingFileId.value = null
  }
}

async function onViewParsed(file: ProjectFile) {
  try {
    selectedParsedFile.value = file
    selectedParsed.value = await projectApi.getParsedDocument(projectId, file.id)
    parsedDialogVisible.value = true
  } catch (e) {
    ElMessage.error((e as Error).message || '读取解析结果失败')
  }
}

function formatStructuredContent(content: Record<string, unknown> | null) {
  return content ? JSON.stringify(content, null, 2) : '暂无结构化数据'
}

onMounted(load)
</script>

<style scoped>
.project-page{padding-top:22px}.back-link{display:flex;align-items:center;gap:6px;margin-bottom:21px;padding:0;border:0;background:transparent;color:#6e6e73;cursor:pointer;font-size:12px}.back-link:hover{color:#0071e3}.project-hero{display:flex;align-items:center;justify-content:space-between;gap:24px;margin-bottom:24px}.project-title-wrap{display:flex;align-items:center;gap:16px}.project-badge{width:56px;height:56px;display:grid;place-items:center;border-radius:17px;color:#0071e3;background:linear-gradient(145deg,#eef7ff,#dceeff);font-size:25px;box-shadow:inset 0 0 0 1px rgba(0,113,227,.08)}.project-meta{display:flex;align-items:center;gap:8px;color:#86868b;font-size:10px;font-weight:600}.project-meta i{width:3px;height:3px;border-radius:50%;background:#c7c7cc}.project-hero h1{margin:5px 0 4px;font-size:28px;line-height:1.2;letter-spacing:-.035em}.project-hero p{margin:0;color:#6e6e73;font-size:13px}.hero-actions{display:flex;align-items:center;gap:12px}.workflow-rail{display:grid;grid-template-columns:repeat(4,1fr);padding:17px 18px;margin-bottom:16px}.workflow-step{position:relative;display:flex;align-items:center;gap:10px;padding:7px 13px;border:0;border-radius:14px;background:transparent;text-align:left;cursor:pointer}.workflow-step:hover,.workflow-step.active{background:#f1f7fd}.step-dot{position:relative;z-index:2;flex:0 0 29px;width:29px;height:29px;display:grid;place-items:center;border-radius:50%;color:#6e6e73;background:#eeeef0;font-size:10px;font-weight:700}.workflow-step.active .step-dot{color:white;background:#0071e3;box-shadow:0 5px 12px rgba(0,113,227,.2)}.workflow-step.done .step-dot{color:white;background:#34c759}.step-copy strong,.step-copy small{display:block}.step-copy strong{color:#1d1d1f;font-size:12px}.step-copy small{margin-top:3px;color:#86868b;font-size:9px}.step-line{position:absolute;top:21px;right:-10px;width:20px;height:1px;background:#d2d2d7}.tabs{margin-top:4px}.project-tabs:deep(>.el-tabs__header){position:static;z-index:8;padding:0 8px;margin-bottom:18px!important;border:1px solid rgba(0,0,0,.06);border-radius:16px;background:rgba(255,255,255,.87);box-shadow:0 8px 28px rgba(0,0,0,.04);backdrop-filter:blur(20px)}.project-tabs:deep(>.el-tabs__header .el-tabs__nav-wrap::after){display:none}.project-tabs:deep(>.el-tabs__header .el-tabs__item){height:52px!important}.project-tabs:deep(>.el-tabs__content>.el-tab-pane>.el-card){border:none}

.material-row {
  display: flex;
  gap: 8px;
  margin-bottom: 8px;
  align-items: center;
}

.material-row .el-input {
  width: 16%;
}

.parsed-text {
  max-height: 480px;
  overflow: auto;
  white-space: pre-wrap;
  word-break: break-word;
  background: #f7f8fa;
  padding: 16px;
  border-radius: 14px;
}
@media(max-width:1000px){.workflow-rail{grid-template-columns:1fr 1fr;gap:5px}.step-line{display:none}.project-hero{align-items:flex-start;flex-direction:column}.hero-actions{width:100%;justify-content:space-between}}@media(max-width:650px){.workflow-rail{grid-template-columns:1fr}.project-badge{display:none}.project-title-wrap{align-items:flex-start}.material-row{align-items:stretch;flex-direction:column}.material-row .el-input{width:100%}}
</style>
<style scoped>
.project-nav {
  position: static;
  z-index: 8;
  display: flex;
  gap: 4px;
  width: fit-content;
  max-width: 100%;
  margin-bottom: 22px;
  padding: 5px;
  border-radius: 15px;
  overflow-x: auto;
}
.project-nav button {
  min-width: 104px;
  height: 42px;
  padding: 0 14px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 7px;
  color: #6e6e73;
  border: 0;
  border-radius: 11px;
  background: transparent;
  cursor: pointer;
  font-size: 12px;
  font-weight: 600;
  white-space: nowrap;
  outline: none;
}
.project-nav button:hover { color: #1d1d1f; background: #f2f2f4; }
.project-nav button.active { color: #1d1d1f; background: #fff; box-shadow: 0 2px 9px rgba(0,0,0,.1); }
.project-nav button:focus-visible { box-shadow: 0 0 0 3px rgba(0,113,227,.18); }
.project-nav button small { min-width: 18px; height: 18px; padding: 0 5px; display: grid; place-items: center; border-radius: 9px; background: #ededf0; font-size: 9px; }
.workspace-content { min-height: 620px; }
.report-mode { width: 100%; max-width: 1680px; min-height: calc(100vh - 64px); height: auto; padding-top: 12px; padding-bottom: 32px; display: block; overflow: visible; }
.report-mode .back-link,
.report-mode .project-hero { display: none; }
.report-mode .project-badge { width: 42px; height: 42px; border-radius: 13px; font-size: 19px; }
.report-mode .project-hero h1 { margin-top: 2px; font-size: 21px; }
.report-mode .project-hero p { font-size: 10px; }
.report-mode .hero-actions { display: none; }
.report-mode .project-nav { width: 100%; margin-bottom: 10px; }
.report-mode .workspace-content { min-height: 0; display: block; overflow: visible; }
.report-mode .writing-section { width: 100%; min-height: 0; display: block !important; overflow: visible; }
.workspace-section { animation: section-enter .22s ease; }
@keyframes section-enter { from { opacity: 0; transform: translateY(4px); } to { opacity: 1; transform: none; } }
.workspace-heading { display: flex; align-items: flex-end; justify-content: space-between; gap: 20px; margin: 0 2px 17px; }
.workspace-heading h2, .panel-heading h2 { margin: 0; font-size: 25px; letter-spacing: -.035em; }
.workspace-heading p, .panel-heading p { margin: 5px 0 0; color: #86868b; font-size: 11px; }
.content-panel { padding: 26px; overflow: hidden; }
.panel-heading { grid-column: 1 / -1; padding-bottom: 19px; border-bottom: 1px solid rgba(0,0,0,.07); }
.info-panel { display: grid; grid-template-columns: minmax(0, 1.35fr) minmax(300px, .65fr); gap: 28px; align-items: start; }
.info-panel > :deep(.el-form) { max-width: none !important; }
.info-panel > :deep(.el-descriptions) { margin-top: 0; }
.info-panel :deep(.el-descriptions__title) { margin-bottom: 14px; font-size: 13px; }
.profile-panel > :deep(.el-form) { max-width: none !important; display: grid; grid-template-columns: 1fr 1fr; column-gap: 22px; }
.profile-panel :deep(.el-divider), .profile-panel .material-row, .profile-panel > :deep(.el-form > .el-button) { grid-column: 1 / -1; }
.profile-panel :deep(.el-divider__text) { padding: 0 12px 0 0; background: #fff; font-size: 13px; font-weight: 700; }
.profile-panel :deep(.el-form-item__label) { width: 100% !important; justify-content: flex-start; margin-bottom: 6px; color: #6e6e73 !important; font-size: 10px; }
.profile-panel :deep(.el-form-item) { display: block; margin-bottom: 20px; }
.material-row { padding: 12px; border: 1px solid rgba(0,0,0,.07); border-radius: 14px; background: #fafafa; }
.files-panel :deep(.el-upload) { width: 100%; }
.files-panel :deep(.el-upload-dragger) { width: 100%; min-height: 170px; padding: 34px; border: 1px dashed #b8c1cc; border-radius: 17px; background: #fafbfc; }
.files-panel :deep(.el-upload-dragger:hover) { border-color: #0071e3; background: #f5f9ff; }
.upload-icon { margin-bottom: 11px; color: #0071e3; font-size: 29px; }
.upload-title { color: #1d1d1f; font-size: 13px; font-weight: 650; }
.upload-copy { margin-top: 6px; color: #86868b; font-size: 10px; }
.files-panel :deep(.el-table) { margin-top: 24px !important; }
@media (max-width: 900px) {
  .project-nav { width: 100%; }
  .project-nav button { min-width: 92px; flex: 1; }
  .info-panel { grid-template-columns: 1fr; }
  .profile-panel > :deep(.el-form) { grid-template-columns: 1fr; }
  .profile-panel :deep(.el-divider), .profile-panel .material-row { grid-column: 1; }
}
</style>
