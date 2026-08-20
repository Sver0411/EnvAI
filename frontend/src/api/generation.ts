import { request } from './client'
import type { DocumentInstance, DocumentTemplate, GenerationRun, SectionDraft, SectionPreflight, SectionView } from '../types'

export function listDocumentTemplates() { return request<DocumentTemplate[]>({ method: 'GET', url: '/document-templates' }) }
export function createDocumentInstance(projectId: number, payload: { template_id: number; title?: string }) { return request<DocumentInstance>({ method: 'POST', url: `/projects/${projectId}/document-instances`, data: payload }) }
export function listDocumentInstances(projectId: number) { return request<DocumentInstance[]>({ method: 'GET', url: `/projects/${projectId}/document-instances` }) }
export function getSection(instanceId: number, sectionId: number) { return request<SectionView>({ method: 'GET', url: `/document-instances/${instanceId}/sections/${sectionId}` }) }
export function preflightSection(instanceId: number, sectionId: number) { return request<SectionPreflight>({ method: 'POST', url: `/document-instances/${instanceId}/sections/${sectionId}/preflight` }) }
export function generateSection(instanceId: number, sectionId: number) { return request<GenerationRun>({ method: 'POST', url: `/document-instances/${instanceId}/sections/${sectionId}/generate` }) }
export function updateDraft(draftId: number, content: string) { return request<SectionDraft>({ method: 'PUT', url: `/section-drafts/${draftId}`, data: { content } }) }
