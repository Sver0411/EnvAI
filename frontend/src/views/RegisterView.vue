<template>
  <div class="register-page">
    <header><router-link to="/login" class="brand"><span><i></i><i></i><i></i></span><strong>EnvAI</strong></router-link><router-link to="/login">已有账号？登录</router-link></header>
    <main>
      <div class="register-heading"><h1>创建工作账号</h1><p>注册后即可建立个人工作区。</p></div>
      <section class="register-card surface">
        <el-form :model="form" label-position="top" @submit.prevent="onSubmit">
          <div class="form-row"><el-form-item label="用户名"><el-input v-model="form.username" size="large" placeholder="至少 3 位" /></el-form-item><el-form-item label="姓名（可选）"><el-input v-model="form.full_name" size="large" placeholder="用于工作区显示" /></el-form-item></div>
          <el-form-item label="邮箱"><el-input v-model="form.email" size="large" placeholder="name@company.com" /></el-form-item>
          <el-form-item label="密码"><el-input v-model="form.password" type="password" size="large" placeholder="至少 6 位" show-password @keyup.enter="onSubmit" /></el-form-item>
          <p class="agreement">创建账号即表示你同意服务条款和隐私政策。</p>
          <el-button type="primary" size="large" class="submit" :loading="loading" @click="onSubmit">创建账号</el-button>
        </el-form>
      </section>
      <p class="secure-note">企业数据按工作区隔离存储</p>
    </main>
  </div>
</template>
<script setup lang="ts">
import { reactive,ref } from 'vue';import { useRouter } from 'vue-router';import { ElMessage } from 'element-plus';import { authApi } from '../api/auth';const router=useRouter();const form=reactive({username:'',email:'',full_name:'',password:''});const loading=ref(false);async function onSubmit(){if(!form.username||!form.email||!form.password)return ElMessage.warning('请填写用户名、邮箱和密码');loading.value=true;try{await authApi.register({username:form.username,email:form.email,password:form.password,full_name:form.full_name||undefined});ElMessage.success('账号已创建，请登录');router.push({name:'login'})}catch(e){ElMessage.error((e as Error).message||'注册失败')}finally{loading.value=false}}
</script>
<style scoped>
.register-page{min-height:100vh;background:#f5f5f7}.register-page header{height:72px;padding:0 6%;display:flex;align-items:center;justify-content:space-between;border-bottom:1px solid rgba(0,0,0,.06);background:rgba(255,255,255,.8);backdrop-filter:blur(20px)}.register-page header>a:last-child{font-size:12px}.brand{display:flex;align-items:center;gap:9px;color:#1d1d1f}.brand>span{position:relative;width:30px;height:30px;border-radius:10px;background:#0071e3}.brand i{position:absolute;bottom:7px;width:4px;border-radius:3px;background:#fff}.brand i:nth-child(1){left:7px;height:8px;opacity:.6}.brand i:nth-child(2){left:13px;height:13px;opacity:.8}.brand i:nth-child(3){left:19px;height:18px}.brand strong{font-size:18px}.register-page main{width:min(660px,calc(100% - 36px));margin:0 auto;padding:60px 0}.register-heading{text-align:center}.register-heading h1{margin:0;font-size:38px;letter-spacing:-.045em}.register-heading p{margin:10px 0 28px;color:#86868b}.register-card{padding:30px}.form-row{display:grid;grid-template-columns:1fr 1fr;gap:14px}.register-card :deep(.el-form-item){margin-bottom:20px}.agreement{margin:-2px 0 20px;color:#86868b;font-size:10px}.submit{width:100%;height:48px}.secure-note{text-align:center;color:#a1a1a6;font-size:10px}@media(max-width:600px){.form-row{grid-template-columns:1fr}.register-card{padding:22px}.register-page main{padding-top:40px}}
</style>
