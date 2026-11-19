import { HeartHandshake, Languages, ShieldCheck, Sprout } from "lucide-react";
import { BeforeAfter } from "@/components/site/BeforeAfter";
import { ClosingCta, PageHero } from "@/components/site/SiteLayout";
import { usePublicConfig } from "@/hooks/usePublicConfig";

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
  const company = usePublicConfig().data?.company;
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

      {company?.parent ? (
        <section className="mx-auto max-w-7xl px-5 pb-20 sm:px-8">
          <div className="overflow-hidden rounded-[28px] bg-night text-jasmine">
            <div className="grid gap-8 p-7 sm:p-10 lg:grid-cols-[1.1fr_1fr] lg:items-center">
              <div>
                <p className="font-display text-sm font-semibold uppercase tracking-[0.18em] text-turmeric">The people behind it</p>
                <h2 className="mt-2 font-display text-[2.4rem] font-bold leading-[1.05] sm:text-[3rem]">Built by {company.parent}.<br /><span className="text-turmeric">Made for restaurants.</span></h2>
                <p className="mt-4 max-w-xl text-lg text-mist">{company.name} is the restaurant software of {company.parent}, a Coimbatore company. We build the tools and run the service. Your kitchen, your guests and your name stay yours.</p>
              </div>
              <div className="relative rounded-[22px] bg-white/[0.06] p-5" aria-label={`${company.parent} is the parent company of ${company.name}`}>
                <div className="rounded-[16px] border-2 border-white/15 px-5 py-4 text-center">
                  <p className="text-sm text-mist">Parent company</p>
                  <p className="font-display text-2xl font-bold">{company.parent}</p>
                  <p className="text-sm text-mist">Coimbatore, Tamil Nadu</p>
                </div>
                <div className="mx-auto h-8 w-0.5 bg-turmeric" aria-hidden="true" />
                <div className="rounded-[16px] bg-turmeric px-5 py-4 text-center text-night">
                  <p className="text-sm font-semibold">Our product</p>
                  <p className="font-display text-2xl font-bold">{company.name}</p>
                  <p className="text-sm">Review care and AI staff for restaurants</p>
                </div>
              </div>
            </div>
            <ul className="grid border-t border-white/10 sm:grid-cols-3">
              {[
                { t: "We make software, not food", b: "We don't own or run any restaurant, so we're never your competitor." },
                { t: "Your guests stay yours", b: "Reviews, guest contacts and QR feedback belong to you. One restaurant never sees another's." },
                { t: "Why @skminimart.com?", b: `Our emails come from ${company.parent}, the company behind ${company.name}. Same team, one inbox.` },
              ].map((x) => (
                <li key={x.t} className="border-white/10 p-6 sm:border-l sm:first:border-l-0">
                  <p className="font-display text-lg font-bold text-turmeric">{x.t}</p>
                  <p className="mt-1 text-mist">{x.b}</p>
                </li>
              ))}
            </ul>
          </div>
        </section>
      ) : null}
      <ClosingCta title="Made in Tamil Nadu, for the kitchens that feed it." />
    </>
  );
}
