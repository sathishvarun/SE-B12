import i18n from "@/i18n"
import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { toast } from "sonner"

import { getErrorMessage } from "@/services/api"
import {
  createContact,
  deleteContact,
  getContact,
  listContactOptions,
  listContacts,
  updateContact,
  type ContactListParams,
} from "@/services/contacts"
import { createTag, listTags } from "@/services/tags"
import type { ContactInput } from "@/types"

// Every contact query key starts with "contacts", so invalidating ["contacts"]
// refreshes lists, options and detail pages at once.
export const contactKeys = {
  all: ["contacts"] as const,
  list: (params: ContactListParams) => ["contacts", params] as const,
  options: ["contacts", "options"] as const,
  detail: (id: number) => ["contacts", "detail", id] as const,
}

export function useContacts(params: ContactListParams) {
  return useQuery({
    queryKey: contactKeys.list(params),
    queryFn: () => listContacts(params),
    placeholderData: keepPreviousData,
  })
}

export function useContactOptions() {
  return useQuery({ queryKey: contactKeys.options, queryFn: listContactOptions })
}

export function useContact(id: number) {
  return useQuery({
    queryKey: contactKeys.detail(id),
    queryFn: () => getContact(id),
    enabled: Number.isFinite(id),
  })
}

export function useCreateContact() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (input: ContactInput) => createContact(input),
    onSuccess: (contact) => {
      toast.success(i18n.t("contacts.toast.created", { name: contact.name }))
      void queryClient.invalidateQueries({ queryKey: contactKeys.all })
      void queryClient.invalidateQueries({ queryKey: ["dashboard"] })
    },
    onError: (err) => toast.error(getErrorMessage(err)),
  })
}

export function useUpdateContact(id: number) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (input: ContactInput) => updateContact(id, input),
    onSuccess: () => {
      toast.success(i18n.t("contacts.toast.updated"))
      void queryClient.invalidateQueries({ queryKey: contactKeys.all })
    },
    onError: (err) => toast.error(getErrorMessage(err)),
  })
}

export function useDeleteContact() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (id: number) => deleteContact(id),
    onSuccess: () => {
      toast.success(i18n.t("contacts.toast.deleted"))
      // Deleting a contact also removes its deals and attachments.
      void queryClient.invalidateQueries({ queryKey: contactKeys.all })
      void queryClient.invalidateQueries({ queryKey: ["deals"] })
      void queryClient.invalidateQueries({ queryKey: ["tasks"] })
      void queryClient.invalidateQueries({ queryKey: ["dashboard"] })
    },
    onError: (err) => toast.error(getErrorMessage(err)),
  })
}

export function useTags() {
  return useQuery({ queryKey: ["tags"], queryFn: listTags })
}

export function useCreateTag() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (name: string) => createTag(name),
    onSuccess: (tag) => {
      toast.success(i18n.t("contacts.toast.tagCreated", { name: tag.name }))
      void queryClient.invalidateQueries({ queryKey: ["tags"] })
    },
    onError: (err) => toast.error(getErrorMessage(err)),
  })
}
