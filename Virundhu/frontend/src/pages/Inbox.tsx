import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, Check, CheckCheck, Copy, ExternalLink, Search, Send, ShieldAlert, X } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { toast } from "sonner";
import { ReplyClock } from "@/components/review/ReplyClock";
import { CategoryChip, LanguageChip, SentimentChip, UrgencyChip } from "@/components/review/Tags";
import { Button } from "@/components/ui/button";
import { Chip, Skeleton, Spinner, Stars } from "@/components/ui/misc";
import { platformLabel, shortDate } from "@/lib/copy";
import { cn } from "@/lib/utils";
import { appApi, errorMessage } from "@/services/api";
import type { InboxView, Review, WorkflowStatus } from "@/types";

// Zomato and Swiggy have no public reply API, so the reply is copied and their partner site opens for pasting.
const PARTNER_URL: Record<string, string | undefined> = {
  zomato: "https://www.zomato.com/partners", swiggy: "https://partner.swiggy.com", tripadvisor: "https://www.tripadvisor.in/Owners",
  instagram: "https://www.instagram.com/", facebook: "https://business.facebook.com/latest/inbox",
};

const VIEWS: { key: InboxView; label: string }[] = [
  { key: "clock", label: "Waiting for a reply" },
  { key: "today", label: "Urgent" },
  { key: "week", label: "This week" },
  { key: "all", label: "All reviews" },
  { key: "replied", label: "Replied" },
];

const URGENCY_BAR = { high: "bg-chilli", medium: "bg-turmeric", low: "bg-leaf" } as const;

function ReviewDetail({ review, onBack, onNext }: { review: Review; onBack: () => void; onNext: () => void }) {
  const qc = useQueryClient();
  const a = review.analysis;
  const [reply, setReply] = useState(review.final_reply ?? a?.suggested_reply ?? "");
  const [copied, setCopied] = useState(false);

  const mutation = useMutation({
    mutationFn: (status: WorkflowStatus) => appApi.updateReview(review.id, { workflow_status: status, final_reply: reply }),
    onSuccess: (_, status) => {
      toast.success(status === "replied" ? "Marked as replied" : "Moved out of the inbox");
      void qc.invalidateQueries({ queryKey: ["reviews"] });
      void qc.invalidateQueries({ queryKey: ["overview"] });
      onNext();
    },
    onError: (err) => toast.error(errorMessage(err)),
  });

  const postGoogle = useMutation({
    mutationFn: () => appApi.postReply(review.id, reply),
    onSuccess: () => {
      toast.success("Reply posted on Google");
      void qc.invalidateQueries({ queryKey: ["reviews"] });
      void qc.invalidateQueries({ queryKey: ["overview"] });
    },
    onError: (err) => toast.error(errorMessage(err)),
  });

  async function copy() {
    try {
      await navigator.clipboard.writeText(reply);
      setCopied(true);
      toast.success("Reply copied. Paste it on " + platformLabel[review.platform] + ".");
      setTimeout(() => setCopied(false), 1800);
    } catch {
      toast.error("Your browser blocked copying. Select the text and copy it by hand.");
    }
  }

  // Keyboard: c = copy, r = mark replied (when not typing)
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const tag = (e.target as HTMLElement).tagName;
      if (tag === "TEXTAREA" || tag === "INPUT" || e.metaKey || e.ctrlKey) return;
      if (e.key === "c") { e.preventDefault(); void copy(); }
      if (e.key === "r") { e.preventDefault(); mutation.mutate("replied"); }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  });

  return (
    <article className="flex h-full flex-col rounded-[20px] border-2 border-line bg-white">
      <div className="flex items-center justify-between gap-3 border-b-2 border-jasmine-2 px-5 py-3.5 sm:px-6">
        <button onClick={onBack} className="flex items-center gap-1.5 text-sm font-semibold text-ink-soft hover:text-ink lg:hidden cursor-pointer"><ArrowLeft className="h-4 w-4" /> All reviews</button>
        <p className="text-sm text-ink-soft">{platformLabel[review.platform]} review, {review.outlet_name}, {shortDate(review.review_date)}</p>
        <Stars rating={review.rating} className="text-ink" />
      </div>
      <div className="flex-1 space-y-5 overflow-y-auto px-5 py-5 sm:px-6">
        <p className="font-display text-[1.45rem] font-medium leading-snug">{review.review_text}</p>
        {review.guest_name || review.guest_contact ? (
          <p className="text-sm text-ink-soft">From {review.guest_name || "a guest"}{review.guest_contact ? <>, wants a reply at <b className="text-ink">{review.guest_contact}</b></> : null}</p>
        ) : null}
        {a ? (
          <>
            <div className="flex flex-wrap gap-2">
              {a.urgency ? <UrgencyChip urgency={a.urgency} /> : null}
              {a.sentiment ? <SentimentChip sentiment={a.sentiment} /> : null}
              {a.category ? <CategoryChip category={a.category} /> : null}
              {a.language ? <LanguageChip language={a.language} /> : null}
              <ReplyClock review={review} />
              {review.workflow_status === "replied" ? <Chip tone="dark" className="bg-night text-jasmine"><CheckCheck className="h-3.5 w-3.5" />Replied</Chip> : null}
              {review.reply_posted_at ? <Chip tone="sky">{review.auto_replied ? "Replied on Google automatically" : "Reply posted on Google"}</Chip> : null}
              {review.is_sample ? <Chip tone="turmeric">Sample data, not a real guest</Chip> : null}
            </div>
            {a.food_safety ? (
              <p className="flex items-start gap-2 rounded-[12px] bg-chilli-soft p-3 text-sm font-semibold text-[#b32f12]">
                <ShieldAlert className="mt-0.5 h-4 w-4 shrink-0" /> Food-safety complaint. Call the outlet manager and check the kitchen today.
              </p>
            ) : null}
            <div className="rounded-[14px] bg-jasmine px-4 py-3">
              <p className="text-sm text-ink-soft">In one line</p>
              <p className="font-semibold">{a.summary}</p>
            </div>
          </>
        ) : <p className="text-ink-soft">This review hasn't been read yet.</p>}
        <div>
          <label htmlFor="reply" className="text-sm font-semibold">Reply draft. Edit it, copy it, post it.</label>
          <textarea id="reply" value={reply} onChange={(e) => setReply(e.target.value)} rows={5}
            className="mt-2 w-full resize-y rounded-[14px] border-2 border-line p-3.5 leading-relaxed focus:border-night focus:outline-none" />
        </div>
      </div>
      <div className="flex flex-wrap items-center gap-2 border-t-2 border-jasmine-2 px-5 py-4 sm:px-6">
        {review.can_post_to_google ? (
          <Button onClick={() => postGoogle.mutate()} variant="primary" disabled={postGoogle.isPending}>
            {postGoogle.isPending ? <Spinner /> : <Send className="h-4 w-4" />} {review.reply_posted_at ? "Update reply on Google" : "Post reply on Google"}
          </Button>
        ) : null}
        {PARTNER_URL[review.platform] ? (
          <Button variant="primary" onClick={() => { void copy(); window.open(PARTNER_URL[review.platform], "_blank", "noopener"); }}>
            <ExternalLink className="h-4 w-4" /> Copy reply and open {platformLabel[review.platform]}
          </Button>
        ) : null}
        <Button onClick={copy} variant={review.can_post_to_google || PARTNER_URL[review.platform] ? "outline" : "primary"}>{copied ? <><Check className="h-4 w-4" /> Copied</> : <><Copy className="h-4 w-4" /> Copy reply</>}</Button>
        <Button onClick={() => mutation.mutate("replied")} variant="dark" disabled={mutation.isPending || review.workflow_status === "replied"}>
          {mutation.isPending ? <Spinner /> : <CheckCheck className="h-4 w-4" />} Mark as replied
        </Button>
        <Button onClick={() => mutation.mutate("ignored")} variant="ghost" disabled={mutation.isPending}><X className="h-4 w-4" /> No reply needed</Button>
        <span className="ml-auto hidden text-xs text-ink-soft xl:inline">Keys: J / K move, C copy, R replied</span>
      </div>
    </article>
  );
}

