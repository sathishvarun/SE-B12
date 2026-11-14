import { render, screen } from "@testing-library/react"
import { MemoryRouter } from "react-router-dom"

import type { Deal } from "@/types"

import { DealCard } from "./DealCard"
import { formatDate, isBeforeToday, sumValues, todayISO } from "./format"

const deal: Deal = {
  id: 12,
  title: "Website redesign",
  value: "150000.00",
  currency: "INR",
  stage: "proposal",
  expected_close_date: "2000-03-01",
  contact_id: 4,
  contact: { id: 4, name: "Arjun Mehta", company: "Acme" },
  position: 0,
  notes: null,
  closed_at: null,
  created_at: "2000-01-01T00:00:00Z",
  updated_at: "2000-01-01T00:00:00Z",
}

function renderCard(value: Deal) {
  return render(
    <MemoryRouter>
      <DealCard deal={value} />
    </MemoryRouter>,
  )
}

describe("DealCard", () => {
  it("shows title link, contact and formatted value", () => {
    renderCard(deal)
    expect(screen.getByRole("link", { name: "Website redesign" })).toHaveAttribute("href", "/deals/12")
    expect(screen.getByText("Arjun Mehta")).toBeInTheDocument()
    expect(screen.getByText("₹1,50,000")).toBeInTheDocument()
  })

  it("highlights a past expected close date on open deals only", () => {
    const { unmount } = renderCard(deal)
    expect(screen.getByTitle("Expected close date has passed")).toBeInTheDocument()
    unmount()
    renderCard({ ...deal, stage: "won" })
    expect(screen.queryByTitle("Expected close date has passed")).not.toBeInTheDocument()
  })
})

describe("format helpers", () => {
  it("compares dates as local YYYY-MM-DD strings", () => {
    expect(todayISO()).toMatch(/^\d{4}-\d{2}-\d{2}$/)
    expect(isBeforeToday("2000-01-01")).toBe(true)
    expect(isBeforeToday(todayISO())).toBe(false)
    expect(isBeforeToday(null)).toBe(false)
  })

  it("formats date-only strings without shifting the day", () => {
    expect(formatDate("2026-03-01")).toContain("1")
    expect(formatDate("2026-03-01")).toContain("Mar")
    expect(formatDate(null)).toBe("—")
  })

  it("sums string values", () => {
    expect(sumValues([{ value: "10.50" }, { value: "4.50" }])).toBe(15)
  })
})
