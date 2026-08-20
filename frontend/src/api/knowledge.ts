import { request, uploadRequest } from './client'
import type { KnowledgeBase, KnowledgeDocument, KnowledgeChunk, KnowledgeSearchResponse } from '../types'

export function listKnowledgeBases() {
  return request<KnowledgeBase[]>({ method: 'GET', url: '/knowledge-bases' })
}

export function createKnowledgeBase(payload: { name: string; description?: string; scope: string }) {
  return request<KnowledgeBase>({ method: 'POST', url: '/knowledge-bases', data: payload })
}

export function deleteKnowledgeBase(id: number) {
  return request<null>({ method: 'DELETE', url: `/knowledge-bases/${id}` })
}

export function listKnowledgeDocuments(id: number) {
  return request<KnowledgeDocument[]>({ method: 'GET', url: `/knowledge-bases/${id}/documents` })
}

export function uploadKnowledgeDocument(id: number, file: File, metadata: Record<string, unknown>) {
  const form = new FormData()
  form.append('file', file)
  form.append('metadata', JSON.stringify(metadata))
  return uploadRequest<KnowledgeDocument>({ method: 'POST', url: `/knowledge-bases/${id}/documents`, data: form })
}

export function processKnowledgeDocument(id: number) {
  return request<KnowledgeDocumentStatus>({ method: 'POST', url: `/knowledge-documents/${id}/process` })
}

export function listKnowledgeChunks(id: number) {
  return request<KnowledgeChunk[]>({ method: 'GET', url: `/knowledge-documents/${id}/chunks` })
}

export function searchKnowledge(payload: Record<string, unknown>) {
  return request<KnowledgeSearchResponse>({ method: 'POST', url: '/knowledge/search', data: payload })
}

export interface KnowledgeDocumentStatus {
  document_id: number
  parser_status: string
  index_status: string
  error_message: string | null
  chunks_count: number
  embedded_count: number
  latest_run_id: number | null
}
