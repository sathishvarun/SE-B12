import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Bell, ShieldAlert } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { timeAgo } from "@/lib/time";
import { cn } from "@/lib/utils";
import { appApi } from "@/services/api";

/** Bell with unread count. Checks every 15 seconds and pops a toast for each new urgent alert. */
export function NotificationBell({ onDark = false, align = "right" }: { onDark?: boolean; align?: "left" | "right" }) {
  const qc = useQueryClient();
  const navigate = useNavigate();
  const [open, setOpen] = useState(false);
  const seen = useRef<number | null>(null);
  const box = useRef<HTMLDivElement>(null);
  const { data } = useQuery({ queryKey: ["notifications"], queryFn: appApi.notifications, refetchInterval: 15_000 });

  useEffect(() => {
    if (!data) return;
    const newest = data.items[0]?.id ?? 0;
    if (seen.current !== null && newest > seen.current) {
      data.items.filter((n) => n.id > (seen.current ?? 0) && !n.read).slice(0, 3).forEach((n) =>
        toast.error(n.title, { description: n.body, action: n.review_id ? { label: "Open", onClick: () => navigate(`/app/inbox?view=today&id=${n.review_id}`) } : undefined }));
      void qc.invalidateQueries({ queryKey: ["overview"] });
      void qc.invalidateQueries({ queryKey: ["reviews"] });
    }
    seen.current = newest;
  }, [data, qc, navigate]);

  useEffect(() => {
    if (!open) return;
    const close = (e: MouseEvent) => { if (box.current && !box.current.contains(e.target as Node)) setOpen(false); };
    document.addEventListener("mousedown", close);
    return () => document.removeEventListener("mousedown", close);
  }, [open]);

  async function readAll() {
    await appApi.readAll();
    void qc.invalidateQueries({ queryKey: ["notifications"] });
  }

  const unread = data?.unread ?? 0;
  return (
    <div className="relative" ref={box}>
      <button onClick={() => setOpen((o) => !o)} aria-label={`Alerts, ${unread} unread`} aria-expanded={open}
        className={cn("relative rounded-full p-2.5 transition-colors cursor-pointer", onDark ? "text-mist hover:bg-white/10 hover:text-white" : "bg-white text-ink shadow-sm ring-2 ring-line hover:ring-night")}>
        <Bell className="h-5 w-5" />
        {unread ? <span className="absolute -right-1 -top-1 min-w-5 rounded-full bg-chilli px-1.5 text-center text-[0.7rem] font-bold leading-5 text-white">{unread > 99 ? "99+" : unread}</span> : null}
      </button>
      {open ? (
        <div className={cn("absolute z-50 mt-2 w-[min(380px,calc(100vw-24px))]", align === "left" ? "left-0" : "right-0", " overflow-hidden rounded-[18px] border-2 border-night bg-white text-ink shadow-[8px_8px_0_#0c3b2e]")}>
          <div className="flex items-center justify-between border-b-2 border-jasmine-2 px-4 py-3">
            <p className="font-display text-lg font-bold">Alerts</p>
            {unread ? <button onClick={readAll} className="text-sm font-semibold text-ink-soft hover:text-ink cursor-pointer">Mark all read</button> : null}
          </div>
          <ul className="max-h-[360px] overflow-y-auto">
            {!data?.items.length ? <li className="px-4 py-8 text-center text-ink-soft">No alerts yet. You'll hear here the moment a guest has a serious problem.</li> : null}
            {data?.items.slice(0, 8).map((n) => (
              <li key={n.id}>
                <Link to={n.review_id ? `/app/inbox?view=today&id=${n.review_id}` : "/app/alerts"} onClick={() => setOpen(false)}
                  className={cn("flex gap-3 px-4 py-3 hover:bg-jasmine", !n.read && "bg-chilli-soft/50")}>
                  <ShieldAlert className="mt-0.5 h-5 w-5 shrink-0 text-chilli" />
                  <div className="min-w-0">
                    <p className="font-semibold leading-snug">{n.title}</p>
                    <p className="line-clamp-2 text-sm text-ink-soft">{n.body}</p>
                    <p className="mt-0.5 text-xs text-ink-soft">{timeAgo(n.created_at)}</p>
                  </div>
                </Link>
              </li>
            ))}
          </ul>
          <Link to="/app/alerts" onClick={() => setOpen(false)} className="block border-t-2 border-jasmine-2 px-4 py-3 text-center text-sm font-semibold hover:bg-jasmine">See all alerts</Link>
        </div>
      ) : null}
    </div>
  );
}
