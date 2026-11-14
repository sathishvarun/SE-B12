import { render, screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { AxiosError, AxiosHeaders, type AxiosResponse } from "axios"
import { MemoryRouter } from "react-router-dom"

import { LoginForm } from "@/components/auth/LoginForm"
import { AuthProvider } from "@/context/AuthContext"
import { tokenStorage } from "@/lib/tokenStorage"
import { authService } from "@/services/auth"
import type { User } from "@/types"

const me: User = {
  id: 1,
  email: "jane@example.com",
  full_name: "Jane",
  is_active: true,
  is_verified: false,
  is_admin: false,
  oauth_provider: null,
  has_password: true,
  plan: "free",
  created_at: "2026-01-01T00:00:00Z",
}

function renderForm() {
  const onSuccess = vi.fn<(user: User) => void>()
  render(
    <QueryClientProvider client={new QueryClient()}>
      <MemoryRouter>
        <AuthProvider>
          <LoginForm onSuccess={onSuccess} />
        </AuthProvider>
      </MemoryRouter>
    </QueryClientProvider>,
  )
  return onSuccess
}

afterEach(() => {
  vi.restoreAllMocks()
  tokenStorage.clear()
})

describe("LoginForm", () => {
  it("shows validation errors and does not call login", async () => {
    const loginSpy = vi.spyOn(authService, "login")
    const user = userEvent.setup()
    renderForm()

    await user.type(screen.getByLabelText("Email"), "not-an-email")
    await user.click(screen.getByRole("button", { name: "Log in" }))

    expect(await screen.findByText("Enter a valid email address")).toBeInTheDocument()
    expect(screen.getByText("Password is required")).toBeInTheDocument()
    expect(loginSpy).not.toHaveBeenCalled()
  })

  it("logs in, stores tokens and calls onSuccess with the user", async () => {
    const loginSpy = vi
      .spyOn(authService, "login")
      .mockResolvedValue({ access_token: "acc", refresh_token: "ref", token_type: "bearer" })
    vi.spyOn(authService, "getMe").mockResolvedValue(me)
    const user = userEvent.setup()
    const onSuccess = renderForm()

    await user.type(screen.getByLabelText("Email"), "jane@example.com")
    await user.type(screen.getByLabelText("Password"), "secret-pass")
    await user.click(screen.getByRole("button", { name: "Log in" }))

    await waitFor(() => expect(onSuccess).toHaveBeenCalledWith(me))
    expect(loginSpy).toHaveBeenCalledWith({ email: "jane@example.com", password: "secret-pass" })
    expect(tokenStorage.getAccessToken()).toBe("acc")
    expect(tokenStorage.getRefreshToken()).toBe("ref")
  })

  it("does not call onSuccess when the server rejects the credentials", async () => {
    const response: AxiosResponse = {
      data: { detail: "Incorrect email or password" },
      status: 401,
      statusText: "Unauthorized",
      headers: {},
      config: { headers: new AxiosHeaders() },
    }
    vi.spyOn(authService, "login").mockRejectedValue(
      new AxiosError("401", "ERR_BAD_REQUEST", response.config, null, response),
    )
    const getMeSpy = vi.spyOn(authService, "getMe")
    const user = userEvent.setup()
    const onSuccess = renderForm()

    await user.type(screen.getByLabelText("Email"), "jane@example.com")
    await user.type(screen.getByLabelText("Password"), "wrong")
    await user.click(screen.getByRole("button", { name: "Log in" }))

    await waitFor(() => expect(screen.getByRole("button", { name: "Log in" })).toBeEnabled())
    expect(onSuccess).not.toHaveBeenCalled()
    expect(getMeSpy).not.toHaveBeenCalled()
    expect(tokenStorage.getAccessToken()).toBeNull()
  })

  it("links to the forgot-password page", () => {
    renderForm()
    expect(screen.getByRole("link", { name: "Forgot password?" })).toHaveAttribute("href", "/forgot-password")
  })
})
