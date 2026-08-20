<template>
  <div class="structured-page" v-loading="loading">
    <div class="structured-toolbar">
      <div>
        <h2>项目数据</h2>
        <span v-if="data?.latest_run">资料整理{{ runStatusLabel(data.latest_run.status) }}</span>
        <span v-if="data?.latest_run" class="run-meta">
          {{ data.latest_run.facts_count }} 项信息 · {{ data.latest_run.conflicts_count }} 项待核对
        </span>
      </div>
      <el-button type="primary" :loading="extracting" @click="startExtraction">从资料更新数据</el-button>
    </div>

    <el-alert
      title="系统会整理已解析资料中的产品、设备和原辅材料；缺失信息保持为空，确认后的数据才会用于报告编制。"
      type="info"
      show-icon
      :closable="false"
      style="margin-bottom: 16px"
    />

    <el-empty v-if="!data || !data.latest_run" description="暂无整理后的项目数据" />
    <template v-else>
      <div class="data-summary">
        <div><span>产品</span><strong>{{ data.products.length }}</strong></div>
        <div><span>生产设备</span><strong>{{ data.equipment.length }}</strong></div>
        <div><span>原辅材料</span><strong>{{ data.raw_materials.length }}</strong></div>
        <div :class="{ attention: reviewFacts.length + openConflicts.length }"><span>待核对</span><strong>{{ reviewFacts.length + openConflicts.length }}</strong></div>
      </div>
      <nav class="data-nav" aria-label="项目数据分类">
        <button v-for="item in dataNavigation" :key="item.key" :class="{ active: activeDataset === item.key }" @click="activeDataset = item.key">{{ item.label }}<span>{{ item.count }}</span></button>
      </nav>

      <section v-show="activeDataset === 'profile'" class="data-panel surface">
        <header><h3>企业基础资料</h3><span>已确认信息</span></header>
        <el-descriptions v-if="data.profile" :column="3" border>
          <el-descriptions-item label="企业名称">{{ data.profile.company_name || '—' }}</el-descriptions-item>
          <el-descriptions-item label="项目地址">{{ data.profile.project_address || '—' }}</el-descriptions-item>
          <el-descriptions-item label="法定代表人">{{ data.profile.legal_representative || '—' }}</el-descriptions-item>
          <el-descriptions-item label="行业">{{ data.profile.industry_category || '—' }}</el-descriptions-item>
        </el-descriptions>
        <el-empty v-else description="没有识别到企业基础资料" :image-size="60" />
      </section>

      <section v-show="activeDataset === 'products'" class="data-panel surface">
        <header><h3>产品与产能</h3><span>{{ data.products.length }} 项</span></header>
        <el-table :data="data.products">
          <el-table-column prop="name" label="名称" />
          <el-table-column label="年产能"><template #default="{ row }">{{ formatValue(row.annual_capacity) }}</template></el-table-column>
          <el-table-column prop="unit" label="单位" />
          <el-table-column prop="verification_status" label="状态" :formatter="verificationFormatter" />
          <el-table-column label="操作" width="150">
            <template #default="{ row }"><el-button link type="primary" @click="openEdit('product', row)">修改</el-button><el-popconfirm title="删除这条产品数据？" @confirm="remove('product', row.id)"><template #reference><el-button link type="danger">删除</el-button></template></el-popconfirm></template>
          </el-table-column>
        </el-table>
        <el-empty v-if="data.products.length === 0" description="暂无产品" :image-size="50" />
      </section>

      <section v-show="activeDataset === 'equipment'" class="data-panel surface">
        <header><h3>生产设备</h3><span>{{ data.equipment.length }} 项</span></header>
        <el-table :data="data.equipment">
          <el-table-column prop="name" label="设备名称" />
          <el-table-column prop="model" label="型号" />
          <el-table-column label="数量"><template #default="{ row }">{{ formatValue(row.quantity) }}</template></el-table-column>
          <el-table-column prop="unit" label="单位" />
          <el-table-column prop="verification_status" label="状态" :formatter="verificationFormatter" />
          <el-table-column label="操作" width="150">
            <template #default="{ row }"><el-button link type="primary" @click="openEdit('equipment', row)">修改</el-button><el-popconfirm title="删除这条设备数据？" @confirm="remove('equipment', row.id)"><template #reference><el-button link type="danger">删除</el-button></template></el-popconfirm></template>
          </el-table-column>
        </el-table>
        <el-empty v-if="data.equipment.length === 0" description="暂无生产设备" :image-size="50" />
      </section>

      <section v-show="activeDataset === 'materials'" class="data-panel surface">
        <header><h3>原辅材料</h3><span>{{ data.raw_materials.length }} 项</span></header>
        <el-table :data="data.raw_materials">
          <el-table-column prop="name" label="名称" />
          <el-table-column label="年用量"><template #default="{ row }">{{ formatValue(row.annual_usage) }}</template></el-table-column>
          <el-table-column prop="annual_usage_unit" label="单位" />
          <el-table-column label="最大储量"><template #default="{ row }">{{ formatValue(row.max_storage) }}</template></el-table-column>
          <el-table-column prop="storage_location" label="储存位置" />
          <el-table-column prop="verification_status" label="状态" :formatter="verificationFormatter" />
          <el-table-column label="操作" width="150">
            <template #default="{ row }"><el-button link type="primary" @click="openEdit('raw_material', row)">修改</el-button><el-popconfirm title="删除这条原辅材料数据？" @confirm="remove('raw_material', row.id)"><template #reference><el-button link type="danger">删除</el-button></template></el-popconfirm></template>
          </el-table-column>
        </el-table>
        <el-empty v-if="data.raw_materials.length === 0" description="暂无原辅材料" :image-size="50" />
      </section>

      <section v-show="activeDataset === 'facts'" class="data-panel surface">
        <header><h3>待确认信息</h3><span>{{ reviewFacts.length }} 项</span></header>
        <el-table :data="reviewFacts">
          <el-table-column prop="entity_key" label="资料项" width="140" />
          <el-table-column prop="field_name" label="内容字段" width="150" />
          <el-table-column label="整理结果" min-width="150">
            <template #default="{ row }">{{ row.raw_value }} {{ row.unit || '' }}</template>
          </el-table-column>
          <el-table-column label="来源" min-width="230">
            <template #default="{ row }">{{ sourceText(row) }}</template>
          </el-table-column>
          <el-table-column label="状态" width="90"><template #default="{ row }">{{ factStatusLabel(row.status) }}</template></el-table-column>
          <el-table-column label="操作" width="150">
            <template #default="{ row }">
              <el-button link type="success" :disabled="row.status === 'accepted'" @click="accept(row.id)">确认</el-button>
              <el-button link type="danger" :disabled="row.status === 'rejected'" @click="reject(row.id)">拒绝</el-button>
            </template>
          </el-table-column>
        </el-table>
        <el-empty v-if="reviewFacts.length === 0" description="暂无待审核事实" :image-size="50" />
      </section>

      <section v-show="activeDataset === 'conflicts'" class="data-panel surface">
        <header><h3>来源不一致</h3><span>{{ openConflicts.length }} 项</span></header>
        <el-table :data="openConflicts">
          <el-table-column prop="entity_key" label="资料项" width="140" />
          <el-table-column prop="field_name" label="内容字段" width="150" />
          <el-table-column label="左侧内容 / 来源" min-width="220">
            <template #default="{ row }">{{ row.value_a }}；{{ conflictSource(row.source_a) }}</template>
          </el-table-column>
          <el-table-column label="右侧内容 / 来源" min-width="220">
            <template #default="{ row }">{{ row.value_b }}；{{ conflictSource(row.source_b) }}</template>
          </el-table-column>
          <el-table-column label="操作" width="190">
            <template #default="{ row }">
              <el-button link type="primary" @click="resolve(row.id, 'use_a')">采用左侧</el-button>
              <el-button link type="primary" @click="resolve(row.id, 'use_b')">采用右侧</el-button>
              <el-button link type="info" @click="resolve(row.id, 'ignore')">忽略</el-button>
            </template>
          </el-table-column>
        </el-table>
        <el-empty v-if="openConflicts.length === 0" description="没有需要核对的信息" :image-size="50" />
      </section>
    </template>

    <el-dialog v-model="editVisible" title="修改结构化数据" width="520px">
      <el-form label-width="100px">
        <el-form-item label="名称"><el-input v-model="editForm.name" /></el-form-item>
        <el-form-item v-if="editKind === 'product'" label="年产能">
          <el-input v-model="editForm.annual_capacity" /><el-input v-model="editForm.unit" placeholder="单位" style="margin-top: 8px" />
        </el-form-item>
        <template v-if="editKind === 'equipment'">
          <el-form-item label="型号"><el-input v-model="editForm.model" /></el-form-item>
          <el-form-item label="数量"><el-input v-model="editForm.quantity" /><el-input v-model="editForm.unit" placeholder="单位" style="margin-top: 8px" /></el-form-item>
        </template>
        <template v-if="editKind === 'raw_material'">
          <el-form-item label="年用量"><el-input v-model="editForm.annual_usage" /><el-input v-model="editForm.annual_usage_unit" placeholder="单位" style="margin-top: 8px" /></el-form-item>
          <el-form-item label="最大储量"><el-input v-model="editForm.max_storage" /></el-form-item>
          <el-form-item label="储存位置"><el-input v-model="editForm.storage_location" /></el-form-item>
        </template>
      </el-form>
      <template #footer><el-button @click="editVisible = false">取消</el-button><el-button type="primary" :loading="saving" @click="saveEdit">保存</el-button></template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { projectApi } from '../api/projects'
