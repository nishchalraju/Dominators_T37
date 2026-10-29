// Types mirroring the backend's Pydantic schemas (see docs/API.md).

export type Language = 'en' | 'kn' | 'hi'
export type CaseStatus = 'in_progress' | 'under_review' | 'closed'
export type Role = 'admin' | 'investigator'
export type EngineChoice = 'ai' | 'schematic'
/** attribute key -> controlled value (null/missing = not specified) */
export type Attributes = Record<string, string | null>

// ---- meta ------------------------------------------------------------------------------------
export interface AttributeValueMeta {
  value: string
  label: string
  /** Optional colour chip (#rrggbb), for example the skin colours. The schematic engine paints exactly this colour. */
  swatch?: string
}
export interface AttributeMeta {
  key: string
  label: string
  ordered: boolean
  schematic_supported: boolean
  values: AttributeValueMeta[]
}
export interface LanguageMeta {
  code: Language
  label: string
  native_label: string
}
export interface Meta {
  app: { name: string; version: string }
  vocabulary_version: string
  attributes: AttributeMeta[]
  languages: LanguageMeta[]
  case_statuses: CaseStatus[]
  max_additional_details: number
  parser: { name: string; version: string; lexicon_status: Record<string, string> }
  disclaimers: { preliminary: string; no_identification: string; responsible_use: string[] }
  registration_open: boolean
}

// ---- auth ------------------------------------------------------------------------------------
export interface User {
  id: number
  username: string
  display_name: string | null
  role: Role
  created_at: string
}
export interface TokenResponse {
  access_token: string
  token_type: string
  expires_in: number
  user: User
}

// ---- cases ------------------------------------------------------------------------------------
export interface CaseSummary {
  case_id: string
  title: string
  incident_date: string
  status: CaseStatus
  investigator_ref: string
  /** Empty string = not recorded (the case was created before names were collected). */
  investigator_name: string
  witness_name: string
  created_at: string
  updated_at: string
  description_count: number
  sketch_count: number
  selected_sketch_id: number | null
}
export interface CaseDetail extends CaseSummary {
  incident_description: string
  note_count: number
  owner_username: string | null
}
export interface CaseList {
  items: CaseSummary[]
  total: number
  page: number
  page_size: number
}
export interface CaseCreate {
  title: string
  incident_date: string
  incident_description: string
  investigator_ref: string
  investigator_name: string
  witness_name: string
}
export type CaseUpdate = Partial<CaseCreate> & { status?: CaseStatus }
export interface CaseQuery {
  q?: string
  status?: CaseStatus | ''
  sort?: 'updated_desc' | 'created_desc' | 'title_asc' | 'incident_desc'
  page?: number
  page_size?: number
}
export interface Note {
  id: number
  body: string
  sketch_version_id: number | null
  author_username: string | null
  created_at: string
}
export interface Activity {
  id: number
  action: string
  summary: string
  case_ref: string | null
  username: string | null
  created_at: string
}
export interface DashboardStats {
  scope: 'own' | 'all'
  total_cases: number
  status_counts: Record<CaseStatus, number>
  cases_with_selected_sketch: number
  witness_descriptions: number
  sketch_versions: number
  schematic_versions: number
  ai_versions: number
  notes: number
  recent_cases: CaseSummary[]
  recent_activity: Activity[]
}

// ---- descriptions -------------------------------------------------------------------------------
export interface ExtractedValue {
  attribute: string
  value: string
  evidence: string
  language: string
  match_type: string
  note: string | null
}
export interface Unrecognized {
  text: string
  reason: string
}
export interface Conflict {
  attribute: string
  values: string[]
  evidence: string[]
}
export interface ParseResponse {
  attributes: Attributes
  details: ExtractedValue[]
  unrecognized: Unrecognized[]
  conflicts: Conflict[]
  warnings: string[]
  declared_language: string
  detected_scripts: string[]
  parser_name: string
  parser_version: string
  lexicon_status: Record<string, string>
  notice: string
}
export interface Description {
  id: number
  label: string
  language: Language
  original_text: string
  extracted_attributes: Attributes
  confirmed_attributes: Attributes
  additional_details: string
  parse_details: ExtractedValue[]
  unrecognized: Unrecognized[]
  warnings: string[]
  parser_version: string
  created_at: string
  updated_at: string
  review_status: 'parser_output' | 'edited_by_investigator'
}
export interface DescriptionCreate {
  label: string
  language: Language
  original_text: string
  confirmed_attributes?: Attributes
  additional_details?: string
}

