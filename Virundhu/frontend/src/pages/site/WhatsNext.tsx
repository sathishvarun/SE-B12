import { CalendarClock } from "lucide-react";
import { ClosingCta, PageHero } from "@/components/site/SiteLayout";

const LIVE = [
  "Your AI staff of seven: the Guest Whisperer, Reply Maestro, Kitchen Guardian, Trouble Spotter, Comeback Captain, Star Builder and Monday Strategist",
  "Today's 3 moves, picked from your last 7 days of reviews",
  "Crisis radar for repeating complaints at one outlet",
  "Win-back messages with comeback codes, sent on WhatsApp",
  "Money at risk and money won back, in rupees",
  "Your rules: banned words and topics that always wait for you",
];

const SOON: { when: string; title: string; body: string }[] = [
  { when: "Coming soon", title: "Talk to Virundhu in Tamil", body: "Send a voice note: \"What went wrong at the Gandhipuram branch this week?\" and hear the answer back." },
  { when: "Coming soon", title: "Approve replies on WhatsApp", body: "Every Zomato and Swiggy reply arrives on WhatsApp; tap Approve and it's ready to post." },
  { when: "Coming soon", title: "Neighbour watch", body: "Each month, your Google rating and top complaints compared with five restaurants nearby." },
  { when: "Coming soon", title: "Menu doctor", body: "Dishes guests keep complaining about, with a suggested fix: portion, spice, packaging or price." },
  { when: "Coming soon", title: "Staff coach", body: "A short weekly note for each branch team: who guests praised, and one habit to improve." },
  { when: "Later in 2027", title: "POS partnership", body: "Orders and reviews joined up, so you see which bill a complaint came from." },
  { when: "Later in 2027", title: "More languages", body: "Malayalam, Kannada and Arabic, for Kerala, Karnataka and Gulf restaurants." },
  { when: "Later in 2027", title: "For consultants and chains", body: "White-label reports and an API for restaurant consultants who manage many brands." },
];

export default function WhatsNext() {
  return (
    <>
      <PageHero title="What's live, and what's coming next"
        intro="We ship something useful every few weeks. Here's what your AI staff already does, and what we're building with our first restaurants." />
      <section className="mx-auto grid max-w-7xl gap-10 px-5 py-16 sm:px-8 lg:grid-cols-[1fr_1.5fr]">
        <div>
          <h2 className="font-display text-3xl font-bold">Live today</h2>
          <ul className="mt-4 space-y-3">
            {LIVE.map((l) => <li key={l} className="rounded-[16px] border-2 border-leaf/40 bg-leaf-soft px-4 py-3 font-medium">{l}</li>)}
          </ul>
        </div>
        <div>
          <h2 className="font-display text-3xl font-bold">Coming next</h2>
          <ol className="mt-4 grid gap-3 sm:grid-cols-2">
            {SOON.map((s) => (
              <li key={s.title} className="rounded-[18px] border-2 border-line bg-white p-4">
                <p className="flex items-center gap-1.5 text-sm font-semibold text-chilli"><CalendarClock className="h-4 w-4" /> {s.when}</p>
                <p className="mt-1 font-display text-xl font-bold">{s.title}</p>
                <p className="mt-1 text-ink-soft">{s.body}</p>
              </li>
            ))}
          </ol>
          <p className="mt-4 text-sm text-ink-soft">Want something sooner? Tell us on the Contact page; our first restaurants decide the order.</p>
        </div>
      </section>
      <ClosingCta />
    </>
  );
}
