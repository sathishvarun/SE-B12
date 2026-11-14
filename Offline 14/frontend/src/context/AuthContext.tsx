import { useCallback, useEffect, useMemo, useState, type ReactNode } from "react"
import { useQueryClient } from "@tanstack/react-query"

import { AuthContext, type AuthContextValue } from "@/hooks/useAuth"
import { tokenStorage } from "@/lib/tokenStorage"
import { authService } from "@/services/auth"
import type { LoginInput, RegisterInput, User } from "@/types"

/** Holds the logged-in user and the login/logout actions. Wrap the app in this. */
export function AuthProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient()
  const [user, setUser] = useState<User | null>(null)
  // Only show a loading state if there is a token to check.
  const [isLoading, setIsLoading] = useState<boolean>(() => tokenStorage.getAccessToken() !== null)

  // On startup: if we have a token, load the current user.
  useEffect(() => {
    if (!tokenStorage.getAccessToken()) {
      return
    }
    let cancelled = false
    authService
      .getMe()
      .then((me) => {
        if (!cancelled) setUser(me)
      })
      .catch(() => {
        // Token is invalid and could not be refreshed: start logged out.
        if (!cancelled) {
          tokenStorage.clear()
          setUser(null)
        }
      })
      .finally(() => {
        if (!cancelled) setIsLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [])

  const loginWithTokens = useCallback(async (accessToken: string, refreshToken: string) => {
    tokenStorage.setTokens(accessToken, refreshToken)
    try {
      const me = await authService.getMe()
      setUser(me)
      return me
    } catch (err) {
      tokenStorage.clear()
      throw err
    }
  }, [])

  const login = useCallback(
    async (input: LoginInput) => {
      const tokens = await authService.login(input)
      return loginWithTokens(tokens.access_token, tokens.refresh_token)
    },
    [loginWithTokens],
  )

  const register = useCallback(
    async (input: RegisterInput) => {
      const tokens = await authService.register(input)
      return loginWithTokens(tokens.access_token, tokens.refresh_token)
    },
    [loginWithTokens],
  )

  const logout = useCallback(async () => {
    const refreshToken = tokenStorage.getRefreshToken()
    try {
      if (refreshToken) {
        await authService.logout(refreshToken)
      }
    } catch {
      // Even if the server call fails, the user is logged out locally.
    } finally {
      tokenStorage.clear()
      setUser(null)
      // Drop cached data so the next user never sees it.
      queryClient.clear()
    }
  }, [queryClient])

  const refreshUser = useCallback(async () => {
    if (!tokenStorage.getAccessToken()) {
      setUser(null)
      return null
    }
    const me = await authService.getMe()
    setUser(me)
    return me
  }, [])

  const value = useMemo<AuthContextValue>(
    () => ({ user, isLoading, login, register, logout, refreshUser, loginWithTokens }),
    [user, isLoading, login, register, logout, refreshUser, loginWithTokens],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}
