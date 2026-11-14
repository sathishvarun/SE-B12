import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { MemoryRouter } from "react-router-dom"

import { tasksService } from "@/services/tasks"
import type { Task } from "@/types"

import { TaskItem } from "./TaskItem"

const baseTask: Task = {
  id: 7,
  title: "Call Priya",
  description: null,
  due_date: "2000-01-15",
  priority: "high",
  status: "pending",
  contact_id: 3,
  lead_id: null,
  deal_id: null,
  linked_type: "contact",
  linked_name: "Priya Sharma",
  is_overdue: true,
  completed_at: null,
  created_at: "2000-01-01T00:00:00Z",
  updated_at: "2000-01-01T00:00:00Z",
}

function renderTask(task: Task) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } })
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter>
        <TaskItem task={task} />
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

describe("TaskItem", () => {
  afterEach(() => vi.restoreAllMocks())

  it("shows priority, overdue due date and linked record", () => {
    renderTask(baseTask)
    expect(screen.getByText("High")).toBeInTheDocument()
    expect(screen.getByText(/Overdue/)).toHaveClass("text-rose-600")
    expect(screen.getByRole("link", { name: /Priya Sharma/ })).toHaveAttribute("href", "/contacts/3")
  })

  it("completes the task when the checkbox is clicked", async () => {
    const complete = vi.spyOn(tasksService, "complete").mockResolvedValue({ ...baseTask, status: "done" })
    renderTask(baseTask)
    await userEvent.click(screen.getByRole("checkbox", { name: /mark call priya as done/i }))
    expect(complete).toHaveBeenCalledWith(7)
  })

  it("renders done tasks as checked and disabled", () => {
    renderTask({ ...baseTask, status: "done", is_overdue: false, completed_at: "2000-01-16T10:00:00Z" })
    const checkbox = screen.getByRole("checkbox")
    expect(checkbox).toBeChecked()
    expect(checkbox).toBeDisabled()
    expect(screen.queryByText(/Overdue/)).not.toBeInTheDocument()
  })
})
