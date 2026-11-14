import { render, screen } from "@testing-library/react"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { MemoryRouter } from "react-router-dom"

import { AppRoutes } from "@/App"
import { AuthProvider } from "@/context/AuthContext"
import { tokenStorage } from "@/lib/tokenStorage"
import { authService } from "@/services/auth"
import type { User } from "@/types"

const testUser: User = {
  id: 1,
  email: "jane@example.com",
  full_name: "Jane Doe",
  is_active: true,
  is_verified: true,
  is_admin: false,
  oauth_provider: null,
  has_password: true,
  plan: "free",
  created_at: "2026-01-01T00:00:00Z",
}

function renderAt(path: string) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[path]}>
        <AuthProvider>
          <AppRoutes />
        </AuthProvider>
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

afterEach(() => {
  tokenStorage.clear()
  vi.restoreAllMocks()
})

describe("AppRoutes (logged out)", () => {
  it("redirects protected pages to the login page", async () => {
    renderAt("/")
    expect(await screen.findByRole("heading", { name: "Log in" })).toBeInTheDocument()
    expect(screen.queryByRole("link", { name: /contacts/i })).not.toBeInTheDocument()
  })

  it("renders public pages without the sidebar", async () => {
    renderAt("/register")
    expect(await screen.findByRole("heading", { name: "Create your account" })).toBeInTheDocument()
    expect(screen.queryByRole("link", { name: /contacts/i })).not.toBeInTheDocument()
  })

  it("shows the 404 page for unknown routes", async () => {
    renderAt("/does-not-exist")
    expect(await screen.findByText("Page not found")).toBeInTheDocument()
  })
})

describe("AppRoutes (logged in)", () => {
  beforeEach(() => {
    tokenStorage.setTokens("access", "refresh")
  })

  it("loads the user and shows the app layout", async () => {
    vi.spyOn(authService, "getMe").mockResolvedValue(testUser)
    renderAt("/settings")
    expect(await screen.findByRole("heading", { name: "Settings" })).toBeInTheDocument()
    expect(screen.getByRole("link", { name: /contacts/i })).toBeInTheDocument()
    expect(screen.getAllByText("Jane Doe").length).toBeGreaterThan(0)
    expect(screen.getByRole("link", { name: /upgrade/i })).toBeInTheDocument()
    expect(screen.queryByRole("link", { name: /^admin$/i })).not.toBeInTheDocument()
  })

  it("redirects logged-in users away from the login page", async () => {
    vi.spyOn(authService, "getMe").mockResolvedValue(testUser)
    renderAt("/login")
    expect(await screen.findByRole("link", { name: /contacts/i })).toBeInTheDocument()
    expect(screen.queryByRole("heading", { name: "Log in" })).not.toBeInTheDocument()
  })

  it("sends non-admins away from admin pages", async () => {
    vi.spyOn(authService, "getMe").mockResolvedValue(testUser)
    renderAt("/admin")
    expect(await screen.findByRole("link", { name: /contacts/i })).toBeInTheDocument()
    expect(screen.queryByRole("heading", { name: "Admin Dashboard" })).not.toBeInTheDocument()
  })
})
