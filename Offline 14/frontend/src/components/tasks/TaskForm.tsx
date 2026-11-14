import i18n from "@/i18n"
import { useTranslation } from "react-i18next"
import { Controller, useForm, useWatch } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import { z } from "zod"

import { GradientButton } from "@/components/common"
import { ContactSelect } from "@/components/deals/ContactSelect"
import { FieldError } from "@/components/deals/FieldError"
import { PRIORITY_LABELS } from "@/components/deals/format"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Textarea } from "@/components/ui/textarea"
import { useDeals } from "@/hooks/useDeals"
import { useLeadOptions } from "@/hooks/useLeadOptions"
import type { Task, TaskInput, TaskPriority } from "@/types"

export type TaskLinkType = "none" | "contact" | "lead" | "deal"

// Getters, so the labels always use the current language.
const LINK_TYPE_LABELS: Record<TaskLinkType, string> = {
  get none() { return i18n.t("tasks.linkType.none") },
  get contact() { return i18n.t("tasks.linkType.contact") },
  get lead() { return i18n.t("tasks.linkType.lead") },
  get deal() { return i18n.t("tasks.linkType.deal") },
}

const PRIORITIES: TaskPriority[] = ["low", "medium", "high"]

const taskSchema = z
  .object({
    title: z
      .string()
      .trim()
      .min(1, { error: () => i18n.t("validation.titleRequired") })
      .max(200, { error: () => i18n.t("validation.titleTooLong") }),
    description: z.string().max(5000, { error: () => i18n.t("validation.descriptionTooLong") }),
    due_date: z.string(),
    priority: z.enum(["low", "medium", "high"]),
    link_type: z.enum(["none", "contact", "lead", "deal"]),
    link_id: z.string(),
  })
  .refine((v) => v.link_type === "none" || v.link_id !== "", {
    error: () => i18n.t("validation.chooseRecord"),
    path: ["link_id"],
  })

type TaskFormValues = z.infer<typeof taskSchema>

interface TaskFormProps {
  /** Existing task when editing. */
  task?: Task
  /** Prefilled link when creating from a contact/lead/deal page. */
  defaultLink?: { type: Exclude<TaskLinkType, "none">; id: number }
  submitLabel: string
  isSubmitting?: boolean
  onSubmit: (input: TaskInput) => void
}

function initialLink(task?: Task, defaultLink?: TaskFormProps["defaultLink"]): { type: TaskLinkType; id: string } {
  if (task?.contact_id) return { type: "contact", id: String(task.contact_id) }
  if (task?.lead_id) return { type: "lead", id: String(task.lead_id) }
  if (task?.deal_id) return { type: "deal", id: String(task.deal_id) }
  if (!task && defaultLink) return { type: defaultLink.type, id: String(defaultLink.id) }
  return { type: "none", id: "" }
}

