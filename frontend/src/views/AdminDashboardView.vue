<template><div class="admin-page"><header class="admin-heading"><div><h1>平台概览</h1><p>核心运营指标与服务使用情况</p></div><el-select v-model="days" @change="load"><el-option :value="1" label="今日"/><el-option :value="7" label="最近 7 天"/><el-option :value="30" label="最近 30 天"/></el-select></header><section class="primary-metrics"><article v-for="card in primaryCards" :key="card.label" class="surface"><div><span>{{card.label}}</span><strong>{{card.value}}</strong></div><el-icon><component :is="card.icon"/></el-icon></article></section><section class="admin-grid"><div class="surface usage-panel"><header><div><h2>使用情况</h2><p>{{days}} 天内的平台活动</p></div></header><div class="usage-bars"><div v-for="item in usageCards" :key="item.label"><span>{{item.label}}</span><strong>{{item.value}}</strong><i><b :style="{width:item.percent+'%'}"></b></i></div></div></div><div class="surface health-panel"><header><h2>服务状态</h2><span>正常</span></header><div class="health-row"><span><i></i>文档生成服务</span><strong>{{data?.failed_jobs ? `${data.failed_jobs} 个异常` : '运行正常'}}</strong></div><div class="health-row"><span><i></i>存储服务</span><strong>{{formatBytes(data?.storage_bytes||0)}} 已使用</strong></div><div class="health-row"><span><i></i>导出服务</span><strong>{{data?.exports||0}} 次导出</strong></div></div></section></div></template>
<script setup lang="ts">
import { computed, markRaw, onMounted, ref } from 'vue'
import { Document, Folder, OfficeBuilding, User } from '@element-plus/icons-vue'
import { adminApi } from '../api/admin'
import type { AdminDashboard } from '../types'
const days = ref(30)
const data = ref<AdminDashboard | null>(null)
const load = async () => { data.value = await adminApi.dashboard(days.value) }
const primaryCards = computed(() => [
  { label: '企业工作区', value: data.value?.organizations ?? '-', icon: markRaw(OfficeBuilding) },
  { label: '活跃用户', value: data.value?.active_users ?? '-', icon: markRaw(User) },
  { label: '咨询项目', value: data.value?.projects ?? '-', icon: markRaw(Folder) },
  { label: '生成文档', value: data.value?.documents_generated ?? '-', icon: markRaw(Document) },
])
const usageCards = computed(() => {
  const values = [{ label: '模型调用量', value: data.value?.ai_requests || 0 }, { label: '文本处理量', value: data.value?.llm_tokens || 0 }, { label: '知识索引量', value: data.value?.embedding_usage || 0 }]
  const max = Math.max(...values.map((item) => item.value), 1)
  return values.map((item) => ({ ...item, percent: Math.max(4, Math.round(item.value / max * 100)) }))
})
function formatBytes(value: number) { if (value < 1024) return `${value} B`; if (value < 1024 ** 2) return `${(value / 1024).toFixed(1)} KB`; if (value < 1024 ** 3) return `${(value / 1024 ** 2).toFixed(1)} MB`; return `${(value / 1024 ** 3).toFixed(1)} GB` }
onMounted(load)
</script>
<style scoped>.admin-heading p { display: none; }</style>
<style scoped>.admin-page{max-width:1320px;margin:0 auto}.admin-heading{display:flex;align-items:flex-end;justify-content:space-between;margin-bottom:25px}.admin-heading h1{margin:0;font-size:30px;letter-spacing:-.04em}.admin-heading p{margin:7px 0 0;color:#86868b;font-size:12px}.primary-metrics{display:grid;grid-template-columns:repeat(4,1fr);gap:13px}.primary-metrics article{padding:20px;display:flex;align-items:center;justify-content:space-between}.primary-metrics span,.primary-metrics strong{display:block}.primary-metrics span{color:#86868b;font-size:10px}.primary-metrics strong{margin-top:7px;font-size:27px;letter-spacing:-.04em}.primary-metrics .el-icon{width:39px;height:39px;padding:10px;border-radius:12px;color:#0071e3;background:#e8f2ff;font-size:19px}.admin-grid{display:grid;grid-template-columns:1.5fr 1fr;gap:13px;margin-top:13px}.usage-panel,.health-panel{padding:22px}.usage-panel header,.health-panel header{display:flex;justify-content:space-between;align-items:center}.usage-panel h2,.health-panel h2{margin:0;font-size:16px}.usage-panel header p{margin:4px 0 0;color:#86868b;font-size:9px}.health-panel header>span{padding:5px 9px;border-radius:999px;color:#1f8f40;background:#edf9ef;font-size:9px}.usage-bars{margin-top:25px}.usage-bars>div{display:grid;grid-template-columns:110px 90px 1fr;align-items:center;margin:19px 0;font-size:10px}.usage-bars>div>span{color:#6e6e73}.usage-bars>div>strong{font-size:12px}.usage-bars i{height:7px;border-radius:6px;background:#ededf0;overflow:hidden}.usage-bars b{display:block;height:100%;border-radius:6px;background:#0071e3}.health-row{display:flex;justify-content:space-between;padding:18px 0;border-bottom:1px solid rgba(0,0,0,.06);font-size:10px}.health-row span{display:flex;align-items:center;gap:7px;color:#515154}.health-row i{width:7px;height:7px;border-radius:50%;background:#34c759}.health-row strong{font-weight:500;color:#86868b}@media(max-width:1000px){.primary-metrics{grid-template-columns:1fr 1fr}.admin-grid{grid-template-columns:1fr}}@media(max-width:550px){.primary-metrics{grid-template-columns:1fr}.admin-heading{align-items:flex-start;flex-direction:column;gap:14px}}</style>
