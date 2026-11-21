import { Clock } from "lucide-react";
import { useEffect, useState } from "react";
import { cn } from "@/lib/utils";
import type { Review } from "@/types";

/** Minutes left (negative = late) until the reply promise deadline, ticking every 30 seconds. */
export function useMinutesLeft(due: string | null | undefined): number | null {
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    if (!due) return;
    const t = setInterval(() => setNow(Date.now()), 30_000);
    return () => clearInterval(t);
  }, [due]);
  if (!due) return null;
  return Math.round((new Date(due).getTime() - now) / 60_000);
}

function span(min: number): string {
  const m = Math.abs(min);
  if (m < 60) return `${m} min`;
  const h = Math.floor(m / 60);
  return m % 60 ? `${h} h ${m % 60} min` : `${h} h`;
}

/** "38 min left to reply" on bad reviews still waiting; red once the promise is broken. */
export function ReplyClock({ review, className }: { review: Review; className?: string }) {
  const pending = review.workflow_status === "new" || review.workflow_status === "in_progress";
  const left = useMinutesLeft(pending ? review.reply_due_at : null);
  if (left === null) return null;
  const late = left < 0;
  const close = !late && left <= 15;
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-semibold tabular",
        late ? "bg-chilli text-white" : close ? "bg-[#fdefc9] text-[#8a5a00]" : "bg-[#dff3e8] text-[#16784a]",
        className,
      )}
      title="Your promise: every bad review answered within the time you chose in Automation"
    >
      <Clock className="h-3.5 w-3.5" aria-hidden="true" />
      {late ? `${span(left)} late` : `${span(left)} left to reply`}
    </span>
  );
}
