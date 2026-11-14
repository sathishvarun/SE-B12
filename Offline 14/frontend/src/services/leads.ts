import api from "@/services/api"
import type {
  ConvertLeadInput,
  ConvertLeadResult,
  Lead,
  LeadInput,
  LeadSource,
  LeadStatus,
  Page,
  PaginationParams,
} from "@/types"

export interface LeadListParams extends PaginationParams {
  status?: LeadStatus
  source?: LeadSource
  search?: string
}

export async function listLeads(params: LeadListParams = {}): Promise<Page<Lead>> {
  const { data } = await api.get<Page<Lead>>("/leads", { params })
  return data
}

export async function getLead(id: number): Promise<Lead> {
  const { data } = await api.get<Lead>(`/leads/${id}`)
  return data
}

export async function createLead(input: LeadInput): Promise<Lead> {
  const { data } = await api.post<Lead>("/leads", input)
  return data
}

export async function updateLead(id: number, input: LeadInput): Promise<Lead> {
  const { data } = await api.put<Lead>(`/leads/${id}`, input)
  return data
}

/** Change status. "converted" is not allowed here - use convertLead instead. */
export async function updateLeadStatus(id: number, status: Exclude<LeadStatus, "converted">): Promise<Lead> {
  const { data } = await api.patch<Lead>(`/leads/${id}/status`, { status })
  return data
}

export async function deleteLead(id: number): Promise<void> {
  await api.delete(`/leads/${id}`)
}

/** Turn a lead into a contact + deal in one step. */
export async function convertLead(id: number, input: ConvertLeadInput): Promise<ConvertLeadResult> {
  const { data } = await api.post<ConvertLeadResult>(`/leads/${id}/convert`, input)
  return data
}
