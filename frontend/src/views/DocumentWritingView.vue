<template>
  <div class="writing-page">
    <header v-if="!instance" class="studio-header">
      <div><h2>报告编制</h2></div>
      <div v-if="instance" class="header-progress"><div><span>整体进度</span><strong>{{ completionPercent }}%</strong></div><el-progress :percentage="completionPercent" :show-text="false" :stroke-width="6" /></div>
    </header>

    <section v-if="!instance" class="start-studio surface">
      <div class="start-visual"><div class="document-stack"><span></span><span></span><span><el-icon><Document /></el-icon></span></div></div>
      <div class="start-copy"><h3>新建报告</h3><p>选择成果类型后即可查看完整目录、编制正文和管理导出版本。</p><el-select v-model="templateId" size="large" placeholder="报告类型"><el-option v-for="item in templates" :key="item.id" :label="`${item.name} · ${item.version}`" :value="item.id" /></el-select><el-button type="primary" size="large" :disabled="!templateId" @click="createInstance">创建报告<el-icon><ArrowRight /></el-icon></el-button><small><el-icon><CircleCheck /></el-icon>默认使用专业 Word 版式</small></div>
    </section>

    <template v-if="instance && template && overview">
      <section class="document-bar surface">
        <div class="document-name"><span class="doc-icon"><el-icon><Document /></el-icon></span><div><strong>{{ instance.title }}</strong></div></div>
        <div class="document-progress"><span>完成度</span><el-progress :percentage="completionPercent" :show-text="false" :stroke-width="5" /><strong>{{ completionPercent }}%</strong></div>
        <div class="document-actions"><el-tag :type="instanceStatusType(overview.instance.status)">{{ instanceStatusLabel(overview.instance.status) }}</el-tag><el-button @click="refreshOverview"><el-icon><Refresh /></el-icon>刷新资料</el-button><el-button type="primary" :disabled="!overview.summary.ready_sections" :loading="batching" @click="batchGenerateAll"><el-icon><EditPen /></el-icon>生成可编制章节</el-button></div>
      </section>

      <section class="studio-grid">
        <aside class="chapters-pane surface">
          <div class="pane-head"><div><h3>报告章节</h3></div><span>{{ overview.summary.completed_sections }}/{{ overview.summary.total_sections }}</span></div>
          <div class="chapter-filter"><small>{{ overview.summary.ready_sections }} 个可生成</small></div>
          <div class="chapter-list">
            <button v-for="snapshot in overview.sections" :key="snapshot.id" class="chapter" :class="{ active: selectedSection?.id === snapshot.id }" @click="selectSection(snapshot)">
              <span class="chapter-code">{{ snapshot.section_code }}</span><span class="chapter-copy"><strong>{{ snapshot.title }}</strong><small>{{ sectionStatusLabel(snapshot.status) }}</small></span><span class="state-dot" :class="snapshot.status"></span>
            </button>
          </div>
          <div class="quality-actions"><button @click="validate"><el-icon><Connection /></el-icon><span><strong>一致性检查</strong><small>检查前后数据是否一致</small></span></button><button :disabled="reviewing" @click="runQualityReview"><el-icon><CircleCheck /></el-icon><span><strong>专业质量审查</strong><small>检查内容完整性和风险</small></span></button></div>
        </aside>

        <main class="editor-pane surface" v-loading="loading">
          <template v-if="selectedSection">
            <header class="editor-head"><div><span>章节 {{ selectedSection.section_code }}</span><h3>{{ selectedSection.title }}</h3></div><div class="editor-actions"><el-button @click="check">资料状态</el-button><el-button type="primary" :loading="generating" :disabled="!preflight?.ready || selectedSection.status === 'locked'" @click="generate"><el-icon><EditPen /></el-icon>{{ draft ? '重新生成' : '生成初稿' }}</el-button></div></header>
            <div v-if="preflight" class="readiness-strip" :class="preflight.ready ? 'ready' : 'waiting'"><el-icon><CircleCheck v-if="preflight.ready"/><WarningFilled v-else/></el-icon><div class="readiness-copy"><strong>{{ preflight.ready ? '资料已满足生成条件' : '还需补充资料才能生成' }}</strong><span>企业信息 {{ preflight.project_fact_count }} 条 · 项目资料 {{ preflight.project_source_count }} 份 · 专业依据 {{ preflight.knowledge_source_count }} 条</span></div><el-button v-if="!preflight.ready" class="readiness-action" size="small" @click="openCollectDialog">补充资料</el-button></div>
            <div v-if="draft" class="draft-toolbar"><div><el-tag :type="draftTagType(draft.status)">{{ draftStatusLabel(draft.status) }}</el-tag><span>版本 {{ draft.version }}</span></div><span>专业文稿 · 自动保存</span></div>
            <div v-if="draft" class="paper"><el-input v-model="content" type="textarea" :autosize="{ minRows: 18 }" :disabled="selectedSection.status === 'locked'" /></div>
            <div v-else class="editor-empty"><span><el-icon><Document /></el-icon></span><h3>{{ selectedSection.title }}</h3><p>{{ preflight?.ready ? '资料已齐全，可以开始生成本章初稿。' : '先补充本章所需资料，生成按钮会自动开放。' }}</p><el-button v-if="preflight && !preflight.ready" type="primary" @click="openCollectDialog">补充本章资料</el-button><el-button v-else type="primary" @click="check">查看资料状态</el-button></div>
            <footer v-if="draft" class="review-bar"><el-button v-if="selectedSection.status !== 'locked'" @click="saveDraft">保存修改</el-button><div class="review-actions"><el-button v-if="!['locked','approved'].includes(selectedSection.status)" type="warning" @click="review('revision_required')">标记需修改</el-button><el-button v-if="!['locked','approved'].includes(selectedSection.status)" type="success" @click="review('approved')">审核通过</el-button><el-button v-if="selectedSection.status === 'approved'" @click="lock">锁定章节</el-button><el-button v-if="selectedSection.status === 'locked'" @click="unlock">解锁编辑</el-button></div></footer>
          </template>
          <div v-else class="editor-empty"><span><el-icon><Document /></el-icon></span><h3>未选择章节</h3></div>
        </main>

        <aside class="inspector-pane">
          <nav class="inspector-nav"><button :class="{ active: inspectorTab === 'sources' }" @click="inspectorTab = 'sources'">资料</button><button :class="{ active: inspectorTab === 'export' }" @click="inspectorTab = 'export'">导出</button><button :class="{ active: inspectorTab === 'issues' }" @click="inspectorTab = 'issues'">问题<span v-if="issueCount">{{ issueCount }}</span></button></nav>
          <section v-show="inspectorTab === 'sources'" class="inspector-card surface"><div class="inspector-title"><span><el-icon><DataAnalysis /></el-icon></span><div><strong>本章资料</strong></div></div><template v-if="preflight"><div class="source-stat"><span>企业确认信息</span><strong>{{ preflight.project_fact_count }} 条</strong></div><div class="source-stat"><span>已解析项目资料</span><strong>{{ preflight.project_source_count }} 份</strong></div><div class="source-stat"><span>可引用专业依据</span><strong>{{ preflight.knowledge_source_count }} 条</strong></div><div v-if="preflight.missing_fields.length" class="notice warning"><strong>还需补充</strong><span v-for="item in preflight.missing_fields" :key="item.field">{{ missingFieldLabel(item.field) }}：{{ item.reason }}</span><el-button size="small" @click="openCollectDialog">现在补充</el-button></div><div v-if="preflight.conflicts.length" class="notice danger"><strong>信息需要确认</strong><span v-for="item in preflight.conflicts" :key="item">{{ conflictLabel(item) }}</span></div></template><p v-else class="inspector-empty">资料状态尚未载入</p></section>
          <section v-if="draft && inspectorTab === 'sources'" class="inspector-card surface"><div class="inspector-title"><span><el-icon><Link /></el-icon></span><div><strong>引用与提示</strong></div></div><div v-if="draft.citations.length" class="citations"><div v-for="citation in draft.citations" :key="citation.source_id"><el-tag size="small">{{ sourceTypeLabel(citation.source_id) }}</el-tag><p>{{ citation.claim }}</p></div></div><p v-else class="inspector-empty">本章节暂未引用外部资料。</p><div v-for="warning in draft.warnings" :key="warning" class="notice warning"><span>{{ warning }}</span></div></section>
          <section v-show="inspectorTab === 'export'" class="inspector-card export-card surface"><div class="inspector-title"><span><el-icon><Download /></el-icon></span><div><strong>报告导出</strong></div></div><p>未选择自有模板时使用默认版式。</p><el-select v-model="reportTemplateId" clearable placeholder="默认专业版式"><el-option v-for="item in reportTemplates" :key="item.id" :label="`${item.name} · ${item.version}`" :value="item.id" /></el-select><div v-if="exportState" class="export-state" :class="exportState.ready ? 'ready' : 'waiting'"><strong>{{ exportState.ready ? '可以导出正式版本' : '暂时不能正式导出' }}</strong><span>{{ exportState.ready ? (exportState.selected_template || '系统默认版式') : exportState.blocking_issues.map(humanizeIssue).join('；') }}</span></div><el-button class="wide" @click="checkExport">检查导出条件</el-button><el-button class="wide" type="primary" :disabled="!exportState?.ready" :loading="exporting" @click="exportReport">生成并下载报告</el-button><div v-for="artifact in artifacts" :key="artifact.id" class="download-item"><a :href="`/api/v1/export-artifacts/${artifact.id}/download`" target="_blank">下载 {{ artifact.format.toUpperCase() }}</a><span>{{ Math.ceil(artifact.file_size / 1024) }} KB</span></div></section>
          <section v-show="inspectorTab === 'issues'" class="inspector-card surface"><div class="inspector-title"><span class="danger-icon"><el-icon><WarningFilled /></el-icon></span><div><strong>待处理问题</strong><small>{{ issueCount }} 项</small></div></div><template v-if="issueCount"><div class="issue" v-for="issue in reviewIssues" :key="`r${issue.id}`">{{ humanizeIssue(`${issue.title}：${issue.description}`) }}</div><div class="issue" v-for="issue in issues" :key="issue.id">{{ humanizeIssue(issue.message) }}</div><div class="issue" v-for="reason in readiness?.blocking_reasons || []" :key="reason">{{ humanizeIssue(reason) }}</div></template><p v-else class="inspector-empty">当前没有待处理问题</p></section>
        </aside>
      </section>
    </template>
    <el-dialog v-model="collectDialog" title="补充本章资料" width="650px" class="collect-dialog">
      <div class="collect-intro">当前章节需要：<strong>{{ missingItems.map((item) => missingFieldLabel(item.field)).join('、') }}</strong></div>
      <el-tabs v-model="collectTab">
        <el-tab-pane v-if="manualFields.length" label="直接填写" name="manual">
          <el-form label-position="top" class="collect-form">
            <el-form-item v-for="field in manualFields" :key="field" :label="missingFieldLabel(field)">
              <el-input v-model="collectForm[field]" :type="field === 'production_process' ? 'textarea' : 'text'" :rows="field === 'production_process' ? 4 : undefined" :placeholder="manualFieldPlaceholder(field)" />
            </el-form-item>
          </el-form>
        </el-tab-pane>
        <el-tab-pane label="上传资料" name="upload">
          <div v-if="needsKnowledgeSource" class="collect-field"><label>专业资料库</label><el-select v-model="selectedKnowledgeBaseId" placeholder="选择要存放的知识库"><el-option v-for="base in knowledgeBases" :key="base.id" :label="base.name" :value="base.id" /></el-select></div>
          <el-upload class="collect-upload" drag :auto-upload="false" :limit="5" multiple :file-list="collectFiles" :on-change="onCollectFileChange" :on-remove="onCollectFileRemove" accept=".pdf,.doc,.docx,.xls,.xlsx,.png,.jpg,.jpeg,.txt">
            <el-icon class="el-icon--upload"><UploadFilled /></el-icon><div class="el-upload__text">拖入文件，或<em>点击选择</em></div><div class="el-upload__tip">上传后会自动解析；专业法规、标准请放入知识库，项目说明放入项目资料。</div>
          </el-upload>
        </el-tab-pane>
      </el-tabs>
      <template #footer><el-button @click="collectDialog = false">取消</el-button><el-button type="primary" :loading="collecting" @click="saveCollectedData">保存并刷新本章</el-button></template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, type UploadFile, type UploadFiles } from 'element-plus'
