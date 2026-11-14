import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { AxiosError, AxiosHeaders, type AxiosResponse } from "axios"
import { MemoryRouter } from "react-router-dom"

import { RegisterForm } from "@/components/auth/RegisterForm"
import { AuthProvider } from "@/context/AuthContext"
import { authService } from "@/services/auth"

function renderForm() {
  const onSuccess = vi.fn<() => void>()
  render(
    <QueryClientProvider client={new QueryClient()}>
      <MemoryRouter>
        <AuthProvider>
          <RegisterForm onSuccess={onSuccess} />
        </AuthProvider>
      </MemoryRouter>
    </QueryClientProvider>,
  )
  return onSuccess
}

describe("RegisterForm", () => {
  it("validates email, password length and matching passwords", async () => {
    const registerSpy = vi.spyOn(authService, "register")
    const user = userEvent.setup()
    renderForm()

    await user.type(screen.getByLabelText("Full name"), "Jane")
    await user.type(screen.getByLabelText("Email"), "not-an-email")
    await user.type(screen.getByLabelText("Password"), "short")
    await user.type(screen.getByLabelText("Confirm password"), "different")
    await user.click(screen.getByRole("button", { name: "Create account" }))

    expect(await screen.findByText("Enter a valid email address")).toBeInTheDocument()
    expect(screen.getByText("Password must be at least 8 characters")).toBeInTheDocument()
    expect(screen.getByText("Passwords do not match")).toBeInTheDocument()
    expect(registerSpy).not.toHaveBeenCalled()
  })

  it("shows a clear message under the email field when the email is already registered", async () => {
    const response: AxiosResponse = {
      data: { detail: "Email is already registered" },
      status: 409,
      statusText: "Conflict",
      headers: {},
      config: { headers: new AxiosHeaders() },
    }
    vi.spyOn(authService, "register").mockRejectedValue(
      new AxiosError("409", "ERR_BAD_REQUEST", response.config, null, response),
    )
    const user = userEvent.setup()
    const onSuccess = renderForm()

    await user.type(screen.getByLabelText("Full name"), "Jane")
    await user.type(screen.getByLabelText("Email"), "jane@example.com")
    await user.type(screen.getByLabelText("Password"), "long-enough")
    await user.type(screen.getByLabelText("Confirm password"), "long-enough")
    await user.click(screen.getByRole("button", { name: "Create account" }))

    expect(await screen.findByText(/This email is already registered/)).toBeInTheDocument()
    expect(screen.getByLabelText("Email")).toHaveAttribute("aria-invalid", "true")
    expect(onSuccess).not.toHaveBeenCalled()
  })
})
