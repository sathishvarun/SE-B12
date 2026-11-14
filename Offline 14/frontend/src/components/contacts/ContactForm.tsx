import { useTranslation } from "react-i18next"
import { zodResolver } from "@hookform/resolvers/zod"
import { Controller, useForm } from "react-hook-form"
import { z } from "zod"

import { GradientButton } from "@/components/common"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import i18n from "@/i18n"
import type { Contact, ContactInput } from "@/types"

import { TagMultiSelect } from "./TagMultiSelect"
import { emptyToNull } from "./utils"

const contactSchema = z.object({
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
  address: z.string(),
  notes: z.string(),
  tag_ids: z.array(z.number()),
})

type ContactFormValues = z.infer<typeof contactSchema>

interface ContactFormProps {
  /** Existing contact when editing. */
  contact?: Contact
  onSubmit: (input: ContactInput) => void
  isSubmitting?: boolean
  submitLabel?: string
}

export function ContactForm({ contact, onSubmit, isSubmitting = false, submitLabel }: ContactFormProps) {
  const { t } = useTranslation()
  const {
    register,
    control,
    handleSubmit,
    formState: { errors },
  } = useForm<ContactFormValues>({
    resolver: zodResolver(contactSchema),
    defaultValues: {
      name: contact?.name ?? "",
      email: contact?.email ?? "",
      phone: contact?.phone ?? "",
      company: contact?.company ?? "",
      address: contact?.address ?? "",
      notes: contact?.notes ?? "",
      tag_ids: contact?.tags.map((t) => t.id) ?? [],
    },
  })

  const submit = (values: ContactFormValues) => {
    onSubmit({
      name: values.name.trim(),
      email: emptyToNull(values.email),
      phone: emptyToNull(values.phone),
      company: emptyToNull(values.company),
      address: emptyToNull(values.address),
      notes: emptyToNull(values.notes),
      tag_ids: values.tag_ids,
    })
  }

  return (
    <form onSubmit={handleSubmit(submit)} noValidate className="flex flex-col gap-5">
      <div className="grid gap-5 sm:grid-cols-2">
        <div className="flex flex-col gap-2">
          <Label htmlFor="contact-name">{t("common.nameRequiredLabel")}</Label>
          <Input id="contact-name" aria-invalid={!!errors.name} {...register("name")} />
          {errors.name && <p className="text-sm text-destructive">{errors.name.message}</p>}
        </div>
        <div className="flex flex-col gap-2">
          <Label htmlFor="contact-email">{t("common.email")}</Label>
          <Input id="contact-email" type="email" aria-invalid={!!errors.email} {...register("email")} />
          {errors.email && <p className="text-sm text-destructive">{errors.email.message}</p>}
        </div>
        <div className="flex flex-col gap-2">
          <Label htmlFor="contact-phone">{t("common.phone")}</Label>
          <Input id="contact-phone" type="tel" {...register("phone")} />
        </div>
        <div className="flex flex-col gap-2">
          <Label htmlFor="contact-company">{t("common.company")}</Label>
          <Input id="contact-company" {...register("company")} />
        </div>
      </div>
      <div className="flex flex-col gap-2">
        <Label htmlFor="contact-address">{t("common.address")}</Label>
        <Input id="contact-address" {...register("address")} />
      </div>
      <div className="flex flex-col gap-2">
        <Label htmlFor="contact-notes">{t("common.notes")}</Label>
        <Textarea id="contact-notes" rows={4} {...register("notes")} />
      </div>
      <div className="flex flex-col gap-2">
        <Label>{t("common.tags")}</Label>
        <Controller
          control={control}
          name="tag_ids"
          render={({ field }) => <TagMultiSelect value={field.value} onChange={field.onChange} />}
        />
      </div>
      <div className="flex justify-end">
        <GradientButton type="submit" disabled={isSubmitting}>
          {isSubmitting ? t("common.saving") : (submitLabel ?? t("common.save"))}
        </GradientButton>
      </div>
    </form>
  )
}
