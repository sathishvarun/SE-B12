import { useQuery, useQueryClient } from "@tanstack/react-query";
import { BellRing, CheckCheck, ShieldAlert } from "lucide-react";
import { Link } from "react-router-dom";
import { timeAgo } from "@/lib/time";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/misc";
import { cn } from "@/lib/utils";
import { appApi } from "@/services/api";

/** Every instant alert, newest first. Alerts are created the moment a serious review is read. */
export default function Alerts() {
  const qc = useQueryClient();
  const { data, isLoading } = useQuery({ queryKey: ["notifications"], queryFn: appApi.notifications, refetchInterval: 15_000 });

  async function readAll() {
    await appApi.readAll();
    void qc.invalidateQueries({ queryKey: ["notifications"] });
  }

  return (
    <div className="mx-auto max-w-4xl">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-[2.3rem] font-bold">Alerts</h1>
          <p className="mt-1 max-w-xl text-ink-soft">
            The moment a guest reports something serious (food safety, a wrong or late order, a refund demand, rude staff),
            Virundhu alerts the owner and managers here, on the bell, and by email.
          </p>
        </div>
        {data?.unread ? <Button variant="dark" onClick={readAll}><CheckCheck className="h-4 w-4" /> Mark all read</Button> : null}
      </div>

      <div className="mt-6 grid grid-cols-1 gap-3 sm:grid-cols-3">
        <div className="rounded-[16px] bg-chilli p-4 text-white"><p className="text-sm font-semibold text-white/85">Unread</p><p className="tabular font-display text-[2.2rem] font-bold leading-none">{data?.unread ?? "-"}</p></div>
        <div className="rounded-[16px] border-2 border-line bg-white p-4"><p className="text-sm font-semibold text-ink-soft">Last 30 alerts</p><p className="tabular font-display text-[2.2rem] font-bold leading-none">{data?.items.length ?? "-"}</p></div>
        <div className="rounded-[16px] border-2 border-line bg-white p-4"><p className="text-sm font-semibold text-ink-soft">How fast</p><p className="font-display text-[1.4rem] font-bold leading-tight">Within seconds of the review arriving</p></div>
      </div>

      <ul className="mt-6 space-y-3">
        {isLoading ? Array.from({ length: 4 }, (_, i) => <li key={i}><Skeleton className="h-[92px]" /></li>) : null}
        {!isLoading && !data?.items.length ? (
          <li className="rounded-[20px] border-2 border-dashed border-ink/15 bg-white p-10 text-center">
            <BellRing className="mx-auto h-10 w-10 text-turmeric" />
            <p className="mt-3 font-display text-xl font-bold">No alerts yet</p>
            <p className="mx-auto mt-1 max-w-md text-ink-soft">Go to Connections and start the Zomato or Swiggy test feed to see alerts arrive live.</p>
            <Link to="/app/connections" className="mt-4 inline-block font-semibold underline decoration-turmeric decoration-2 underline-offset-4">Open Connections</Link>
          </li>
        ) : null}
        {data?.items.map((n) => (
          <li key={n.id}>
            <Link to={n.review_id ? `/app/inbox?view=today&id=${n.review_id}` : "#"}
              className={cn("flex gap-4 rounded-[18px] border-2 bg-white p-4 transition-colors hover:border-night", n.read ? "border-transparent" : "border-chilli/40")}>
              <span className={cn("flex h-11 w-11 shrink-0 items-center justify-center rounded-full", n.read ? "bg-jasmine-2 text-ink-soft" : "bg-chilli text-white")}>
                <ShieldAlert className="h-5 w-5" />
              </span>
              <div className="min-w-0 flex-1">
                <div className="flex flex-wrap items-baseline justify-between gap-2">
                  <p className="font-display text-lg font-bold leading-snug">{n.title}</p>
                  <span className="text-sm text-ink-soft">{timeAgo(n.created_at)}</span>
                </div>
                <p className="mt-0.5 text-ink-soft">{n.body}</p>
              </div>
            </Link>
          </li>
        ))}
      </ul>
    </div>
  );
}
