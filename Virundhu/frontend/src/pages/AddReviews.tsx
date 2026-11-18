import { useQuery, useQueryClient } from "@tanstack/react-query";
import { CheckCircle2, Download, FileUp, ImageUp, Upload } from "lucide-react";
import { useEffect, useRef, useState, type DragEvent, type FormEvent } from "react";
import { Link } from "react-router-dom";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Spinner } from "@/components/ui/misc";
import { platformLabel } from "@/lib/copy";
import { cn } from "@/lib/utils";
import { API_URL, appApi, errorMessage, tokens, viewAs } from "@/services/api";
import type { ImportBatch, Platform } from "@/types";

function Progress({ batch }: { batch: ImportBatch }) {
  const pct = batch.valid_rows ? Math.round((batch.analyzed_rows / batch.valid_rows) * 100) : 100;
  const done = batch.status === "completed";
  return (
    <div className="rounded-[18px] bg-night p-5 text-jasmine">
      <div className="flex items-center justify-between gap-3">
        <p className="font-display text-xl font-bold">{done ? "All done" : `Reading review ${batch.analyzed_rows + 1} of ${batch.valid_rows}`}</p>
        {done ? <CheckCircle2 className="h-6 w-6 text-leaf" /> : <Spinner className="h-5 w-5 text-turmeric" />}
      </div>
      <div className="mt-3 h-3 overflow-hidden rounded-full bg-white/10"><div className="h-full rounded-full bg-turmeric transition-[width] duration-500" style={{ width: `${pct}%` }} /></div>
      <ul className="mt-4 grid grid-cols-2 gap-3 text-sm sm:grid-cols-4">
        <li><span className="tabular block font-display text-2xl font-bold">{batch.valid_rows}</span>new reviews</li>
        <li><span className="tabular block font-display text-2xl font-bold">{batch.analyzed_rows}</span>read by AI</li>
        <li><span className="tabular block font-display text-2xl font-bold">{batch.duplicate_rows}</span>already in Virundhu</li>
        <li><span className="tabular block font-display text-2xl font-bold text-[#ffb3a3]">{batch.invalid_rows}</span>rows skipped</li>
      </ul>
      {batch.errors?.length ? (
        <details className="mt-4 rounded-[12px] bg-white/[0.06] p-3 text-sm">
          <summary className="cursor-pointer font-semibold">Why {batch.invalid_rows} rows were skipped</summary>
          <ul className="mt-2 space-y-1 text-mist">{batch.errors.slice(0, 20).map((e) => <li key={e.row}>Row {e.row}: {e.reason}</li>)}</ul>
        </details>
      ) : null}
      {done ? <Link to="/app/inbox?view=today" className="mt-4 inline-block font-semibold text-turmeric underline underline-offset-4">Open the inbox</Link> : null}
    </div>
  );
}

function UploadBox() {
  const qc = useQueryClient();
  const input = useRef<HTMLInputElement>(null);
  const [drag, setDrag] = useState(false);
  const [busy, setBusy] = useState(false);
  const [batchId, setBatchId] = useState<number | null>(null);
  const { data: batch } = useQuery({
    queryKey: ["batch", batchId], queryFn: () => appApi.batch(batchId as number), enabled: batchId !== null,
    refetchInterval: (q) => (q.state.data?.status === "completed" ? false : 1500),
  });
  useEffect(() => {
    if (batch?.status === "completed") {
      void qc.invalidateQueries({ queryKey: ["overview"] });
      void qc.invalidateQueries({ queryKey: ["reviews"] });
      void qc.invalidateQueries({ queryKey: ["notifications"] });
    }
  }, [batch?.status, qc]);

  async function send(file: File | undefined) {
    if (!file) return;
    if (!/\.(csv|xlsx|xls)$/i.test(file.name)) { toast.error("Please choose a .csv or .xlsx file."); return; }
    setBusy(true);
    try {
      const b = await appApi.upload(file);
      setBatchId(b.id);
      toast.success(`${b.valid_rows} new reviews added. Reading them now.`);
    } catch (err) { toast.error(errorMessage(err)); } finally { setBusy(false); }
  }

  function onDrop(e: DragEvent) { e.preventDefault(); setDrag(false); void send(e.dataTransfer.files[0]); }

  async function downloadTemplate() {
    const res = await fetch(`${API_URL}/api/v1/imports/template.csv`, { headers: { Authorization: `Bearer ${tokens.access() ?? ""}`, ...(viewAs.get() ? { "X-Org-Id": String(viewAs.get()?.id) } : {}) } });
    const url = URL.createObjectURL(await res.blob());
    const a = document.createElement("a"); a.href = url; a.download = "virundhu-reviews-template.csv"; a.click(); URL.revokeObjectURL(url);
  }

  return (
    <div className="space-y-4">
      <div onDragOver={(e) => { e.preventDefault(); setDrag(true); }} onDragLeave={() => setDrag(false)} onDrop={onDrop}
        className={cn("flex flex-col items-center justify-center rounded-[22px] border-[3px] border-dashed bg-white px-6 py-12 text-center transition-colors",
          drag ? "border-turmeric bg-turmeric/10" : "border-ink/15")}>
        <span className="flex h-16 w-16 items-center justify-center rounded-[18px] bg-night text-turmeric"><FileUp className="h-8 w-8" /></span>
        <p className="mt-4 font-display text-2xl font-bold">Drop your reviews file here</p>
        <p className="mt-1 max-w-md text-ink-soft">CSV or Excel, up to 5,000 reviews. Needs <b>rating</b> and <b>review_text</b> columns; date, platform, outlet and review_id are optional.</p>
        <div className="mt-5 flex flex-wrap justify-center gap-3">
          <Button onClick={() => input.current?.click()} disabled={busy}>{busy ? <><Spinner /> Uploading...</> : <><Upload className="h-4 w-4" /> Choose a file</>}</Button>
          <Button variant="outline" onClick={downloadTemplate}><Download className="h-4 w-4" /> Download template</Button>
        </div>
        <input ref={input} type="file" aria-label="Screenshots" accept=".csv,.xlsx,.xls" className="hidden" onChange={(e) => { void send(e.target.files?.[0]); e.target.value = ""; }} />
      </div>
      {batch ? <Progress batch={batch} /> : null}
    </div>
  );
}

