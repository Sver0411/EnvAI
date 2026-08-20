export type ProjectType = 'environmental_impact' | 'emergency_response' | 'risk_assessment' | 'other'

export type ProjectStatus = 'draft' | 'collecting_data' | 'analyzing' | 'generating' | 'reviewing' | 'completed'

export interface User {
  id: number
  username: string
  email: string
  full_name: string | null
  is_active: boolean
  platform_role?: 'user' | 'platform_admin' | 'platform_super_admin'
  status?: string
  last_login_at?: string | null
  created_at: string
}

export interface AdminPage<T> { items: T[]; total: number; page: number; page_size: number }
export interface AdminDashboard { organizations: number; active_organizations: number; users: number; active_users: number; projects: number; documents_generated: number; ai_requests: number; llm_tokens: number; embedding_usage: number; storage_bytes: number; exports: number; failed_jobs: number; start: string; end: string }
export interface AdminOrganization { id: number; name: string; slug: string; status: string; plan_id: number | null; members_count: number; projects_count: number; usage: number; created_at: string }

export interface TokenOut {
  access_token: string
  token_type: string
  user: User
}

export interface Project {
  id: number
  name: string
  project_type: ProjectType
  company_name: string | null
  status: ProjectStatus
  description: string | null
  owner_id: number
  created_at: string
  updated_at: string
}

export interface ProjectPage {
  items: Project[]
  total: number
  page: number
  page_size: number
}

export interface RawMaterial {
  name: string
  annual_usage: string
  unit: string
  max_storage: string
  storage_location: string
  cas_number: string
}

export interface CompanyProfile {
  id: number
  project_id: number
  company_name: string | null
  credit_code: string | null
  legal_representative: string | null
  contact_name: string | null
  contact_phone: string | null
  project_address: string | null
  industry_category: string | null
  land_area: string | null
  building_area: string | null
  products: string | null
  annual_output: string | null
  production_process: string | null
  equipment: unknown[] | null
  raw_materials: RawMaterial[] | null
  pollution_control: Record<string, unknown> | null
  risk_substances: Record<string, unknown> | null
  created_at: string
  updated_at: string
}

export interface ProjectFile {
  id: number
  project_id: number
  uploader_id: number
  filename: string
  file_type: string | null
  file_size: number
  storage_path: string | null
  parse_status: 'uploaded' | 'parsing' | 'parsed' | 'failed'
  created_at: string
  updated_at: string
}

export type ParseDocumentStatus = 'pending' | 'parsing' | 'parsed' | 'failed'

export interface ParsedDocumentStatus {
  project_file_id: number
  status: ParseDocumentStatus
  parser_name: string | null
  parser_version: string | null
  error_message: string | null
  parsed_at: string | null
  warnings: string[]
}

export interface ParsedDocument extends ParsedDocumentStatus {
  id: number
  plain_text: string | null
  structured_content: Record<string, unknown> | null
  metadata: Record<string, unknown> | null
  created_at: string
  updated_at: string
}

export interface StructuredProduct {
  id: number
  project_id: number
  name: string
  annual_capacity: string | number | null
  unit: string | null
  specification: string | null
  notes: string | null
  verification_status: 'ai_extracted' | 'user_verified'
  source_fact_id: number | null
}

export interface StructuredEquipment {
  id: number
  project_id: number
  name: string
  model: string | null
  quantity: string | number | null
  unit: string | null
  power: string | number | null
  power_unit: string | null
  location: string | null
  notes: string | null
  verification_status: 'ai_extracted' | 'user_verified'
  source_fact_id: number | null
}

export interface StructuredRawMaterial {
  id: number
  project_id: number
  name: string
  annual_usage: string | number | null
  annual_usage_unit: string | null
  max_storage: string | number | null
  storage_unit: string | null
  storage_location: string | null
  cas_number: string | null
  hazardous: boolean | null
  risk_material: boolean | null
  verification_status: 'ai_extracted' | 'user_verified'
  source_fact_id: number | null
}

export interface ExtractedFact {
  id: number
  project_id: number
  extraction_run_id: number
  project_file_id: number | null
  entity_type: string
  entity_key: string
  field_name: string
  raw_value: string
  normalized_value: Record<string, unknown> | null
  unit: string | null
  confidence: string | number | null
  source_type: string
  source_location: Record<string, unknown> | null
  source_text: string | null
  status: 'pending' | 'accepted' | 'rejected' | 'conflict' | 'superseded'
  verification_status: string
  source_filename: string | null
}

