import { useQuery } from "@tanstack/react-query";
import { Phone, Star } from "lucide-react";
import { Link } from "react-router-dom";
import { NoMapYet, OpenInMaps } from "@/components/review/MapLinks";
import { buttonVariants } from "@/components/ui/button";
import { Chip, Skeleton } from "@/components/ui/misc";
import { cn } from "@/lib/utils";
import { appApi } from "@/services/api";

function whereIs(place?: string | null, city?: string | null, pin?: string | null): string {
  const parts = [place, city && !(place ?? "").toLowerCase().includes(city.toLowerCase()) ? city : null, pin].filter(Boolean);
  return parts.join(", ") || "No address yet";
}

/** Every branch with its place on Google Maps: a map when Virundhu has a Maps key, otherwise a one-tap link. */
export default function Branches() {
  const { data: outlets, isLoading } = useQuery({ queryKey: ["outlets"], queryFn: appApi.outlets });
  const list = outlets ?? [];
  const linked = list.filter((o) => o.on_google_maps).length;
  return (
    <div className="mx-auto max-w-[1280px]">
      <h1 className="text-[2.3rem] font-bold">Branches on the map</h1>
      <p className="mt-1 max-w-2xl text-ink-soft">
        Each branch with its Google Maps place, rating and phone. Tap a branch to open it in Google Maps for directions,
        photos and its live reviews.
      </p>
      <div className="mt-4 flex flex-wrap items-center gap-3">
        <Chip tone={linked === list.length && list.length ? "leaf" : "turmeric"}>{linked} of {list.length} linked to their Google listing</Chip>
        {linked < list.length ? (
          <Link to="/app/connections" className="text-sm font-semibold text-night underline-offset-4 hover:underline">Link the rest on Connections</Link>
        ) : null}
        <Link to="/app/settings" className={cn(buttonVariants({ variant: "outline", size: "sm" }), "ml-auto")}>Edit addresses</Link>
      </div>
      <ul className="mt-6 grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        {isLoading ? Array.from({ length: 3 }, (_, i) => <li key={i}><Skeleton className="h-[260px]" /></li>) : null}
        {list.map((o) => (
          <li key={o.id} className="flex flex-col overflow-hidden rounded-[20px] border-2 border-line bg-white">
            {o.map_embed_url ? (
              <iframe title={`${o.name} on Google Maps`} src={o.map_embed_url} loading="lazy" referrerPolicy="no-referrer-when-downgrade"
                className="h-44 w-full border-0" allowFullScreen />
            ) : null}
            <div className="flex flex-1 flex-col gap-2 p-4">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <p className="font-display text-xl font-bold leading-tight">{o.name}</p>
                  <p className="text-sm text-ink-soft">{whereIs(o.address || o.area, o.city, o.pincode)}</p>
                </div>
                {o.google_rating ? (
                  <span className="inline-flex shrink-0 items-center gap-1 rounded-full bg-jasmine px-2.5 py-1 text-sm font-semibold">
                    <Star className="h-4 w-4 fill-turmeric text-turmeric" aria-hidden="true" />{o.google_rating.toFixed(1)}
                    {o.google_rating_count ? <span className="font-normal text-ink-soft">({o.google_rating_count.toLocaleString("en-IN")})</span> : null}
                  </span>
                ) : null}
              </div>
              {o.phone ? <a href={`tel:${o.phone}`} className="inline-flex items-center gap-1.5 text-sm text-ink-soft hover:text-ink"><Phone className="h-4 w-4" aria-hidden="true" />{o.phone}</a> : null}
              <div className="mt-auto pt-2">{o.directions_url ? <OpenInMaps url={o.directions_url} /> : <NoMapYet />}</div>
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}