import { ArrowRight, CircleCheck, Connection, DataAnalysis, Document, Download, EditPen, Link, Refresh, UploadFilled, WarningFilled } from '@element-plus/icons-vue'
import { createDocumentInstance, generateSection, getSection, listDocumentInstances, listDocumentTemplates, preflightSection, updateDraft } from '../api/generation'
import { batchGenerate, getDocumentOverview, getReadiness, listValidationIssues, lockSection, reviewSection, unlockSection, validateDocument } from '../api/workflow'
import { getQualityGate, listReviewIssues, startProfessionalReview } from '../api/review'
import { createReportSnapshot, exportPreflight, listExportArtifacts, listReportSnapshots, listReportTemplates, startReportExport } from '../api/exports'
import { listKnowledgeBases, processKnowledgeDocument, uploadKnowledgeDocument } from '../api/knowledge'
import { projectApi } from '../api/projects'
import type { DocumentTemplate, DocumentInstance, SectionDraft, SectionPreflight, SectionInstance, DocumentOverview, ValidationIssue, Readiness, ReviewIssue, QualityGate, ExportArtifact, ExportPreflight, ReportSnapshot, ReportTemplate, KnowledgeBase } from '../types'

const props = defineProps<{ projectId: number }>()
const templates = ref<DocumentTemplate[]>([]); const templateId = ref<number>(); const template = ref<DocumentTemplate | null>(null); const instance = ref<DocumentInstance | null>(null); const overview = ref<DocumentOverview | null>(null); const selectedSection = ref<SectionInstance | null>(null); const preflight = ref<SectionPreflight | null>(null); const draft = ref<SectionDraft | null>(null); const content = ref(''); const loading = ref(false); const generating = ref(false); const batching = ref(false); const reviewing = ref(false); const exporting = ref(false); const issues = ref<ValidationIssue[]>([]); const reviewIssues = ref<ReviewIssue[]>([]); const qualityGate = ref<QualityGate | null>(null); const readiness = ref<Readiness | null>(null); const reportTemplates = ref<ReportTemplate[]>([]); const reportTemplateId = ref<number>(); const exportState = ref<ExportPreflight | null>(null); const reportSnapshots = ref<ReportSnapshot[]>([]); const artifacts = ref<ExportArtifact[]>([])
const completionPercent = computed(() => overview.value?.summary.total_sections ? Math.round((overview.value.summary.completed_sections / overview.value.summary.total_sections) * 100) : 0)
const inspectorTab = ref<'sources' | 'export' | 'issues'>('sources')
const issueCount = computed(() => issues.value.length + reviewIssues.value.length + (readiness.value?.blocking_reasons.length || 0))
const collectDialog = ref(false)
const collectTab = ref<'manual' | 'upload'>('manual')
const collecting = ref(false)
const collectFiles = ref<UploadFile[]>([])
const collectForm = reactive<Record<string, string>>({})
const knowledgeBases = ref<KnowledgeBase[]>([])
const selectedKnowledgeBaseId = ref<number>()
const manualFieldKeys = new Set(['company_name', 'project_address', 'industry_category', 'land_area', 'building_area', 'products', 'annual_output', 'production_process'])
const missingItems = computed(() => preflight.value?.missing_fields || [])
const manualFields = computed(() => missingItems.value.map((item) => item.field).filter((field) => manualFieldKeys.has(field)))
const needsKnowledgeSource = computed(() => missingItems.value.some((item) => item.field === 'knowledge_sources'))
async function refreshOverview() { if (!instance.value) return; overview.value = await getDocumentOverview(instance.value.id); readiness.value = await getReadiness(instance.value.id); if (!selectedSection.value && overview.value.sections[0]) await selectSection(overview.value.sections[0]); else if (selectedSection.value) { const current = overview.value.sections.find((item) => item.id === selectedSection.value?.id); if (current) selectedSection.value = current } }
async function createInstance() { if (!templateId.value) return; instance.value = await createDocumentInstance(props.projectId, { template_id: templateId.value }); template.value = templates.value.find((item) => item.id === templateId.value) || null; const matching = reportTemplates.value.find((item) => item.document_type === template.value?.document_type); reportTemplateId.value = matching?.id; exportState.value = null; await refreshOverview(); if (overview.value?.sections[0]) await selectSection(overview.value.sections[0]); ElMessage.success('报告工作区已创建，从第一章开始编制吧') }
function cleanDraft(value: SectionDraft | null) { return value ? { ...value, warnings: value.warnings.map(humanizeIssue) } : null }
async function selectSection(snapshot: SectionInstance) { selectedSection.value = snapshot; preflight.value = null; draft.value = null; const templateSection = template.value?.sections.find((item) => item.id === snapshot.template_section_id); if (instance.value && templateSection) { const [view, state] = await Promise.all([getSection(instance.value.id, templateSection.id), preflightSection(instance.value.id, templateSection.id)]); draft.value = cleanDraft(view.draft); content.value = view.draft?.content || ''; preflight.value = state } }
async function check() { if (!instance.value || !selectedSection.value) return; loading.value = true; try { preflight.value = await preflightSection(instance.value.id, selectedSection.value.template_section_id) } finally { loading.value = false } }
function manualFieldPlaceholder(field: string) {
  return ({ company_name: '例如：江苏清源新材料有限公司', project_address: '例如：江苏省苏州市工业园区', industry_category: '例如：化学原料和化学制品制造业', land_area: '例如：12000 m²', building_area: '例如：8600 m²', products: '例如：水性丙烯酸树脂、水性聚氨酯树脂', annual_output: '例如：20000 t/a', production_process: '简要描述主要生产工艺和污染环节' } as Record<string, string>)[field] || '请填写已确认的信息'
}
async function openCollectDialog() {
  if (!preflight.value) await check()
  collectFiles.value = []
  Object.keys(collectForm).forEach((key) => delete collectForm[key])
  if (manualFields.value.length) {
    try {
      const profile = await projectApi.getProfile(props.projectId)
      for (const field of manualFields.value) collectForm[field] = String((profile as unknown as Record<string, unknown>)[field] || '')
    } catch {
      // 新项目还没有企业资料时，保留空白表单即可。
    }
  }
  if (needsKnowledgeSource.value && !knowledgeBases.value.length) {
    try { knowledgeBases.value = await listKnowledgeBases(); selectedKnowledgeBaseId.value = knowledgeBases.value[0]?.id } catch { /* 保存时再提示 */ }
  }
  collectTab.value = manualFields.value.length ? 'manual' : 'upload'
  collectDialog.value = true
}
function onCollectFileChange(_file: UploadFile, files: UploadFiles) { collectFiles.value = files }
function onCollectFileRemove(_file: UploadFile, files: UploadFiles) { collectFiles.value = files }
async function saveCollectedData() {
  const rawFiles = collectFiles.value.flatMap((item) => (item.raw ? [item.raw] : []))
  const hasManualValues = collectTab.value === 'manual' && manualFields.value.some((field) => collectForm[field]?.trim())
  if (!hasManualValues && !rawFiles.length) return ElMessage.warning('请填写缺少的信息或选择要上传的文件')
  collecting.value = true
  try {
    if (collectTab.value === 'manual' && manualFields.value.length) {
      const payload = Object.fromEntries(manualFields.value.filter((field) => collectForm[field]?.trim()).map((field) => [field, collectForm[field].trim()]))
      if (Object.keys(payload).length) await projectApi.saveProfile(props.projectId, payload)
    }
    if (rawFiles.length) {
      if (needsKnowledgeSource.value) {
        if (!selectedKnowledgeBaseId.value) throw new Error('请先选择专业资料库')
        for (const file of rawFiles) {
          const document = await uploadKnowledgeDocument(selectedKnowledgeBaseId.value, file, { title: file.name.replace(/\.[^.]+$/, ''), document_type: 'technical_guideline', status: 'active', category_codes: [] })
          await processKnowledgeDocument(document.id)
        }
      } else {
        const uploaded = await projectApi.uploadFiles(props.projectId, rawFiles)
        for (const file of uploaded) await projectApi.parseFile(props.projectId, file.id)
      }
    }
    collectDialog.value = false
    await refreshOverview()
    if (selectedSection.value) {
      const current = overview.value?.sections.find((item) => item.id === selectedSection.value?.id)
      if (current) await selectSection(current)
    }
    ElMessage.success('资料已保存，本章状态已刷新')
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '资料保存失败')
  } finally { collecting.value = false }
}
async function generate() { if (!instance.value || !selectedSection.value) return; generating.value = true; try { const run = await generateSection(instance.value.id, selectedSection.value.template_section_id); ElMessage[run.status === 'blocked' ? 'warning' : 'success'](run.status === 'blocked' ? '还缺少必要资料，请先按右侧提示补充' : '章节初稿已生成'); const view = await getSection(instance.value.id, selectedSection.value.template_section_id); draft.value = cleanDraft(view.draft); content.value = view.draft?.content || ''; await refreshOverview() } catch (error) { ElMessage.error(error instanceof Error ? error.message : '生成失败') } finally { generating.value = false } }
async function saveDraft() { if (!draft.value) return; draft.value = cleanDraft(await updateDraft(draft.value.id, content.value)); ElMessage.success('修改已保存为新版本'); await refreshOverview() }
async function batchGenerateAll() { if (!instance.value) return; batching.value = true; try { const run = await batchGenerate(instance.value.id); ElMessage.success(`已完成 ${run.completed_sections}/${run.total_sections} 个章节`); await refreshOverview(); if (selectedSection.value) await selectSection(overview.value?.sections.find((item) => item.id === selectedSection.value?.id) || selectedSection.value) } catch (error) { ElMessage.error(error instanceof Error ? error.message : '批量生成失败') } finally { batching.value = false } }
async function validate() { if (!instance.value) return; await validateDocument(instance.value.id); issues.value = await listValidationIssues(instance.value.id); readiness.value = await getReadiness(instance.value.id); ElMessage.success('一致性检查完成') }
async function runQualityReview() { if (!instance.value) return; reviewing.value = true; try { const run = await startProfessionalReview(instance.value.id); reviewIssues.value = await listReviewIssues(instance.value.id); qualityGate.value = await getQualityGate(instance.value.id); ElMessage.success(`质量审查完成，发现 ${run.issues_count} 个待关注项`) } catch (error) { ElMessage.error(error instanceof Error ? error.message : '质量审查失败') } finally { reviewing.value = false } }
async function loadExportHistory() { if (!instance.value) return; reportSnapshots.value = await listReportSnapshots(instance.value.id) }
async function checkExport() { if (!instance.value) return; try { exportState.value = await exportPreflight(instance.value.id, reportTemplateId.value); reportTemplateId.value = exportState.value.selected_template_id || reportTemplateId.value; reportTemplates.value = await listReportTemplates(); await loadExportHistory() } catch (error) { ElMessage.error(error instanceof Error ? error.message : '导出检查失败') } }
async function exportReport() { if (!instance.value) return; exporting.value = true; try { const snapshot = await createReportSnapshot(instance.value.id); const job = await startReportExport(snapshot.id, reportTemplateId.value); artifacts.value = await listExportArtifacts(job.id); await loadExportHistory(); ElMessage.success(job.status === 'completed' ? 'Word 和 PDF 已生成，请在下方下载' : 'Word 已生成，PDF 暂未完成') } catch (error) { ElMessage.error(error instanceof Error ? error.message : '导出失败') } finally { exporting.value = false } }
async function review(status: string) {
  if (!selectedSection.value) return
  const sectionId = selectedSection.value.id
  await reviewSection(sectionId, status)
  ElMessage.success(status === 'approved' ? '章节已审核通过' : '章节已标记为需要修改')
  await refreshOverview()
  // 审核接口会同步更新草稿状态；重新读取当前章节，避免列表已经显示
  // “审核通过”，编辑器仍停留在旧的“等待复核”标签。
  const current = overview.value?.sections.find((item) => item.id === sectionId)
  if (current) await selectSection(current)
}
async function lock() { if (!selectedSection.value) return; await lockSection(selectedSection.value.id); await refreshOverview(); ElMessage.success('章节已锁定') }
async function unlock() { if (!selectedSection.value) return; await unlockSection(selectedSection.value.id); await refreshOverview(); ElMessage.success('章节已解锁') }
function sectionStatusLabel(status: string) { return ({ ready: '等待生成', generating: '正在生成', generated: '等待审核', approved: '审核通过', locked: '已锁定', blocked: '资料不足', warning: '建议补充资料', revision_required: '需要修改', stale: '资料变化，建议更新' } as Record<string, string>)[status] || '进行中' }
function instanceStatusLabel(status: string) { return ({ draft: '刚创建', collecting_data: '正在准备资料', ready_for_generation: '可以开始生成', generating: '正在生成', in_review: '正在审核', revision_required: '需要修改', ready_for_export: '可以导出', completed: '已完成', archived: '已归档' } as Record<string, string>)[status] || '处理中' }
function instanceStatusType(status: string) { return ['ready_for_export', 'completed'].includes(status) ? 'success' : ['revision_required', 'archived'].includes(status) ? 'warning' : 'primary' }
function draftStatusLabel(status: string) { return ({ draft: '草稿', generated: '初稿，等待审核', reviewed: '已保存，等待复核', approved: '审核通过', rejected: '已退回修改', partial: '部分完成', blocked: '资料不足' } as Record<string, string>)[status] || '处理中' }
function draftTagType(status: string) { return ['generated', 'approved'].includes(status) ? 'success' : ['blocked', 'rejected'].includes(status) ? 'danger' : 'warning' }
function missingFieldLabel(field: string) { return ({ company_profile: '企业基本资料（企业名称、地址、行业）', company_name: '企业名称', project_address: '项目地址', industry_category: '行业类别', production_process: '生产工艺和污染环节', knowledge_sources: '专业依据（法规、标准或技术导则）', project_sources: '项目资料（上传并处理相关文件）', products: '产品和产能信息', raw_material: '原辅材料及用量', production_equipment: '生产设备及数量', environmental_facility: '环保设施及处理能力' } as Record<string, string>)[field] || field.replaceAll('_', ' ') }
function conflictLabel(value: string) { return value.split('.').map((part) => missingFieldLabel(part)).join(' · ') }
function sourceTypeLabel(sourceId: string) { return sourceId.startsWith('K') ? '专业知识库' : sourceId.startsWith('F') ? '项目资料' : sourceId.startsWith('P') ? '企业信息' : '参考来源' }
function humanizeIssue(value: string) {
  let text = value || ''
  if (/正文出现未在已确认项目事实中找到的数字|正文中有数字无法对应已确认的项目资料/.test(text)) return '正文中有数字无法对应已确认项目资料，请核对产能、用量、面积等关键数值；电话和标准编号无需处理。'
  text = text.replace(/必填章节\s*([^\s]+)\s*尚未审核通过(?:（[^）]+）)?/g, '章节 $1 还没有审核通过，请打开该章节并点击“审核通过”。')
  text = text.replace(/专业质量门禁未通过：Critical\s*(\d+)，Major\s*(\d+)/gi, (_, critical, major) => `专业质量检查发现 ${critical} 项严重问题、${major} 项重要问题，请打开“问题”逐项处理。`)
  text = text.replace(/章节存在待补充信息/g, '本章节还有资料未补充，请打开“资料”查看具体缺项。')
  text = text.replace(/\s*[（(](reviewing|warning|blocked|ready|generated|approved|locked|revision_required)[）)]/gi, '').replaceAll('reviewing', '待审核').replaceAll('warning', '需关注').replaceAll('blocked', '资料不足')
  return text
}
async function loadExistingInstance() {
  const instances = await listDocumentInstances(props.projectId)
  const latest = instances[0]
  if (!latest) return
  instance.value = latest
  templateId.value = latest.template_id
  template.value = templates.value.find((item) => item.id === latest.template_id) || null
  const matching = reportTemplates.value.find((item) => item.document_type === template.value?.document_type)
  reportTemplateId.value = matching?.id
  await refreshOverview()
  if (overview.value?.sections[0]) await selectSection(overview.value.sections[0])
  await loadExportHistory()
}
onMounted(async () => { try { [templates.value, reportTemplates.value] = await Promise.all([listDocumentTemplates(), listReportTemplates()]); await loadExistingInstance() } catch (error) { ElMessage.error(error instanceof Error ? error.message : '报告加载失败') } })
</script>

