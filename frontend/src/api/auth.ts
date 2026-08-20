import { request } from './client'
import type { TokenOut, User } from '../types'

export const authApi = {
  async register(data: { username: string; email: string; password: string; full_name?: string }) {
    return request<User>({ url: '/auth/register', method: 'POST', data })
  },
  async login(data: { username: string; password: string }) {
    return request<TokenOut>({ url: '/auth/login', method: 'POST', data })
  },
  async me() {
    return request<User>({ url: '/auth/me', method: 'GET' })
  },
}