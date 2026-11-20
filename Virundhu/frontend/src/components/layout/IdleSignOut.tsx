import { Clock } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/context/AuthContext";
import { IDLE_LIMIT_MS, IDLE_WARN_MS, clearActive, lastActive, markActive } from "@/lib/idle";

const EVENTS = ["mousemove", "mousedown", "keydown", "touchstart", "scroll", "wheel"] as const;

/** Signs the person out after inactivity (admin 5 min, restaurant users 15 min), with a one-minute warning. */
export function IdleSignOut() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const limit = user?.is_superadmin ? IDLE_LIMIT_MS.admin : IDLE_LIMIT_MS.user;
  const [left, setLeft] = useState<number | null>(null);
  const lastWrite = useRef(0);

  const bump = useCallback(() => {
    const now = Date.now();
    if (now - lastWrite.current < 5_000) return; // write at most every 5 seconds
    lastWrite.current = now;
    markActive(limit);
  }, [limit]);

  useEffect(() => {
    if (!user) return;
    markActive(limit);
    lastWrite.current = Date.now();
    const onAct = () => bump();
    EVENTS.forEach((e) => window.addEventListener(e, onAct, { passive: true }));
    let done = false;
    const check = async () => {
      if (done) return;
      const v = lastActive();
      const idle = Date.now() - (v?.at ?? Date.now());
      if (idle >= limit) {
        done = true;
        clearActive();
        await logout();
        navigate(`/login?timeout=${user.is_superadmin ? 5 : 15}`, { replace: true });
        return;
      }
      setLeft(idle >= limit - IDLE_WARN_MS ? Math.ceil((limit - idle) / 1000) : null);
    };
    const timer = window.setInterval(check, 1_000);
    const onWake = () => { void check(); };
    document.addEventListener("visibilitychange", onWake);
    window.addEventListener("focus", onWake);
    return () => {
      done = true;
      window.clearInterval(timer);
      EVENTS.forEach((e) => window.removeEventListener(e, onAct));
      document.removeEventListener("visibilitychange", onWake);
      window.removeEventListener("focus", onWake);
    };
  }, [user, limit, bump, logout, navigate]);

  if (left === null) return null;
  return (
    <div role="alertdialog" aria-live="assertive" aria-labelledby="idle-title" className="fixed inset-x-4 bottom-24 z-50 mx-auto max-w-md rounded-[20px] border-2 border-night bg-white p-5 shadow-[6px_6px_0_#0c3b2e] lg:bottom-8">
      <p id="idle-title" className="flex items-center gap-2 font-display text-lg font-bold"><Clock className="h-5 w-5 text-[#b32f12]" /> Still there?</p>
      <p className="mt-1 text-ink-soft">For your security you'll be signed out in <b className="text-ink">{left} second{left === 1 ? "" : "s"}</b> because nothing has happened for a while.</p>
      <Button className="mt-4" onClick={() => { markActive(limit); lastWrite.current = Date.now(); setLeft(null); }}>Stay signed in</Button>
    </div>
  );
}
