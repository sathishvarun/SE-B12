import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Copy, Star, Trash2 } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Chip, Skeleton } from "@/components/ui/misc";
import { cn } from "@/lib/utils";
import { demoPrepApi, errorMessage, type DemoPrepRow } from "@/services/api";

const EMPTY = [{ text: "", rating: "" }, { text: "", rating: "" }, { text: "", rating: "" }];

/**
 * Admin → Demo prep. Open every demo with the owner's own latest reviews already answered: paste their Google Maps
 * link (or up to three reviews from Zomato/Swiggy) and Virundhu drafts the replies in under a minute.
 */
export function DemoPrepPanel() {
  const qc = useQueryClient();
  const { data, isLoading } = useQuery({
    queryKey: ["demo-preps"], queryFn: demoPrepApi.list,
    refetchInterval: (q) => (q.state.data?.some((p) => p.status === "queued") ? 2500 : 30_000),
  });
  const [restaurant, setRestaurant] = useState("");
  const [link, setLink] = useState("");
  const [tone, setTone] = useState("warm");
  const [paste, setPaste] = useState(false);
  const [reviews, setReviews] = useState(EMPTY);
  const create = useMutation({
    mutationFn: () => demoPrepApi.create({
      restaurant: restaurant.trim(), maps_link: paste ? "" : link.trim(), tone,
      reviews: paste ? reviews.filter((r) => r.text.trim().length >= 3).map((r) => ({ text: r.text.trim(), rating: r.rating ? Number(r.rating) : null })) : [],
    }),
    onSuccess: () => { toast.success("Drafting the replies. This takes under a minute."); setLink(""); setReviews(EMPTY); void qc.invalidateQueries({ queryKey: ["demo-preps"] }); },
    onError: (e) => toast.error(errorMessage(e)),
  });
  const remove = useMutation({ mutationFn: demoPrepApi.remove, onSuccess: () => void qc.invalidateQueries({ queryKey: ["demo-preps"] }) });
  const ready = restaurant.trim().length >= 2 && (paste ? reviews.some((r) => r.text.trim().length >= 3) : true);

  return (
    <div className="space-y-6">
      <p className="max-w-3xl text-ink-soft">
        Open the call with their own guests already answered: owners see the value before you explain anything. Paste the
        restaurant's Google Maps link and Virundhu drafts replies to its three newest reviews. When the restaurant fills
        the contact form with its Maps link, this happens by itself.
      </p>
      <form className="rounded-[20px] border-2 border-line bg-white p-5" onSubmit={(e) => { e.preventDefault(); if (ready) create.mutate(); }}>
        <div className="grid gap-3 md:grid-cols-[1fr_1.4fr_auto]">
          <label className="text-sm font-semibold">Restaurant
            <input value={restaurant} onChange={(e) => setRestaurant(e.target.value)} placeholder="Annapoorna, RS Puram" maxLength={160}
              className="mt-1 h-11 w-full rounded-[12px] border-2 border-line px-3 font-normal focus:border-night focus:outline-none" />
          </label>
          {!paste ? (
            <label className="text-sm font-semibold">Google Maps link <span className="font-normal text-ink-soft">(optional: else we search by name)</span>
              <input value={link} onChange={(e) => setLink(e.target.value)} placeholder="https://maps.app.goo.gl/…" maxLength={500}
                className="mt-1 h-11 w-full rounded-[12px] border-2 border-line px-3 font-normal focus:border-night focus:outline-none" />
            </label>
          ) : <div />}
          <label className="text-sm font-semibold">Tone
            <select value={tone} onChange={(e) => setTone(e.target.value)} className="mt-1 h-11 w-full cursor-pointer rounded-[12px] border-2 border-line bg-white px-3 font-normal">
              <option value="warm">Warm</option><option value="friendly">Friendly</option><option value="formal">Formal</option>
            </select>
          </label>
        </div>
        <button type="button" onClick={() => setPaste(!paste)} className="mt-3 block cursor-pointer text-sm font-semibold text-night underline-offset-4 hover:underline">
          {paste ? "Use the Google Maps link instead" : "No Maps link, or a Zomato/Swiggy restaurant? Paste up to 3 reviews"}
        </button>
        {paste ? (
          <div className="mt-3 grid gap-3">
            {reviews.map((r, i) => (
              <div key={i} className="grid gap-2 sm:grid-cols-[1fr_100px]">
                <textarea value={r.text} rows={2} maxLength={2000} placeholder={`Review ${i + 1}`}
                  onChange={(e) => setReviews(reviews.map((x, j) => (j === i ? { ...x, text: e.target.value } : x)))}
                  className="rounded-[12px] border-2 border-line px-3 py-2 focus:border-night focus:outline-none" />
                <select aria-label={`Stars for review ${i + 1}`} value={r.rating} onChange={(e) => setReviews(reviews.map((x, j) => (j === i ? { ...x, rating: e.target.value } : x)))}
                  className="h-11 cursor-pointer rounded-[12px] border-2 border-line bg-white px-2">
                  <option value="">Stars</option>{[5, 4, 3, 2, 1].map((n) => <option key={n} value={n}>{n}★</option>)}
                </select>
              </div>
            ))}
          </div>
        ) : null}
        <Button type="submit" className="mt-4" disabled={!ready || create.isPending}>Draft the replies</Button>
      </form>

      {isLoading ? <Skeleton className="h-[200px]" /> : (data ?? []).map((p) => <PrepCard key={p.id} p={p} onDelete={() => remove.mutate(p.id)} />)}
      {data && data.length === 0 ? <p className="text-ink-soft">No demo preps yet.</p> : null}
    </div>
  );
}

