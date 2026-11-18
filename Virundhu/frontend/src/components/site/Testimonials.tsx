import { useQuery } from "@tanstack/react-query";
import { Quote } from "lucide-react";
import { Reveal } from "@/components/motion/Reveal";
import { publicApi } from "@/services/api";

/** Real owners' words, added by the admin with permission. Shows nothing until at least one is published. */
export function Testimonials() {
  const { data } = useQuery({ queryKey: ["testimonials"], queryFn: publicApi.testimonials, staleTime: 600_000 });
  if (!data?.length) return null;
  return (
    <section className="mx-auto max-w-7xl px-5 py-14 sm:px-8 lg:py-20">
      <Reveal><h2 className="type-section max-w-3xl">What owners say</h2></Reveal>
      <div className="mt-8 grid gap-5 md:grid-cols-2 lg:grid-cols-3">
        {data.map((t, i) => (
          <Reveal key={t.id} delay={i * 0.08}>
            <figure className="lift flex h-full flex-col rounded-[22px] border-2 border-line bg-white p-6">
              <Quote className="h-8 w-8 text-turmeric" />
              <blockquote className="mt-3 flex-1 text-lg leading-relaxed">{t.quote}</blockquote>
              <figcaption className="mt-5"><b>{t.name}</b>{t.role ? <span className="block text-sm text-ink-soft">{t.role}</span> : null}</figcaption>
            </figure>
          </Reveal>
        ))}
      </div>
    </section>
  );
}
