import { ArrowRight, PlayCircle } from "lucide-react";
import { FeastLeaf } from "@/components/landing/FeastLeaf";
import { Reveal, RiseWords } from "@/components/motion/Reveal";
import { cn } from "@/lib/utils";
import { useCountUp } from "@/lib/useCountUp";
import { Link } from "react-router-dom";
import { LiveBoard } from "@/components/landing/LiveBoard";
import { TryIt } from "@/components/landing/TryIt";
import { AutomationCards } from "@/components/site/AutomationCards";
import { ClosingCta } from "@/components/site/SiteLayout";
import { Testimonials } from "@/components/site/Testimonials";
import { buttonVariants } from "@/components/ui/button";

function Stat({ value, prefix, suffix, label }: { value: number; prefix: string; suffix: string; label: string }) {
  const n = useCountUp(value, 1400);
  return (
    <Reveal>
      <dt className="sr-only">{label}</dt>
      <dd className="font-display text-[2.6rem] font-extrabold leading-none text-turmeric tabular">{prefix}{Math.round(n)}{suffix}</dd>
      <p className="mt-2 text-sm text-mist">{label}</p>
    </Reveal>
  );
}

export default function Home() {
  return (
    <>
      {/* Hero: the headline rises in word by word while a kolam draws itself behind the live board */}
      <section className="kolam-dark relative overflow-hidden text-jasmine">
        <div aria-hidden="true" className="pointer-events-none absolute -right-40 -top-40 h-[520px] w-[520px] rounded-full bg-turmeric/20 blur-[120px]" />
        <div aria-hidden="true" className="pointer-events-none absolute -bottom-48 -left-32 h-[420px] w-[420px] rounded-full bg-lotus/15 blur-[120px]" />
        <div className="relative mx-auto grid max-w-7xl items-center gap-12 px-5 pb-16 pt-12 sm:px-8 lg:grid-cols-[1fr_minmax(0,560px)] lg:gap-14 lg:pb-24 lg:pt-16">
          <div>
            <p className="type-label text-turmeric animate-rise">For restaurants and cloud kitchens in Tamil Nadu</p>
            <h1 className="type-hero mt-4">
              <RiseWords text="Every guest, heard." delay={0.1} />
              <br />
              <RiseWords text="Every complaint, caught." delay={0.4} className="text-turmeric" />
            </h1>
            <p className="type-lead mt-6 max-w-xl text-mist animate-rise [animation-delay:700ms]">
              Google and QR-code reviews come in by themselves; Zomato and Swiggy with one paste or a screenshot. Virundhu reads them in Tamil, Tanglish and English, alerts you the minute something is serious, and writes the reply.
            </p>
            <div className="mt-9 flex flex-wrap gap-3 animate-rise [animation-delay:900ms]">
              <Link to="/register" className={cn(buttonVariants({ size: "lg" }), "h-auto min-h-12 max-w-full whitespace-normal py-3 text-center")}>Start 14-day free trial</Link>
              <Link to="/how-it-works#demo" className={cn(buttonVariants({ variant: "outlineDark", size: "lg" }), "h-auto min-h-12 max-w-full whitespace-normal py-3 text-center")}><PlayCircle className="h-5 w-5" /> See how it works</Link>
            </div>
            <p className="mt-5 text-sm text-mist animate-rise [animation-delay:1000ms]">No card needed. Set up in 10 minutes.</p>
          </div>
          <div className="relative mx-auto w-full max-w-[560px] animate-rise [animation-delay:300ms]">
            <FeastLeaf className="hidden px-6 py-10 sm:block" />
            <FeastLeaf compact className="px-2 py-8 sm:hidden" />
          </div>
        </div>
        {/* Numbers band */}
        <div className="relative border-t border-white/10">
          <dl className="mx-auto grid max-w-7xl grid-cols-2 gap-6 px-5 py-8 sm:px-8 md:grid-cols-4">
            {[
              [1, " min", "from a food-safety complaint to your phone"],
              [3, "", "languages read: Tamil, Tanglish, English"],
              [24, "×7", "every review read, day and night"],
              [649, "", "₹ per outlet a month for big chains", "₹"],
            ].map(([n, suffix, label, prefix]) => (
              <Stat key={String(label)} value={Number(n)} prefix={String(prefix ?? "")} suffix={String(suffix)} label={String(label)} />
            ))}
          </dl>
        </div>
      </section>

      {/* Three steps, short. The full story lives on How it works. */}
      <section className="mx-auto max-w-7xl px-5 py-14 sm:px-8 lg:py-20">
        <Reveal><h2 className="type-section max-w-3xl">How it works, in three steps</h2></Reveal>
        <ol className="mt-8 grid gap-4 md:grid-cols-3">
          {[
            ["Reviews come in", "Google and your QR code by themselves. Zomato and Swiggy with one paste or a screenshot."],
            ["Virundhu reads every one", "In Tamil, Tanglish or English. Food-safety complaints alert you and that branch's manager in a minute."],
            ["Replies go out", "Happy guests are thanked by themselves. For complaints, the reply is ready for you to check."],
          ].map(([title, body], i) => (
            <Reveal key={title} delay={i * 0.12}><li className="lift flex h-full gap-4 rounded-[20px] border-2 border-line bg-white p-5">
              <span className="grid h-10 w-10 shrink-0 place-items-center rounded-full bg-night font-display text-lg font-bold text-jasmine">{i + 1}</span>
              <div><h3 className="text-xl">{title}</h3><p className="mt-1 text-ink-soft">{body}</p></div>
            </li></Reveal>
          ))}
        </ol>
        <Link to="/how-it-works" className="mt-6 inline-flex items-center gap-1.5 font-semibold text-night hover:underline">Follow one review from start to finish <ArrowRight className="h-4 w-4" /></Link>
      </section>

      {/* The product, live: reviews landing and being sorted */}
      <section className="kolam-dark text-jasmine">
        <div className="mx-auto grid max-w-7xl items-center gap-10 px-5 py-14 sm:px-8 lg:grid-cols-[1fr_minmax(0,560px)] lg:py-20">
          <div>
            <h2 className="type-section">Every plate, every comment, sorted as it lands</h2>
            <p className="type-lead mt-4 max-w-xl text-mist">Praise goes to the thank-you pile. A salty sambar goes to the kitchen. A food-safety complaint goes straight to your phone.</p>
          </div>
          <LiveBoard />
        </div>
      </section>

      {/* Automation */}
      <section className="mx-auto max-w-7xl px-5 py-14 sm:px-8 lg:py-24">
        <div className="flex flex-wrap items-end justify-between gap-4">
          <div>
            <h2 className="type-section max-w-3xl">Runs by itself. You step in only when it matters.</h2>
            <p className="mt-3 hidden max-w-2xl text-lg text-ink-soft sm:block">The routine work is automatic, so your team spends its time on the guests who need a person.</p>
          </div>
          <Link to="/how-it-works" className="flex items-center gap-1.5 font-semibold text-night hover:underline">What's automatic, exactly <ArrowRight className="h-4 w-4" /></Link>
        </div>
        <div className="mt-8"><AutomationCards phoneLimit={2} /></div>
      </section>

      {/* Live AI demo */}
      <section id="try" className="kolam-light border-y-2 border-line bg-jasmine-2/60 scroll-mt-16">
        <div className="mx-auto max-w-7xl px-5 py-14 sm:px-8 lg:py-24">
          <h2 className="type-section max-w-3xl">Try it on a real review, right now</h2>
          <p className="mt-3 max-w-2xl text-lg text-ink-soft">This is the real AI, not a recording. Paste something a guest actually wrote, in any language.</p>
          <div className="mt-10"><TryIt /></div>
        </div>
      </section>

      <section className="mx-auto max-w-7xl px-5 py-12 sm:px-8">
        <p className="text-lg text-ink-soft">₹1,499 per outlet a month, down to ₹649 for big chains. 14 days free. <Link to="/pricing" className="font-semibold text-night underline decoration-turmeric decoration-2 underline-offset-4">Work out your price</Link></p>
      </section>

      <Testimonials />

      <ClosingCta />
    </>
  );
}
