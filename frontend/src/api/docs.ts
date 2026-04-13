import client from './client'
import type { DocumentDetail, DocumentListResponse, DocumentUploadResponse } from '../types/api'

export async function uploadDocument(formData: FormData): Promise<DocumentUploadResponse> {
  const params: Record<string, string> = {
    title: formData.get('title') as string,
    doc_type: (formData.get('doc_type') as string) || 'architecture',
  }

  const fileBody = new FormData()
  fileBody.append('file', formData.get('file') as File)

  const response = await client.post<DocumentUploadResponse>('/knowledge-base/upload', fileBody, {
    headers: { 'Content-Type': 'multipart/form-data' },
    params,
  })
  return response.data
}

export async function getDocument(id: string): Promise<DocumentDetail> {
  const response = await client.get<DocumentDetail>(`/knowledge-base/${id}`)
  return response.data
}

export async function listDocuments(page = 1, pageSize = 50): Promise<DocumentListResponse> {
  const response = await client.get<DocumentListResponse>('/knowledge-base', {
    params: { page, page_size: pageSize },
  })
  return response.data
}
