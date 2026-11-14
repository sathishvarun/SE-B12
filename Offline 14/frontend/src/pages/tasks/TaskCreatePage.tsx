import { useTranslation } from "react-i18next"
import { useNavigate, useSearchParams } from "react-router-dom"

import { GlassCard, PageWrapper } from "@/components/common"
import { TaskForm } from "@/components/tasks/TaskForm"
import { useCreateTask } from "@/hooks/useTasks"

import { linkPath, readPrefillLink } from "@/components/tasks/taskLinks"

export default function TaskCreatePage() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const prefill = readPrefillLink(searchParams)
  const createTask = useCreateTask()

  return (
    <PageWrapper title={t("tasks.newTitle")}>
      <GlassCard hoverable={false} className="dark:border-white/10 dark:bg-card/70">
        <TaskForm
          defaultLink={prefill}
          submitLabel={t("tasks.create")}
          isSubmitting={createTask.isPending}
          onSubmit={(input) =>
            createTask.mutate(input, { onSuccess: () => navigate(prefill ? linkPath(prefill) : "/tasks") })
          }
        />
      </GlassCard>
    </PageWrapper>
  )
}
