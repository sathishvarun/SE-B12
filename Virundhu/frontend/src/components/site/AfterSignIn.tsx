import { useState } from "react";
import { cn } from "@/lib/utils";

const VIEWS = {
  owner: {
    tab: "What you see",
    img: "/demo/after-owner.jpg",
    alt: "The Your AI staff screen of a restaurant: money at risk, today's 3 moves, crisis radar and the seven staff cards",
    lead: "Sign in and open Your AI staff. Everything your reviews said overnight is already sorted into what to do today.",
    steps: [
      { t: "Today's 3 moves", b: "The three things worth your time today, each with the rupees at risk. Tap one and it opens the review or the dish." },
      { t: "Crisis radar", b: "If three guests mention the same problem within 72 hours, or anyone mentions hygiene, it turns red and your phone gets a message." },
      { t: "Win-back list", b: "Unhappy guests who left a number get a ready Tamil or English WhatsApp note with a return-visit code. You press send." },
      { t: "Your rules", b: "Tell the staff what never to do, such as no auto-reply to 1-star reviews. Autopilot follows it on every reply." },
    ],
  },
  admin: {
    tab: "What our agents do",
    img: "/demo/after-admin.jpg",
    alt: "Our team's Autopilot screen: new leads, trials ending, open support, account health and payments today",
    lead: "Behind the scenes, our own AI agents run the service: Mani, the lead agent, hands every job to the right one, day and night.",
    steps: [
      { t: "Demos book themselves", b: "Nila emails open times within a minute; you tap one and get a calendar invite for Meet, Zoom, Teams, phone or in person." },
      { t: "Trials ending", b: "Reminders go out 5, 4, 3, 2 and 1 day before your trial ends, and stop the moment you pay." },
      { t: "Support answers itself", b: "Tara replies to your ticket within minutes. If a payment didn't switch your plan on, she checks it and fixes it." },
      { t: "Health checks", b: "Dev watches syncing, emails and backups every night, so problems are caught before you notice." },
    ],
  },
} as const;

/** "What happens after you sign in": the owner's screen and our team's screen, side by side. */
export function AfterSignIn() {
  const [view, setView] = useState<keyof typeof VIEWS>("owner");
  const v = VIEWS[view];
  return (
    <section className="mx-auto max-w-7xl px-5 py-14 sm:px-8 lg:py-20">
      <div className="max-w-2xl">
        <h2 className="type-section">What happens after you sign in</h2>
        <p className="mt-2 text-lg text-ink-soft">Real screens from a demo restaurant. Switch to see the other side.</p>
      </div>
      <div role="tablist" aria-label="Choose a screen" className="mt-6 inline-flex rounded-full border-2 border-line bg-white p-1">
        {(Object.keys(VIEWS) as (keyof typeof VIEWS)[]).map((k) => (
          <button
            key={k}
            role="tab"
            aria-selected={view === k}
            onClick={() => setView(k)}
            className={cn("rounded-full px-5 py-2 font-semibold transition-colors focus-visible:outline-2 focus-visible:outline-offset-2", view === k ? "bg-night text-jasmine" : "text-ink-soft hover:text-night")}
          >
            {VIEWS[k].tab}
          </button>
        ))}
      </div>
      <div className="mt-6 grid gap-8 lg:grid-cols-[1.35fr_1fr] lg:items-start">
        <figure className="overflow-hidden rounded-[22px] border-2 border-line bg-white shadow-[0_18px_40px_-24px_rgba(20,50,40,0.45)]">
          <img key={v.img} src={v.img} alt={v.alt} loading="lazy" className="w-full" />
        </figure>
        <div>
          <p className="text-lg">{v.lead}</p>
          <ol className="mt-5 space-y-4">
            {v.steps.map((s, i) => (
              <li key={s.t} className="flex gap-4">
                <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-turmeric font-display font-bold text-night">{i + 1}</span>
                <div><p className="font-display text-lg font-bold">{s.t}</p><p className="text-ink-soft">{s.b}</p></div>
              </li>
            ))}
          </ol>
        </div>
      </div>
    </section>
  );
}
