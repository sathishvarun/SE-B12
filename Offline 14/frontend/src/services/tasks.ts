import api from "@/services/api"
import type { Page, PaginationParams, Task, TaskInput, TaskView } from "@/types"

export interface TaskListParams extends PaginationParams {
  /** Omit for "all pending tasks". */
  view?: TaskView
  contact_id?: number
  lead_id?: number
  deal_id?: number
}

/** Thin wrappers around the /tasks endpoints. */
export const tasksService = {
  async list(params: TaskListParams = {}): Promise<Page<Task>> {
    const { data } = await api.get<Page<Task>>("/tasks", { params })
    return data
  },

  async get(id: number): Promise<Task> {
    const { data } = await api.get<Task>(`/tasks/${id}`)
    return data
  },

  async create(input: TaskInput): Promise<Task> {
    const { data } = await api.post<Task>("/tasks", input)
    return data
  },

  async update(id: number, input: TaskInput): Promise<Task> {
    const { data } = await api.put<Task>(`/tasks/${id}`, input)
    return data
  },

  async complete(id: number): Promise<Task> {
    const { data } = await api.patch<Task>(`/tasks/${id}/complete`)
    return data
  },

  async remove(id: number): Promise<void> {
    await api.delete(`/tasks/${id}`)
  },
}
