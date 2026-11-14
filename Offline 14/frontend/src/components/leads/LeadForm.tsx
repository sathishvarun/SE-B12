import i18n from "@/i18n"
import { useTranslation } from "react-i18next"
import { zodResolver } from "@hookform/resolvers/zod"
import { Controller, useForm } from "react-hook-form"
import { z } from "zod"

import { GradientButton } from "@/components/common"
import { emptyToNull } from "@/components/contacts/utils"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Textarea } from "@/components/ui/textarea"
import type { Lead, LeadInput } from "@/types"

import { LEAD_SOURCE_LABELS, LEAD_SOURCES } from "./constants"

const leadSchema = z.object({
  name: z
    .string()
    .trim()
    .min(1, { error: () => i18n.t("validation.nameRequired") })
    .max(255, { error: () => i18n.t("validation.nameTooLong") }),
  email: z
    .string()
    .trim()
    .refine((v) => v === "" || z.email().safeParse(v).success, { error: () => i18n.t("validation.emailInvalid") }),
  phone: z.string(),
  company: z.string(),
  source: z.enum(["website", "referral", "social", "other"]),
  notes: z.string(),
})

type LeadFormValues = z.infer<typeof leadSchema>

interface LeadFormProps {
  lead?: Lead
  onSubmit: (input: LeadInput) => void
  isSubmitting?: boolean
  submitLabel?: string
}

export function LeadForm({ lead, onSubmit, isSubmitting = false, submitLabel }: LeadFormProps) {
  const { t } = useTranslation()
  const {
    register,
    control,
    handleSubmit,
    formState: { errors },
  } = useForm<LeadFormValues>({
    resolver: zodResolver(leadSchema),
    defaultValues: {
      name: lead?.name ?? "",
      email: lead?.email ?? "",
      phone: lead?.phone ?? "",
      company: lead?.company ?? "",
      source: lead?.source ?? "website",
      notes: lead?.notes ?? "",
    },
  })

  const submit = (values: LeadFormValues) => {
    onSubmit({
      name: values.name.trim(),
      email: emptyToNull(values.email),
      phone: emptyToNull(values.phone),
      company: emptyToNull(values.company),
      source: values.source,
      notes: emptyToNull(values.notes),
    })
  }

  return (
    <form onSubmit={handleSubmit(submit)} noValidate className="flex flex-col gap-5">
      <div className="grid gap-5 sm:grid-cols-2">
        <div className="flex flex-col gap-2">
          <Label htmlFor="lead-name">{t("common.nameRequiredLabel")}</Label>
          <Input id="lead-name" aria-invalid={!!errors.name} {...register("name")} />
          {errors.name && <p className="text-sm text-destructive">{errors.name.message}</p>}
        </div>
        <div className="flex flex-col gap-2">
          <Label htmlFor="lead-email">{t("common.email")}</Label>
          <Input id="lead-email" type="email" aria-invalid={!!errors.email} {...register("email")} />
          {errors.email && <p className="text-sm text-destructive">{errors.email.message}</p>}
        </div>
        <div className="flex flex-col gap-2">
          <Label htmlFor="lead-phone">{t("common.phone")}</Label>
          <Input id="lead-phone" type="tel" {...register("phone")} />
        </div>
        <div className="flex flex-col gap-2">
          <Label htmlFor="lead-company">{t("common.company")}</Label>
          <Input id="lead-company" {...register("company")} />
        </div>
        <div className="flex flex-col gap-2">
          <Label htmlFor="lead-source">{t("common.source")}</Label>
          <Controller
            control={control}
            name="source"
            render={({ field }) => (
              <Select value={field.value} onValueChange={field.onChange}>
                <SelectTrigger id="lead-source" className="w-full">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {LEAD_SOURCES.map((source) => (
                    <SelectItem key={source} value={source}>
                      {LEAD_SOURCE_LABELS[source]}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            )}
          />
        </div>
      </div>
      <div className="flex flex-col gap-2">
        <Label htmlFor="lead-notes">{t("common.notes")}</Label>
        <Textarea id="lead-notes" rows={4} {...register("notes")} />
      </div>
      <div className="flex justify-end">
        <GradientButton type="submit" disabled={isSubmitting}>
          {isSubmitting ? t("common.saving") : (submitLabel ?? t("common.save"))}
        </GradientButton>
      </div>
    </form>
  )
}
