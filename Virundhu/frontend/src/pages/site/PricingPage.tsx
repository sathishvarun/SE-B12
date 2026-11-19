import { PRICING_FAQS as QA } from "@/lib/faqs";
import { RiseWords } from "@/components/motion/Reveal";
import { PriceCalculator } from "@/components/site/PriceCalculator";
import { SavingsCalculator } from "@/components/site/SavingsCalculator";
import { ClosingCta } from "@/components/site/SiteLayout";

export default function PricingPage() {
  return (
    <>
      <section className="kolam-dark relative overflow-hidden text-jasmine">
        <div aria-hidden="true" className="pointer-events-none absolute -right-32 -top-40 h-[420px] w-[420px] rounded-full bg-turmeric/15 blur-[110px]" />
        <div className="relative mx-auto max-w-7xl px-5 pb-20 pt-14 sm:px-8 lg:pt-20">
          <h1 className="type-hero max-w-4xl"><RiseWords text="One price per outlet. Bigger chains pay less." /></h1>
          <p className="mt-5 max-w-2xl text-[1.2rem] text-mist">Tell us how many outlets you run and how long you want. The price works itself out. Every restaurant starts with 14 days free.</p>
          <div className="mt-6 inline-flex flex-wrap items-center gap-3 rounded-[16px] border-2 border-dashed border-turmeric/70 px-4 py-3">
            <span className="rounded-[10px] bg-turmeric px-3 py-1 font-mono text-lg font-bold tracking-wider text-night">FIRST10</span>
            <span>First 10 restaurants get 20% off.</span>
          </div>
          <div className="mt-12"><PriceCalculator tone="dark" /></div>
        </div>
      </section>

      <section className="mx-auto max-w-7xl px-5 py-20 sm:px-8 lg:py-24">
        <h2 className="type-section">Is it worth it for you?</h2>
        <div className="mt-8"><SavingsCalculator /></div>
      </section>

      <section className="mx-auto max-w-4xl px-5 pb-20 sm:px-8 lg:pb-24">
        <h2 className="type-section">Billing questions</h2>
        <dl className="mt-8 divide-y-2 divide-line border-y-2 border-line">
          {QA.map(([q, a]) => (
            <div key={q} className="py-5"><dt className="font-display text-[1.2rem] font-semibold">{q}</dt><dd className="mt-1 text-ink-soft">{a}</dd></div>
          ))}
        </dl>
      </section>

      <ClosingCta />
    </>
  );
}
