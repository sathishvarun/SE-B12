import api, { API_BASE_URL } from "@/services/api"
import type { LoginInput, RegisterInput, TokenResponse, UpdateProfileInput, User } from "@/types"

interface MessageResponse {
  message: string
}

/** Calls for the /auth endpoints. Most components should use `useAuth()` instead. */
export const authService = {
  login: async (input: LoginInput): Promise<TokenResponse> => {
    const { data } = await api.post<TokenResponse>("/auth/login", input)
    return data
  },

  register: async (input: RegisterInput): Promise<TokenResponse> => {
    const { data } = await api.post<TokenResponse>("/auth/register", input)
    return data
  },

  logout: async (refreshToken: string): Promise<void> => {
    await api.post("/auth/logout", { refresh_token: refreshToken })
  },

  getMe: async (): Promise<User> => {
    const { data } = await api.get<User>("/auth/me")
    return data
  },

  updateMe: async (input: UpdateProfileInput): Promise<User> => {
    const { data } = await api.put<User>("/auth/me", input)
    return data
  },

  forgotPassword: async (email: string): Promise<MessageResponse> => {
    const { data } = await api.post<MessageResponse>("/auth/forgot-password", { email })
    return data
  },

  resetPassword: async (token: string, newPassword: string): Promise<MessageResponse> => {
    const { data } = await api.post<MessageResponse>("/auth/reset-password", {
      token,
      new_password: newPassword,
    })
    return data
  },

  /** Full URL that starts the Google OAuth flow (the browser navigates here). */
  googleLoginUrl: `${API_BASE_URL}/auth/google`,
}