import type { DataConflict, ExtractedFact, StructuredProjectData } from '../types'

const props = defineProps<{ projectId: number }>()
const loading = ref(false)
const extracting = ref(false)
const saving = ref(false)
const data = ref<StructuredProjectData | null>(null)
const editVisible = ref(false)
const activeDataset = ref('profile')
const editKind = ref<'product' | 'equipment' | 'raw_material'>('product')
const editId = ref(0)
const editForm = reactive<Record<string, string>>({})

const reviewFacts = computed(() => data.value?.facts.filter((fact) => fact.status === 'pending' || fact.status === 'conflict') || [])
const openConflicts = computed(() => data.value?.conflicts.filter((conflict) => conflict.status === 'open') || [])
const dataNavigation = computed(() => [
  { key: 'profile', label: '企业概况', count: data.value?.profile ? 1 : 0 },
  { key: 'products', label: '产品', count: data.value?.products.length || 0 },
  { key: 'equipment', label: '设备', count: data.value?.equipment.length || 0 },
  { key: 'materials', label: '原辅材料', count: data.value?.raw_materials.length || 0 },
  { key: 'facts', label: '待确认', count: reviewFacts.value.length },
  { key: 'conflicts', label: '不一致', count: openConflicts.value.length },
])

async function load() {
  loading.value = true
  try { data.value = await projectApi.getStructuredData(props.projectId) } catch (e) { ElMessage.error((e as Error).message) } finally { loading.value = false }
}

