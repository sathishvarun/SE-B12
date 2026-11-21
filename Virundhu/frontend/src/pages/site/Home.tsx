import { ArrowRight, PlayCircle } from "lucide-react";
import { FeastLeaf } from "@/components/landing/FeastLeaf";
import { Reveal, RiseWords } from "@/components/motion/Reveal";
import { cn } from "@/lib/utils";
import { useCountUp } from "@/lib/useCountUp";
import { Link } from "react-router-dom";
import { LiveBoard } from "@/components/landing/LiveBoard";
import { TryIt } from "@/components/landing/TryIt";
import { AfterSignIn } from "@/components/site/AfterSignIn";
import { AutomationCards } from "@/components/site/AutomationCards";
import { ClosingCta } from "@/components/site/SiteLayout";
import { Testimonials } from "@/components/site/Testimonials";
import { buttonVariants } from "@/components/ui/button";

function Stat({ value, prefix, suffix, label }: { value: number; prefix: string; suffix: string; label: string }) {
  const n = useCountUp(value, 1400, true);
  return (
    <Reveal className="flex flex-col">
      <dt className="order-2 mt-2 text-sm text-mist">{label}</dt>
      <dd className="order-1 font-display text-[2.6rem] font-extrabold leading-none text-turmeric tabular">{prefix}{Math.round(n)}{suffix}</dd>
    </Reveal>
  );
}

const OUTCOMES: [string, string][] = [
  ["No bad review left waiting", "Every 1 to 3 star or urgent review starts a clock. Reminders keep coming until it's answered."],
  ["Replies already written", "In the guest's language and your tone. Never promises refunds, never blames your staff. Copy, post, done."],
  ["Food-safety complaints in a minute", "Hygiene, a hair in the food, a guest who fell sick: you and that branch's manager hear at once."],
  ["Every branch, one score", "Which outlet answers in time and which doesn't, and the dish guests keep complaining about."],
];

