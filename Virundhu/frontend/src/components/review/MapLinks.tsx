import { MapPin, Navigation } from "lucide-react";
import { cn } from "@/lib/utils";

export function OpenInMaps({ url, className, label = "Open in Google Maps" }: { url: string | null | undefined; className?: string; label?: string }) {
  if (!url) return null;
  return (
    <a href={url} target="_blank" rel="noopener noreferrer"
      className={cn("inline-flex items-center gap-1.5 rounded-full bg-[#e8f1ff] px-3 py-1.5 text-sm font-semibold text-[#1a56b8] hover:bg-[#d6e6ff]", className)}>
      <Navigation className="h-4 w-4" aria-hidden="true" /> {label}
    </a>
  );
}

export function NoMapYet({ className }: { className?: string }) {
  return (
    <span className={cn("inline-flex items-center gap-1.5 text-sm text-ink-soft", className)}>
      <MapPin className="h-4 w-4" aria-hidden="true" /> Add the address or city to get a map link
    </span>
  );
}