async function startExtraction() {
  extracting.value = true
  try { await projectApi.extract(props.projectId); await load(); ElMessage.success('项目数据已更新') } catch (e) { ElMessage.error((e as Error).message || '数据整理失败') } finally { extracting.value = false }
}

async function accept(id: number) { try { await projectApi.acceptFact(props.projectId, id); await load(); ElMessage.success('已确认') } catch (e) { ElMessage.error((e as Error).message) } }
async function reject(id: number) { try { await projectApi.rejectFact(props.projectId, id); await load(); ElMessage.success('已拒绝') } catch (e) { ElMessage.error((e as Error).message) } }
async function resolve(id: number, resolution: 'use_a' | 'use_b' | 'ignore') { try { await projectApi.resolveConflict(props.projectId, id, resolution); await load(); ElMessage.success('冲突已处理') } catch (e) { ElMessage.error((e as Error).message) } }

function sourceText(fact: ExtractedFact) {
  const location = fact.source_location || {}
  const parts = [fact.source_filename, location.page ? `第 ${location.page} 页` : '', location.sheet ? `工作表 ${location.sheet}` : '', location.row ? `第 ${location.row} 行` : ''].filter(Boolean)
  return `${parts.join(' / ')}${fact.source_text ? `：${fact.source_text}` : ''}`
}
function conflictSource(source: Record<string, unknown> | null) { return source?.location ? JSON.stringify(source.location) : '人工数据' }
function runStatusLabel(status: string) { return ({ completed: '已完成', partial: '部分完成', running: '中', failed: '失败' } as Record<string, string>)[status] || '' }
function factStatusLabel(status: string) { return ({ pending: '待确认', conflict: '需核对', accepted: '已确认', rejected: '已忽略' } as Record<string, string>)[status] || '待确认' }
function verificationFormatter(row: { verification_status: string }) { return row.verification_status === 'user_verified' ? '已确认' : '待确认' }
function formatValue(value: string | number | null) { if (value === null || value === '') return '—'; const numeric = Number(value); return Number.isFinite(numeric) ? new Intl.NumberFormat('zh-CN', { maximumFractionDigits: 3 }).format(numeric) : value }

