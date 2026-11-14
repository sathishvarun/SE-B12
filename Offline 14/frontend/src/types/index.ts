// Shared types used across modules.
// Module-specific types (auth, contacts, leads, deals, ...) are added in
// Phase 2 as one file per module, e.g. `types/contact.ts`, and re-exported below.

/** Paginated list response returned by list endpoints. */
export interface Page<T> {
  items: T[]
  total: number
  page: number
  page_size: number
}

/** A single FastAPI validation error entry (422 responses). */
export interface ValidationErrorItem {
  loc: (string | number)[]
  msg: string
  type: string
}

/** Error body returned by the backend. `detail` is a string for most errors
 *  and a list of validation errors for 422 responses. */
export interface ApiError {
  detail: string | ValidationErrorItem[]
}

/** Common query params for paginated list endpoints. */
export interface PaginationParams {
  page?: number
  page_size?: number
}

export * from "./admin"
export * from "./attachment"
export * from "./auth"
export * from "./billing"
export * from "./contact"
export * from "./dashboard"
export * from "./deal"
export * from "./lead"
export * from "./task"
