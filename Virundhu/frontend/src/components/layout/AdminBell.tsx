import { useQuery } from "@tanstack/react-query";
import { Bell, Building2, Clock, CreditCard, KeyRound, Mail, ShieldAlert, Trash2 } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { timeAgo } from "@/lib/time";
import { cn } from "@/lib/utils";
import { adminApi } from "@/services/api";

const SEEN = "vr_admin_seen";
const ICON: Record<string, typeof Bell> = {
  signup: Building2, trial_ending: Clock, trial_ended: Clock, urgent_waiting: ShieldAlert,
  password_changed: KeyRound, password_reset: KeyRound, account_deleted: Trash2, payment: CreditCard, demo_request: Mail,
};

/** The admin's bell: new customers, trials ending, urgent reviews, password changes, deleted accounts, payments, demo requests. */
export function AdminBell({ align = "right" }: { align?: "left" | "right" }) {
  const [open, setOpen] = useState(false);
  const [seen, setSeen] = useState<string[]>(() => { try { return JSON.parse(localStorage.getItem(SEEN) ?? "[]") as string[]; } catch { return []; } });
  const box = useRef<HTMLDivElement>(null);
  const { data } = useQuery({ queryKey: ["admin-events"], queryFn: adminApi.events, refetchInterval: 60_000 });
  const unread = (data ?? []).filter((e) => !seen.includes(e.id)).length;

  useEffect(() => {
    if (!open) return;
    const close = (e: MouseEvent) => { if (box.current && !box.current.contains(e.target as Node)) setOpen(false); };
    document.addEventListener("mousedown", close);
    return () => document.removeEventListener("mousedown", close);
  }, [open]);

  function markSeen() {
    const ids = (data ?? []).map((e) => e.id);
    setSeen(ids);
    try { localStorage.setItem(SEEN, JSON.stringify(ids)); } catch { /* storage off */ }
  }

  return (
    <div className="relative" ref={box}>
      <button onClick={() => { setOpen((o) => !o); if (!open) markSeen(); }} aria-label={`Admin alerts, ${unread} new`}
        className="relative rounded-full p-2.5 text-mist hover:bg-white/10 hover:text-white cursor-pointer">
        <Bell className="h-5 w-5" />
        {unread ? <span className="absolute -right-1 -top-1 min-w-5 rounded-full bg-turmeric px-1.5 text-center text-[0.7rem] font-bold leading-5 text-night">{unread}</span> : null}
      </button>
      {open ? (
        <div className={cn("absolute z-50 mt-2 w-[min(380px,calc(100vw-24px))] overflow-hidden rounded-[18px] border-2 border-night bg-white text-ink shadow-[8px_8px_0_#0c3b2e]", align === "left" ? "left-0" : "right-0")}>
          <p className="border-b-2 border-jasmine-2 px-4 py-3 font-display text-lg font-bold">Needs your attention</p>
          <ul className="max-h-[380px] overflow-y-auto">
            {!data?.length ? <li className="px-4 py-8 text-center text-ink-soft">All quiet. New customers, ending trials and unanswered urgent reviews show up here.</li> : null}
            {data?.map((e) => { const Icon = ICON[e.kind] ?? Bell; return (
              <li key={e.id} className="flex gap-3 border-b border-jasmine-2 px-4 py-3">
                <Icon className={cn("mt-0.5 h-5 w-5 shrink-0", e.kind === "urgent_waiting" ? "text-chilli" : e.kind === "signup" ? "text-leaf" : "text-turmeric-deep")} />
                <div><p className="font-semibold leading-snug">{e.title}</p><p className="text-sm text-ink-soft">{e.body}</p><p className="text-xs text-ink-soft">{timeAgo(e.at)}</p></div>
              </li>
            ); })}
          </ul>
        </div>
      ) : null}
    </div>
  );
}
