import { ArrowDown, ArrowRight, Bell, BarChart3, Inbox, MessageSquareReply, QrCode, Star } from "lucide-react";
import { Faq } from "@/components/landing/Faq";
import { Reveal } from "@/components/motion/Reveal";
import { DemoVideos } from "@/components/site/DemoVideos";
import { ReviewJourney } from "@/components/site/ReviewJourney";
import { ClosingCta, PageHero } from "@/components/site/SiteLayout";
import { RESTAURANT_STAFF, SERVICE_AGENTS } from "@/lib/agents";
import { cn } from "@/lib/utils";

const SOURCES = [
  { name: "Google", how: "Automatic, every 10 minutes", auto: true },
  { name: "Your QR link", how: "Automatic, instantly", auto: true },
  { name: "Zomato", how: "Paste or upload", auto: false },
  { name: "Swiggy", how: "Paste or upload", auto: false },
];
const OUTPUTS = [
  { icon: Bell, name: "Alerts", how: "Bell, email, WhatsApp" },
  { icon: Inbox, name: "Inbox", how: "Bad reviews first, with a countdown" },
  { icon: MessageSquareReply, name: "Replies", how: "Google: by itself or one click" },
  { icon: BarChart3, name: "Dashboard", how: "Trends per outlet, priorities" },
];

const MATRIX: { what: string; google: string; qr: string; aggregators: string }[] = [
  { what: "Review comes in", google: "Automatic", qr: "Automatic", aggregators: "You paste it" },
  { what: "Read, tagged, summarised", google: "Automatic", qr: "Automatic", aggregators: "Automatic" },
  { what: "Serious complaint alert", google: "Automatic", qr: "Automatic", aggregators: "Automatic" },
  { what: "Reply written", google: "Automatic", qr: "Automatic", aggregators: "Automatic" },
  { what: "One-hour clock and reminders", google: "Automatic", qr: "Automatic", aggregators: "Automatic, from when you paste it" },
  { what: "Reply posted", google: "Automatic for happy reviews, one click for the rest", qr: "You call or message the guest", aggregators: "One click copies it and opens their site" },
];

function Cell({ text }: { text: string }) {
  const auto = text.startsWith("Automatic");
  return (
    <td className="px-4 py-3 align-top">
      <span className={cn("inline-flex items-start gap-2", auto ? "text-[#1d7a4d]" : "text-ink")}>
        <span className={cn("mt-2 h-2 w-2 shrink-0 rounded-full", auto ? "bg-leaf" : "bg-turmeric")} />{text}
      </span>
    </td>
  );
}