export interface DataConflict {
  id: number
  project_id: number
  extraction_run_id: number
  entity_type: string
  entity_key: string
  field_name: string
  value_a: string
  value_b: string
  fact_a_id: number | null
  fact_b_id: number | null
  source_a: Record<string, unknown> | null
  source_b: Record<string, unknown> | null
  status: 'open' | 'resolved' | 'ignored'
  resolution: string | null
}

export interface ExtractionRun {
  id: number
  project_id: number
  status: string
  files_count: number
  facts_count: number
  conflicts_count: number
  provider_name: string | null
  model_name: string | null
  error_message: string | null
}

export interface StructuredProjectData {
  profile: CompanyProfile | null
  products: StructuredProduct[]
  equipment: StructuredEquipment[]
  raw_materials: StructuredRawMaterial[]
  environmental_facilities: Array<Record<string, unknown>>
  facts: ExtractedFact[]
  conflicts: DataConflict[]
  latest_run: ExtractionRun | null
}

export interface ApiResponse<T> {
  code: number
  message: string
  data: T | null
}

export interface KnowledgeBase {
  id: number
  name: string
  description: string | null
  scope: 'system' | 'private'
  status: string
  created_by: number
  created_at: string
  updated_at: string
  document_count: number
}

export interface KnowledgeDocument {
  id: number
  knowledge_base_id: number
  title: string
  document_type: string
  document_number: string | null
  issuing_authority: string | null
  publish_date: string | null
  effective_date: string | null
  expiry_date: string | null
  version: string | null
  revision: string | null
  status: string
  source_url: string | null
  original_file_name: string
  mime_type: string | null
  file_size: number
  sha256: string
  language: string
  country: string | null
  province: string | null
  city: string | null
  district: string | null
  source_authority: string
  parser_status: string
  index_status: string
  parser_name: string | null
  parser_version: string | null
  error_message: string | null
  created_by: number | null
  created_at: string
  updated_at: string
  categories: string[]
  chunk_count: number
}

export interface KnowledgeChunk {
  id: number
  knowledge_document_id: number
  chunk_index: number
  content: string
  content_type: string
  section_title: string | null
  section_level: number | null
  section_path: string[] | null
  article_number: string | null
  page_start: number | null
  page_end: number | null
  table_index: number | null
  structured_table: Record<string, unknown> | null
  token_count: number
  character_count: number
  metadata_json: Record<string, unknown> | null
  content_hash: string
  chunk_fingerprint: string
  embedding_status: string
}

export interface KnowledgeSearchResult {
  chunk_id: number
  document_id: number
  document_title: string
  document_number: string | null
  document_type: string
  categories: string[]
  jurisdiction: Record<string, string | null>
  version: string | null
  status: string
  section_title: string | null
  section_path: string[] | null
  article_number: string | null
  page_start: number | null
  page_end: number | null
  content: string
  vector_score: number | null
  keyword_score: number
  rerank_score: number | null
  final_score: number
}

export interface KnowledgeSearchResponse {
  query: string
  results: KnowledgeSearchResult[]
}

