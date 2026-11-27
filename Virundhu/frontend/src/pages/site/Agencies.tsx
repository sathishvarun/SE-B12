import { Link } from "react-router-dom";
import { ClosingCta, PageHero } from "@/components/site/SiteLayout";
import { buttonVariants } from "@/components/ui/button";
import { cn } from "@/lib/utils";

const POINTS: [string, string][] = [
  ["Every client in one list", "Each morning you see which restaurant has bad reviews waiting and which one is past the hour. Open it with one click."],
  ["Replies ready, in the client's voice", "Each restaurant keeps its own tone and sign-off. Replies come in Tamil, Tanglish or English, whichever the guest wrote."],
  ["Proof for your monthly report", "Bad reviews answered within an hour, usual reply time and the dishes guests complain about, for each client."],
  ["Clean separation", "Each client is its own restaurant with its own data and plan. A client can never see another client, and you can be removed by them at any time."],
];

const STEPS: [string, string][] = [
  ["Add your clients", "From \"All your restaurants\", add each client by name. Each starts its own 14-day free trial."],
  ["Or get invited", "A restaurant already on Virundhu invites your email from its Settings. You join with your existing login."],
  ["Work the queue", "Switch between clients from the menu. The one-hour clock and reminders run for each one."],
];

/** Public page for PR and reputation agencies that manage reviews for many restaurants. */
export default function Agencies() {
  return (
    <>
      <PageHero title="For agencies that manage many restaurants"
        intro="Your clients' Google, Zomato and Swiggy reviews in one login. Bad ones get a ready reply and a one-hour clock, so no client's unhappy guest is left waiting." />
      <section className="mx-auto max-w-7xl px-5 py-16 sm:px-8 lg:py-20">
        <ul className="grid gap-4 md:grid-cols-2">
          {POINTS.map(([t, b], i) => (
            <li key={t} className={cn("rounded-[20px] p-6", i === 0 ? "bg-night text-jasmine" : "border-2 border-line bg-white")}>
              <h2 className="font-display text-2xl font-bold">{t}</h2>
              <p className={cn("mt-2 text-lg", i === 0 ? "text-mist" : "text-ink-soft")}>{b}</p>
            </li>
          ))}
        </ul>
        <h2 className="type-section mt-16 max-w-3xl">How it works for an agency</h2>
        <ol className="mt-6 grid gap-4 md:grid-cols-3">
          {STEPS.map(([t, b], i) => (
            <li key={t} className="rounded-[20px] border-2 border-line bg-white p-5">
              <span className="grid h-9 w-9 place-items-center rounded-full bg-turmeric font-bold text-night">{i + 1}</span>
              <p className="mt-3 text-lg font-bold">{t}</p>
              <p className="mt-1 text-ink-soft">{b}</p>
            </li>
          ))}
        </ol>
        <div className="mt-10 rounded-[20px] bg-jasmine p-6 sm:flex sm:items-center sm:justify-between sm:gap-6">
          <p className="max-w-3xl text-lg"><b>Pricing:</b> each client restaurant is billed per outlet like any other, so you can pass it on or bundle it into your retainer. Ten clients or more? Talk to us about one invoice.</p>
          <div className="mt-4 flex shrink-0 gap-3 sm:mt-0">
            <Link to="/register" className={buttonVariants({ variant: "dark" })}>Start free</Link>
            <Link to="/contact" className={buttonVariants({ variant: "outline" })}>Talk to us</Link>
          </div>
        </div>
      </section>
      <ClosingCta />
    </>
  );
}
