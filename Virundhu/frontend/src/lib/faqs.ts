/** Questions shown on the site; also sent to Google as FAQ structured data (see lib/seo.ts). */

export const HOW_FAQS: [string, string][] = [
  ["Does it really understand Tanglish?", "Yes. Reviews like \"saapadu nalla irundhuchu but bill la extra charge\" are read correctly, summarised in English, and answered in Tanglish. Tamil script works the same way."],
  ["Where do the reviews come from?", "Google connects officially: reviews flow in automatically and replies go back to Google. Your own QR feedback link (on the bill or food packet) also arrives by itself. Zomato and Swiggy don't offer a public review API, so you paste their reviews or upload a file; the reply is copied for you with one click."],
  ["Will it post replies without us checking?", "Only if you switch on auto-pilot, and only for happy 4 or 5 star Google reviews. Anything unhappy, urgent or about hygiene always waits for a person."],
  ["What makes a review urgent?", "Health or hygiene problems, wrong or missing orders, refund demands and rude-staff complaints. Words like \"mudi\", \"vaanthi\" or \"insect\" always mark a review urgent, even if the AI is unsure."],
  ["How fast do I hear about a serious complaint?", "Within seconds of the review arriving. You get a notification in the app, an email and a WhatsApp message, with the review, a one-line summary and a ready reply."],
  ["Are the dashboard numbers made up by the AI?", "Never. Every count and percentage is calculated from your data. The AI only reads each review and drafts the reply."],
  ["Can my team use it on their phones?", "Yes. The inbox and dashboard work on any phone browser."],
];

export const PRICING_FAQS: [string, string][] = [
  ["Is there a free trial?", "Yes, 14 days with everything switched on. No card needed to start."],
  ["How is the price worked out?", "By the number of outlets you run and how long you pay for. The more outlets, the lower the price per outlet: a 100-branch chain pays far less per branch than a single shop. Paying for 3, 6, 9 or 12 months gives a discount, and 9 and 12 months add free months on top."],
  ["How do I pay?", "UPI or card through Dodo Payments. You get an invoice by email. One payment for the period you choose; no contract and no automatic renewal."],
  ["Can I add outlets later?", "Yes. Pay again with the new outlet count; your time left carries over and the new period is added on."],
  ["What happens when the trial or plan ends?", "Nothing is deleted. You can still look at everything; adding and replying to reviews pauses until you pay."],
  ["Is there a launch offer?", "Yes. The first 10 restaurants get 20% off with the code FIRST10 on the payment page."],
];
