import type {
  Activity,
  Attributes,
  CaseCreate,
  CaseDetail,
  CaseList,
  CaseQuery,
  CaseUpdate,
  DashboardStats,
  DatasetStatusResponse,
  Description,
  DescriptionCreate,
  EngineStatus,
  Evaluation,
  GenerateBody,
  InspectResult,
  Language,
  Meta,
  Note,
  ParseResponse,
  ReviseBody,
  SketchVersion,
  SketchVersionList,
  TokenResponse,
  User,
} from '@/types/api'
import { request, requestBlob } from './http'

type Signal = { signal?: AbortSignal }

/** One typed function per backend endpoint (see docs/API.md). */
export const api = {
  meta: (o?: Signal) => request<Meta>('/api/meta/attributes', o),

  register: (body: { username: string; password: string; display_name?: string; acknowledge_responsible_use: boolean }) =>
    request<TokenResponse>('/api/auth/register', { method: 'POST', body }),
  login: (body: { username: string; password: string }) => request<TokenResponse>('/api/auth/login', { method: 'POST', body }),
  me: (o?: Signal) => request<User>('/api/auth/me', o),

  dashboard: (o?: Signal) => request<DashboardStats>('/api/dashboard', o),
  activity: (limit = 20, o?: Signal) => request<Activity[]>('/api/activity', { query: { limit }, ...o }),

  listCases: (query: CaseQuery, o?: Signal) => request<CaseList>('/api/cases', { query: { ...query }, ...o }),
  createCase: (body: CaseCreate) => request<CaseDetail>('/api/cases', { method: 'POST', body }),
  getCase: (caseId: string, o?: Signal) => request<CaseDetail>(`/api/cases/${encodeURIComponent(caseId)}`, o),
  updateCase: (caseId: string, body: CaseUpdate) => request<CaseDetail>(`/api/cases/${encodeURIComponent(caseId)}`, { method: 'PATCH', body }),
  deleteCase: (caseId: string) => request<void>(`/api/cases/${encodeURIComponent(caseId)}`, { method: 'DELETE' }),
  listNotes: (caseId: string, o?: Signal) => request<Note[]>(`/api/cases/${encodeURIComponent(caseId)}/notes`, o),
  addNote: (caseId: string, body: { body: string; sketch_version_id?: number | null }) =>
    request<Note>(`/api/cases/${encodeURIComponent(caseId)}/notes`, { method: 'POST', body }),

  parseDescription: (body: { text: string; language: Language }) => request<ParseResponse>('/api/descriptions/parse', { method: 'POST', body }),
  listDescriptions: (caseId: string, o?: Signal) => request<Description[]>(`/api/cases/${encodeURIComponent(caseId)}/descriptions`, o),
  saveDescription: (caseId: string, body: DescriptionCreate) =>
    request<Description>(`/api/cases/${encodeURIComponent(caseId)}/descriptions`, { method: 'POST', body }),
  updateDescription: (caseId: string, id: number, body: { confirmed_attributes: Attributes; additional_details: string }) =>
    request<Description>(`/api/cases/${encodeURIComponent(caseId)}/descriptions/${id}`, { method: 'PUT', body }),

  generateSketch: (body: GenerateBody) => request<SketchVersion>('/api/sketches/generate', { method: 'POST', body }),
  reviseSketch: (sketchId: number, body: ReviseBody) => request<SketchVersion>(`/api/sketches/${sketchId}/revise`, { method: 'POST', body }),
  listVersions: (caseId: string, o?: Signal) => request<SketchVersionList>('/api/sketch-versions', { query: { case_id: caseId }, ...o }),
  selectVersion: (sketchId: number) => request<SketchVersion>(`/api/sketch-versions/${sketchId}/select`, { method: 'POST' }),
  engines: (o?: Signal) => request<EngineStatus[]>('/api/engines', o),

  datasetsStatus: (o?: Signal) => request<DatasetStatusResponse>('/api/datasets/status', o),
  inspectDatasets: (datasetKey?: string) =>
    request<{ results: InspectResult[] }>('/api/datasets/inspect', { method: 'POST', body: datasetKey ? { dataset_key: datasetKey } : {} }),
  listEvaluations: (o?: Signal) => request<Evaluation[]>('/api/evaluations', o),
  runEvaluation: (body: { split: 'dev' | 'test' | 'all'; only_reviewed_translations: boolean }) =>
    request<Evaluation>('/api/evaluations', { method: 'POST', body: { evaluation_type: 'description_parser', ...body } }),

  downloadReport: (caseId: string) => requestBlob(`/api/cases/${encodeURIComponent(caseId)}/report`),
  imageBlob: (url: string, o?: Signal) => requestBlob(url, o),
}
