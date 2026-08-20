import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { User } from '../types'
import { authApi } from '../api/auth'

export const useAuthStore = defineStore('auth', () => {
  const token = ref<string | null>(localStorage.getItem('envai_token'))
  const user = ref<User | null>(JSON.parse(localStorage.getItem('envai_user') || 'null'))

  function setAuth(newToken: string, newUser: User) {
    token.value = newToken
    user.value = newUser
    localStorage.setItem('envai_token', newToken)
    localStorage.setItem('envai_user', JSON.stringify(newUser))
  }

  async function login(username: string, password: string) {
    const data = await authApi.login({ username, password })
    setAuth(data.access_token, data.user)
  }

  async function fetchMe() {
    const me = await authApi.me()
    user.value = me
    localStorage.setItem('envai_user', JSON.stringify(me))
  }

  function logout() {
    token.value = null
    user.value = null
    localStorage.removeItem('envai_token')
    localStorage.removeItem('envai_user')
  }

  return { token, user, setAuth, login, fetchMe, logout }
})