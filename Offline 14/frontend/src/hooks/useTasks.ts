import i18n from "@/i18n"
import { useMutation, useQueries, useQuery, useQueryClient, type QueryClient } from "@tanstack/react-query"
import { toast } from "sonner"

import { dashboardKeys } from "@/hooks/useDashboard"
import { getErrorMessage } from "@/services/api"
import { tasksService, type TaskListParams } from "@/services/tasks"
import type { TaskInput, TaskView } from "@/types"

export const taskKeys = {
  all: ["tasks"] as const,
  list: (params: TaskListParams) => ["tasks", "list", params] as const,
  detail: (id: number) => ["tasks", "detail", id] as const,
}

/** Tasks show up on the dashboard and on contact/lead/deal detail pages. */
function invalidateTaskData(queryClient: QueryClient) {
  void queryClient.invalidateQueries({ queryKey: taskKeys.all })
  void queryClient.invalidateQueries({ queryKey: dashboardKeys.all })
  void queryClient.invalidateQueries({ queryKey: ["deals"] })
  void queryClient.invalidateQueries({ queryKey: ["contacts"] })
  void queryClient.invalidateQueries({ queryKey: ["leads"] })
}

export function useTasks(params: TaskListParams = {}) {
  return useQuery({ queryKey: taskKeys.list(params), queryFn: () => tasksService.list(params) })
}

/** Total task count for each tab, fetched with page_size=1 so it stays cheap. */
export function useTaskCounts(views: TaskView[]) {
  return useQueries({
    queries: views.map((view) => {
      const params: TaskListParams = { view, page: 1, page_size: 1 }
      return { queryKey: taskKeys.list(params), queryFn: () => tasksService.list(params) }
    }),
    combine: (results) =>
      Object.fromEntries(views.map((view, i) => [view, results[i]?.data?.total])) as Partial<
        Record<TaskView, number>
      >,
  })
}

export function useTask(id: number) {
  return useQuery({
    queryKey: taskKeys.detail(id),
    queryFn: () => tasksService.get(id),
    enabled: Number.isFinite(id) && id > 0,
  })
}

export function useCreateTask() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (input: TaskInput) => tasksService.create(input),
    onSuccess: () => {
      toast.success(i18n.t("tasks.toast.created"))
      invalidateTaskData(queryClient)
    },
    onError: (err) => toast.error(getErrorMessage(err)),
  })
}

export function useUpdateTask(id: number) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (input: TaskInput) => tasksService.update(id, input),
    onSuccess: () => {
      toast.success(i18n.t("tasks.toast.updated"))
      invalidateTaskData(queryClient)
    },
    onError: (err) => toast.error(getErrorMessage(err)),
  })
}

export function useCompleteTask() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (id: number) => tasksService.complete(id),
    onSuccess: () => {
      toast.success(i18n.t("tasks.toast.completed"))
      invalidateTaskData(queryClient)
    },
    onError: (err) => toast.error(getErrorMessage(err)),
  })
}

export function useDeleteTask() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (id: number) => tasksService.remove(id),
    onSuccess: (_data, id) => {
      toast.success(i18n.t("tasks.toast.deleted"))
      queryClient.removeQueries({ queryKey: taskKeys.detail(id) })
      invalidateTaskData(queryClient)
    },
    onError: (err) => toast.error(getErrorMessage(err)),
  })
}
