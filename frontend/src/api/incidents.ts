import client from './client'
import type {
  IncidentDetail,
  IncidentListResponse,
  IncidentUploadResponse,
} from '../types/api'

export interface CreateIncidentPayload {
  title: string
  severity: string
  status: string
  services_affected: string[]
  description?: string
  occurred_at?: string
}

export async function createIncident(payload: CreateIncidentPayload): Promise<IncidentUploadResponse> {
  const response = await client.post<IncidentUploadResponse>('/incidents', payload)
  return response.data
}

export async function uploadIncident(formData: FormData): Promise<IncidentUploadResponse> {
  const params: Record<string, string> = {
    title: formData.get('title') as string,
    severity: (formData.get('severity') as string) || 'sev3',
    status: (formData.get('status') as string) || 'open',
  }
  const servicesAffected = formData.get('services_affected') as string | null
  if (servicesAffected) params.services_affected = servicesAffected
  const occurredAt = formData.get('occurred_at') as string | null
  if (occurredAt) params.occurred_at = occurredAt

  const fileBody = new FormData()
  fileBody.append('file', formData.get('file') as File)

  const response = await client.post<IncidentUploadResponse>('/incidents/upload', fileBody, {
    headers: { 'Content-Type': 'multipart/form-data' },
    params,
  })
  return response.data
}

export async function getIncident(id: string): Promise<IncidentDetail> {
  const response = await client.get<IncidentDetail>(`/incidents/${id}`)
  return response.data
}

export async function listIncidents(page = 1, pageSize = 20): Promise<IncidentListResponse> {
  const response = await client.get<IncidentListResponse>('/incidents', {
    params: { page, page_size: pageSize },
  })
  return response.data
}
