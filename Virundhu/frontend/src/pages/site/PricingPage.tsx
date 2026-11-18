import { RiseWords } from "@/components/motion/Reveal";
import { PriceCalculator } from "@/components/site/PriceCalculator";
import { SavingsCalculator } from "@/components/site/SavingsCalculator";
import { ClosingCta } from "@/components/site/SiteLayout";

const QA = [
  ["Is there a free trial?", "Yes, 14 days with everything switched on. No card needed to start."],
  ["How is the price worked out?", "By the number of outlets you run and how long you pay for. The more outlets, the lower the price per outlet: a 100-branch chain pays far less per branch than a single shop. Paying for 3, 6, 9 or 12 months gives a discount, and 9 and 12 months add free months on top."],
  ["How do I pay?", "UPI or card through Dodo Payments. You get a GST invoice. One payment for the period you choose; no contract and no automatic renewal."],
  ["Can I add outlets later?", "Yes. Pay again with the new outlet count; your time left carries over and the new period is added on."],
  ["What happens when the trial or plan ends?", "Nothing is deleted. You can still look at everything; adding and replying to reviews pauses until you pay."],
  ["Is there a launch offer?", "Yes. The first 10 restaurants get 20% off with the code FIRST10 on the payment page."],
];

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
