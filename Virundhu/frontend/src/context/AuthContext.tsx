import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { clearActive, idleExpired } from "@/lib/idle";
import { authApi, tokens } from "@/services/api";
import type { CurrentUser } from "@/types";

interface AuthState {
  user: CurrentUser | null;
  ready: boolean;
  login: (email: string, password: string) => Promise<CurrentUser>;
  refreshUser: () => Promise<void>;
  acceptTokens: (data: { access_token: string }) => Promise<CurrentUser>;
  register: (body: { full_name: string; organization_name: string; city?: string; email: string; password: string; accept_terms: boolean; phone?: string; outlets?: number }) => Promise<CurrentUser>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthState | null>(null);

/** Keeps the signed-in user; restores the session on page load. */
export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<CurrentUser | null>(null);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    let alive = true;
    (async () => {
      if (!tokens.signedIn()) { setReady(true); return; }
      if (idleExpired()) {
        // Left idle past the limit (tab closed or computer asleep): end the session instead of restoring it.
        tokens.clear();
        clearActive();
        await authApi.logout().catch(() => undefined);
        if (alive) setReady(true);
        return;
      }
      try {
        if (!(await authApi.refresh())) throw new Error("signed out");
        const me = await authApi.me();
        if (alive) setUser(me);
      } catch {
        tokens.clear();
      } finally {
        if (alive) setReady(true);
      }
    })();
    return () => { alive = false; };
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    const data = await authApi.login(email, password);
    tokens.save(data);
    setUser(data.user);
    return data.user;
  }, []);

  const refreshUser = useCallback(async () => {
    setUser(await authApi.me());
  }, []);

  const acceptTokens = useCallback(async (data: { access_token: string }) => {
    tokens.save(data);
    const me = await authApi.me();
    setUser(me);
    return me;
  }, []);

  const register = useCallback(async (body: Parameters<AuthState["register"]>[0]) => {
    const data = await authApi.register(body);
    tokens.save(data);
    setUser(data.user);
    return data.user;
  }, []);

  const logout = useCallback(async () => {
    tokens.clear();
    clearActive();
    setUser(null);
    await authApi.logout().catch(() => undefined);
  }, []);

  const value = useMemo(() => ({ user, ready, login, refreshUser, acceptTokens, register, logout }), [user, ready, login, refreshUser, acceptTokens, register, logout]);
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

// eslint-disable-next-line react-refresh/only-export-components
export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside AuthProvider");
  return ctx;
}
