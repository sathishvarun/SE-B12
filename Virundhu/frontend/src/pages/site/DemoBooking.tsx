import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { CalendarCheck } from "lucide-react";
import { useMemo, useState } from "react";
import { Link, useParams, useSearchParams } from "react-router-dom";
import { PageHero } from "@/components/site/SiteLayout";
import { Button, buttonVariants } from "@/components/ui/button";
import { Spinner } from "@/components/ui/misc";
import { cn } from "@/lib/utils";
import { demoApi, errorMessage, type DemoView } from "@/services/api";

const TZ = "Asia/Kolkata";
const day = (iso: string) => new Date(iso).toLocaleDateString("en-IN", { weekday: "long", day: "numeric", month: "short", timeZone: TZ });
const clock = (iso: string) => new Date(iso).toLocaleTimeString("en-IN", { hour: "numeric", minute: "2-digit", timeZone: TZ });

/** The demo agent's booking page: the restaurant picks a time and a way to meet; no sign-in. */
export default function DemoBooking() {
  const { token = "" } = useParams();
  const [params] = useSearchParams();
  const qc = useQueryClient();
  const q = useQuery({ queryKey: ["demo", token], queryFn: () => demoApi.get(token), retry: false });
  const [picked, setSlot] = useState<string | null>(null);
  const [chosenMode, setMode] = useState<string | null>(null);
  const fromLink = q.data && params.get("slot") !== null ? q.data.slots[Number(params.get("slot"))] ?? null : null;
  const slot = picked ?? fromLink;
  const mode = chosenMode ?? q.data?.mode ?? "meet";
  const [error, setError] = useState<string | null>(null);
  const done = (d: DemoView) => { qc.setQueryData(["demo", token], d); setError(null); };
  const book = useMutation({ mutationFn: () => demoApi.book(token, slot ?? "", mode), onSuccess: done, onError: (e) => setError(errorMessage(e)) });
  const more = useMutation({ mutationFn: () => demoApi.more(token), onSuccess: done });
  const cancel = useMutation({ mutationFn: () => demoApi.cancel(token), onSuccess: done });

  const byDay = useMemo(() => {
    const m = new Map<string, string[]>();
    for (const s of q.data?.slots ?? []) m.set(day(s), [...(m.get(day(s)) ?? []), s]);
    return [...m.entries()];
  }, [q.data]);

  if (q.isLoading) return <div className="flex min-h-[50vh] items-center justify-center"><Spinner /></div>;
  if (q.isError || !q.data) {
    return (
      <>
        <PageHero title="This link has closed" intro="Ask for a demo again and Nila will send fresh times within a minute." />
        <div className="mx-auto max-w-3xl px-5 py-12 sm:px-8"><Link to="/contact" className={buttonVariants({ size: "lg" })}>Ask for a demo</Link></div>
      </>
    );
  }
  const d = q.data;

  if (d.status === "booked" && d.starts_at) {
    return (
      <>
        <PageHero title={`You're booked, ${d.name}`} intro={`Your Virundhu demo for ${d.restaurant}. The calendar invite is in your email.`} />
        <section className="mx-auto max-w-3xl px-5 py-12 sm:px-8">
          <div className="rounded-[24px] border-2 border-night bg-white p-7 shadow-[8px_8px_0_#0c3b2e]">
            <CalendarCheck className="h-10 w-10 text-leaf" />
            <p className="mt-4 font-display text-3xl font-bold">{day(d.starts_at)}, {clock(d.starts_at)}</p>
            <p className="mt-1 text-ink-soft">India time · {d.minutes} minutes</p>
            <p className="mt-4 break-words text-lg">{d.where}</p>
            <p className="mt-4 text-sm text-ink-soft">We'll remind you a day before and an hour before.</p>
            <div className="mt-6 flex flex-wrap gap-3">
              <Button variant="outline" onClick={() => cancel.mutate()} disabled={cancel.isPending}>Change the time</Button>
            </div>
          </div>
        </section>
      </>
    );
  }

  return (
    <>
      <PageHero title={`Pick a time, ${d.name}`} intro={`A ${d.minutes}-minute Virundhu demo for ${d.restaurant}, using your own reviews. Times are India time.`} />
      <section className="mx-auto max-w-4xl px-5 py-12 sm:px-8">
        <h2 className="font-display text-2xl font-bold">How would you like to meet?</h2>
        <div className="mt-3 flex flex-wrap gap-2">
          {Object.entries(d.modes).map(([k, label]) => (
            <button key={k} type="button" aria-pressed={mode === k} onClick={() => setMode(k)}
              className={cn("rounded-full border-2 px-4 py-2 font-semibold transition-colors", mode === k ? "border-night bg-night text-jasmine" : "border-line bg-white hover:border-night")}>
              {label}
            </button>
          ))}
        </div>
        {mode === "in_person" ? <p className="mt-2 text-sm text-ink-soft">At {d.office}.</p> : null}

        <h2 className="mt-10 font-display text-2xl font-bold">Choose a time</h2>
        {byDay.length === 0 ? <p className="mt-3 text-ink-soft">No open times left on this link.</p> : null}
        <div className="mt-3 space-y-5">
          {byDay.map(([label, slots]) => (
            <div key={label}>
              <p className="font-semibold">{label}</p>
              <div className="mt-2 flex flex-wrap gap-2">
                {slots.map((s) => (
                  <button key={s} type="button" aria-pressed={slot === s} onClick={() => setSlot(s)}
                    className={cn("rounded-[12px] border-2 px-5 py-3 font-display text-lg font-bold transition-colors", slot === s ? "border-night bg-turmeric text-night" : "border-line bg-white hover:border-night")}>
                    {clock(s)}
                  </button>
                ))}
              </div>
            </div>
          ))}
        </div>
        <button type="button" onClick={() => more.mutate()} disabled={more.isPending} className="mt-4 font-semibold text-night underline underline-offset-4">
          {more.isPending ? "Finding more times..." : "None of these work? Show more times"}
        </button>
        {error ? <p role="alert" className="mt-5 rounded-[12px] bg-chilli-soft px-3.5 py-2.5 font-semibold text-[#b32f12]">{error}</p> : null}
        <div className="mt-8">
          <Button size="lg" disabled={!slot || book.isPending} onClick={() => book.mutate()}>
            {book.isPending ? <><Spinner /> Booking...</> : slot ? `Book ${day(slot)}, ${clock(slot)}` : "Pick a time first"}
          </Button>
        </div>
      </section>
    </>
  );
}
