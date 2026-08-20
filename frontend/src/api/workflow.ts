import { request } from './client'
import type { BatchGenerationRun, DocumentOverview, Readiness, SectionInstance, ValidationIssue, ValidationRun } from '../types'

export function getDocumentOverview(id: number) { return request<DocumentOverview>({ method: 'GET', url: `/document-instances/${id}/overview` }) }
export function batchGenerate(id: number, sectionIds: number[] = []) { return request<BatchGenerationRun>({ method: 'POST', url: `/document-instances/${id}/generate`, data: { section_ids: sectionIds } }) }
export function reviewSection(id: number, status: string, comment?: string) { return request<{ id: number; status: string }>({ method: 'POST', url: `/document-sections/${id}/review`, data: { status, comment } }) }
export function lockSection(id: number) { return request<null>({ method: 'POST', url: `/document-sections/${id}/lock` }) }
export function unlockSection(id: number) { return request<null>({ method: 'POST', url: `/document-sections/${id}/unlock` }) }
export function validateDocument(id: number) { return request<ValidationRun>({ method: 'POST', url: `/document-instances/${id}/validate` }) }
export function listValidationIssues(id: number) { return request<ValidationIssue[]>({ method: 'GET', url: `/document-instances/${id}/validation-issues` }) }
export function getReadiness(id: number) { return request<Readiness>({ method: 'GET', url: `/document-instances/${id}/readiness` }) }
