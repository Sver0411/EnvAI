import { request } from './client'
import type { AdminDashboard, AdminOrganization, AdminPage } from '../types'

export const adminApi = {
  dashboard: (days = 30) => request<AdminDashboard>({ method: 'GET', url: '/admin/dashboard', params: { days } }),
  organizations: (page = 1, search = '') => request<AdminPage<AdminOrganization>>({ method: 'GET', url: '/admin/organizations', params: { page, page_size: 20, search: search || undefined } }),
  suspendOrganization: (id: number, reason: string) => request<{ id: number; status: string }>({ method: 'POST', url: `/admin/organizations/${id}/suspend`, params: { reason } }),
  activateOrganization: (id: number) => request<{ id: number; status: string }>({ method: 'POST', url: `/admin/organizations/${id}/activate` }),
}
