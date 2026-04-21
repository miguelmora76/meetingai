import client from './client'
import type {
  AirtableBasesListResponse,
  AirtableConnection,
  AirtableImportRequest,
  AirtableImportStatusResponse,
  AirtableTablesListResponse,
} from '../types/api'

export async function getAirtableConnection(): Promise<AirtableConnection> {
  const response = await client.get<AirtableConnection>('/airtable/connection')
  return response.data
}

export async function connectAirtable(token: string): Promise<AirtableConnection> {
  const response = await client.post<AirtableConnection>('/airtable/connect', { token })
  return response.data
}

export async function disconnectAirtable(): Promise<void> {
  await client.delete('/airtable/connection')
}

export async function listAirtableBases(): Promise<AirtableBasesListResponse> {
  const response = await client.get<AirtableBasesListResponse>('/airtable/bases')
  return response.data
}

export async function listAirtableTables(baseId: string): Promise<AirtableTablesListResponse> {
  const response = await client.get<AirtableTablesListResponse>(
    `/airtable/bases/${baseId}/tables`,
  )
  return response.data
}

export async function startAirtableImport(
  request: AirtableImportRequest,
): Promise<AirtableImportStatusResponse> {
  const response = await client.post<AirtableImportStatusResponse>('/airtable/import', request)
  return response.data
}

export async function getAirtableImport(
  importId: string,
): Promise<AirtableImportStatusResponse> {
  const response = await client.get<AirtableImportStatusResponse>(
    `/airtable/imports/${importId}`,
  )
  return response.data
}
