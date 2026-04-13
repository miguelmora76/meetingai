import client from './client'
import type {
  MeetingUploadResponse,
  MeetingDetail,
  MeetingListResponse,
} from '../types/api'

export async function uploadMeeting(formData: FormData): Promise<MeetingUploadResponse> {
  // FastAPI expects file in the multipart body but title/date/participants as query params
  const params: Record<string, string> = {
    title: formData.get('title') as string,
  }
  const date = formData.get('date') as string | null
  const participants = formData.get('participants') as string | null
  if (date) params.date = date
  if (participants) params.participants = participants

  const fileBody = new FormData()
  fileBody.append('file', formData.get('file') as File)

  const response = await client.post<MeetingUploadResponse>('/meetings/upload', fileBody, {
    headers: { 'Content-Type': 'multipart/form-data' },
    params,
  })
  return response.data
}

export async function processMeeting(id: string): Promise<void> {
  await client.post(`/meetings/${id}/process`)
}

export async function getMeeting(id: string): Promise<MeetingDetail> {
  const response = await client.get<MeetingDetail>(`/meetings/${id}`)
  return response.data
}

export async function listMeetings(
  page = 1,
  pageSize = 20,
  status?: string,
): Promise<MeetingListResponse> {
  const params: Record<string, string | number> = { page, page_size: pageSize }
  if (status) params.status = status
  const response = await client.get<MeetingListResponse>('/meetings', { params })
  return response.data
}
