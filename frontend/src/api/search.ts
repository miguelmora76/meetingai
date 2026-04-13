import client from './client'
import type { SearchRequest, SearchResponse, QARequest, QAResponse } from '../types/api'

export async function searchMeetings(req: SearchRequest): Promise<SearchResponse> {
  // Strip undefined fields so the API doesn't receive nulls
  const payload: Record<string, unknown> = { query: req.query, top_k: req.top_k }
  if (req.source_type) payload.source_type = req.source_type
  if (req.source_id) payload.source_id = req.source_id
  const response = await client.post<SearchResponse>('/search', payload)
  return response.data
}

export async function askQuestion(req: QARequest): Promise<QAResponse> {
  const payload: Record<string, unknown> = { question: req.question }
  if (req.source_type) payload.source_type = req.source_type
  if (req.source_id) payload.source_id = req.source_id
  const response = await client.post<QAResponse>('/qa', payload)
  return response.data
}
