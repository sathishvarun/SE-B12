import { Bell, MessageCircleQuestion, QrCode, Star } from "lucide-react";
import { cn } from "@/lib/utils";

const CARDS = [
  {
    icon: Star,
    title: "Happy Google reviews answer themselves",
    body: "4 and 5 star reviews get a warm thank-you posted automatically. Anything unhappy waits for you.",
    visual: (
      <div className="rounded-[14px] bg-jasmine p-3 text-sm">
        <p>★★★★★ "Best biryani in Coimbatore!"</p>
        <p className="mt-2 rounded-[10px] bg-white px-2.5 py-1.5"><b className="text-leaf">Replied automatically:</b> Thank you so much! See you again soon.</p>
      </div>
    ),
  },
  {
    icon: QrCode,
    title: "Your own feedback, from every guest",
    body: "A QR code on the bill and the food packet. Dine-in, takeaway and delivery guests rate you in seconds, straight into Virundhu.",
    visual: (
      <div className="flex items-center gap-3 rounded-[14px] bg-jasmine p-3">
        <div className="grid h-14 w-14 shrink-0 grid-cols-4 gap-0.5 rounded-[8px] bg-white p-1.5">
          {Array.from({ length: 16 }, (_, i) => <span key={i} className={cn("rounded-[1px]", [0, 2, 3, 5, 6, 9, 10, 12, 15].includes(i) ? "bg-night" : "bg-transparent")} />)}
        </div>
        <p className="text-sm">"Scan to tell us how your food was." No app, no sign-in.</p>
      </div>
    ),
  },
  {
    icon: Bell,
    title: "Serious complaints reach you in a minute",
    body: "Food safety or a furious guest: a bell, an email and a WhatsApp message to you and your outlet managers.",
    visual: (
      <div className="rounded-[14px] bg-jasmine p-3 text-sm">
        <p className="font-semibold text-[#b32f12]">Food-safety complaint at RS Puram</p>
        <p className="text-ink-soft">Hair found in the chicken. Call the outlet today.</p>
      </div>
    ),
  },
  {
    icon: MessageCircleQuestion,
    title: "Ask what to fix first",
    body: "Ask in English, Tamil or Tanglish. Get priority 1, 2 and 3, with the numbers counted from your own reviews.",
    visual: (
      <div className="space-y-2 rounded-[14px] bg-jasmine p-3 text-sm">
        <p className="ml-auto w-fit rounded-[10px] bg-night px-2.5 py-1.5 text-jasmine">Indha vaaram enna fix pannanum?</p>
        <p className="w-fit rounded-[10px] bg-white px-2.5 py-1.5"><b>Priority 1:</b> late deliveries at Anna Nagar (9 this week).</p>
      </div>
    ),
  },
];

/** `phoneLimit`: on small screens show only the first few cards (keeps the home page short on a phone). */
export function AutomationCards({ phoneLimit }: { phoneLimit?: number }) {
  return (
    <div className="grid grid-cols-1 gap-5 md:grid-cols-2">
      {CARDS.map((c, i) => (
        <article key={c.title} className={`${phoneLimit !== undefined && i >= phoneLimit ? "hidden md:flex" : "flex"} flex-col rounded-[22px] border-2 border-line bg-white p-6 transition-transform hover:-translate-y-1`}>
          <c.icon className="h-7 w-7 text-night" strokeWidth={1.7} />
          <h3 className="mt-4 text-[1.4rem] font-bold">{c.title}</h3>
          <p className="mt-2 flex-1 text-ink-soft">{c.body}</p>
          <div className="mt-5">{c.visual}</div>
        </article>
      ))}
    </div>
  );
}
