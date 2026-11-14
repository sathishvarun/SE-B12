// Small wrapper around localStorage for the JWT access/refresh tokens.
// Every call is wrapped in try/catch because localStorage can throw
// (private browsing, storage disabled, quota exceeded).

const ACCESS_TOKEN_KEY = "access_token"
const REFRESH_TOKEN_KEY = "refresh_token"

function read(key: string): string | null {
  try {
    return window.localStorage.getItem(key)
  } catch {
    return null
  }
}

function write(key: string, value: string): void {
  try {
    window.localStorage.setItem(key, value)
  } catch {
    // Storage unavailable: the user just won't stay logged in across reloads.
  }
}

function remove(key: string): void {
  try {
    window.localStorage.removeItem(key)
  } catch {
    // Ignore: nothing we can do if storage is unavailable.
  }
}

export const tokenStorage = {
  getAccessToken: (): string | null => read(ACCESS_TOKEN_KEY),
  getRefreshToken: (): string | null => read(REFRESH_TOKEN_KEY),
  setTokens: (accessToken: string, refreshToken: string): void => {
    write(ACCESS_TOKEN_KEY, accessToken)
    write(REFRESH_TOKEN_KEY, refreshToken)
  },
  clear: (): void => {
    remove(ACCESS_TOKEN_KEY)
    remove(REFRESH_TOKEN_KEY)
  },
}
