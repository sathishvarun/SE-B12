import { Plus } from "lucide-react";

const faqs = [
  ["Does it really understand Tanglish?", "Yes. Reviews like \"saapadu nalla irundhuchu but bill la extra charge\" are read correctly, summarised in English, and answered in Tanglish. Tamil script works the same way."],
  ["Where do the reviews come from?", "Google connects officially: reviews flow in automatically and replies go back to Google. Your own QR feedback link (on the bill or food packet) also arrives by itself. Zomato and Swiggy don't offer a public review API, so you paste their reviews or upload a file; the reply is copied for you with one click."],
  ["Will it post replies without us checking?", "Only if you switch on auto-pilot, and only for happy 4 or 5 star Google reviews. Anything unhappy, urgent or about hygiene always waits for a person."],
  ["What makes a review urgent?", "Health or hygiene problems, wrong or missing orders, refund demands and rude-staff complaints. Words like \"mudi\", \"vaanthi\" or \"insect\" always mark a review urgent, even if the AI is unsure."],
  ["How fast do I hear about a serious complaint?", "Within seconds of the review arriving. You get a notification in the app, an email and a WhatsApp message, with the review, a one-line summary and a ready reply."],
  ["Are the dashboard numbers made up by the AI?", "Never. Every count and percentage is calculated from your data. The AI only reads each review and drafts the reply."],
  ["Can my team use it on their phones?", "Yes. The inbox and dashboard work on any phone browser."],
];

export function Faq() {
  return (
    <div className="divide-y-2 divide-line border-y-2 border-line">
      {faqs.map(([q, a]) => (
        <details key={q} className="group py-1">
          <summary className="flex cursor-pointer list-none items-center justify-between gap-4 py-4 font-display text-[1.2rem] font-semibold [&::-webkit-details-marker]:hidden">
            {q}
            <Plus className="h-5 w-5 shrink-0 transition-transform group-open:rotate-45" />
          </summary>
          <p className="max-w-3xl pb-5 text-ink-soft">{a}</p>
        </details>
      ))}
    </div>
  );
}
