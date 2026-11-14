// Helpers for "where did we come from?" navigation in the task pages.

export type PrefillLink = { type: "contact" | "lead" | "deal"; id: number }

/** Read ?contact_id= / ?lead_id= / ?deal_id= (first one wins). */
export function readPrefillLink(params: URLSearchParams): PrefillLink | undefined {
  for (const type of ["contact", "lead", "deal"] as const) {
    const id = Number(params.get(`${type}_id`))
    if (Number.isInteger(id) && id > 0) return { type, id }
  }
  return undefined
}

export function linkPath(link: PrefillLink): string {
  return `/${link.type}s/${link.id}`
}

/** Only allow in-app paths like "/tasks?view=done" (never "//evil.com"). */
export function safeReturnPath(value: string | null): string | null {
  return value && value.startsWith("/") && !value.startsWith("//") ? value : null
}
