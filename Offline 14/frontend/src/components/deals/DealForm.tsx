import i18n from "@/i18n"
import { useTranslation } from "react-i18next"
import { useSearchParams } from "react-router-dom"
import { Controller, useForm } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import { z } from "zod"

import { GradientButton } from "@/components/common"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Textarea } from "@/components/ui/textarea"
import { DEAL_STAGES, type Deal, type DealInput } from "@/types"

import { ContactSelect } from "./ContactSelect"
import { FieldError } from "./FieldError"
import { STAGE_LABELS } from "./format"

const dealSchema = z.object({
  title: z
    .string()
    .trim()
    .min(1, { error: () => i18n.t("validation.titleRequired") })
    .max(200, { error: () => i18n.t("validation.titleTooLong") }),
  contact_id: z.string().min(1, { error: () => i18n.t("validation.chooseContact") }),
  value: z
    .string()
    .trim()
    .min(1, { error: () => i18n.t("validation.valueRequired") })
    .refine((v) => Number.isFinite(Number(v)) && Number(v) >= 0, { error: () => i18n.t("validation.amountInvalid") }),
  currency: z
    .string()
    .trim()
    .regex(/^[A-Za-z]{3}$/, { error: () => i18n.t("validation.currencyCode") }),
  stage: z.enum(["prospect", "proposal", "negotiation", "won", "lost"]),
  expected_close_date: z.string(),
  notes: z.string().max(5000, { error: () => i18n.t("validation.notesTooLong") }),
})

type DealFormValues = z.infer<typeof dealSchema>

interface DealFormProps {
  /** Existing deal when editing; omit when creating. */
  deal?: Deal
  submitLabel: string
  isSubmitting?: boolean
  onSubmit: (input: DealInput) => void
}

export function DealForm({ deal, submitLabel, isSubmitting = false, onSubmit }: DealFormProps) {
  const { t } = useTranslation()
  // When creating from a contact page (/deals/new?contact_id=5) the contact is preselected.
  const [searchParams] = useSearchParams()
  const prefillContact = searchParams.get("contact_id") ?? ""

  const {
    register,
    control,
    handleSubmit,
    formState: { errors },
  } = useForm<DealFormValues>({
    resolver: zodResolver(dealSchema),
    defaultValues: {
      title: deal?.title ?? "",
      contact_id: deal ? String(deal.contact_id) : prefillContact,
      value: deal?.value ?? "",
      currency: deal?.currency ?? "INR",
      stage: deal?.stage ?? "prospect",
      expected_close_date: deal?.expected_close_date ?? "",
      notes: deal?.notes ?? "",
    },
  })

  function submit(values: DealFormValues) {
    onSubmit({
      title: values.title,
      contact_id: Number(values.contact_id),
      value: values.value,
      currency: values.currency.toUpperCase(),
      stage: values.stage,
      expected_close_date: values.expected_close_date || null,
      notes: values.notes.trim() || null,
    })
  }

  return (
    <form onSubmit={handleSubmit(submit)} className="grid gap-5 sm:grid-cols-2" noValidate>
      <div className="grid gap-2 sm:col-span-2">
        <Label htmlFor="deal-title">{t("deals.title")}</Label>
        <Input id="deal-title" aria-invalid={!!errors.title || undefined} {...register("title")} />
        <FieldError message={errors.title?.message} />
      </div>

      <div className="grid gap-2 sm:col-span-2">
        <Label htmlFor="deal-contact">{t("common.contact")}</Label>
        <Controller
          control={control}
          name="contact_id"
          render={({ field }) => (
            <ContactSelect
              id="deal-contact"
              value={field.value}
              onChange={field.onChange}
              invalid={!!errors.contact_id}
            />
          )}
        />
        <FieldError message={errors.contact_id?.message} />
      </div>

      <div className="grid gap-2">
        <Label htmlFor="deal-value">{t("deals.value")}</Label>
        <Input
          id="deal-value"
          type="number"
          inputMode="decimal"
          min="0"
          step="0.01"
          aria-invalid={!!errors.value || undefined}
          {...register("value")}
        />
        <FieldError message={errors.value?.message} />
      </div>

      <div className="grid gap-2">
        <Label htmlFor="deal-currency">{t("deals.currency")}</Label>
        <Input
          id="deal-currency"
          maxLength={3}
          className="uppercase"
          aria-invalid={!!errors.currency || undefined}
          {...register("currency")}
        />
        <FieldError message={errors.currency?.message} />
      </div>

      <div className="grid gap-2">
        <Label htmlFor="deal-stage">{t("deals.stageLabel")}</Label>
        <Controller
          control={control}
          name="stage"
          render={({ field }) => (
            <Select value={field.value} onValueChange={field.onChange}>
              <SelectTrigger id="deal-stage" className="w-full">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {DEAL_STAGES.map((stage) => (
                  <SelectItem key={stage} value={stage}>
                    {STAGE_LABELS[stage]}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          )}
        />
      </div>

      <div className="grid gap-2">
        <Label htmlFor="deal-close">{t("common.expectedCloseDate")}</Label>
        <Input id="deal-close" type="date" {...register("expected_close_date")} />
      </div>

      <div className="grid gap-2 sm:col-span-2">
        <Label htmlFor="deal-notes">{t("common.notes")}</Label>
        <Textarea id="deal-notes" rows={4} aria-invalid={!!errors.notes || undefined} {...register("notes")} />
        <FieldError message={errors.notes?.message} />
      </div>

      <div className="sm:col-span-2">
        <GradientButton type="submit" disabled={isSubmitting}>
          {isSubmitting ? t("common.saving") : submitLabel}
        </GradientButton>
      </div>
    </form>
  )
}