export default function Home() {
  return (
    <>
      {/* Hero: the headline rises in word by word while a kolam draws itself behind the live board */}
      <section className="kolam-dark relative overflow-hidden text-jasmine">
        <div aria-hidden="true" className="pointer-events-none absolute -right-40 -top-40 h-[520px] w-[520px] rounded-full bg-turmeric/20 blur-[120px]" />
        <div aria-hidden="true" className="pointer-events-none absolute -bottom-48 -left-32 h-[420px] w-[420px] rounded-full bg-lotus/15 blur-[120px]" />
        <div className="relative mx-auto grid max-w-7xl items-center gap-12 px-5 pb-16 pt-12 sm:px-8 lg:grid-cols-[1fr_minmax(0,560px)] lg:gap-14 lg:pb-24 lg:pt-16">
          <div>
            <p className="type-label text-turmeric animate-rise">For restaurants and cloud kitchens in Tamil Nadu: Zomato, Swiggy and Google reviews</p>
            <h1 className="type-hero mt-4">
              <RiseWords text="No bad review sits unanswered" delay={0.1} />
              <br />
              <RiseWords text="for more than an hour." delay={0.2} className="text-turmeric" />
            </h1>
            <p className="type-lead mt-6 max-w-xl text-mist animate-rise [animation-delay:120ms]">
              Every 1 to 3 star review gets a reply ready in seconds, in Tamil, Tanglish or English. If nobody has answered it,
              Virundhu reminds the branch manager at 30 minutes and you at 60, until someone does. Every Monday you see the score.
            </p>
            <div className="mt-9 flex flex-wrap gap-3 animate-rise [animation-delay:160ms]">
              <Link to="/register" className={cn(buttonVariants({ size: "lg" }), "h-auto min-h-12 max-w-full whitespace-normal py-3 text-center")}>Start 14-day free trial</Link>
              <Link to="/how-it-works#demo" className={cn(buttonVariants({ variant: "outlineDark", size: "lg" }), "h-auto min-h-12 max-w-full whitespace-normal py-3 text-center")}><PlayCircle className="h-5 w-5" /> See how it works</Link>
            </div>
            <p className="mt-5 text-sm text-mist animate-rise [animation-delay:200ms]">14 days free, no card needed. Set up in 10 minutes.</p>
          </div>
          <div className="relative mx-auto w-full max-w-[560px] animate-rise [animation-delay:60ms]">
            <FeastLeaf className="hidden px-6 py-10 sm:block" />
            <FeastLeaf compact className="px-2 py-8 sm:hidden" />
          </div>
        </div>
        {/* Numbers band */}
        <div className="relative border-t border-white/10">
          <dl className="mx-auto grid max-w-7xl grid-cols-2 gap-6 px-5 py-8 sm:px-8 md:grid-cols-4">
            {[
              [60, " min", "the longest a bad review should wait"],
              [30, " min", "first reminder to the branch manager"],
              [3, "", "languages for replies: Tamil, Tanglish, English"],
              [649, "", "₹ per outlet a month for big chains", "₹"],
            ].map(([n, suffix, label, prefix]) => (
              <Stat key={String(label)} value={Number(n)} prefix={String(prefix ?? "")} suffix={String(suffix)} label={String(label)} />
            ))}
          </dl>
        </div>
      </section>

      {/* Three steps, short. The full story lives on How it works. */}
      <section className="mx-auto max-w-7xl px-5 py-14 sm:px-8 lg:py-20">
        <Reveal><h2 className="type-section max-w-3xl">How the one-hour promise works</h2></Reveal>
        <ol className="mt-8 grid gap-4 md:grid-cols-3">
          {[
            ["A bad review lands", "Google reviews arrive by themselves. Zomato and Swiggy: paste them or drop a screenshot, and the clock starts."],
            ["The reply is ready in seconds", "A polite reply in the guest's own language, waiting in the inbox with a countdown: 52 min left."],
            ["Nobody forgets it", "No reply at 30 minutes? The branch manager gets a reminder on their phone. At 60, you do. Tap Replied and the clock stops."],
          ].map(([title, body], i) => (
            <li key={title} className="h-full"><Reveal delay={i * 0.12} className="h-full"><div className="lift flex h-full gap-4 rounded-[20px] border-2 border-line bg-white p-5">
              <span className="grid h-10 w-10 shrink-0 place-items-center rounded-full bg-night font-display text-lg font-bold text-jasmine">{i + 1}</span>
              <div><h3 className="text-xl">{title}</h3><p className="mt-1 text-ink-soft">{body}</p></div>
            </div></Reveal></li>
          ))}
        </ol>
        <Link to="/how-it-works" className="mt-6 inline-flex items-center gap-1.5 font-semibold text-night hover:underline">Follow one review from start to finish <ArrowRight className="h-4 w-4" /></Link>
      </section>

      {/* What the owner gets: outcomes, not technology. The team behind it lives on How it works (for the demo). */}
      <section className="mx-auto max-w-7xl px-5 py-14 sm:px-8 lg:py-20" aria-labelledby="what-you-get">
        <div className="flex flex-wrap items-end justify-between gap-4">
          <div className="max-w-2xl">
            <h2 id="what-you-get" className="type-section">What you get, in plain words</h2>
            <p className="mt-2 text-lg text-ink-soft">No new software to learn. Reminders reach your managers on their phones, and Virundhu makes sure no unhappy guest is left waiting.</p>
          </div>
          <Link to="/how-it-works" className="inline-flex items-center gap-1 font-semibold text-night underline-offset-4 hover:underline">See it working <ArrowRight className="h-4 w-4" /></Link>
        </div>
        <ul className="mt-8 grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          {OUTCOMES.map(([title, body], i) => (
            <li key={title} className={cn("rounded-[20px] p-5", i === 0 ? "bg-night text-jasmine" : "border-2 border-line bg-white")}>
              <p className="font-display text-xl font-bold leading-snug">{title}</p>
              <p className={cn("mt-2", i === 0 ? "text-mist" : "text-ink-soft")}>{body}</p>
            </li>
          ))}
        </ul>
        <div className="mt-6 rounded-[20px] bg-jasmine p-5 sm:flex sm:items-center sm:justify-between sm:gap-6">
          <p className="max-w-3xl"><b>Your dashboard, every day:</b> "Bad reviews answered within 1 hour: 94% this week. Usual reply: 18 minutes. 2 waiting." The same line comes to your phone every Monday.</p>
          <Link to="/register" className={cn(buttonVariants({ variant: "dark" }), "mt-4 shrink-0 sm:mt-0")}>Start free</Link>
        </div>
        <p className="mt-4 text-sm text-ink-soft">Zomato and Swiggy don't let any outside app read or post their reviews. Their clock starts when the review reaches Virundhu by paste, upload or screenshot, and you post the ready reply on their partner app with one copy.</p>
      </section>

      <AfterSignIn />

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