function PrepCard({ p, onDelete }: { p: DemoPrepRow; onDelete: () => void }) {
  return (
    <article className="rounded-[20px] border-2 border-line bg-white p-5">
      <header className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h3 className="font-display text-xl font-bold">{p.place_name ?? p.restaurant}</h3>
          <p className="text-sm text-ink-soft">
            {p.rating ? <span className="mr-2 inline-flex items-center gap-1 font-semibold text-ink"><Star className="h-4 w-4 fill-turmeric text-turmeric" aria-hidden="true" />{p.rating.toFixed(1)}{p.rating_count ? ` (${p.rating_count.toLocaleString("en-IN")})` : ""}</span> : null}
            {p.lead_id ? "From the contact form" : "Prepared by you"}, {new Date(p.created_at).toLocaleString("en-IN", { dateStyle: "medium", timeStyle: "short" })}
          </p>
        </div>
        <div className="flex items-center gap-2">
          {p.status === "queued" ? <Chip tone="turmeric">Drafting…</Chip> : p.status === "failed" ? <Chip tone="chilli">Couldn't prepare</Chip> : <Chip tone="leaf">Ready for the call</Chip>}
          <button type="button" onClick={onDelete} aria-label="Delete this prep" className="cursor-pointer rounded-full p-2 text-ink-soft hover:bg-jasmine"><Trash2 className="h-4 w-4" /></button>
        </div>
      </header>
      {p.error ? <p className="mt-3 rounded-[12px] bg-chilli-soft px-3 py-2 text-sm text-[#b32f12]">{p.error}</p> : null}
      {p.status === "ready" ? (
        <ol className="mt-4 grid gap-3 lg:grid-cols-3">
          {p.reviews.map((r, i) => (
            <li key={i} className="flex flex-col rounded-[16px] bg-jasmine p-4">
              <p className="text-xs font-semibold text-ink-soft">{r.author ?? "A guest"}{r.rating ? `, ${r.rating}★` : ""}{r.when ? `, ${r.when}` : ""}</p>
              <p className="mt-1 text-sm">"{r.text}"</p>
              <p className="mt-3 text-xs font-semibold text-[#16784a]">Reply ready</p>
              <p className={cn("mt-1 flex-1 whitespace-pre-line rounded-[12px] bg-white p-3 text-sm")}>{r.reply}</p>
              <button type="button" onClick={() => { void navigator.clipboard.writeText(r.reply ?? ""); toast.success("Reply copied"); }}
                className="mt-2 inline-flex cursor-pointer items-center gap-1.5 self-start text-sm font-semibold text-night hover:underline"><Copy className="h-4 w-4" /> Copy</button>
            </li>
          ))}
        </ol>
      ) : null}
    </article>
  );
}
