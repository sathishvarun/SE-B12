import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { render, screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"

import type { ContactInput, Tag } from "@/types"

import { ContactForm } from "./ContactForm"

vi.mock("@/services/tags", () => ({
  listTags: vi.fn<() => Promise<Tag[]>>(async () => [{ id: 1, name: "VIP" }]),
  createTag: vi.fn<(name: string) => Promise<Tag>>(),
}))

function renderForm(onSubmit = vi.fn<(input: ContactInput) => void>()) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  render(
    <QueryClientProvider client={queryClient}>
      <ContactForm onSubmit={onSubmit} submitLabel="Create contact" />
    </QueryClientProvider>,
  )
  return onSubmit
}

describe("ContactForm", () => {
  it("requires a name", async () => {
    const onSubmit = renderForm()
    await userEvent.click(screen.getByRole("button", { name: "Create contact" }))
    expect(await screen.findByText("Name is required")).toBeInTheDocument()
    expect(onSubmit).not.toHaveBeenCalled()
  })

  it("rejects an invalid email", async () => {
    const onSubmit = renderForm()
    await userEvent.type(screen.getByLabelText("Name *"), "Ada")
    await userEvent.type(screen.getByLabelText("Email"), "not-an-email")
    await userEvent.click(screen.getByRole("button", { name: "Create contact" }))
    expect(await screen.findByText("Enter a valid email address")).toBeInTheDocument()
    expect(onSubmit).not.toHaveBeenCalled()
  })

  it("submits trimmed values, empty fields as null, and selected tags", async () => {
    const onSubmit = renderForm()
    await userEvent.type(screen.getByLabelText("Name *"), "  Ada Lovelace ")
    await userEvent.click(await screen.findByRole("button", { name: "VIP" }))
    await userEvent.click(screen.getByRole("button", { name: "Create contact" }))
    await waitFor(() => expect(onSubmit).toHaveBeenCalledTimes(1))
    expect(onSubmit).toHaveBeenCalledWith({
      name: "Ada Lovelace",
      email: null,
      phone: null,
      company: null,
      address: null,
      notes: null,
      tag_ids: [1],
    })
  })
})
