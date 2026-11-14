import i18n from "@/i18n"
import { useTranslation } from "react-i18next"
import { useState } from "react"
import { zodResolver } from "@hookform/resolvers/zod"
import { useForm } from "react-hook-form"
import { useNavigate } from "react-router-dom"
import { z } from "zod"

import { PlanLimitNotice } from "@/components/contacts/PlanLimitNotice"
import { isPlanLimitError } from "@/components/contacts/utils"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { useConvertLead } from "@/hooks/useLeads"
import { getErrorMessage } from "@/services/api"
import type { Lead } from "@/types"

const convertSchema = z.object({
  deal_title: z.string().trim().min(1, { error: () => i18n.t("validation.dealTitleRequired") }),
  deal_value: z
    .string()
    .trim()
    .min(1, { error: () => i18n.t("validation.dealValueRequired") })
    .refine((v) => !Number.isNaN(Number(v)) && Number(v) >= 0, {
      error: () => i18n.t("validation.amountNonNegative"),
    }),
  expected_close_date: z.string(),
})

type ConvertFormValues = z.infer<typeof convertSchema>

interface ConvertLeadDialogProps {
  lead: Lead
  open: boolean
  onOpenChange: (open: boolean) => void
}

/** Converts a lead into a contact + deal, then opens the new contact. */
export function ConvertLeadDialog({ lead, open, onOpenChange }: ConvertLeadDialogProps) {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const convert = useConvertLead(lead.id)
  const [limitMessage, setLimitMessage] = useState<string | null>(null)

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<ConvertFormValues>({
    resolver: zodResolver(convertSchema),
    defaultValues: {
      deal_title: t("leads.defaultDealTitle", { name: lead.company ?? lead.name }),
      deal_value: "",
      expected_close_date: "",
    },
  })

  const submit = (values: ConvertFormValues) => {
    setLimitMessage(null)
    convert.mutate(
      {
        deal_title: values.deal_title.trim(),
        deal_value: values.deal_value.trim(),
        expected_close_date: values.expected_close_date || null,
      },
      {
        onSuccess: (result) => {
          onOpenChange(false)
          navigate(`/contacts/${result.contact.id}`)
        },
        onError: (err) => {
          if (isPlanLimitError(err)) setLimitMessage(getErrorMessage(err))
        },
      },
    )
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>{t("leads.convertTitle")}</DialogTitle>
          <DialogDescription>
            {t("leads.convertText", { name: lead.name })}
          </DialogDescription>
        </DialogHeader>
        <form id="convert-lead-form" onSubmit={handleSubmit(submit)} noValidate className="flex flex-col gap-4">
          {limitMessage && <PlanLimitNotice message={limitMessage} />}
          <div className="flex flex-col gap-2">
            <Label htmlFor="deal-title">{t("leads.dealTitle")}</Label>
            <Input id="deal-title" aria-invalid={!!errors.deal_title} {...register("deal_title")} />
            {errors.deal_title && <p className="text-sm text-destructive">{errors.deal_title.message}</p>}
          </div>
          <div className="flex flex-col gap-2">
            <Label htmlFor="deal-value">{t("leads.dealValue")}</Label>
            <Input
              id="deal-value"
              type="number"
              min="0"
              step="0.01"
              inputMode="decimal"
              aria-invalid={!!errors.deal_value}
              {...register("deal_value")}
            />
            {errors.deal_value && <p className="text-sm text-destructive">{errors.deal_value.message}</p>}
          </div>
          <div className="flex flex-col gap-2">
            <Label htmlFor="deal-close">{t("common.expectedCloseDate")}</Label>
            <Input id="deal-close" type="date" {...register("expected_close_date")} />
          </div>
        </form>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)} disabled={convert.isPending}>
            {t("common.cancel")}
          </Button>
          <Button type="submit" form="convert-lead-form" disabled={convert.isPending}>
            {convert.isPending ? t("leads.converting") : t("leads.convert")}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
