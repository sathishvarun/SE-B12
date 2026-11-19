import { HOW_FAQS as faqs } from "@/lib/faqs";
import { Plus } from "lucide-react";

export function Faq() {
  return (
    <div className="divide-y-2 divide-line border-y-2 border-line">
      {faqs.map(([q, a]) => (
        <details key={q} className="group py-1">
          <summary className="flex cursor-pointer list-none items-center justify-between gap-4 py-4 font-display text-[1.2rem] font-semibold [&::-webkit-details-marker]:hidden">
            {q}
            <Plus className="h-5 w-5 shrink-0 transition-transform group-open:rotate-45" />
          </summary>
          <p className="max-w-3xl pb-5 text-ink-soft">{a}</p>
        </details>
      ))}
    </div>
  );
}
