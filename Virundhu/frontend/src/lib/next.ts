/**
 * Where to go after signing in: the page the person was trying to open (e.g. a link to /app/admin/money).
 * Kept in sessionStorage as well as router state so it survives the Google sign-in round trip. Only /app paths are
 * accepted, so the value can never send someone to another site.
 */
const KEY = "virundhu.next";

const safe = (p: string | null | undefined) => (p && p.startsWith("/app") && !p.startsWith("//") ? p : null);

export function rememberNext(path: string) {
  try { if (safe(path)) sessionStorage.setItem(KEY, path); } catch { /* storage may be off */ }
}

export function takeNext(fromState: string | null | undefined, isAdmin: boolean | undefined): string {
  let stored: string | null = null;
  try { stored = sessionStorage.getItem(KEY); sessionStorage.removeItem(KEY); } catch { /* storage may be off */ }
  const want = safe(fromState) ?? safe(stored);
  if (isAdmin) return want && want.startsWith("/app/admin") ? want : "/app/admin";
  return want && !want.startsWith("/app/admin") ? want : "/app";
}
