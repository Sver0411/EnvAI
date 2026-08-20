import { request } from './client'
import type { ExportArtifact, ExportPreflight, ReportExportJob, ReportSnapshot, ReportTemplate } from '../types'

export function listReportTemplates() { return request<ReportTemplate[]>({ method: 'GET', url: '/report-templates' }) }
export function exportPreflight(instanceId: number, reportTemplateId?: number) { return request<ExportPreflight>({ method: 'POST', url: `/document-instances/${instanceId}/export-preflight`, params: reportTemplateId ? { report_template_id: reportTemplateId } : {} }) }
export function createReportSnapshot(instanceId: number, isDraftExport = false) { return request<ReportSnapshot>({ method: 'POST', url: `/document-instances/${instanceId}/snapshots`, data: { is_draft_export: isDraftExport } }) }
export function listReportSnapshots(instanceId: number) { return request<ReportSnapshot[]>({ method: 'GET', url: `/document-instances/${instanceId}/snapshots` }) }
export function startReportExport(snapshotId: number, reportTemplateId?: number, formats: Array<'docx' | 'pdf'> = ['docx', 'pdf']) { return request<ReportExportJob>({ method: 'POST', url: `/report-snapshots/${snapshotId}/exports`, data: { report_template_id: reportTemplateId, formats } }) }
export function listExportArtifacts(jobId: number) { return request<ExportArtifact[]>({ method: 'GET', url: `/report-export-jobs/${jobId}/artifacts` }) }