export default function HowItWorks() {
  return (
    <>
      <PageHero title="How Virundhu works" intro="Reviews come in from four places. Every bad one gets a reply ready in seconds and a one-hour clock, with reminders until it is answered." />

      <section id="demo" className="kolam-dark scroll-mt-16 border-t border-white/10 text-jasmine">
        <div className="mx-auto max-w-7xl px-5 py-16 sm:px-8 lg:py-20">
          <Reveal>
            <h2 className="type-section max-w-3xl">How to use Virundhu, step by step</h2>
            <p className="type-lead mt-3 max-w-2xl text-mist">A short video of the real app with a sample restaurant: from creating your account to replying to guests. Each step is explained on screen; click a step to jump to it.</p>
          </Reveal>
          <Reveal className="mt-10" delay={0.1}><DemoVideos /></Reveal>
        </div>
      </section>

      {/* Flow diagram: sources -> Virundhu -> outputs */}
      <section className="mx-auto max-w-7xl px-5 py-20 sm:px-8 lg:py-24">
        <h2 className="type-section">Where reviews come from, and where they go</h2>
        <div className="mt-10 grid items-center gap-6 lg:grid-cols-[1fr_auto_1fr_auto_1fr]">
          <div className="space-y-3">
            {SOURCES.map((s) => (
              <div key={s.name} className={cn("rounded-[16px] border-2 bg-white px-4 py-3", s.auto ? "border-leaf/50" : "border-dashed border-turmeric")}>
                <p className="flex items-center gap-2 font-display text-lg font-bold">{s.name === "Your QR link" ? <QrCode className="h-5 w-5" /> : s.name === "Google" ? <Star className="h-5 w-5" /> : null}{s.name}</p>
                <p className="text-sm text-ink-soft">{s.how}</p>
              </div>
            ))}
          </div>
          <ArrowRight className="mx-auto hidden h-8 w-8 text-ink-soft lg:block" /><ArrowDown className="mx-auto h-8 w-8 text-ink-soft lg:hidden" />
          <div className="kolam-dark rounded-[24px] p-6 text-jasmine shadow-[8px_8px_0_#f6b93b]">
            <p className="font-display text-2xl font-bold">Virundhu reads it</p>
            <ul className="mt-3 space-y-1.5 text-mist">
              <li>Happy, mixed or unhappy</li><li>What it's about</li><li>English, Tamil or Tanglish</li><li>How urgent</li><li>One line in English</li><li>A reply in the guest's language</li>
            </ul>
          </div>
          <ArrowRight className="mx-auto hidden h-8 w-8 text-ink-soft lg:block" /><ArrowDown className="mx-auto h-8 w-8 text-ink-soft lg:hidden" />
          <div className="space-y-3">
            {OUTPUTS.map((o) => (
              <div key={o.name} className="flex items-center gap-3 rounded-[16px] border-2 border-line bg-white px-4 py-3">
                <o.icon className="h-6 w-6 shrink-0 text-night" />
                <div><p className="font-display text-lg font-bold">{o.name}</p><p className="text-sm text-ink-soft">{o.how}</p></div>
              </div>
            ))}
          </div>
        </div>
        <p className="mt-6 flex flex-wrap gap-5 text-sm text-ink-soft">
          <span className="flex items-center gap-2"><span className="h-3 w-6 rounded border-2 border-leaf/50" /> automatic</span>
          <span className="flex items-center gap-2"><span className="h-3 w-6 rounded border-2 border-dashed border-turmeric" /> needs a paste</span>
        </p>
      </section>

      {/* The journey again, for people who land here directly */}
      <section className="kolam-dark text-jasmine">
        <div className="mx-auto max-w-7xl px-5 py-20 sm:px-8 lg:py-24">
          <h2 className="type-section">One review, step by step</h2>
          <div className="mt-10"><ReviewJourney /></div>
        </div>
      </section>

      {/* Honest matrix */}
      <section className="mx-auto max-w-7xl px-5 py-20 sm:px-8 lg:py-24">
        <h2 className="type-section">What's automatic, honestly</h2>
        <p className="mt-3 max-w-3xl text-lg text-ink-soft">
          Zomato and Swiggy don't let outside software read or post reviews, so those need one paste. We don't copy their
          websites behind their back, because that can put your listing at risk.
        </p>
        <div className="mt-8 overflow-x-auto rounded-[20px] border-2 border-line bg-white">
          <table className="w-full min-w-[640px] text-left">
            <thead className="bg-jasmine-2 font-display text-lg">
              <tr><th className="px-4 py-3">Step</th><th className="px-4 py-3">Google</th><th className="px-4 py-3">Your QR link</th><th className="px-4 py-3">Zomato / Swiggy</th></tr>
            </thead>
            <tbody>
              {MATRIX.map((r) => (
                <tr key={r.what} className="border-t-2 border-jasmine-2">
                  <td className="px-4 py-3 align-top font-semibold">{r.what}</td>
                  <Cell text={r.google} /><Cell text={r.qr} /><Cell text={r.aggregators} />
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {/* Owner setup */}
      <section className="bg-jasmine-2">
        <div className="mx-auto max-w-7xl px-5 py-20 sm:px-8 lg:py-24">
          <h2 className="type-section">Set up in four steps</h2>
          <ol className="mt-10 grid gap-5 md:grid-cols-4">
            {[
              ["Sign up", "Restaurant name and city. 14 days free, no card."],
              ["Connect Google", "One click. Your Google reviews start flowing in."],
              ["Print your QR", "On the bill and the food packet. Guests rate you in seconds."],
              ["Add your managers' numbers", "They get the 30-minute reminder for their branch. You get the 60-minute one."],
            ].map(([t, b], i) => (
              <li key={t} className="rounded-[20px] border-2 border-line bg-white p-5">
                <span className="flex h-10 w-10 items-center justify-center rounded-full bg-night font-display text-lg font-bold text-turmeric">{i + 1}</span>
                <h3 className="mt-4 text-xl font-bold">{t}</h3>
                <p className="mt-1 text-ink-soft">{b}</p>
              </li>
            ))}
          </ol>
        </div>
      </section>

      {/* For the demo: the technology behind the promise */}
      <section className="mx-auto max-w-7xl px-5 py-20 sm:px-8 lg:py-24" aria-labelledby="inside">
        <h2 id="inside" className="type-section max-w-3xl">Inside Virundhu: the team behind the promise</h2>
        <p className="mt-3 max-w-3xl text-lg text-ink-soft">
          For the curious. Each job is done by its own AI assistant with strict rules: replies never promise refunds or blame
          staff, numbers are counted by the database (never guessed by the AI), and anything risky waits for a person.
        </p>
        <h3 className="mt-8 text-xl font-bold">Working in your restaurant</h3>
        <ul className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          {RESTAURANT_STAFF.map((m) => (
            <li key={m.name} className="rounded-[18px] border-2 border-line bg-white p-4">
              <p className="font-display text-lg font-bold leading-tight">{m.name} <span className="text-[0.95rem] font-semibold text-[#b32f12]">· {m.role}</span></p>
              <p className="mt-2 text-sm">{m.job}</p>
            </li>
          ))}
        </ul>
        <h3 className="mt-8 text-xl font-bold">Looking after your account</h3>
        <ul className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          {SERVICE_AGENTS.map((a) => (
            <li key={a.name} className="rounded-[18px] bg-night p-4 text-jasmine">
              <p className="font-display text-lg font-bold">{a.name} <span className="text-[0.95rem] font-semibold text-turmeric">· {a.role}</span></p>
              <p className="mt-1 text-sm text-mist">{a.job}</p>
            </li>
          ))}
        </ul>
      </section>

      <section className="mx-auto max-w-4xl px-5 py-20 sm:px-8 lg:py-24">
        <h2 className="type-section">Questions owners ask</h2>
        <div className="mt-8"><Faq /></div>
      </section>

      <ClosingCta />
    </>
  );
}