// ---- sketches --------------------------------------------------------------------------------------
export interface Change {
  attribute: string
  label: string
  before: string | null
  after: string
  evidence: string
  kind: string
  note: string | null
}
export interface RevisionDetails {
  changes: Change[]
  ignored: Unrecognized[]
  notes: string[]
}
export interface SketchVersion {
  id: number
  case_id: string
  version_number: number
  parent_id: number | null
  parent_version_number: number | null
  kind: 'initial' | 'revision'
  instruction: string
  instruction_language: string | null
  target_attribute: string | null
  attributes: Attributes
  additional_details: string
  engine: string
  engine_label: string
  is_ai_generated: boolean
  model_name: string | null
  notes: string[]
  revision_details: RevisionDetails | null
  is_selected: boolean
  created_by: string | null
  created_at: string
  width: number
  height: number
  file_size: number
  sha256: string
  image_url: string
  thumbnail_url: string
  download_url: string
}
export interface SketchVersionList {
  case_id: string
  items: SketchVersion[]
}
export interface GenerateBody {
  case_id: string
  description_id?: number | null
  attributes?: Attributes | null
  additional_details?: string | null
  engine: EngineChoice
}
export interface ReviseBody {
  instruction: string
  language: Language
  engine?: EngineChoice | null
}
export interface EngineStatus {
  engine: string
  label: string
  is_ai: boolean
  state: 'ready' | 'setup_required' | 'disabled'
  available: boolean
  detail: string
  setup_steps: string[]
  supports_generate: boolean
  supports_edit: boolean
  models: Record<string, string>
  licence_note: string | null
  verified: boolean
  last_success_at: string | null
  last_error: string | null
  last_error_at: string | null
  last_evaluated_at: string | null
}

// ---- datasets and evaluation --------------------------------------------------------------------------
export interface DatasetStatus {
  key: string
  name: string
  kind: 'external' | 'custom'
  description: string
  licence: string
  access: string
  citation: string
  source_url: string
  expected_path: string
  installed: boolean
  inspected: boolean
  last_inspected_at: string | null
  files_found: number | null
  records: number
  valid_records: number
  labelled_records: number
  notes: string[]
  translation_review: Record<string, number> | null
}
export interface DatasetStatusResponse {
  datasets: DatasetStatus[]
  totals: Record<string, number>
}
export interface InspectResult {
  dataset_key: string
  installed: boolean
  files_found: number
  valid: number
  invalid: number
  truncated: boolean
  summary: Record<string, unknown>
  problems: { record: string; problems: string[] }[]
  notes: string[]
  inspected_at: string
}
export interface AttributeMetric {
  attribute: string
  label: string
  n_gold: number
  tp: number
  fp: number
  fn: number
  accuracy: number | null
  precision: number | null
  recall: number | null
}
export interface LanguageMetric {
  language: string
  n: number
  exact_match: number | null
  mean_attribute_accuracy: number | null
  lexicon_review_status: string
  translation_reviewed_n: number
}
export interface EvaluationMetrics {
  n_examples: number
  exact_match: number | null
  micro_precision: number | null
  micro_recall: number | null
  per_attribute: AttributeMetric[]
  by_language: LanguageMetric[]
  cross_language_agreement: { groups: number; agreement: number | null }
  failures_listed: { sample_id: string; language: string; wrong: { attribute: string; expected: string | null; got: string | null }[] }[]
  caveats: string[]
  selection?: { split: string; only_reviewed_translations: boolean; invalid_rows_excluded: number }
}
export interface Evaluation {
  id: number
  evaluation_type: string
  target_name: string
  target_version: string
  dataset_name: string
  dataset_version: string
  split: string
  n_examples: number
  metrics: EvaluationMetrics
  notes: string | null
  status: string
  created_at: string
}