<style scoped>
.writing-page{margin-top:8px}.studio-header{display:flex;align-items:flex-end;justify-content:space-between;margin:0 2px 18px}.studio-header h2{margin:5px 0 3px;font-size:25px;letter-spacing:-.03em}.studio-header p{margin:0;color:#6e6e73;font-size:12px}.header-progress{width:210px}.header-progress>div{display:flex;justify-content:space-between;margin-bottom:8px;color:#6e6e73;font-size:11px}.header-progress strong{color:#1d1d1f}.start-studio{min-height:500px;display:grid;grid-template-columns:1fr 1.3fr;align-items:center;gap:45px;padding:50px 8%;overflow:hidden}.start-visual{display:grid;place-items:center}.document-stack{position:relative;width:210px;height:260px}.document-stack span{position:absolute;inset:0;display:grid;place-items:center;border:1px solid rgba(0,0,0,.06);border-radius:24px;background:white;box-shadow:0 20px 55px rgba(0,0,0,.09)}.document-stack span:nth-child(1){transform:rotate(-10deg) translate(-18px,10px);background:#e8f2ff}.document-stack span:nth-child(2){transform:rotate(7deg) translate(19px,8px);background:#f1eaff}.document-stack span:nth-child(3){font-size:50px;color:#0071e3}.start-copy{max-width:530px}.start-copy h3{margin:8px 0 10px;font-size:30px;letter-spacing:-.035em}.start-copy p{margin:0 0 24px;color:#6e6e73;line-height:1.7}.start-copy .el-select{width:100%;margin-bottom:12px}.start-copy .el-button{width:100%}.start-copy>small{display:flex;align-items:center;justify-content:center;gap:5px;margin-top:13px;color:#86868b}.start-steps{grid-column:1/-1;display:grid;grid-template-columns:repeat(4,1fr);padding-top:25px;border-top:1px solid rgba(0,0,0,.07)}.start-steps div{display:flex;align-items:center;gap:8px;justify-content:center}.start-steps span{width:24px;height:24px;display:grid;place-items:center;border-radius:50%;color:#0071e3;background:#e8f2ff;font-size:10px}.start-steps strong{font-size:11px}.document-bar{display:flex;align-items:center;justify-content:space-between;gap:18px;padding:14px 16px;margin-bottom:12px}.document-name{display:flex;align-items:center;gap:11px}.doc-icon{width:38px;height:38px;display:grid;place-items:center;border-radius:12px;color:#0071e3;background:#e8f2ff}.document-name small,.document-name strong{display:block}.document-name small{color:#86868b;font-size:9px}.document-name strong{margin-top:3px;font-size:13px}.document-actions{display:flex;align-items:center;gap:8px}.studio-grid{display:grid;grid-template-columns:250px minmax(460px,1fr) 292px;gap:12px;align-items:start}.chapters-pane,.editor-pane,.inspector-card{border-radius:18px}.chapters-pane{position:sticky;top:134px;max-height:calc(100vh - 155px);overflow:hidden}.pane-head{display:flex;align-items:flex-end;justify-content:space-between;padding:18px 17px 12px}.pane-head h3{margin:3px 0 0;font-size:16px}.pane-head>span{color:#86868b;font-size:11px}.chapter-filter{display:flex;justify-content:space-between;padding:9px 16px;color:#515154;background:#f7f7f8;font-size:10px}.chapter-filter small{color:#86868b}.chapter-list{max-height:calc(100vh - 385px);padding:7px;overflow:auto}.chapter{position:relative;width:100%;min-height:53px;padding:8px;display:flex;align-items:center;gap:8px;border:0;border-radius:12px;background:transparent;text-align:left;cursor:pointer}.chapter:hover{background:#f4f4f6}.chapter.active{background:#eaf4ff}.chapter-code{flex:0 0 27px;width:27px;height:27px;display:grid;place-items:center;border-radius:9px;color:#6e6e73;background:#eeeeef;font-size:9px}.chapter.active .chapter-code{color:#fff;background:#0071e3}.chapter-copy{min-width:0;flex:1}.chapter-copy strong,.chapter-copy small{display:block;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.chapter-copy strong{font-size:11px}.chapter-copy small{margin-top:4px;color:#86868b;font-size:9px}.state-dot{width:6px;height:6px;border-radius:50%;background:#c7c7cc}.state-dot.generated,.state-dot.approved,.state-dot.locked{background:#34c759}.state-dot.ready{background:#ff9f0a}.state-dot.blocked,.state-dot.revision_required{background:#ff453a}.quality-actions{padding:9px;border-top:1px solid rgba(0,0,0,.06)}.quality-actions button{width:100%;padding:9px;display:flex;align-items:center;gap:9px;border:0;border-radius:11px;background:transparent;color:#515154;text-align:left;cursor:pointer}.quality-actions button:hover{background:#f4f4f6}.quality-actions strong,.quality-actions small{display:block}.quality-actions strong{font-size:10px}.quality-actions small{margin-top:2px;color:#86868b;font-size:8px}.editor-pane{min-height:680px;overflow:hidden}.editor-head{min-height:76px;padding:17px 20px;display:flex;align-items:center;justify-content:space-between;gap:15px;border-bottom:1px solid rgba(0,0,0,.07)}.editor-head span{color:#0071e3;font-size:9px;font-weight:700}.editor-head h3{margin:4px 0 0;font-size:18px}.editor-actions{display:flex;gap:7px}.readiness-strip{display:flex;align-items:center;gap:10px;margin:15px 20px 0;padding:12px 14px;border-radius:13px}.readiness-strip.ready{color:#1f8f40;background:#edf9ef}.readiness-strip.waiting{color:#b56800;background:#fff5e5}.readiness-strip strong,.readiness-strip span{display:block}.readiness-strip strong{font-size:11px}.readiness-strip span{margin-top:3px;color:#6e6e73;font-size:9px}.draft-toolbar{display:flex;justify-content:space-between;align-items:center;padding:13px 22px;color:#86868b;font-size:9px}.draft-toolbar>div{display:flex;align-items:center;gap:8px}.paper{margin:0 20px 18px;padding:30px 38px;border:1px solid rgba(0,0,0,.07);border-radius:4px;background:#fff;box-shadow:0 9px 25px rgba(0,0,0,.035)}.paper :deep(.el-textarea__inner){padding:0;background:#fff!important;box-shadow:none!important;color:#262628;font-family:"Songti SC","SimSun",serif;font-size:14px;line-height:2;text-align:justify}.editor-empty{min-height:520px;display:flex;align-items:center;justify-content:center;flex-direction:column;text-align:center}.editor-empty>span{width:60px;height:60px;display:grid;place-items:center;border-radius:20px;color:#0071e3;background:#e8f2ff;font-size:26px}.editor-empty h3{margin:18px 0 7px}.editor-empty p{max-width:330px;margin:0 0 18px;color:#86868b;font-size:12px;line-height:1.6}.review-bar{position:sticky;bottom:0;display:flex;justify-content:space-between;padding:13px 18px;border-top:1px solid rgba(0,0,0,.07);background:rgba(255,255,255,.92);backdrop-filter:blur(20px)}.inspector-pane{display:flex;flex-direction:column;gap:12px}.inspector-card{padding:16px}.inspector-title{display:flex;align-items:center;gap:9px;margin-bottom:15px}.inspector-title>span{width:31px;height:31px;display:grid;place-items:center;border-radius:10px;color:#0071e3;background:#e8f2ff}.inspector-title>span.danger-icon{color:#ff453a;background:#ffefee}.inspector-title strong,.inspector-title small{display:block}.inspector-title strong{font-size:12px}.inspector-title small{margin-top:2px;color:#86868b;font-size:9px}.source-stat{display:flex;justify-content:space-between;padding:8px 0;border-bottom:1px solid rgba(0,0,0,.05);color:#6e6e73;font-size:10px}.source-stat strong{color:#1d1d1f}.notice{margin-top:10px;padding:10px;border-radius:10px;font-size:9px;line-height:1.5}.notice strong,.notice span{display:block}.notice.warning{color:#8b5800;background:#fff5e5}.notice.danger{color:#b42318;background:#fff0ef}.inspector-empty{margin:0;color:#86868b;font-size:10px;line-height:1.55}.citations>div{padding:9px 0;border-top:1px solid rgba(0,0,0,.05)}.citations p{margin:5px 0 0;color:#6e6e73;font-size:9px;line-height:1.5}.export-card>p{margin:-3px 0 12px;color:#6e6e73;font-size:10px;line-height:1.55}.export-card .el-select{width:100%;margin-bottom:8px}.wide{width:100%;margin:7px 0 0!important}.export-state{margin:4px 0 8px;padding:10px;border-radius:10px}.export-state.ready{color:#1f8f40;background:#edf9ef}.export-state.waiting{color:#8b5800;background:#fff5e5}.export-state strong,.export-state span{display:block;font-size:9px}.export-state span{margin-top:4px;line-height:1.45}.download-item{display:flex;justify-content:space-between;padding-top:10px;font-size:10px}.issue{padding:8px 0;border-top:1px solid rgba(0,0,0,.05);color:#b42318;font-size:9px;line-height:1.5}@media(max-width:1250px){.studio-grid{grid-template-columns:225px minmax(420px,1fr)}.inspector-pane{grid-column:1/-1;display:grid;grid-template-columns:repeat(3,1fr)}.inspector-card{min-width:0}}@media(max-width:900px){.studio-grid{grid-template-columns:1fr}.chapters-pane{position:static;max-height:none}.chapter-list{max-height:320px}.inspector-pane{display:grid;grid-template-columns:1fr 1fr}.document-bar,.studio-header{align-items:flex-start;flex-direction:column}.document-actions{flex-wrap:wrap}.start-studio{grid-template-columns:1fr}.start-steps{grid-template-columns:1fr 1fr;gap:12px}.paper{padding:22px}}@media(max-width:600px){.inspector-pane{grid-template-columns:1fr}.start-studio{padding:30px 20px}.editor-head{align-items:flex-start;flex-direction:column}.review-bar{align-items:flex-start;flex-direction:column;gap:8px}}
</style>
<style scoped>
.writing-page { width: 100%; min-height: 0; margin: 0; display: block; overflow: visible; }
.document-bar { flex: none; min-height: 64px; margin-bottom: 10px; padding: 10px 13px; }
.document-progress { width: 190px; display: grid; grid-template-columns: auto 1fr auto; align-items: center; gap: 8px; color: #86868b; font-size: 9px; }
.document-progress .el-progress { width: 100%; }
.document-progress strong { color: #1d1d1f; font-size: 10px; }
.studio-grid { min-height: 0; grid-template-columns: 238px minmax(440px, 1fr) 280px; gap: 10px; align-items: start; overflow: visible; }
.chapters-pane { position: static; height: auto; max-height: none; display: block; overflow: visible; }
.chapter-list { min-height: 0; max-height: none; overflow: visible; }
.chapter-filter { justify-content: flex-end; }
.editor-pane { height: auto; min-height: 680px; overflow: hidden; }
.review-bar { position: static; backdrop-filter: none; }
.inspector-pane { height: auto; gap: 0; border: 1px solid rgba(0,0,0,.065); border-radius: 18px; background: #fff; box-shadow: 0 14px 42px rgba(0,0,0,.055); overflow: hidden; }
.inspector-nav { position: static; display: grid; grid-template-columns: repeat(3, 1fr); gap: 3px; margin: 8px; padding: 3px; border-radius: 10px; background: #ededf0; }
.inspector-nav button { height: 30px; display: flex; align-items: center; justify-content: center; gap: 4px; border: 0; border-radius: 8px; color: #6e6e73; background: transparent; cursor: pointer; font-size: 9px; font-weight: 650; }
.inspector-nav button.active { color: #1d1d1f; background: #fff; box-shadow: 0 1px 5px rgba(0,0,0,.08); }
.inspector-nav button span { min-width: 15px; height: 15px; padding: 0 4px; display: grid; place-items: center; border-radius: 8px; color: #fff; background: #d70015; font-size: 7px; }
.inspector-card { border: 0 !important; border-bottom: 1px solid rgba(0,0,0,.065) !important; border-radius: 0 !important; background: transparent !important; box-shadow: none !important; backdrop-filter: none !important; }
.inspector-card:last-child { border-bottom: 0 !important; }
.editor-empty { min-height: 100%; }
@media (max-width: 1250px) {
  .document-bar { display: grid; grid-template-columns: minmax(150px, 1fr) 130px auto; gap: 10px; }
  .document-progress { width: auto; }
  .document-actions { justify-content: flex-end; }
  .document-actions .el-tag { display: none; }
  .document-actions .el-button { min-height: 34px; padding: 0 12px; font-size: 10px; }
  .studio-grid { grid-template-columns: 180px minmax(300px, 1fr) 210px; }
  .inspector-pane { grid-column: auto; display: block; }
  .pane-head { padding: 14px 12px 10px; }
  .chapter-filter { padding: 8px 11px; }
  .chapter-list { padding: 5px; }
  .chapter { min-height: 48px; padding: 6px; }
  .chapter-code { flex-basis: 24px; width: 24px; height: 24px; }
  .editor-head { min-height: 64px; padding: 12px 14px; }
  .editor-head h3 { font-size: 15px; }
  .editor-actions .el-button { min-height: 34px; padding: 0 11px; font-size: 10px; }
  .readiness-strip { margin: 10px 12px 0; padding: 10px; }
  .paper { margin: 0 12px 12px; padding: 24px 26px; }
  .inspector-card { padding: 13px; }
}
@media (max-width: 720px) {
  .studio-grid { display: block; overflow: visible; }
  .chapters-pane, .editor-pane, .inspector-pane { height: auto; margin-bottom: 10px; overflow: visible; }
  .chapter-list { max-height: 320px; }
}
</style>
<style scoped>
.readiness-strip { align-items: center; }
.readiness-copy { min-width: 0; flex: 1; }
.readiness-action { flex: none; margin-left: auto; color: #8b5800 !important; border-color: rgba(139,88,0,.28) !important; background: rgba(255,255,255,.72) !important; }
.notice.warning .el-button { margin-top: 10px; color: #8b5800; border-color: rgba(139,88,0,.28); background: rgba(255,255,255,.72); }
.chapter-copy strong { font-size: 13px; }
.chapter-copy small { font-size: 11px; }
.chapter-code { font-size: 11px; }
.pane-head h3 { font-size: 19px; }
.pane-head > span, .chapter-filter { font-size: 12px; }
.editor-head h3 { font-size: 22px; }
.editor-head span { font-size: 11px; }
.editor-actions .el-button { font-size: 13px; }
.readiness-strip strong { font-size: 13px; }
.readiness-strip span { font-size: 11px; }
.draft-toolbar { font-size: 11px; }
.editor-empty p { font-size: 14px; }
.inspector-title strong { font-size: 14px; }
.source-stat, .inspector-empty { font-size: 12px; }
.notice { font-size: 11px; }
.collect-intro { margin-bottom: 16px; color: #6e6e73; font-size: 14px; line-height: 1.6; }
.collect-intro strong { color: #1d1d1f; }
.collect-form { display: grid; grid-template-columns: 1fr 1fr; column-gap: 16px; }
.collect-form .el-form-item:last-child { grid-column: 1 / -1; }
.collect-form :deep(.el-form-item__label), .collect-field label { color: #515154; font-size: 13px; font-weight: 650; }
.collect-field { margin-bottom: 18px; }
.collect-field label { display: block; margin-bottom: 8px; }
.collect-field .el-select { width: 100%; }
.collect-upload :deep(.el-upload-dragger) { min-height: 170px; padding: 30px; border-radius: 16px; }
.collect-upload :deep(.el-upload__tip) { color: #86868b; font-size: 12px; line-height: 1.5; }
@media (max-width: 700px) { .collect-form { grid-template-columns: 1fr; }.collect-form .el-form-item:last-child { grid-column: auto; } .readiness-strip { align-items: flex-start; flex-wrap: wrap; } .readiness-action { margin-left: 34px; } }
</style>
