import { Check, Minus, X } from "lucide-react";
import { ClosingCta, PageHero } from "@/components/site/SiteLayout";

type Mark = "yes" | "part" | "no";
const ROWS: { what: string; virundhu: Mark; dashboards: Mark; pos: Mark; global: Mark; note: string }[] = [
  { what: "Does the work for you (replies, alerts, win-back), not just shows it", virundhu: "yes", dashboards: "part", pos: "no", global: "part", note: "Seven AI staff members with your rules; you approve only what needs you." },
  { what: "Reads Tamil and Tanglish, replies in the guest's own language", virundhu: "yes", dashboards: "part", pos: "no", global: "no", note: "Built in Tamil Nadu for Tamil Nadu guests." },
  { what: "Crisis radar: catches the same complaint repeating at one outlet", virundhu: "yes", dashboards: "no", pos: "no", global: "part", note: "3 complaints in 72 hours at one branch is flagged with the likely cause and a fix." },
  { what: "Today's 3 moves: what to fix, which dish, who to thank", virundhu: "yes", dashboards: "no", pos: "no", global: "no", note: "Picked from your last 7 days of reviews, every morning." },
  { what: "Win-back: apology and comeback code to unhappy guests", virundhu: "yes", dashboards: "no", pos: "part", global: "no", note: "Sent on WhatsApp in one tap; tracks who came back." },
  { what: "Shows money at risk and money won back", virundhu: "yes", dashboards: "no", pos: "no", global: "no", note: "Uses your own average order value, with every assumption shown." },
  { what: "Food-safety complaint to the branch manager within a minute", virundhu: "yes", dashboards: "part", pos: "no", global: "part", note: "Hygiene always waits for a person; never auto-replied." },
  { what: "Your rules: words a reply must never use, topics that wait for you", virundhu: "yes", dashboards: "no", pos: "no", global: "part", note: "\"Never promise a refund\" is enforced on every reply." },
  { what: "Priced per outlet in rupees, cheaper per outlet as you grow", virundhu: "yes", dashboards: "yes", pos: "part", global: "no", note: "From ₹1,499 per outlet a month; 14-day free trial." },
  { what: "Honest about Zomato and Swiggy (no scraping, no account risk)", virundhu: "yes", dashboards: "part", pos: "yes", global: "part", note: "Screenshots and files in; replies go out through the partner apps." },
];

function Cell({ m }: { m: Mark }) {
  if (m === "yes") return <span className="inline-flex h-7 w-7 items-center justify-center rounded-full bg-leaf text-white" ><span className="sr-only">Yes</span><Check aria-hidden="true" className="h-4 w-4" /></span>;
  if (m === "part") return <span className="inline-flex h-7 w-7 items-center justify-center rounded-full bg-turmeric text-night" ><span className="sr-only">Partly</span><Minus aria-hidden="true" className="h-4 w-4" /></span>;
  return <span className="inline-flex h-7 w-7 items-center justify-center rounded-full bg-jasmine-2 text-ink-soft" ><span className="sr-only">No</span><X aria-hidden="true" className="h-4 w-4" /></span>;
}

export default function Compare() {
  return (
    <>
      <PageHero title="What makes Virundhu different"
        intro="Most review tools give you one more screen to check. Virundhu gives you a team that does the checking, replying and following up, in your guests' language, and tells you what it's worth in rupees." />
      <section className="mx-auto max-w-7xl px-5 py-16 sm:px-8">
        <div className="overflow-x-auto rounded-[22px] border-2 border-line bg-white">
          <table className="w-full min-w-[860px] text-left">
            <thead className="bg-night text-jasmine">
              <tr>
                <th className="px-5 py-4 font-display text-lg">What you get</th>
                <th className="px-3 py-4 text-center font-display text-lg text-turmeric">Virundhu</th>
                <th className="px-3 py-4 text-center text-sm font-semibold">Review dashboards</th>
                <th className="px-3 py-4 text-center text-sm font-semibold">POS and billing apps</th>
                <th className="px-3 py-4 text-center text-sm font-semibold">Global reputation tools</th>
              </tr>
            </thead>
            <tbody>
              {ROWS.map((r) => (
                <tr key={r.what} className="border-t-2 border-jasmine-2 align-top">
                  <td className="px-5 py-4"><p className="font-semibold">{r.what}</p><p className="mt-0.5 text-sm text-ink-soft">{r.note}</p></td>
                  <td className="bg-turmeric/10 px-3 py-4 text-center"><Cell m={r.virundhu} /></td>
                  <td className="px-3 py-4 text-center"><Cell m={r.dashboards} /></td>
                  <td className="px-3 py-4 text-center"><Cell m={r.pos} /></td>
                  <td className="px-3 py-4 text-center"><Cell m={r.global} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="mt-3 text-sm text-ink-soft">Comparison by type of tool, from their public feature pages, November 2026. Partly = some plans or some platforms only.</p>
      </section>
      <ClosingCta title="Hire your AI review team for less than one day of a waiter's salary." />
    </>
  );
}
