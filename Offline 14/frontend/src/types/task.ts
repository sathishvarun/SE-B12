export type TaskPriority = "low" | "medium" | "high"
export type TaskStatus = "pending" | "done"
export type TaskView = "today" | "upcoming" | "overdue" | "done"

export interface Task {
  id: number
  title: string
  description: string | null
  due_date: string | null
  priority: TaskPriority
  status: TaskStatus
  contact_id: number | null
  lead_id: number | null
  deal_id: number | null
  linked_type: "contact" | "lead" | "deal" | null
  linked_name: string | null
  is_overdue: boolean
  completed_at: string | null
  created_at: string
  updated_at: string
}

export interface TaskInput {
  title: string
  description?: string | null
  due_date?: string | null
  priority?: TaskPriority
  contact_id?: number | null
  lead_id?: number | null
  deal_id?: number | null
}
