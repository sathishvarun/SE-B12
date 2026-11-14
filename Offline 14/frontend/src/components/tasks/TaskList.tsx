import { useTranslation } from "react-i18next"
import { CheckSquare } from "lucide-react"

import { AnimatedList, EmptyState } from "@/components/common"
import type { Task } from "@/types"

import { TaskItem } from "./TaskItem"

interface TaskListProps {
  tasks: Task[]
  emptyTitle?: string
  emptyDescription?: string
  hideLinks?: boolean
}

export function TaskList({ tasks, emptyTitle, emptyDescription, hideLinks = false }: TaskListProps) {
  const { t } = useTranslation()
  if (tasks.length === 0) {
    return <EmptyState icon={CheckSquare} title={emptyTitle ?? t("tasks.noTasks")} description={emptyDescription} className="p-6" />
  }
  return (
    <AnimatedList className="gap-2">
      {tasks.map((task) => (
        <TaskItem key={task.id} task={task} hideLink={hideLinks} />
      ))}
    </AnimatedList>
  )
}