function openEdit(kind: 'product' | 'equipment' | 'raw_material', row: Record<string, unknown>) {
  editKind.value = kind; editId.value = Number(row.id); Object.keys(editForm).forEach((key) => delete editForm[key])
  Object.entries(row).forEach(([key, value]) => { if (value !== null && value !== undefined) editForm[key] = String(value) })
  editVisible.value = true
}
async function saveEdit() {
  saving.value = true
  try {
    const payload = { ...editForm }
    if (payload.annual_capacity) payload.annual_capacity = String(payload.annual_capacity)
    if (payload.annual_usage) payload.annual_usage = String(payload.annual_usage)
    if (payload.max_storage) payload.max_storage = String(payload.max_storage)
    if (payload.quantity) payload.quantity = String(payload.quantity)
    if (editKind.value === 'product') await projectApi.updateProduct(props.projectId, editId.value, payload)
    if (editKind.value === 'equipment') await projectApi.updateEquipment(props.projectId, editId.value, payload)
    if (editKind.value === 'raw_material') await projectApi.updateRawMaterial(props.projectId, editId.value, payload)
    editVisible.value = false; await load(); ElMessage.success('已保存并标记为人工确认')
  } catch (e) { ElMessage.error((e as Error).message) } finally { saving.value = false }
}

async function remove(kind: 'product' | 'equipment' | 'raw_material', id: number) {
  try {
    if (kind === 'product') await projectApi.removeProduct(props.projectId, id)
    if (kind === 'equipment') await projectApi.removeEquipment(props.projectId, id)
    if (kind === 'raw_material') await projectApi.removeRawMaterial(props.projectId, id)
    await load(); ElMessage.success('已删除')
  } catch (e) { ElMessage.error((e as Error).message) }
}

onMounted(load)
</script>

<style scoped>
.structured-toolbar { display: flex; align-items: flex-end; justify-content: space-between; margin-bottom: 16px; }
.structured-toolbar h2 { margin: 0 0 7px; font-size: 24px; letter-spacing: -.03em; }
.structured-toolbar > div > span { color: #6e6e73; font-size: 11px; }
.run-meta { margin-left: 12px; color: #909399; font-size: 13px; }
.data-summary { display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; margin: 20px 0 14px; }
.data-summary > div { padding: 16px 18px; border: 1px solid rgba(0,0,0,.065); border-radius: 16px; background: #fff; }
.data-summary span, .data-summary strong { display: block; }
.data-summary span { color: #86868b; font-size: 10px; }
.data-summary strong { margin-top: 5px; font-size: 23px; letter-spacing: -.04em; }
.data-summary .attention strong { color: #d05f00; }
.data-nav { display: flex; gap: 3px; width: fit-content; max-width: 100%; margin-bottom: 14px; padding: 4px; border-radius: 13px; background: #e9e9ec; overflow-x: auto; }
.data-nav button { height: 36px; padding: 0 13px; display: flex; align-items: center; gap: 7px; border: 0; border-radius: 10px; color: #6e6e73; background: transparent; cursor: pointer; font-size: 10px; font-weight: 600; white-space: nowrap; outline: none; }
.data-nav button.active { color: #1d1d1f; background: #fff; box-shadow: 0 1px 6px rgba(0,0,0,.09); }
.data-nav button:focus-visible { box-shadow: 0 0 0 3px rgba(0,113,227,.18); }
.data-nav button span { min-width: 17px; height: 17px; padding: 0 4px; display: grid; place-items: center; border-radius: 9px; color: #6e6e73; background: #ededf0; font-size: 8px; }
.data-panel { padding: 8px 18px 18px; overflow: hidden; }
.data-panel > header { height: 58px; display: flex; align-items: center; justify-content: space-between; border-bottom: 1px solid rgba(0,0,0,.065); }
.data-panel > header h3 { margin: 0; font-size: 15px; }
.data-panel > header span { color: #86868b; font-size: 9px; }
.data-panel :deep(.el-descriptions) { margin-top: 18px; }
@media (max-width: 700px) { .data-summary { grid-template-columns: 1fr 1fr; } .structured-toolbar { align-items: flex-start; flex-direction: column; gap: 14px; } }
</style>
