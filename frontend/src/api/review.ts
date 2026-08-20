import { request } from './client'
import type { ProfessionalReviewRun, QualityGate, QualityScore, ReviewIssue } from '../types'
export function startProfessionalReview(id: number, mode = 'full') { return request<ProfessionalReviewRun>({ method: 'POST', url: `/document-instances/${id}/reviews`, data: { mode } }) }
export function listReviewIssues(id: number) { return request<ReviewIssue[]>({ method: 'GET', url: `/document-instances/${id}/review-issues` }) }
export function getQualityScore(id: number) { return request<QualityScore | null>({ method: 'GET', url: `/document-instances/${id}/quality-score` }) }
export function getQualityGate(id: number) { return request<QualityGate>({ method: 'GET', url: `/document-instances/${id}/quality-gate` }) }
export function dismissReviewIssue(id: number, reason: string) { return request<ReviewIssue>({ method: 'POST', url: `/review-issues/${id}/dismiss`, data: { reason } }) }
export function completeReviewChecklist(checklistId: number, documentInstanceId: number, status: 'pass' | 'fail' | 'warning' | 'not_applicable' | 'needs_review', message?: string) {
  return request({ method: 'POST', url: `/review-checklist-items/${checklistId}/complete`, params: { document_instance_id: documentInstanceId }, data: { status, message } })
}
