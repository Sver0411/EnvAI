<template>
  <div class="create-page">
    <button class="back" @click="router.back()"><el-icon><ArrowLeft /></el-icon>返回项目工作台</button>
    <div class="create-heading"><h1 class="page-title">新建项目</h1></div>

    <div class="create-layout">
      <main class="form-surface surface">
        <section>
          <div class="step-label"><div><strong>报告类型</strong><small>选择与本项目对应的咨询成果</small></div></div>
          <div class="type-grid">
            <button v-for="item in projectTypes" :key="item.value" class="type-card" :class="{ active: form.project_type === item.value }" @click="form.project_type = item.value">
              <span class="type-icon"><el-icon><component :is="item.icon" /></el-icon></span><strong>{{ item.title }}</strong><small>{{ item.description }}</small>
            </button>
          </div>
        </section>
        <div class="divider"></div>
        <section>
          <div class="step-label"><div><strong>项目信息</strong><small>带 * 的项目为必填项</small></div></div>
          <el-form label-position="top" class="project-form">
            <el-form-item label="项目名称 *"><el-input v-model="form.name" size="large" placeholder="例如：某某有限公司突发环境事件应急预案" /></el-form-item>
            <el-form-item label="服务企业"><el-input v-model="form.company_name" size="large" placeholder="输入企业工商登记全称，稍后也可以补充" /></el-form-item>
            <el-form-item label="项目说明（可选）"><el-input v-model="form.description" type="textarea" :rows="4" placeholder="记录项目背景、交付要求或需要特别注意的事项" /></el-form-item>
          </el-form>
        </section>
        <footer class="form-footer"><span><el-icon><Lock /></el-icon>仅当前工作区成员可见</span><div><el-button @click="router.back()">取消</el-button><el-button type="primary" size="large" :loading="loading" @click="onSubmit">创建项目<el-icon><ArrowRight /></el-icon></el-button></div></footer>
      </main>

      <aside class="preview surface">
        <div class="preview-top"><span class="preview-icon"><el-icon><Document /></el-icon></span><div><strong>{{ selectedType.title }}</strong></div></div>
        <div class="preview-line"></div>
        <h3>项目摘要</h3>
        <dl class="project-summary"><div><dt>项目名称</dt><dd>{{ form.name || '未命名项目' }}</dd></div><div><dt>服务企业</dt><dd>{{ form.company_name || '待补充' }}</dd></div><div><dt>成果类型</dt><dd>{{ selectedType.title }}</dd></div></dl>
        <div class="document-preview"><span></span><span></span><strong>{{ selectedType.title }}</strong><small>{{ form.company_name || '企业名称' }}</small></div>
      </aside>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, markRaw, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { ArrowLeft, ArrowRight, DataAnalysis, Document, Lock, SetUp, Warning } from '@element-plus/icons-vue'
import { projectApi } from '../api/projects'
import type { ProjectType } from '../types'

const router = useRouter(); const loading = ref(false)
const form = reactive({ name: '', project_type: 'emergency_response' as ProjectType, company_name: '', description: '' })
const projectTypes = [
  { value: 'environmental_impact' as ProjectType, title: '环境影响评价', description: '建设项目环境影响分析与评价', icon: markRaw(DataAnalysis) },
  { value: 'emergency_response' as ProjectType, title: '应急预案', description: '突发环境事件应急准备与响应', icon: markRaw(Warning) },
  { value: 'risk_assessment' as ProjectType, title: '风险评估', description: '环境风险识别、分析与防控', icon: markRaw(SetUp) },
  { value: 'other' as ProjectType, title: '其他咨询报告', description: '使用通用流程组织专业文档', icon: markRaw(Document) },
]
const selectedType = computed(() => projectTypes.find((item) => item.value === form.project_type) || projectTypes[0])
async function onSubmit() { if (!form.name.trim()) return ElMessage.warning('请填写项目名称'); loading.value = true; try { const project = await projectApi.create({ name: form.name.trim(), project_type: form.project_type, company_name: form.company_name.trim() || undefined, description: form.description.trim() || undefined }); ElMessage.success('项目已创建'); router.push({ path: `/projects/${project.id}`, query: { tab: 'profile' } }) } catch (e) { ElMessage.error((e as Error).message) } finally { loading.value = false } }
</script>

