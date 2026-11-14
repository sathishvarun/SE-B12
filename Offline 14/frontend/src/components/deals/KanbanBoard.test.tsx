import { render, screen, within } from "@testing-library/react"
import { MemoryRouter } from "react-router-dom"

import type { Deal, DealBoard, DealStage } from "@/types"

import { KanbanBoard } from "./KanbanBoard"

function makeDeal(id: number, title: string, stage: DealStage, value: string, position: number): Deal {
  return {
    id,
    title,
    value,
    currency: "INR",
    stage,
    expected_close_date: null,
    contact_id: 1,
    contact: { id: 1, name: "Arjun Mehta", company: "Acme" },
    position,
    notes: null,
    closed_at: stage === "won" || stage === "lost" ? "2026-01-01T00:00:00Z" : null,
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-01T00:00:00Z",
  }
}

const board: DealBoard = {
  prospect: [makeDeal(1, "First prospect", "prospect", "1000.00", 0), makeDeal(2, "Second prospect", "prospect", "500.00", 1)],
  proposal: [],
  negotiation: [makeDeal(3, "Big negotiation", "negotiation", "250000.00", 0)],
  won: [makeDeal(4, "Closed won", "won", "75000.00", 0)],
  lost: [],
}

function renderBoard(value: DealBoard = board) {
  const onMove = vi.fn<(dealId: number, stage: DealStage, position: number, nextBoard: DealBoard) => void>()
  render(
    <MemoryRouter>
      <KanbanBoard board={value} onMove={onMove} />
    </MemoryRouter>,
  )
  return onMove
}

describe("KanbanBoard", () => {
  it("renders one column per stage in pipeline order", () => {
    renderBoard()
    const columns = screen.getAllByRole("region")
    expect(columns.map((col) => col.getAttribute("aria-label"))).toEqual([
      "Prospect column",
      "Proposal column",
      "Negotiation column",
      "Won column",
      "Lost column",
    ])
  })

  it("puts each deal in its stage column, ordered as given", () => {
    renderBoard()
    const prospect = screen.getByRole("region", { name: "Prospect column" })
    const links = within(prospect).getAllByRole("link")
    expect(links.map((link) => link.textContent)).toEqual(["First prospect", "Second prospect"])
    expect(within(prospect).getByLabelText("2 deals")).toBeInTheDocument()

    const negotiation = screen.getByRole("region", { name: "Negotiation column" })
    expect(within(negotiation).getByRole("link", { name: "Big negotiation" })).toHaveAttribute("href", "/deals/3")
    expect(within(negotiation).getByLabelText("1 deal")).toBeInTheDocument()

    const won = screen.getByRole("region", { name: "Won column" })
    expect(within(won).getByText("Closed won")).toBeInTheDocument()
    expect(within(won).queryByText("First prospect")).not.toBeInTheDocument()
  })

  it("shows a drop hint in empty columns", () => {
    renderBoard()
    const proposal = screen.getByRole("region", { name: "Proposal column" })
    expect(within(proposal).getByText("Drop deals here")).toBeInTheDocument()
    expect(within(proposal).getByLabelText("0 deals")).toBeInTheDocument()
    const prospect = screen.getByRole("region", { name: "Prospect column" })
    expect(within(prospect).queryByText("Drop deals here")).not.toBeInTheDocument()
  })

  it("makes every deal card a keyboard-draggable item", () => {
    renderBoard()
    const item = screen.getByLabelText("First prospect. Press space to pick up and move.")
    expect(item).toHaveAttribute("role", "button")
    expect(item).toHaveAttribute("tabindex", "0")
  })

  it("re-renders when the parent passes a new board and does not call onMove on render", () => {
    const onMove = renderBoard({ prospect: [], proposal: [], negotiation: [], won: [], lost: [] })
    expect(screen.getAllByText("Drop deals here")).toHaveLength(5)
    expect(onMove).not.toHaveBeenCalled()
  })
})
