import { LEAD_STATUS_LABELS } from "@/components/leads/constants"
import i18n from "@/i18n"
import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { toast } from "sonner"

import { getErrorMessage } from "@/services/api"
import {
  convertLead,
  createLead,
  deleteLead,
  getLead,
  listLeads,
  updateLead,
  updateLeadStatus,
  type LeadListParams,
} from "@/services/leads"
import type { ConvertLeadInput, LeadInput, LeadStatus } from "@/types"

export const leadKeys = {
  all: ["leads"] as const,
  list: (params: LeadListParams) => ["leads", params] as const,
  detail: (id: number) => ["leads", "detail", id] as const,
}

export function useLeads(params: LeadListParams) {
  return useQuery({
    queryKey: leadKeys.list(params),
    queryFn: () => listLeads(params),
    placeholderData: keepPreviousData,
  })
}

export function useLead(id: number) {
  return useQuery({
    queryKey: leadKeys.detail(id),
    queryFn: () => getLead(id),
    enabled: Number.isFinite(id),
  })
}

export function useCreateLead() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (input: LeadInput) => createLead(input),
    onSuccess: (lead) => {
      toast.success(i18n.t("leads.toast.created", { name: lead.name }))
      void queryClient.invalidateQueries({ queryKey: leadKeys.all })
      void queryClient.invalidateQueries({ queryKey: ["dashboard"] })
    },
    onError: (err) => toast.error(getErrorMessage(err)),
  })
}

export function useUpdateLead(id: number) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (input: LeadInput) => updateLead(id, input),
    onSuccess: () => {
      toast.success(i18n.t("leads.toast.updated"))
      void queryClient.invalidateQueries({ queryKey: leadKeys.all })
    },
    onError: (err) => toast.error(getErrorMessage(err)),
  })
}

export function useUpdateLeadStatus(id: number) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (status: Exclude<LeadStatus, "converted">) => updateLeadStatus(id, status),
    onSuccess: (lead) => {
      toast.success(i18n.t("leads.toast.statusChanged", { status: LEAD_STATUS_LABELS[lead.status] }))
      void queryClient.invalidateQueries({ queryKey: leadKeys.all })
      void queryClient.invalidateQueries({ queryKey: ["dashboard"] })
    },
    onError: (err) => toast.error(getErrorMessage(err)),
  })
}

export function useDeleteLead() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (id: number) => deleteLead(id),
    onSuccess: () => {
      toast.success(i18n.t("leads.toast.deleted"))
      void queryClient.invalidateQueries({ queryKey: leadKeys.all })
      void queryClient.invalidateQueries({ queryKey: ["dashboard"] })
    },
    onError: (err) => toast.error(getErrorMessage(err)),
  })
}

export function useConvertLead(id: number) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (input: ConvertLeadInput) => convertLead(id, input),
    onSuccess: (result) => {
      toast.success(i18n.t("leads.toast.converted", { contact: result.contact.name, deal: result.deal.title }))
      // Converting creates a contact and a deal, so refresh those too.
      void queryClient.invalidateQueries({ queryKey: leadKeys.all })
      void queryClient.invalidateQueries({ queryKey: ["contacts"] })
      void queryClient.invalidateQueries({ queryKey: ["deals"] })
      void queryClient.invalidateQueries({ queryKey: ["dashboard"] })
    },
    onError: (err) => toast.error(getErrorMessage(err)),
  })
}