export function TaskForm({ task, defaultLink, submitLabel, isSubmitting = false, onSubmit }: TaskFormProps) {
  const { t } = useTranslation()
  const link = initialLink(task, defaultLink)
  const {
    register,
    control,
    handleSubmit,
    setValue,
    formState: { errors },
  } = useForm<TaskFormValues>({
    resolver: zodResolver(taskSchema),
    defaultValues: {
      title: task?.title ?? "",
      description: task?.description ?? "",
      due_date: task?.due_date ?? "",
      priority: task?.priority ?? "medium",
      link_type: link.type,
      link_id: link.id,
    },
  })

  const linkType = useWatch({ control, name: "link_type" })
  const { data: leads = [], isLoading: leadsLoading } = useLeadOptions()
  const { data: dealsPage, isLoading: dealsLoading } = useDeals({ page_size: 100 })
  const deals = dealsPage?.items ?? []

  function submit(values: TaskFormValues) {
    const id = values.link_id ? Number(values.link_id) : null
    onSubmit({
      title: values.title,
      description: values.description.trim() || null,
      due_date: values.due_date || null,
      priority: values.priority,
      // Only one link is allowed: send the chosen one and clear the others.
      contact_id: values.link_type === "contact" ? id : null,
      lead_id: values.link_type === "lead" ? id : null,
      deal_id: values.link_type === "deal" ? id : null,
    })
  }

  return (
    <form onSubmit={handleSubmit(submit)} className="grid gap-5 sm:grid-cols-2" noValidate>
      <div className="grid gap-2 sm:col-span-2">
        <Label htmlFor="task-title">{t("tasks.title")}</Label>
        <Input id="task-title" aria-invalid={!!errors.title || undefined} {...register("title")} />
        <FieldError message={errors.title?.message} />
      </div>

      <div className="grid gap-2 sm:col-span-2">
        <Label htmlFor="task-description">{t("tasks.description")}</Label>
        <Textarea id="task-description" rows={3} {...register("description")} />
        <FieldError message={errors.description?.message} />
      </div>

      <div className="grid gap-2">
        <Label htmlFor="task-due">{t("tasks.dueDate")}</Label>
        <Input id="task-due" type="date" {...register("due_date")} />
      </div>

      <div className="grid gap-2">
        <Label htmlFor="task-priority">{t("tasks.priorityLabel")}</Label>
        <Controller
          control={control}
          name="priority"
          render={({ field }) => (
            <Select value={field.value} onValueChange={field.onChange}>
              <SelectTrigger id="task-priority" className="w-full">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {PRIORITIES.map((priority) => (
                  <SelectItem key={priority} value={priority}>
                    {PRIORITY_LABELS[priority]}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          )}
        />
      </div>

      <div className="grid gap-2">
        <Label htmlFor="task-link-type">{t("tasks.linkTo")}</Label>
        <Controller
          control={control}
          name="link_type"
          render={({ field }) => (
            <Select
              value={field.value}
              onValueChange={(value) => {
                field.onChange(value)
                setValue("link_id", "")
              }}
            >
              <SelectTrigger id="task-link-type" className="w-full">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {(Object.keys(LINK_TYPE_LABELS) as TaskLinkType[]).map((type) => (
                  <SelectItem key={type} value={type}>
                    {LINK_TYPE_LABELS[type]}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          )}
        />
      </div>

      {linkType !== "none" && (
        <div className="grid gap-2">
          <Label htmlFor="task-link-id">{LINK_TYPE_LABELS[linkType]}</Label>
          <Controller
            control={control}
            name="link_id"
            render={({ field }) =>
              linkType === "contact" ? (
                <ContactSelect
                  id="task-link-id"
                  value={field.value}
                  onChange={field.onChange}
                  invalid={!!errors.link_id}
                />
              ) : (
                <Select value={field.value} onValueChange={field.onChange}>
                  <SelectTrigger id="task-link-id" className="w-full" aria-invalid={!!errors.link_id || undefined}>
                    <SelectValue
                      placeholder={
                        (linkType === "lead" ? leadsLoading : dealsLoading)
                          ? t("common.loading")
                          : linkType === "lead"
                            ? t("tasks.chooseLead")
                            : t("tasks.chooseDeal")
                      }
                    />
                  </SelectTrigger>
                  <SelectContent>
                    {linkType === "lead"
                      ? leads.map((lead) => (
                          <SelectItem key={lead.id} value={String(lead.id)}>
                            {lead.name}
                            {lead.company && <span className="text-muted-foreground"> · {lead.company}</span>}
                          </SelectItem>
                        ))
                      : deals.map((deal) => (
                          <SelectItem key={deal.id} value={String(deal.id)}>
                            {deal.title}
                            <span className="text-muted-foreground"> · {deal.contact.name}</span>
                          </SelectItem>
                        ))}
                  </SelectContent>
                </Select>
              )
            }
          />
          <FieldError message={errors.link_id?.message} />
        </div>
      )}

      <div className="sm:col-span-2">
        <GradientButton type="submit" disabled={isSubmitting}>
          {isSubmitting ? t("common.saving") : submitLabel}
        </GradientButton>
      </div>
    </form>
  )
}
