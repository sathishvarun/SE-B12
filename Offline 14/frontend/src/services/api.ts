import i18n from "@/i18n"
import axios, { type AxiosError, type InternalAxiosRequestConfig } from "axios"

import { tokenStorage } from "@/lib/tokenStorage"
import type { ApiError, TokenResponse } from "@/types"

export const API_BASE_URL = `${import.meta.env.VITE_API_URL ?? "http://localhost:8000"}/api/v1`

/** Shared axios instance. Module services import this: `import api from "@/services/api"`. */
const api = axios.create({
  baseURL: API_BASE_URL,
  headers: { "Content-Type": "application/json" },
})

// Attach the access token (if we have one) to every request.
api.interceptors.request.use((config) => {
  const token = tokenStorage.getAccessToken()
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

/** Request config with our own "already retried once" flag. */
interface RetriableRequestConfig extends InternalAxiosRequestConfig {
  _retry?: boolean
}

// Requests where a 401 means "wrong credentials / bad token", not "access token expired".
const NO_REFRESH_PATHS = ["/auth/login", "/auth/register", "/auth/refresh"]

// Pages that work without being logged in: don't bounce the user to /login from these.
const PUBLIC_PATHS = ["/login", "/register", "/forgot-password", "/reset-password", "/pricing", "/oauth/callback"]

// One shared refresh request. If several requests get a 401 at the same time,
// they all wait for this single promise instead of each calling /auth/refresh
// (the backend rotates refresh tokens, so a second refresh would fail).
let refreshPromise: Promise<string> | null = null

async function refreshAccessToken(): Promise<string> {
  const refreshToken = tokenStorage.getRefreshToken()
  if (!refreshToken) {
    throw new Error("No refresh token")
  }
  // Plain axios (not `api`) so this call never goes through the interceptor again.
  const { data } = await axios.post<TokenResponse>(`${API_BASE_URL}/auth/refresh`, {
    refresh_token: refreshToken,
  })
  tokenStorage.setTokens(data.access_token, data.refresh_token)
  return data.access_token
}

function redirectToLogin(): void {
  if (!PUBLIC_PATHS.includes(window.location.pathname)) {
    window.location.assign("/login")
  }
}

api.interceptors.response.use(
  (response) => response,
  async (error: AxiosError<ApiError>) => {
    const original = error.config as RetriableRequestConfig | undefined
    const url = original?.url ?? ""
    const skipRefresh = NO_REFRESH_PATHS.some((path) => url.includes(path))

    if (error.response?.status !== 401 || !original || original._retry || skipRefresh) {
      return Promise.reject(error)
    }

    original._retry = true
    try {
      refreshPromise ??= refreshAccessToken().finally(() => {
        refreshPromise = null
      })
      const newToken = await refreshPromise
      original.headers.Authorization = `Bearer ${newToken}`
      return api(original)
    } catch {
      tokenStorage.clear()
      redirectToLogin()
      return Promise.reject(error)
    }
  },
)

/** Turn any thrown value (usually an AxiosError) into a user-friendly message. */
export function getErrorMessage(err: unknown): string {
  if (axios.isAxiosError<ApiError>(err)) {
    const detail = err.response?.data?.detail
    if (typeof detail === "string") {
      return detail
    }
    if (Array.isArray(detail) && detail.length > 0) {
      return detail.map((item) => item.msg).join(", ")
    }
    if (!err.response) {
      return i18n.t("errors.network")
    }
    return err.message
  }
  if (err instanceof Error) {
    return err.message
  }
  return i18n.t("errors.generic")
}

export default api
