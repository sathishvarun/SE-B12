import { useQuery } from "@tanstack/react-query";
import { useParams } from "react-router-dom";
import { api } from "@/services/api";

interface WidgetData { restaurant: string; average: number | null; count: number; shown: string; reviews: { rating: number; text: string; date: string; platform: string }[]; branches: { name: string; area: string | null; directions_url: string | null }[] }

/** The review widget a restaurant embeds on its own website (iframe). Average is from every review; it says what it shows. */
export default function Widget() {
  const { token } = useParams();
  const { data } = useQuery({ queryKey: ["widget", token], queryFn: () => api.get<WidgetData>(`/api/v1/public/widget/${token}`).then((r) => r.data) });
  if (!data) return null;
  return (
    <main className="min-h-dvh bg-jasmine p-4 font-sans text-ink">
      <header className="flex flex-wrap items-baseline justify-between gap-2">
        <h1 className="font-display text-xl font-bold">What guests say about {data.restaurant}</h1>
        {data.average ? <p className="font-semibold"><span className="text-turmeric-deep">★</span> {data.average} from {data.count} reviews (last 12 months)</p> : null}
      </header>
      <ul className="mt-3 grid gap-3 sm:grid-cols-2">
        {data.reviews.map((r, i) => (
          <li key={i} className="rounded-[14px] bg-white p-3 shadow-sm">
            <p className="text-turmeric-deep" aria-label={`${r.rating} stars`}>{"★".repeat(r.rating)}</p>
            <p className="mt-1 text-[0.95rem]">“{r.text}”</p>
            <p className="mt-1 text-xs capitalize text-ink-soft">{r.platform}, {new Date(r.date).toLocaleDateString("en-IN", { month: "short", year: "numeric" })}</p>
          </li>
        ))}
      </ul>
      {data.branches.length ? (
        <p className="mt-3 text-sm">Find us: {data.branches.map((b, i) => <span key={b.name}>{i ? " · " : ""}<a className="font-semibold underline" href={b.directions_url ?? "#"} target="_blank" rel="noreferrer">{b.name}</a></span>)}</p>
      ) : null}
      <p className="mt-3 text-xs text-ink-soft">{data.shown}. The average includes every review. Powered by <a className="underline" href="/" target="_blank" rel="noreferrer">Virundhu</a>.</p>
    </main>
  );
}
