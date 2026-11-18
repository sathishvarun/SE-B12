import { HeartHandshake, Languages, ShieldCheck, Sprout } from "lucide-react";
import { BeforeAfter } from "@/components/site/BeforeAfter";
import { ClosingCta, PageHero } from "@/components/site/SiteLayout";

const TIMELINE = [
  { when: "The old way", title: "Reviews scattered across apps", body: "Each outlet's Google, Zomato and Swiggy reviews live in separate apps. Someone checks when they remember." },
  { when: "The cost", title: "Small problems become big ones", body: "A hair in the food or a sick guest is noticed days later, after it's on Instagram. Unanswered reviews make new guests walk past." },
  { when: "What we built", title: "One place that reads everything", body: "Virundhu reads every review the moment it arrives, in Tamil, Tanglish or English, and sorts it by how urgent it is." },
  { when: "Today", title: "Mostly automatic", body: "Alerts, reply drafts, happy-review replies and QR feedback run by themselves, and Ask Virundhu tells you what to fix first. People handle the guests who need a person." },
];

const PRINCIPLES = [
  { icon: Languages, title: "Your guests' language", body: "Tamil and Tanglish are first-class, not an afterthought. Replies go back in the language the guest used." },
  { icon: ShieldCheck, title: "Honest by design", body: "Every number is counted from your reviews, never guessed. We don't scrape Zomato or Swiggy, and we say so up front." },
  { icon: HeartHandshake, title: "People for the hard ones", body: "Food-safety complaints and angry guests always reach a person. Automation handles the routine, never the sensitive." },
  { icon: Sprout, title: "Your data, yours", body: "QR feedback belongs to the restaurant, not to a delivery app. One restaurant never sees another's reviews." },
];

export default function About() {
  return (
    <>
      <PageHero title="Why we built Virundhu"
        intro="Virundhu means a feast, and the Tamil tradition of welcoming every guest. Restaurants here live on word of mouth, and today that word is a review. We built Virundhu so no guest goes unheard." />

      <section className="mx-auto max-w-7xl px-5 py-20 sm:px-8 lg:py-24">
        <h2 className="type-section">The purpose, in one line</h2>
        <p className="mt-4 max-w-3xl font-display text-[1.8rem] font-medium leading-snug sm:text-[2.2rem]">
          Help restaurant owners catch every serious complaint the same day, reply to every guest in their own language,
          and know exactly what to fix, without spending hours on apps.
        </p>
      </section>

      <section className="bg-jasmine-2">
        <div className="mx-auto max-w-7xl px-5 py-20 sm:px-8 lg:py-24">
          <h2 className="type-section">How it was, and how it is now</h2>
          <ol className="relative mt-12 grid gap-6 md:grid-cols-4">
            <span aria-hidden="true" className="absolute left-0 right-0 top-5 hidden h-1 rounded-full bg-linear-to-r from-chilli via-turmeric to-leaf md:block" />
            {TIMELINE.map((t, i) => (
              <li key={t.title} className="relative">
                <span className={`relative z-10 flex h-11 w-11 items-center justify-center rounded-full border-4 border-jasmine-2 font-display font-bold text-white ${["bg-chilli", "bg-chilli", "bg-turmeric", "bg-leaf"][i]}`}>{i + 1}</span>
                <p className="mt-4 text-sm font-semibold text-ink-soft">{t.when}</p>
                <h3 className="mt-1 text-xl font-bold">{t.title}</h3>
                <p className="mt-2 text-ink-soft">{t.body}</p>
              </li>
            ))}
          </ol>
        </div>
      </section>

      <section className="mx-auto max-w-7xl px-5 py-20 sm:px-8 lg:py-24">
        <h2 className="type-section">A normal day, before and after</h2>
        <div className="mt-8"><BeforeAfter /></div>
      </section>

      <section className="kolam-dark text-jasmine">
        <div className="mx-auto max-w-7xl px-5 py-20 sm:px-8 lg:py-24">
          <h2 className="type-section">What we stand for</h2>
          <div className="mt-10 grid gap-5 sm:grid-cols-2">
            {PRINCIPLES.map((p) => (
              <div key={p.title} className="rounded-[20px] border-2 border-white/10 bg-white/5 p-6">
                <p.icon className="h-7 w-7 text-turmeric" strokeWidth={1.7} />
                <h3 className="mt-4 text-[1.4rem] font-bold">{p.title}</h3>
                <p className="mt-2 text-mist">{p.body}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      <ClosingCta title="Made in Tamil Nadu, for the kitchens that feed it." />
    </>
  );
}