export default function Inbox() {
  const [params, setParams] = useSearchParams();
  const view = (params.get("view") as InboxView | null) ?? "clock";
  const selectedId = Number(params.get("id")) || null;
  const [q, setQ] = useState("");
  const [search, setSearch] = useState("");

  useEffect(() => { const t = setTimeout(() => setSearch(q.trim()), 300); return () => clearTimeout(t); }, [q]);

  const { data, isLoading, isError, error } = useQuery({
    queryKey: ["reviews", view, search],
    queryFn: () => appApi.reviews({ view, q: search || undefined }),
    placeholderData: keepPreviousData,
    refetchInterval: 20_000,
  });
  const items = useMemo(() => data?.items ?? [], [data]);
  const selected = items.find((r) => r.id === selectedId) ?? null;

  function select(id: number | null) {
    const next = new URLSearchParams(params);
    if (id) next.set("id", String(id)); else next.delete("id");
    setParams(next, { replace: true });
  }
  function setView(v: InboxView) { setParams({ view: v }, { replace: true }); }

  // Pick the first review on desktop when nothing is selected
  useEffect(() => {
    const first = items[0];
    if (!selectedId && first && window.matchMedia("(min-width: 1024px)").matches) select(first.id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [items, selectedId]);

  function move(step: number) {
    if (!items.length) return;
    const i = items.findIndex((r) => r.id === selectedId);
    const next = items[Math.min(items.length - 1, Math.max(0, (i < 0 ? 0 : i + step)))];
    if (next) select(next.id);
  }

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const tag = (e.target as HTMLElement).tagName;
      if (tag === "TEXTAREA" || tag === "INPUT" || e.metaKey || e.ctrlKey) return;
      if (e.key === "j") { e.preventDefault(); move(1); }
      if (e.key === "k") { e.preventDefault(); move(-1); }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  });

  return (
    <div className="mx-auto max-w-[1400px]">
      <div className={cn(selected && "hidden lg:block")}>
        <h1 className="text-[2.3rem] font-bold">Inbox</h1>
        <p className="mt-1 text-ink-soft">Bad reviews waiting for a reply come first, oldest on top. Each one has a reply ready to copy. Post it, then tap Replied to stop the clock.</p>
        <div className="mt-5 flex flex-wrap items-center gap-3">
          <div className="flex flex-wrap gap-1.5 rounded-full bg-jasmine-2 p-1" role="tablist" aria-label="Inbox views">
            {VIEWS.map((v) => (
              <button key={v.key} role="tab" aria-selected={view === v.key} onClick={() => setView(v.key)}
                className={cn("flex items-center gap-2 rounded-full px-3.5 py-1.5 text-sm font-semibold transition-colors cursor-pointer",
                  view === v.key ? "bg-night text-jasmine" : "text-ink-soft hover:text-ink")}>
                {v.label}
                <span className={cn("tabular rounded-full px-1.5 text-xs leading-5",
                  (v.key === "today" || v.key === "clock") && (data?.counts[v.key] ?? 0) > 0 ? "bg-chilli text-white" : view === v.key ? "bg-white/15" : "bg-white")}>
                  {data?.counts[v.key] ?? "-"}
                </span>
              </button>
            ))}
          </div>
          <label className="relative min-w-[220px] flex-1">
            <span className="sr-only">Search reviews</span>
            <Search className="pointer-events-none absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-ink-soft" />
            <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search, e.g. biryani, late, mudi"
              className="h-10 w-full rounded-full border-2 border-line bg-white pl-10 pr-4 text-[0.95rem] focus:border-night focus:outline-none" />
          </label>
        </div>
      </div>

      {isError ? <p className="mt-6 rounded-[14px] bg-chilli-soft p-4 font-medium text-[#b32f12]">{errorMessage(error)}</p> : null}

      <div className="mt-5 grid grid-cols-1 gap-5 lg:grid-cols-[minmax(0,0.95fr)_minmax(0,1.25fr)]">
        <ul className={cn("space-y-2.5 lg:max-h-[calc(100dvh-230px)] lg:overflow-y-auto lg:pr-1", selected && "hidden lg:block")} aria-label="Reviews">
          {isLoading ? Array.from({ length: 6 }, (_, i) => <li key={i}><Skeleton className="h-[104px]" /></li>) : null}
          {!isLoading && items.length === 0 ? (
            <li className="rounded-[18px] border-2 border-dashed border-ink/15 bg-white p-8 text-center">
              <p className="font-display text-xl font-bold">{view === "clock" ? "No bad review is waiting" : view === "today" ? "Nothing urgent right now" : "No reviews here"}</p>
              <p className="mt-1 text-ink-soft">{view === "clock" || view === "today" ? "Every unhappy guest has an answer. Nice work." : "Try another tab or clear the search."}</p>
            </li>
          ) : null}
          {items.map((r) => (
            <li key={r.id}>
              <button onClick={() => select(r.id)} aria-current={r.id === selectedId}
                className={cn("relative flex w-full gap-3 overflow-hidden rounded-[16px] border-2 bg-white p-4 pl-5 text-left transition-colors cursor-pointer",
                  r.id === selectedId ? "border-night" : "border-transparent hover:border-line")}>
                <span className={cn("absolute inset-y-0 left-0 w-1.5", r.analysis?.urgency ? URGENCY_BAR[r.analysis.urgency] : "bg-line")} aria-hidden="true" />
                <div className="min-w-0 flex-1">
                  <div className="flex items-center justify-between gap-2 text-xs text-ink-soft">
                    <span className="truncate">{platformLabel[r.platform]}, {r.outlet_name}, {shortDate(r.review_date)}</span>
                    <Stars rating={r.rating} className="shrink-0 text-ink" />
                  </div>
                  <p className="mt-1 font-semibold leading-snug">{r.analysis?.summary ?? r.review_text}</p>
                  <p className="mt-0.5 truncate text-sm text-ink-soft">{r.review_text}</p>
                  <div className="mt-1 flex flex-wrap gap-2 text-xs font-semibold">
                    <ReplyClock review={r} />
                    {r.workflow_status === "replied" ? <span className="flex items-center gap-1 text-[#16784a]"><CheckCheck className="h-3.5 w-3.5" />Replied</span> : null}
                    {r.is_sample ? <span className="rounded-full bg-[#fdefc9] px-2 text-[#8a5a00]">Sample</span> : null}
                  </div>
                </div>
              </button>
            </li>
          ))}
        </ul>
        <div className={cn("lg:sticky lg:top-6 lg:h-[calc(100dvh-230px)]", !selected && "hidden lg:block")}>
          {selected ? <ReviewDetail key={selected.id} review={selected} onBack={() => select(null)} onNext={() => move(1)} />
            : <div className="hidden h-full items-center justify-center rounded-[20px] border-2 border-dashed border-ink/15 text-ink-soft lg:flex">Pick a review to read it and reply.</div>}
        </div>
      </div>
    </div>
  );
}
