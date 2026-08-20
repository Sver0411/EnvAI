import { downloadRequest, request, uploadRequest } from './client'
import type {
  CompanyProfile,
  DataConflict,
  ExtractedFact,
  ExtractionRun,
  ParsedDocument,
  ParsedDocumentStatus,
  Project,
  ProjectFile,
  ProjectPage,
  ProjectType,
  StructuredProjectData,
} from '../types'

export const projectApi = {
  async list(params: { page?: number; page_size?: number }) {
    return request<ProjectPage>({ url: '/projects', method: 'GET', params })
  },
  async get(id: number) {
    return request<Project>({ url: `/projects/${id}`, method: 'GET' })
  },
  async create(data: { name: string; project_type: ProjectType; company_name?: string; description?: string }) {
    return request<Project>({ url: '/projects', method: 'POST', data })
  },
  async update(id: number, data: Partial<Project>) {
    return request<Project>({ url: `/projects/${id}`, method: 'PUT', data })
  },
  async remove(id: number) {
    return request<null>({ url: `/projects/${id}`, method: 'DELETE' })
  },
  async getProfile(projectId: number) {
    return request<CompanyProfile>({ url: `/projects/${projectId}/profile`, method: 'GET' })
  },
  async saveProfile(projectId: number, data: Partial<CompanyProfile>) {
    return request<CompanyProfile>({ url: `/projects/${projectId}/profile`, method: 'PUT', data })
  },
  async listFiles(projectId: number) {
    return request<ProjectFile[]>({ url: `/projects/${projectId}/files`, method: 'GET' })
  },
  async uploadFiles(projectId: number, files: File[]) {
    const form = new FormData()
    files.forEach((file) => form.append('files', file))
    return uploadRequest<ProjectFile[]>({ url: `/projects/${projectId}/files`, method: 'POST', data: form })
  },
  async downloadFile(projectId: number, fileId: number) {
    return downloadRequest({ url: `/projects/${projectId}/files/${fileId}/download`, method: 'GET' })
  },
  async removeFile(projectId: number, fileId: number) {
    return request<null>({ url: `/projects/${projectId}/files/${fileId}`, method: 'DELETE' })
  },
  async parseFile(projectId: number, fileId: number) {
    return request<ParsedDocumentStatus>({ url: `/projects/${projectId}/files/${fileId}/parse`, method: 'POST' })
  },
  async getParseStatus(projectId: number, fileId: number) {
    return request<ParsedDocumentStatus>({ url: `/projects/${projectId}/files/${fileId}/parse-status`, method: 'GET' })
  },
  async getParsedDocument(projectId: number, fileId: number) {
    return request<ParsedDocument>({ url: `/projects/${projectId}/files/${fileId}/parsed`, method: 'GET' })
  },
  async extract(projectId: number) {
    return request<ExtractionRun>({ url: `/projects/${projectId}/extract`, method: 'POST' })
  },
  async getStructuredData(projectId: number) {
    return request<StructuredProjectData>({ url: `/projects/${projectId}/extracted-data`, method: 'GET' })
  },
  async acceptFact(projectId: number, factId: number) {
    return request<ExtractedFact>({ url: `/projects/${projectId}/extracted-facts/${factId}/accept`, method: 'POST' })
  },
  async rejectFact(projectId: number, factId: number) {
    return request<ExtractedFact>({ url: `/projects/${projectId}/extracted-facts/${factId}/reject`, method: 'POST' })
  },
  async resolveConflict(projectId: number, conflictId: number, resolution: 'use_a' | 'use_b' | 'ignore', note?: string) {
    return request<DataConflict>({ url: `/projects/${projectId}/conflicts/${conflictId}/resolve`, method: 'POST', data: { resolution, note } })
  },
  async updateProduct(projectId: number, id: number, data: Record<string, unknown>) {
    return request<StructuredProjectData['products'][number]>({ url: `/projects/${projectId}/products/${id}`, method: 'PUT', data })
  },
  async updateEquipment(projectId: number, id: number, data: Record<string, unknown>) {
    return request<StructuredProjectData['equipment'][number]>({ url: `/projects/${projectId}/equipment/${id}`, method: 'PUT', data })
  },
  async updateRawMaterial(projectId: number, id: number, data: Record<string, unknown>) {
    return request<StructuredProjectData['raw_materials'][number]>({ url: `/projects/${projectId}/raw-materials/${id}`, method: 'PUT', data })
  },
  async removeProduct(projectId: number, id: number) { return request<null>({ url: `/projects/${projectId}/products/${id}`, method: 'DELETE' }) },
  async removeEquipment(projectId: number, id: number) { return request<null>({ url: `/projects/${projectId}/equipment/${id}`, method: 'DELETE' }) },
  async removeRawMaterial(projectId: number, id: number) { return request<null>({ url: `/projects/${projectId}/raw-materials/${id}`, method: 'DELETE' }) },
}