function PasteBox() {
  const qc = useQueryClient();
  const [text, setText] = useState("");
  const [rating, setRating] = useState(1);
  const [platform, setPlatform] = useState<Platform>("zomato");
  const [busy, setBusy] = useState(false);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    if (text.trim().length < 2) { toast.error("Paste the review text first."); return; }
    setBusy(true);
    try {
      await appApi.addReview({ text, rating, platform });
      toast.success("Review added. It will appear in the inbox in a few seconds.");
      setText("");
      setTimeout(() => { void qc.invalidateQueries({ queryKey: ["reviews"] }); void qc.invalidateQueries({ queryKey: ["notifications"] }); }, 4000);
    } catch (err) { toast.error(errorMessage(err)); } finally { setBusy(false); }
  }

  return (
    <form onSubmit={onSubmit} className="rounded-[22px] border-2 border-line bg-white p-5 sm:p-6">
      <h2 className="font-display text-xl font-bold">Paste one review</h2>
      <p className="text-sm text-ink-soft">Copy a review from the Zomato or Swiggy partner app and paste it here.</p>
      <div className="mt-4 flex flex-wrap gap-2">
        {(["zomato", "swiggy", "google", "tripadvisor", "instagram", "facebook", "other"] as Platform[]).map((p) => (
          <button key={p} type="button" onClick={() => setPlatform(p)}
            className={cn("rounded-full px-3.5 py-1.5 text-sm font-semibold cursor-pointer", platform === p ? "bg-night text-jasmine" : "bg-jasmine-2 text-ink-soft hover:text-ink")}>{platformLabel[p]}</button>
        ))}
      </div>
      <div className="mt-3 flex items-center gap-1" role="radiogroup" aria-label="Star rating">
        {[1, 2, 3, 4, 5].map((n) => (
          <button key={n} type="button" role="radio" aria-checked={rating === n} onClick={() => setRating(n)}
            className={cn("h-9 w-9 rounded-full text-sm font-bold cursor-pointer", n <= rating ? "bg-turmeric text-night" : "bg-jasmine-2 text-ink-soft")}>{n}★</button>
        ))}
      </div>
      <textarea value={text} onChange={(e) => setText(e.target.value)} rows={4} maxLength={5000} placeholder="e.g. Delivery romba late, food ellam cold"
        className="mt-3 w-full rounded-[14px] border-2 border-line p-3.5 font-display text-[1.05rem] focus:border-night focus:outline-none" />
      <Button type="submit" className="mt-3" disabled={busy}>{busy ? <><Spinner /> Adding...</> : "Add and read this review"}</Button>
    </form>
  );
}

