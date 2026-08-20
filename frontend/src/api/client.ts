import axios, { type AxiosRequestConfig } from 'axios'
import type { ApiResponse } from '../types'

const client = axios.create({
  baseURL: import.meta.env.VITE_API_URL || '/api/v1',
  timeout: 30000,
})

client.interceptors.request.use((config) => {
  const token = localStorage.getItem('envai_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  const organizationId = localStorage.getItem('envai_organization_id')
  if (organizationId) config.headers['X-Organization-ID'] = organizationId
  return config
})

client.interceptors.response.use(
  (response) => {
    return response
  },
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('envai_token')
      localStorage.removeItem('envai_user')
      if (location.pathname !== '/login') {
        location.href = '/login'
      }
    }
    return Promise.reject(error)
  },
)

export async function request<T>(config: AxiosRequestConfig): Promise<T> {
  const resp = await client.request<ApiResponse<T>>(config)
  const body = resp.data
  if (body.code !== 0) {
    throw new Error(body.message || '请求失败')
  }
  return body.data as T
}

export function uploadRequest<T>(config: AxiosRequestConfig): Promise<T> {
  return request(config)
}

export async function downloadRequest(config: AxiosRequestConfig): Promise<Blob> {
  const response = await client.request<Blob>({ ...config, responseType: 'blob' })
  return response.data
}
