export type Plan = "free" | "pro"

export interface TokenResponse {
  access_token: string
  refresh_token: string
  token_type: "bearer"
}

export interface User {
  id: number
  email: string
  full_name: string | null
  is_active: boolean
  is_verified: boolean
  is_admin: boolean
  oauth_provider: "google" | null
  has_password: boolean
  plan: Plan
  created_at: string
}

export interface LoginInput {
  email: string
  password: string
}

export interface RegisterInput {
  email: string
  password: string
  full_name: string
}

export interface UpdateProfileInput {
  full_name?: string
  current_password?: string
  new_password?: string
}
