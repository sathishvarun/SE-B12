import api from "@/services/api"
import type { Contact, ContactDetail, ContactInput, ContactOption, Page, PaginationParams } from "@/types"

export interface ContactListParams extends PaginationParams {
  search?: string
  tag_id?: number
}

export async function listContacts(params: ContactListParams = {}): Promise<Page<Contact>> {
  const { data } = await api.get<Page<Contact>>("/contacts", { params })
  return data
}

/** All contacts as light options, for select dropdowns. */
export async function listContactOptions(): Promise<ContactOption[]> {
  const { data } = await api.get<ContactOption[]>("/contacts/options")
  return data
}

export async function getContact(id: number): Promise<ContactDetail> {
  const { data } = await api.get<ContactDetail>(`/contacts/${id}`)
  return data
}

export async function createContact(input: ContactInput): Promise<Contact> {
  const { data } = await api.post<Contact>("/contacts", input)
  return data
}

export async function updateContact(id: number, input: ContactInput): Promise<Contact> {
  const { data } = await api.put<Contact>(`/contacts/${id}`, input)
  return data
}

export async function deleteContact(id: number): Promise<void> {
  await api.delete(`/contacts/${id}`)
}
