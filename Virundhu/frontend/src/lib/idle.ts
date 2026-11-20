/**
 * Auto sign-out after inactivity (security): 5 minutes for the platform admin, 15 for restaurant users.
 * "Activity" = mouse, keyboard, touch, scroll or wheel in any open Virundhu tab. The last-activity time is shared
 * between tabs through localStorage (a timestamp only, never a token), and it is also checked when the site is
 * opened again, so closing the tab and coming back later still asks for a fresh sign-in.
 */
export const IDLE_LIMIT_MS = { admin: 5 * 60_000, user: 15 * 60_000 } as const;
export const IDLE_WARN_MS = 60_000; // warn one minute before

const KEY = "virundhu.lastActive";

export function markActive(limitMs: number) {
  try { localStorage.setItem(KEY, JSON.stringify({ at: Date.now(), limit: limitMs })); } catch { /* storage may be off */ }
}

export function lastActive(): { at: number; limit: number } | null {
  try {
    const v = JSON.parse(localStorage.getItem(KEY) ?? "null") as { at?: number; limit?: number } | null;
    return v && typeof v.at === "number" && typeof v.limit === "number" ? { at: v.at, limit: v.limit } : null;
  } catch { return null; }
}

export function clearActive() {
  try { localStorage.removeItem(KEY); } catch { /* storage may be off */ }
}

/** True when the saved session has been idle longer than its limit (checked before restoring a session). */
export function idleExpired(now = Date.now()): boolean {
  const v = lastActive();
  return v !== null && now - v.at > v.limit;
}
