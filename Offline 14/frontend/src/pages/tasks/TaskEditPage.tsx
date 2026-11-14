import { useTranslation } from "react-i18next"
import { useNavigate, useParams, useSearchParams } from "react-router-dom"

import { EmptyState, GlassCard, LoadingSpinner, PageWrapper } from "@/components/common"
import { ConfirmDeleteButton } from "@/components/deals/ConfirmDeleteButton"
import { TaskForm } from "@/components/tasks/TaskForm"
import { useDeleteTask, useTask, useUpdateTask } from "@/hooks/useTasks"
import { getErrorMessage } from "@/services/api"

import { safeReturnPath } from "@/components/tasks/taskLinks"

export default function TaskEditPage() {
  const { t } = useTranslation()
  const { id } = useParams<{ id: string }>()
  const taskId = Number(id)
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  // TaskItem links here with ?returnTo=<page it was on>, so we go back there after saving.
  const returnTo = safeReturnPath(searchParams.get("returnTo")) ?? "/tasks"

  const { data: task, isLoading, isError, error } = useTask(taskId)
  const updateTask = useUpdateTask(taskId)
  const deleteTask = useDeleteTask()

  return (
    <PageWrapper
      title={t("tasks.editTitle")}
      actions={
        task && (
          <ConfirmDeleteButton
            itemName={t("tasks.itemName")}
            isDeleting={deleteTask.isPending}
            onConfirm={() => deleteTask.mutate(taskId, { onSuccess: () => navigate(returnTo) })}
          />
        )
      }
    >
      {isLoading && <LoadingSpinner fullPage />}
      {isError && <EmptyState title={t("tasks.loadError")} description={getErrorMessage(error)} />}
      {task && (
        <GlassCard hoverable={false} className="dark:border-white/10 dark:bg-card/70">
          <TaskForm
            task={task}
            submitLabel={t("common.saveChanges")}
            isSubmitting={updateTask.isPending}
            onSubmit={(input) => updateTask.mutate(input, { onSuccess: () => navigate(returnTo) })}
          />
        </GlassCard>
      )}
    </PageWrapper>
  )
}
