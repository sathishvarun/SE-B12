import { createContext, useContext } from "react"

import type { LoginInput, RegisterInput, User } from "@/types"

export interface AuthContextValue {
  /** The logged-in user, or null when logged out. */
  user: User | null
  /** True while the user is being loaded on startup. */
  isLoading: boolean
  login: (input: LoginInput) => Promise<User>
  register: (input: RegisterInput) => Promise<User>
  /** Revokes the refresh token on the server, then clears local tokens. */
  logout: () => Promise<void>
  /** Re-fetch /auth/me (e.g. after a profile or plan change). */
  refreshUser: () => Promise<User | null>
  /** Store tokens we got some other way (Google OAuth callback) and load the user. */
  loginWithTokens: (accessToken: string, refreshToken: string) => Promise<User>
}

// The context object lives here (not in AuthContext.tsx) so that file only
// exports a component, which keeps React Fast Refresh happy.
export const AuthContext = createContext<AuthContextValue | null>(null)

/** Read the current auth state: `const { user, logout } = useAuth()`. */
export function useAuth(): AuthContextValue {
  const value = useContext(AuthContext)
  if (!value) {
    throw new Error("useAuth must be used inside <AuthProvider>")
  }
  return value
}
