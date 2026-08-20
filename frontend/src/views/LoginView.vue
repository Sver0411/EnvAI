<template>
  <div class="auth-page">
    <section class="auth-brand">
      <div class="brand-lockup"><span class="brand-mark"><i></i><i></i><i></i></span><strong>EnvAI</strong></div>
      <div class="brand-message"><h1>环保咨询项目，<br/>从资料到报告。</h1><p>项目资料、专业依据、文档编制和交付版本集中管理。</p></div>
      <div class="brand-preview">
        <div class="preview-sidebar"><span class="mini-logo"></span><i class="active"></i><i></i><i></i></div>
        <div class="preview-body"><div class="preview-title"></div><div class="preview-metrics"><i></i><i></i><i></i></div><div class="preview-table"><span></span><span></span><span></span><span></span></div></div>
      </div>
      <small>企业数据隔离 · 来源可追溯 · 版本可管理</small>
    </section>
    <main class="auth-main">
      <div class="auth-form">
        <div class="mobile-brand"><span class="brand-mark"><i></i><i></i><i></i></span><strong>EnvAI</strong></div>
        <h2>欢迎回来</h2><p>登录你的工作区</p>
        <el-form :model="form" label-position="top" @submit.prevent="onSubmit">
          <el-form-item label="用户名"><el-input v-model="form.username" size="large" placeholder="输入用户名" autocomplete="username" /></el-form-item>
          <el-form-item label="密码"><el-input v-model="form.password" type="password" size="large" placeholder="输入密码" show-password autocomplete="current-password" @keyup.enter="onSubmit" /></el-form-item>
          <div class="form-options"><el-checkbox>保持登录</el-checkbox><a href="#" @click.prevent>忘记密码？</a></div>
          <el-button type="primary" size="large" class="submit" :loading="loading" @click="onSubmit">登录</el-button>
        </el-form>
        <div class="register-link">还没有账号？<router-link to="/register">创建账号</router-link></div>
      </div>
      <footer>© 2026 EnvAI · 隐私与数据安全</footer>
    </main>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useAuthStore } from '../stores/auth'
const router=useRouter();const route=useRoute();const auth=useAuthStore();const form=reactive({username:'',password:''});const loading=ref(false)
async function onSubmit(){if(!form.username||!form.password)return ElMessage.warning('请输入用户名和密码');loading.value=true;try{await auth.login(form.username,form.password);router.push((route.query.redirect as string)||'/projects')}catch(e){ElMessage.error((e as Error).message||'登录失败')}finally{loading.value=false}}
</script>

<style scoped>
.auth-page{min-height:100vh;display:grid;grid-template-columns:minmax(460px,1.08fr) minmax(430px,.92fr);background:#fff}.auth-brand{position:relative;padding:45px 8%;display:flex;flex-direction:column;color:#fff;background:#121315;overflow:hidden}.auth-brand::after{content:"";position:absolute;width:520px;height:520px;right:-230px;top:-220px;border-radius:50%;background:rgba(255,255,255,.035)}.brand-lockup,.mobile-brand{display:flex;align-items:center;gap:10px}.brand-lockup strong,.mobile-brand strong{font-size:19px;letter-spacing:-.03em}.brand-mark{position:relative;width:31px;height:31px;border-radius:10px;background:#0071e3}.brand-mark i{position:absolute;bottom:7px;width:4px;border-radius:3px;background:#fff}.brand-mark i:nth-child(1){left:7px;height:8px;opacity:.6}.brand-mark i:nth-child(2){left:13px;height:13px;opacity:.8}.brand-mark i:nth-child(3){left:19px;height:18px}.brand-message{margin:auto 0 28px}.brand-message h1{margin:0;font-size:clamp(38px,4vw,58px);line-height:1.08;letter-spacing:-.05em}.brand-message p{max-width:520px;margin:18px 0 0;color:rgba(255,255,255,.58);font-size:15px;line-height:1.7}.brand-preview{height:260px;display:flex;border:1px solid rgba(255,255,255,.12);border-radius:19px;background:#f5f5f7;box-shadow:0 30px 70px rgba(0,0,0,.35);overflow:hidden;transform:perspective(900px) rotateX(2deg)}.preview-sidebar{width:75px;padding:17px 12px;background:#ececef}.mini-logo{display:block;width:25px;height:25px;margin-bottom:25px;border-radius:8px;background:#0071e3}.preview-sidebar i{display:block;height:7px;margin:13px 0;border-radius:5px;background:#c8c8cc}.preview-sidebar i.active{background:#7fb7ee}.preview-body{flex:1;padding:25px}.preview-title{width:42%;height:17px;margin-bottom:25px;border-radius:7px;background:#27272a}.preview-metrics{display:grid;grid-template-columns:repeat(3,1fr);gap:10px}.preview-metrics i{height:55px;border:1px solid #e5e5e7;border-radius:11px;background:white}.preview-table{margin-top:14px;padding:8px 14px;border-radius:11px;background:white}.preview-table span{display:block;height:9px;margin:13px 0;border-radius:5px;background:#e5e5e7}.auth-brand>small{margin-top:25px;color:rgba(255,255,255,.42);font-size:10px}.auth-main{position:relative;display:grid;place-items:center;padding:60px 10%}.auth-form{width:min(390px,100%)}.auth-form h2{margin:0;font-size:32px;letter-spacing:-.04em}.auth-form>p{margin:9px 0 33px;color:#86868b;font-size:13px}.auth-form :deep(.el-form-item){margin-bottom:21px}.form-options{display:flex;align-items:center;justify-content:space-between;margin:-5px 0 21px;font-size:11px}.submit{width:100%;height:48px}.register-link{margin-top:24px;text-align:center;color:#86868b;font-size:12px}.register-link a{margin-left:3px;font-weight:600}.auth-main footer{position:absolute;bottom:25px;color:#b0b0b5;font-size:9px}.mobile-brand{display:none;margin-bottom:40px;color:#1d1d1f}@media(max-width:850px){.auth-page{display:block}.auth-brand{display:none}.auth-main{min-height:100vh}.mobile-brand{display:flex}} 
</style>
