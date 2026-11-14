import { render, screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { AxiosError, AxiosHeaders, type AxiosResponse } from "axios"
import { MemoryRouter, Route, Routes } from "react-router-dom"

import { convertLead } from "@/services/leads"
import type { ConvertLeadResult, Lead } from "@/types"

import { ConvertLeadDialog } from "./ConvertLeadDialog"

vi.mock("@/services/leads", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/services/leads")>()
  return { ...actual, convertLead: vi.fn<typeof actual.convertLead>() }
})

const convertLeadMock = vi.mocked(convertLead)

const lead: Lead = {
  id: 7,
  name: "Priya Shah",
  email: "priya@example.com",
  phone: null,
  company: "Shah Traders",
  source: "website",
  status: "qualified",
  notes: null,
  converted_contact_id: null,
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
}

const result: ConvertLeadResult = {
  lead: { ...lead, status: "converted", converted_contact_id: 55 },
  contact: {
    id: 55,
    name: "Priya Shah",
    email: "priya@example.com",
    phone: null,
    company: "Shah Traders",
    address: null,
    notes: null,
    tags: [],
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-01T00:00:00Z",
  },
  deal: {
    id: 9,
    title: "Shah Traders deal",
    value: "2500.00",
    currency: "INR",
    stage: "prospect",
    expected_close_date: null,
    contact_id: 55,
    contact: { id: 55, name: "Priya Shah", company: "Shah Traders" },
    position: 0,
    notes: null,
    closed_at: null,
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-01T00:00:00Z",
  },
}

function renderDialog() {
  const onOpenChange = vi.fn<(open: boolean) => void>()
  const client = new QueryClient({ defaultOptions: { mutations: { retry: false } } })
  render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={["/leads/7"]}>
        <Routes>
          <Route path="/leads/7" element={<ConvertLeadDialog lead={lead} open onOpenChange={onOpenChange} />} />
          <Route path="/contacts/:id" element={<p>Contact page</p>} />
          <Route path="/billing" element={<p>Billing page</p>} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  )
  return onOpenChange
}

afterEach(() => {
  convertLeadMock.mockReset()
})

describe("ConvertLeadDialog", () => {
  it("pre-fills the deal title from the company name", () => {
    renderDialog()
    expect(screen.getByLabelText("Deal title *")).toHaveValue("Shah Traders deal")
  })

  it("requires a title and a non-negative value", async () => {
    const user = userEvent.setup()
    renderDialog()

    await user.clear(screen.getByLabelText("Deal title *"))
    await user.click(screen.getByRole("button", { name: "Convert" }))
    expect(await screen.findByText("Deal title is required")).toBeInTheDocument()
    expect(screen.getByText("Deal value is required")).toBeInTheDocument()

    await user.type(screen.getByLabelText("Deal value *"), "-5")
    await user.click(screen.getByRole("button", { name: "Convert" }))
    expect(await screen.findByText("Enter a valid amount (0 or more)")).toBeInTheDocument()
    expect(convertLeadMock).not.toHaveBeenCalled()
  })

  it("converts the lead and opens the new contact", async () => {
    convertLeadMock.mockResolvedValue(result)
    const user = userEvent.setup()
    const onOpenChange = renderDialog()

    await user.type(screen.getByLabelText("Deal value *"), "2500")
    await user.click(screen.getByRole("button", { name: "Convert" }))

    expect(await screen.findByText("Contact page")).toBeInTheDocument()
    expect(convertLeadMock).toHaveBeenCalledWith(7, {
      deal_title: "Shah Traders deal",
      deal_value: "2500",
      expected_close_date: null,
    })
    expect(onOpenChange).toHaveBeenCalledWith(false)
  })

  it("shows the upgrade notice when the free plan limit is hit (402)", async () => {
    const response: AxiosResponse = {
      data: { detail: "Free plan limit reached: you can have up to 100 contacts." },
      status: 402,
      statusText: "Payment Required",
      headers: {},
      config: { headers: new AxiosHeaders() },
    }
    convertLeadMock.mockRejectedValue(new AxiosError("402", "ERR_BAD_REQUEST", response.config, null, response))
    const user = userEvent.setup()
    const onOpenChange = renderDialog()

    await user.type(screen.getByLabelText("Deal value *"), "10")
    await user.click(screen.getByRole("button", { name: "Convert" }))

    const alert = await screen.findByRole("alert")
    expect(alert).toHaveTextContent("Free plan limit reached")
    expect(screen.getByRole("link", { name: "Upgrade to Pro" })).toHaveAttribute("href", "/billing")
    await waitFor(() => expect(screen.getByRole("button", { name: "Convert" })).toBeEnabled())
    expect(onOpenChange).not.toHaveBeenCalledWith(false)
  })
})