export interface TemplateSection { id: number; template_id: number; parent_id: number | null; section_code: string; title: string; level: number; sort_order: number; description: string | null; generation_mode: string; required: boolean; enabled: boolean; children: TemplateSection[] }
export interface DocumentTemplate { id: number; name: string; code: string; document_type: string; description: string | null; version: string; status: string; sections: TemplateSection[] }
export interface DocumentInstance { id: number; project_id: number; template_id: number; title: string; status: string; reference_date: string | null; created_by: number; organization_id?: number | null; created_at: string; updated_at: string }
export interface MissingInformation { field: string; reason: string }
export interface SectionPreflight { ready: boolean; missing_fields: MissingInformation[]; conflicts: string[]; warnings: string[]; project_fact_count: number; project_source_count: number; knowledge_source_count: number }
export interface SectionDraft { id: number; project_id: number; document_instance_id: number; template_id: number; section_id: number; generation_run_id: number | null; content: string; ai_original_content: string | null; status: string; version: number; citations: Array<{ source_id: string; claim: string }>; missing_information: MissingInformation[]; warnings: string[]; generation_metadata: Record<string, unknown> | null; created_at: string; updated_at: string }
export interface SectionView { section: TemplateSection; draft: SectionDraft | null }
export interface GenerationRun { id: number; project_id: number; document_instance_id: number; section_id: number; status: string; ai_provider: string | null; model: string | null; prompt_version: string | null; input_tokens: number | null; output_tokens: number | null; project_fact_count: number; project_source_count: number; knowledge_source_count: number; error_message: string | null; started_at: string; completed_at: string | null }
export interface SectionInstance { id: number; document_instance_id: number; template_section_id: number; parent_id: number | null; section_code: string; title: string; level: number; sort_order: number; status: string; generation_enabled: boolean; current_draft_id: number | null; approved_version_id: number | null; blocked_reason: string | null; stale_reason: string | null; updated_at: string }
export interface DocumentOverview { instance: { id: number; title: string; status: string; template_version: string }; summary: { total_sections: number; ready_sections: number; blocked_sections: number; completed_sections: number; missing_data_sections: number; conflict_sections: number; warnings: string[]; missing_fields: Array<Record<string, unknown>> }; sections: SectionInstance[] }
export interface BatchGenerationRun { id: number; document_instance_id: number; status: string; total_sections: number; queued_sections: number; completed_sections: number; failed_sections: number; blocked_sections: number; partial_sections: number; started_by: number; started_at: string; completed_at: string | null }
export interface ValidationRun { id: number; document_instance_id: number; status: string; issues_count: number; critical_count: number; warning_count: number; created_by: number; started_at: string; completed_at: string | null }
export interface ValidationIssue { id: number; validation_run_id: number; issue_type: string; severity: string; section_a_id: number | null; section_b_id: number | null; entity_type: string | null; field_name: string | null; expected_value: string | null; actual_value: string | null; message: string; status: string; created_at: string }
export interface Readiness { ready_for_export: boolean; blocking_reasons: string[]; warnings: string[]; required_sections: number; approved_sections: number }
export interface ProfessionalReviewRun { id: number; document_instance_id: number; status: string; review_mode: string; rule_set_id: number | null; rule_set_version: string | null; ai_provider: string | null; ai_model: string | null; issues_count: number; critical_count: number; major_count: number; minor_count: number; input_tokens: number | null; output_tokens: number | null; ai_calls: number; error_message: string | null; started_by: number; started_at: string; completed_at: string | null }
export interface ReviewIssue { id: number; document_instance_id: number; review_run_id: number; section_instance_id: number | null; issue_source: string; issue_type: string; severity: string; title: string; description: string; evidence: Record<string, unknown> | null; suggestion: string | null; confidence: number | null; status: string; dismissal_reason: string | null; created_at: string }
export interface QualityScore { id: number; document_instance_id: number; review_run_id: number | null; overall_score: number; data_integrity_score: number; citation_score: number; coverage_score: number; completeness_score: number; consistency_score: number; critical_issue_count: number; major_issue_count: number; quality_passed: boolean; created_at: string }
export interface QualityGate { passed: boolean; blocking_issues: number; critical: number; major: number; score?: number; reason?: string }
export interface ReportTemplate { id: number; name: string; code: string; document_type: string; version: string; status: string; original_file_name: string; file_size: number; engine: string; created_at: string }
export interface ExportPreflight { ready: boolean; blocking_issues: string[]; warnings: string[]; selected_template?: string | null; selected_template_id?: number | null; snapshot_required: boolean; pdf_available: boolean }
export interface ReportSnapshot { id: number; document_instance_id: number; snapshot_number: number; status: string; document_title: string; template_id: number; template_version: string; quality_review_run_id: number | null; content_hash: string; metadata_json: Record<string, unknown> | null; created_at: string }
export interface ReportExportJob { id: number; report_snapshot_id: number; report_template_id: number; status: string; requested_formats: string[]; docx_status: string; pdf_status: string; exporter_version: string; render_manifest: Record<string, unknown> | null; error_message: string | null; started_at: string; completed_at: string | null }
export interface ExportArtifact { id: number; export_job_id: number; format: string; file_name: string; mime_type: string; file_size: number; sha256: string; created_at: string }
export interface Organization { id: number; name: string; slug: string; status: string; created_by: number; plan_id: number | null; created_at: string }
export interface OrganizationMember { id: number; organization_id: number; user_id: number; role: string; status: string; joined_at: string | null; created_at: string }
export interface UsageSummary { organization_id: number; period: string; totals: Record<string, number>; member_count: number; project_count: number; storage_bytes: number; limits: Record<string, number | null> }