function ScreenshotBox() {
  const qc = useQueryClient();
  const input = useRef<HTMLInputElement>(null);
  const [platform, setPlatform] = useState<Platform>("zomato");
  const [busy, setBusy] = useState(false);
  const [last, setLast] = useState<{ added: number; duplicates: number } | null>(null);
  const { data: outlets } = useQuery({ queryKey: ["outlets"], queryFn: appApi.outlets });
  const [outlet, setOutlet] = useState<number | "">("");

  async function send(files: FileList | null) {
    if (!files?.length) return;
    setBusy(true);
    let added = 0, duplicates = 0;
    try {
      for (const f of Array.from(files).slice(0, 10)) {
        const r = await appApi.screenshot(f, platform, outlet || undefined);
        added += r.added; duplicates += r.duplicates;
      }
      setLast({ added, duplicates });
      toast.success(added ? `${added} review${added === 1 ? "" : "s"} added from the screenshot` : "No new reviews in that screenshot");
      void qc.invalidateQueries({ queryKey: ["reviews"] });
      void qc.invalidateQueries({ queryKey: ["overview"] });
    } catch (err) { toast.error(errorMessage(err)); } finally { setBusy(false); if (input.current) input.current.value = ""; }
  }

  return (
    <section className="rounded-[20px] border-2 border-line bg-white p-5 sm:p-6">
      <div className="flex items-start gap-3">
        <span className="grid h-11 w-11 shrink-0 place-items-center rounded-[14px] bg-night text-turmeric"><ImageUp className="h-5 w-5" /></span>
        <div>
          <h2 className="font-display text-xl font-bold">From a screenshot</h2>
          <p className="text-ink-soft">The quickest way for Zomato and Swiggy. Open reviews in the partner app, take a screenshot, and upload it. The AI picks out every review on it.</p>
        </div>
      </div>
      <div className="mt-4 flex flex-wrap items-center gap-2">
        {(["zomato", "swiggy", "google", "tripadvisor", "instagram", "facebook", "other"] as Platform[]).map((p) => (
          <button key={p} type="button" onClick={() => setPlatform(p)}
            className={cn("rounded-full px-4 py-2 text-sm font-semibold cursor-pointer", platform === p ? "bg-night text-jasmine" : "bg-jasmine-2 text-ink-soft")}>{platformLabel[p]}</button>
        ))}
      </div>
      <input ref={input} type="file" accept="image/png,image/jpeg,image/webp" multiple className="sr-only" id="shot" onChange={(e) => void send(e.target.files)} />
      <Button className="mt-4" onClick={() => input.current?.click()} disabled={busy}>
        {busy ? <><Spinner /> Reading the screenshot...</> : <><ImageUp className="h-4 w-4" /> Choose screenshots (up to 10)</>}
      </Button>
      {last ? <p className="mt-3 text-sm text-ink-soft">Last upload: {last.added} added{last.duplicates ? `, ${last.duplicates} already in Virundhu` : ""}.</p> : null}
      {(outlets?.length ?? 0) > 1 ? (
        <label className="mt-4 block max-w-sm text-sm font-semibold">Which outlet are these reviews for?
          <select value={outlet} onChange={(e) => setOutlet(e.target.value ? Number(e.target.value) : "")}
            className="mt-1.5 h-11 w-full rounded-[12px] border-2 border-line bg-white px-3 font-normal">
            <option value="">Main outlet</option>
            {outlets?.map((o) => <option key={o.id} value={o.id}>{o.name}</option>)}
          </select>
        </label>
      ) : null}
    </section>
  );
}

export default function AddReviews() {
  const { data: batches } = useQuery({ queryKey: ["batches"], queryFn: appApi.batches });
  return (
    <div className="mx-auto max-w-5xl">
      <h1 className="text-[2.3rem] font-bold">Add reviews</h1>
      <p className="mt-1 max-w-2xl text-ink-soft">Every review you add is read by the AI within seconds. Serious ones raise an alert straight away.
        For automatic reviews, see <Link to="/app/connections" className="font-semibold underline decoration-turmeric decoration-2 underline-offset-4">Connections</Link>.</p>
      <div className="mt-6 grid grid-cols-1 gap-5 lg:grid-cols-[1.3fr_1fr]">
        <UploadBox />
        <PasteBox />
      </div>
      <div className="mt-5"><ScreenshotBox /></div>
      {batches?.length ? (
        <div className="mt-8 rounded-[20px] border-2 border-line bg-white p-5">
          <h2 className="font-display text-xl font-bold">Recent uploads</h2>
          <table className="mt-3 w-full text-left text-sm">
            <thead className="text-ink-soft"><tr><th className="py-2">File</th><th>New</th><th>Read</th><th>Duplicates</th><th>Skipped</th><th>Status</th></tr></thead>
            <tbody>{batches.map((b) => (
              <tr key={b.id} className="border-t-2 border-jasmine-2"><td className="max-w-[220px] truncate py-2 font-semibold">{b.filename}</td><td className="tabular">{b.valid_rows}</td><td className="tabular">{b.analyzed_rows}</td><td className="tabular">{b.duplicate_rows}</td><td className="tabular">{b.invalid_rows}</td><td>{b.status === "completed" ? "Done" : "Reading..."}</td></tr>
            ))}</tbody>
          </table>
        </div>
      ) : null}
    </div>
  );
}