<style scoped>
.create-page{width:min(1220px,100%);margin:0 auto;padding:32px 34px 60px}.back{display:flex;align-items:center;gap:6px;margin-bottom:25px;padding:0;border:0;background:transparent;color:#6e6e73;cursor:pointer;font-size:13px}.back:hover{color:#0071e3}.create-heading{max-width:760px;margin-bottom:30px}.create-layout{display:grid;grid-template-columns:minmax(0,1fr) 330px;gap:18px;align-items:start}.form-surface{padding:28px}.step-label{display:flex;align-items:center;gap:12px;margin-bottom:19px}.step-label>span{width:30px;height:30px;display:grid;place-items:center;border-radius:50%;color:#0071e3;background:#e8f2ff;font-size:12px;font-weight:700}.step-label strong,.step-label small{display:block}.step-label strong{font-size:17px}.step-label small{margin-top:4px;color:#86868b;font-size:12px}.type-grid{display:grid;grid-template-columns:1fr 1fr;gap:11px}.type-card{position:relative;min-height:130px;padding:18px;display:flex;align-items:flex-start;flex-direction:column;text-align:left;border:1px solid rgba(0,0,0,.09);border-radius:17px;background:#fff;cursor:pointer;transition:.2s}.type-card:hover{border-color:#9acbfa;transform:translateY(-1px)}.type-card.active{border-color:#0071e3;background:#f5faff;box-shadow:0 0 0 3px rgba(0,113,227,.09)}.type-icon{width:35px;height:35px;display:grid;place-items:center;margin-bottom:12px;border-radius:11px;color:#0071e3;background:#e8f2ff}.type-card strong{font-size:14px}.type-card small{margin-top:5px;color:#86868b;font-size:11px}.type-card i{position:absolute;top:14px;right:14px;width:20px;height:20px;display:none;place-items:center;border-radius:50%;color:#fff;background:#0071e3}.type-card.active i{display:grid}.divider{height:1px;margin:27px 0;background:rgba(0,0,0,.07)}.project-form{max-width:680px}.project-form :deep(.el-form-item){margin-bottom:20px}.form-footer{display:flex;align-items:center;justify-content:space-between;gap:15px;margin:26px -28px -28px;padding:20px 28px;border-top:1px solid rgba(0,0,0,.07);background:#fafafa;border-radius:0 0 22px 22px}.form-footer>span{display:flex;align-items:center;gap:5px;color:#86868b;font-size:11px}.preview{position:static;padding:22px}.preview-top{display:flex;align-items:center;gap:12px}.preview-icon{width:45px;height:45px;display:grid;place-items:center;border-radius:14px;color:#fff;background:linear-gradient(145deg,#0788ff,#0064ca);font-size:20px}.preview-top small,.preview-top strong{display:block}.preview-top small{color:#86868b;font-size:10px}.preview-top strong{margin-top:4px;font-size:14px}.preview-line{height:1px;margin:20px 0;background:rgba(0,0,0,.07)}.preview h3{margin:0 0 17px;font-size:14px}.preview-step{position:relative;display:flex;gap:11px;padding-bottom:18px}.preview-step:not(:last-of-type)::after{content:"";position:absolute;top:25px;left:11px;width:1px;height:16px;background:#d2d2d7}.preview-step>span{flex:0 0 23px;width:23px;height:23px;display:grid;place-items:center;border-radius:50%;color:#0071e3;background:#e8f2ff;font-size:10px;font-weight:700}.preview-step strong,.preview-step small{display:block}.preview-step strong{font-size:12px}.preview-step small{margin-top:4px;color:#86868b;font-size:10px}.ai-note{display:flex;gap:10px;margin-top:5px;padding:14px;border-radius:15px;color:#0068d1;background:#eef7ff}.ai-note>div strong{font-size:11px}.ai-note p{margin:5px 0 0;color:#4d7091;font-size:10px;line-height:1.55}@media(max-width:950px){.create-layout{grid-template-columns:1fr}.preview{position:static}}@media(max-width:600px){.create-page{padding:22px 18px 42px}.type-grid{grid-template-columns:1fr}.form-footer{align-items:flex-start;flex-direction:column}.form-footer>div{width:100%;display:flex}.form-footer .el-button{flex:1}}
</style>
<style scoped>
.project-summary { margin: 0; }
.project-summary div { display: flex; justify-content: space-between; gap: 15px; padding: 9px 0; border-bottom: 1px solid rgba(0,0,0,.06); font-size: 10px; }
.project-summary dt { color: #86868b; }
.project-summary dd { margin: 0; max-width: 170px; overflow: hidden; color: #1d1d1f; text-align: right; text-overflow: ellipsis; white-space: nowrap; }
.document-preview { height: 180px; margin-top: 22px; padding: 30px 22px; display: flex; align-items: center; flex-direction: column; border: 1px solid rgba(0,0,0,.08); border-radius: 8px; background: #fff; box-shadow: 0 13px 32px rgba(0,0,0,.06); }
.document-preview > span { width: 54px; height: 4px; margin-bottom: 7px; border-radius: 3px; background: #d2d2d7; }
.document-preview > span:nth-child(2) { width: 76px; }
.document-preview strong { margin-top: 24px; text-align: center; font-family: "Songti SC", serif; font-size: 15px; }
.document-preview small { margin-top: 10px; color: #86868b; }
</style>
<style scoped>
/* 选择标记只作用于右上角标记，不能把卡片里的报告图标一起隐藏。 */
.type-card .type-icon .el-icon {
  display: inline-flex !important;
  position: static !important;
  width: auto !important;
  height: auto !important;
}
.type-card .type-icon .el-icon svg {
  width: 18px;
  height: 18px;
}
</style>
