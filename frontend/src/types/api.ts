export interface MeetingUploadResponse {
  id: string
  title: string
  status: string
  file_name: string
  file_size_mb: number
  created_at: string
}

export interface MeetingListItem {
  id: string
  title: string
  status: 'uploaded' | 'processing' | 'completed' | 'failed'
  date: string | null
  duration_seconds: number | null
  participants: string[] | null
  created_at: string
}

export interface TranscriptSegment {
  start_time: number
  end_time: number
  speaker: string
  text: string
}

export interface Transcript {
  full_text: string
  language: string
  word_count: number
  segments: TranscriptSegment[]
}

export interface ActionItem {
  id: string
  description: string
  assignee: string | null
  due_date: string | null
  priority: 'high' | 'medium' | 'low' | string
  status: string
  source_quote: string | null
}

export interface Decision {
  id: string
  description: string
  participants: string[] | null
  rationale: string | null
  source_quote: string | null
}

export interface MeetingDetail {
  id: string
  title: string
  status: 'uploaded' | 'processing' | 'completed' | 'failed'
  date: string | null
  participants: string[] | null
  duration_seconds: number | null
  file_name: string
  error_message: string | null
  transcript: Transcript | null
  summary: string | null
  action_items: ActionItem[]
  decisions: Decision[]
  created_at: string
  updated_at: string
}

export interface MeetingListResponse {
  items: MeetingListItem[]
  total: number
  page: number
  page_size: number
}

export interface SearchResultItem {
  source_type: 'meeting' | 'incident' | 'doc'
  source_id: string | null
  source_title: string | null
  // backward-compat meeting fields
  meeting_id: string | null
  meeting_title: string | null
  chunk_text: string
  similarity_score: number
  timestamp_start: number | null
}

export interface SearchRequest {
  query: string
  source_type?: string
  source_id?: string
  // backward-compat
  meeting_id?: string
  top_k?: number
}

export interface SearchResponse {
  results: SearchResultItem[]
  query: string
}

export interface QARequest {
  question: string
  source_type?: string
  source_id?: string
  // backward-compat
  meeting_id?: string
}

export interface QAResponse {
  answer: string
  sources: SearchResultItem[]
  model: string
}

export interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  sources?: SearchResultItem[]
  isPending?: boolean
}

// ── Incident Types ─────────────────────────────────────────────────────────

export type IncidentSeverity = 'sev1' | 'sev2' | 'sev3' | 'sev4'
export type IncidentStatus = 'open' | 'mitigated' | 'resolved' | 'closed'
export type IncidentProcessingStatus = 'pending' | 'analyzing' | 'embedding' | 'completed' | 'failed'

export interface IncidentListItem {
  id: string
  title: string
  severity: IncidentSeverity
  status: IncidentStatus
  processing_status: IncidentProcessingStatus
  services_affected: string[]
  occurred_at: string | null
  created_at: string
}

export interface IncidentListResponse {
  items: IncidentListItem[]
  total: number
  page: number
  page_size: number
}

export interface IncidentTimelineEvent {
  id: string
  event_index: number
  occurred_at: string | null
  description: string
  event_type: string
}

export interface IncidentActionItem {
  id: string
  description: string
  assignee: string | null
  due_date: string | null
  priority: 'high' | 'medium' | 'low' | string
  status: string
  category: string | null
}

export interface IncidentPostmortem {
  executive_summary: string | null
  root_cause_analysis: string | null
  model_used: string | null
  created_at: string | null
}

export interface IncidentDetail {
  id: string
  title: string
  severity: IncidentSeverity
  status: IncidentStatus
  processing_status: IncidentProcessingStatus
  services_affected: string[]
  description: string | null
  raw_text: string | null
  file_name: string | null
  error_message: string | null
  occurred_at: string | null
  resolved_at: string | null
  postmortem: IncidentPostmortem | null
  timeline: IncidentTimelineEvent[]
  action_items: IncidentActionItem[]
  created_at: string
  updated_at: string | null
}

export interface IncidentUploadResponse {
  id: string
  title: string
  processing_status: string
  file_name?: string
  created_at: string
}

// ── Document Types ─────────────────────────────────────────────────────────

export type DocProcessingStatus = 'pending' | 'embedding' | 'completed' | 'failed'

export interface DocumentListItem {
  id: string
  title: string
  doc_type: string
  processing_status: DocProcessingStatus
  file_name: string | null
  file_size_bytes: number | null
  created_at: string
}

export interface DocumentListResponse {
  items: DocumentListItem[]
  total: number
  page: number
  page_size: number
}

export interface DocumentDetail {
  id: string
  title: string
  doc_type: string
  processing_status: DocProcessingStatus
  file_name: string | null
  file_size_bytes: number | null
  content: string | null
  error_message: string | null
  created_at: string
  updated_at: string | null
}

export interface DocumentUploadResponse {
  id: string
  title: string
  processing_status: string
  file_name?: string
  created_at: string
}
