import { KeyRound, Lock, Server, ShieldCheck, Trash2, UserCheck } from "lucide-react";
import type { ReactNode } from "react";
import { Link } from "react-router-dom";
import { PageHero } from "@/components/site/SiteLayout";
import { usePublicConfig } from "@/hooks/usePublicConfig";

const UPDATED = "17 November 2026";

function useCompany() {
  const { data } = usePublicConfig();
  const c = data?.company;
  return {
    name: c?.name ?? "Virundhu",
    email: c?.email ?? null,
    phone: c?.phone ?? null,
    address: c?.address ?? null,
    officer: c?.grievance_officer ?? c?.name ?? "Virundhu",
  };
}

function ContactLines() {
  const c = useCompany();
  return (
    <ul className="mt-2 space-y-1">
      <li><b>{c.officer}</b>, Grievance Officer, for {c.name}</li>
      {c.email ? <li>Email: <a className="underline" href={`mailto:${c.email}`}>{c.email}</a></li> : null}
      {c.phone ? <li>Phone / WhatsApp: <a className="underline" href={`tel:${c.phone.replace(/\s/g, "")}`}>{c.phone}</a></li> : null}
      {c.address ? <li>Address: {c.address}</li> : null}
      {!c.email && !c.phone ? <li>Use the <Link to="/contact" className="underline">Contact page</Link>.</li> : null}
    </ul>
  );
}

function Doc({ title, intro, children }: { title: string; intro: string; children: ReactNode }) {
  return (
    <>
      <PageHero title={title} intro={intro} />
      <article className="mx-auto max-w-3xl px-5 py-14 sm:px-8 lg:py-20">
        <p className="text-sm text-ink-soft">Last updated {UPDATED}</p>
        <div className="mt-6 space-y-9 text-[1.05rem] leading-relaxed [&_h2]:font-display [&_h2]:text-[1.6rem] [&_h2]:font-bold [&_ul_li]:ml-5 [&_ul_li]:list-disc [&_ol_li]:ml-5 [&_ol_li]:list-decimal [&_p]:mt-2 [&_ul]:mt-2 [&_ul]:space-y-1.5 [&_ol]:mt-2 [&_ol]:space-y-1.5">
          {children}
        </div>
      </article>
    </>
  );
}

const DATA_ROWS: [string, string, string][] = [
  ["Your name, email, phone, password (stored only as a one-way hash)", "To create your account, sign you in and contact you about it", "While your account is open"],
  ["Restaurant name, city, outlets, addresses, managers' names and numbers you add", "To organise reviews by outlet and send alerts to the right person", "While your account is open"],
  ["Guest reviews: text, rating, date, platform, outlet, and the reviewer's public name", "To read, sort and prioritise reviews, draft replies and show reports", "While your account is open, or until you delete them"],
  ["QR feedback: rating, comment, and a name and phone or email only if the guest chooses to give them", "To pass the feedback to the restaurant so it can fix the problem and reply", "While the restaurant's account is open"],
  ["Guest phone numbers you enter to ask for a review", "To send one message; afterwards we keep only a one-way hash to avoid asking the same guest twice within 30 days", "Number: not stored. Hash: 12 months"],
  ["Payment status, amount, plan and payment ID (no card or UPI details)", "To activate your plan, show your payment history, handle refunds and meet tax law", "As long as tax law requires"],
  ["Sign-in times, IP address and basic server logs", "To keep the service secure and stop abuse", "Up to 180 days"],
  ["Contact-page and support messages", "To reply to you", "Until the request is closed, then up to 12 months"],
];

export function PrivacyPage() {
  const c = useCompany();
  return (
    <Doc title="Privacy Policy" intro={`What personal data ${c.name} collects, why, who sees it, and how you stay in control.`}>
      <section>
        <h2>1. Who we are and our role</h2>
        <p>{c.name} ("Virundhu", "we", "us") runs the Virundhu review service for restaurants, cloud kitchens and food businesses.</p>
        <ul>
          <li>For the data of restaurant owners, their teams and visitors to this website, we are the <b>data fiduciary</b> under India's
            Digital Personal Data Protection Act, 2023 (DPDP Act): we decide why and how it is used.</li>
          <li>For guest reviews and guest details that a restaurant brings into Virundhu, the <b>restaurant is the data fiduciary</b> and we
            act as its <b>data processor</b>: we process that data only to provide the service to that restaurant, under our{" "}
            <Link to="/data-processing" className="underline">Data Processing Terms</Link>.</li>
        </ul>
      </section>
      <section>
        <h2>2. What we collect, why, and for how long</h2>
        <div className="mt-3 overflow-x-auto rounded-[14px] border-2 border-line">
          <table className="w-full min-w-[560px] text-left text-[0.95rem]">
            <thead className="bg-cream"><tr><th className="p-3">Personal data</th><th className="p-3">Purpose</th><th className="p-3">Kept for</th></tr></thead>
            <tbody>
              {DATA_ROWS.map(([d, p, k]) => (
                <tr key={d} className="border-t border-line align-top"><td className="p-3">{d}</td><td className="p-3">{p}</td><td className="p-3">{k}</td></tr>
              ))}
            </tbody>
          </table>
        </div>
        <p>We collect only what these purposes need. We don't sell personal data, we don't use it for advertising, and we don't build profiles of guests.</p>
      </section>
      <section>
        <h2>3. Where it comes from</h2>
        <ul>
          <li>From you, when you sign up, use the app or contact us.</li>
          <li>From Google, when you connect your Google Business Profile (your locations and the public reviews on them).</li>
          <li>From files, screenshots or text you upload or paste, for example reviews copied from Zomato, Swiggy, Tripadvisor or Instagram.
            Virundhu never logs in to those platforms for you and never scrapes them.</li>
          <li>From guests, when they use a restaurant's QR feedback page.</li>
        </ul>
      </section>
      <section>
        <h2>4. Consent and the legal basis</h2>
        <p>When you create an account you agree to this policy with a tick box, and we record when you did. We process guest data on the
          restaurant's instructions; guests who use a QR page see a short notice before they send anything, and their name and contact
          details are always optional. You can withdraw consent as easily as you gave it: delete your account in Settings, disconnect Google
          on the Connections page, or write to the Grievance Officer. Withdrawing consent doesn't affect processing that already took place.</p>
      </section>
      <section>
        <h2>5. AI processing</h2>
        <p>Review text is sent to our AI provider (currently OpenAI) only to produce tags, a summary and a reply draft, and to answer Ask
          Virundhu questions. Under the provider's API terms this data isn't used to train its models, and we don't use your data to train
          any AI model either. Numbers on your dashboard are counted by Virundhu, not guessed by the AI. AI drafts can be wrong: you decide
          what gets posted. We don't use AI to make decisions about guests or owners that have legal or similar effects.</p>
      </section>
      <section>
        <h2>6. Google user data</h2>
        <p>If you connect Google, we request access to your Google Business Profile only to read your business locations and their reviews,
          and to post the replies you approve (or auto-pilot replies you switch on). If you sign in with Google, we receive only your name,
          email address and profile picture. We store your Google access encrypted, don't share Google user data with anyone except the
          service providers listed below to run these features, don't use it for advertising, and don't use it to train AI models. You can
          disconnect at any time on the Connections page, which deletes the stored access. Virundhu's use and transfer of information
          received from Google APIs adheres to the{" "}
          <a className="underline" href="https://developers.google.com/terms/api-services-user-data-policy" target="_blank" rel="noreferrer">Google API Services User Data Policy</a>,
          including the Limited Use requirements.</p>
      </section>
      <section>
        <h2>7. Who else handles data for us</h2>
        <p>We share data only with service providers who help us run Virundhu, each bound by a contract and given only what their task needs:</p>
        <ul>
          <li><b>Hostinger</b>: servers and database hosting.</li>
          <li><b>OpenAI</b>: reading reviews and drafting replies.</li>
          <li><b>Dodo Payments</b>: payments, invoices and refunds (acts as the merchant of record).</li>
          <li><b>Google</b>: Google sign-in and the Google reviews you choose to connect.</li>
          <li><b>Email provider</b> and <b>Meta (WhatsApp Business)</b>: delivering alerts and messages you switch on.</li>
        </ul>
        <p>Some of these providers process data outside India, which the DPDP Act allows except to countries the Government restricts. We
          may also disclose data if a law, court or government authority requires it.</p>
      </section>
      <section>
        <h2>8. How we protect it</h2>
        <p>Encrypted connections (HTTPS), one-way hashed passwords, encrypted Google access, strict separation so one restaurant can never see
          another's data (checked by automated tests), limits on repeated sign-in attempts, access logs, regular backups, and payments
          verified directly with the payment provider. See our <Link to="/security" className="underline">Security page</Link>.</p>
        <p>If a personal data breach happens, we will inform the affected people without delay and report it to the Data Protection Board of
          India as the DPDP Act and Rules require, and tell restaurants about any breach affecting their guests' data.</p>
      </section>
      <section>
        <h2>9. Your rights</h2>
        <ul>
          <li><b>Access:</b> see a summary of your data and how it's used. Download everything from Settings → Account and privacy.</li>
          <li><b>Correction and updating:</b> edit your details in Settings, or ask us.</li>
          <li><b>Erasure:</b> Settings → Account and privacy → Delete my restaurant, or ask us. Copies in backups are removed within 30 days.</li>
          <li><b>Withdraw consent</b> at any time, as described in section 4.</li>
          <li><b>Nominate</b> someone to exercise these rights if you die or become unable to.</li>
          <li><b>Grievance redressal:</b> write to our Grievance Officer (section 13). If you're not satisfied with the answer, you can complain
            to the Data Protection Board of India.</li>
          <li><b>Guests</b> can ask the restaurant, or us, to correct or remove feedback they left through a QR page. We'll pass the
            request to the restaurant and act on it.</li>
        </ul>
        <p>We may need to confirm your identity before acting on a request.</p>
      </section>
      <section>
        <h2>10. Children</h2>
        <p>Virundhu is a business service for adults. We don't knowingly collect data from anyone under 18, and owners must be 18 or older. If
          you believe a child has given us data, tell us and we'll delete it.</p>
      </section>
      <section>
        <h2>11. Cookies and your browser</h2>
        <p>We store only what's needed to keep you signed in, in your browser's storage. We don't use advertising, analytics or tracking
          cookies, and we don't share browsing data with anyone.</p>
      </section>
      <section>
        <h2>12. Visitors outside India</h2>
        <p>Virundhu is built for businesses in India and its data is handled under Indian law. If you use it from elsewhere, you can still
          ask to access, correct, delete or move your data, and to object to any use of it, by writing to us.</p>
      </section>
      <section>
        <h2>13. Grievance Officer and contact</h2>
        <ContactLines />
        <p>We acknowledge every complaint or request within 24 hours and resolve it within 15 days, usually much sooner.</p>
      </section>
      <section>
        <h2>14. Changes</h2>
        <p>If we change this policy in a way that matters, we'll show a notice in the app or email you before it takes effect, and update the
          date above.</p>
      </section>
    </Doc>
  );
}

export function TermsPage() {
  const c = useCompany();
  return (
    <Doc title="Terms of Service" intro="The agreement between your business and Virundhu when you use the service. Written to be read.">
      <section><h2>1. The service and who it's for</h2><p>Virundhu helps restaurants and food businesses collect, read, prioritise and reply to
        guest reviews. These terms are a contract between the business that signs up ("you") and {c.name} ("we"). By creating an account
        or using the service you accept them, together with our <Link to="/privacy" className="underline">Privacy Policy</Link> and{" "}
        <Link to="/data-processing" className="underline">Data Processing Terms</Link>. Virundhu is a business service, not a consumer one.</p></section>
      <section><h2>2. Your account</h2><ul>
        <li>You must be at least 18 and authorised to act for the business.</li>
        <li>Keep your password safe and tell us at once if you think someone else used your account. You're responsible for activity under it.</li>
        <li>Give us accurate details and keep them up to date.</li></ul></section>
      <section><h2>3. Trial, plans and payment</h2><ul>
        <li>New accounts get a 14-day free trial with all features. No card is needed.</li>
        <li>Paid plans cover 1, 3, 6, 9 or 12 months and are paid in advance in Indian rupees. The price depends on the number of outlets and
          the length of the plan, and the total you see before paying is the full amount you pay, with any applicable taxes included. There
          are no hidden or extra charges.</li>
        <li>Payments are processed by Dodo Payments, which acts as the merchant of record and issues your invoice.</li>
        <li>Plans don't renew automatically and we never charge you without you starting the payment. When a trial or plan ends, your data
          stays and you can still view it, but adding and replying to reviews pauses until you pay.</li>
        <li>Discount codes have the limits shown with them and can't be exchanged for cash.</li>
        <li>See the <Link to="/refunds" className="underline">Refund and Cancellation Policy</Link>.</li></ul></section>
      <section><h2>4. Your content</h2><ul>
        <li>You keep all rights in the reviews, replies, files and other content you bring into Virundhu ("your content"). You give us a
          limited licence to store, copy and process your content only to provide the service to you. It ends when you delete the content
          or your account.</li>
        <li>Reviews belong to the guests who wrote them. You confirm you have the right to bring each review and each piece of personal data
          into Virundhu, for example because it was posted publicly about your business or a guest gave it to you directly.</li>
        <li>You're the data fiduciary for your guests' personal data. You're responsible for having a lawful reason to use it, and for how
          you contact guests who leave a phone number or email.</li>
        <li>We don't claim ownership of your content, don't publish it anywhere, and don't use it to train AI models.</li></ul></section>
      <section><h2>5. Our content</h2><p>The Virundhu software, website, name, logo and design belong to us. You may use them only as part of the service.
        You may not copy, resell or reverse-engineer the service. If you send us ideas or suggestions, we may use them freely.</p></section>
      <section><h2>6. AI drafts and auto-pilot</h2><p>Tags, summaries and reply drafts are produced by AI and can be wrong or incomplete. You decide
        what to post. If you switch on auto-pilot, you allow Virundhu to post replies to qualifying reviews on your behalf, and you're
        responsible for them as if you had posted them yourself. Auto-pilot never promises refunds or compensation, and you can switch it
        off at any time.</p></section>
      <section><h2>7. Rules you agree to follow</h2><ul>
        <li>Don't post or ask for fake reviews, offer guests rewards for reviews, or ask only happy guests to review you on a public platform.
          Google, Zomato, Swiggy and others forbid this, and it can get your listing penalised.</li>
        <li>Don't harass guests, reply abusively, or share a guest's personal details in a public reply.</li>
        <li>Don't upload anything unlawful, or personal data you have no right to use.</li>
        <li>Don't attack the service, try to reach other businesses' data, overload it, or get around its limits.</li>
        <li>Follow the rules of every platform you use with Virundhu (Google, WhatsApp, Zomato, Swiggy and others).</li></ul></section>
      <section><h2>8. Complaints about content</h2><p>If you believe content in Virundhu uses your personal data or your work without permission,
        tell our Grievance Officer (below). We acknowledge within 24 hours and act within 15 days, which can include removing the content and
        telling the business that uploaded it.</p></section>
      <section><h2>9. Availability and changes to the service</h2><p>We work hard to keep Virundhu running and your data safe, but the service is
        provided "as is" and "as available". Google, AI, payment and messaging providers may change or become unavailable, which can affect
        some features. We may improve or change features; if a change takes away something important you paid for, we'll tell you and you
        can ask for a pro-rata refund.</p></section>
      <section><h2>10. Ending the service</h2><p>You can delete your account at any time from Settings. We may suspend or close accounts that break
        these terms, harm others or don't pay, after telling you where possible. After closure you can ask for an export within 30 days;
        then the data is deleted.</p></section>
      <section><h2>11. Responsibility for claims</h2><p>You agree to cover us against claims caused by your content, your replies, or your breach of
        these terms or of the law. We'll tell you promptly about any such claim.</p></section>
      <section><h2>12. Limits on liability</h2><p>To the extent the law allows, neither side is liable for indirect losses such as lost profit or
        reputation, and our total liability is limited to the amount you paid us in the 12 months before the claim. Nothing in these terms
        limits liability that can't be limited by law.</p></section>
      <section><h2>13. Law and disputes</h2><p>These terms are governed by the laws of India. We'll first try to settle any dispute by talking to
        you. If that fails, courts in Coimbatore, Tamil Nadu have jurisdiction.</p></section>
      <section><h2>14. Changes and contact</h2><p>We'll tell you at least 15 days before important changes to these terms take effect. If you
        don't agree, you can stop using the service and ask for a pro-rata refund of the unused period.</p><ContactLines /></section>
    </Doc>
  );
}

export function DataProcessingPage() {
  const c = useCompany();
  return (
    <Doc title="Data Processing Terms" intro="How Virundhu handles your guests' personal data on your behalf. Part of the Terms of Service.">
      <section><h2>1. Roles</h2><p>For guest reviews and guest details you bring into Virundhu, your business is the <b>data fiduciary</b> and {c.name} is
        your <b>data processor</b> under section 8(2) of India's Digital Personal Data Protection Act, 2023. These terms are the contract
        that section requires.</p></section>
      <section><h2>2. What we process</h2><ul>
        <li><b>Guests:</b> review text, rating, date, platform, the reviewer's public name, and any name, phone or email a guest gives on
          your QR page or that you enter to ask for a review.</li>
        <li><b>Purpose:</b> only to provide Virundhu to you: reading and sorting reviews, drafting replies, alerts, reports, review requests
          and posting replies you approve.</li></ul></section>
      <section><h2>3. Our commitments</h2><ol>
        <li>We process guest data only on your instructions, which are your use and settings of the service.</li>
        <li>We keep it confidential and allow only authorised staff to access it, only when needed to support you.</li>
        <li>We protect it with reasonable security safeguards, including encryption in transit, access controls, separation between
          businesses, logging and backups.</li>
        <li>We use only the sub-processors listed in our <Link to="/privacy" className="underline">Privacy Policy</Link>, under contracts with
          equivalent protections, and we tell you before adding a new one.</li>
        <li>We tell you without undue delay, and within 48 hours at the latest, after we learn of a breach affecting your guests' data, with
          what we know and what we're doing, so you can meet your own reporting duties.</li>
        <li>We help you answer guests who ask to access, correct or erase their data.</li>
        <li>When you delete data or your account, we delete it from the live system at once and from backups within 30 days, unless the law
          requires us to keep it.</li>
        <li>We give you the information you reasonably need to show you're complying with the DPDP Act.</li></ol></section>
      <section><h2>4. Your commitments</h2><ul>
        <li>You have a lawful basis for the guest data you bring in, and you give guests any notice the law requires.</li>
        <li>You only ask guests for reviews if they have agreed to hear from you, and you stop if they ask.</li></ul></section>
      <section><h2>5. Contact</h2><ContactLines /></section>
    </Doc>
  );
}

export function RefundsPage() {
  return (
    <Doc title="Refund and Cancellation Policy" intro="Simple rules, because you try everything free for 14 days first.">
      <section><h2>Free trial</h2><p>Every business gets 14 days free with all features. No card, nothing to cancel.</p></section>
      <section><h2>Cancelling</h2><p>Plans are paid for 1, 3, 6, 9 or 12 months at a time and never renew by themselves, so there's nothing to
        cancel: simply don't renew. You keep using everything until the end of the period you paid for. You can delete your account at any
        time from Settings.</p></section>
      <section><h2>Refunds</h2><ul>
        <li>Charged twice or by mistake: we refund the extra charge in full.</li>
        <li>First paid plan: if you ask within 7 days of paying and haven't found Virundhu useful, we refund it in full.</li>
        <li>If we remove an important feature you paid for, or change these terms and you don't accept the change, we refund the unused part
          of your plan.</li>
        <li>Other payments for a period that has already started aren't refundable.</li>
        <li>Refunds go back to the original payment method through Dodo Payments, usually within 5 to 10 working days of approval.</li></ul></section>
      <section><h2>How to ask</h2><p>Write to us with your registered email and the payment ID. We acknowledge within 24 hours and decide within 7 days.</p><ContactLines /></section>
    </Doc>
  );
}

const SECURITY: { icon: typeof Lock; title: string; body: string }[] = [
  { icon: Lock, title: "Encrypted connections", body: "Every page and API call runs over HTTPS. Browser safety headers stop the app being framed or sniffed." },
  { icon: KeyRound, title: "Passwords never stored", body: "Only a one-way bcrypt hash. Reset links work once, expire in an hour, and sign you out everywhere else." },
  { icon: ShieldCheck, title: "Your restaurant, only yours", body: "Every request is checked against your restaurant. Automated tests prove one restaurant can't see another's reviews." },
  { icon: Server, title: "Encrypted Google access", body: "Your Google connection is stored encrypted and used only for your reviews. Disconnect any time." },
  { icon: UserCheck, title: "Payments verified at the source", body: "Card and UPI details stay with Dodo Payments. A plan turns on only after we confirm the payment with them." },
  { icon: Trash2, title: "Export or delete, any time", body: "Download all your data as a spreadsheet, or delete your restaurant and everything in it, from Settings." },
];

export function SecurityPage() {
  const c = useCompany();
  return (
    <>
      <PageHero title="Security and privacy" intro="Your guests trust you with their words. Here's how we look after them." />
      <section className="mx-auto max-w-7xl px-5 py-16 sm:px-8 lg:py-20">
        <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
          {SECURITY.map((s) => (
            <div key={s.title} className="rounded-[20px] border-2 border-line bg-white p-6">
              <s.icon className="h-7 w-7 text-night" strokeWidth={1.7} />
              <h2 className="mt-4 text-xl font-bold">{s.title}</h2>
              <p className="mt-2 text-ink-soft">{s.body}</p>
            </div>
          ))}
        </div>
        <div className="mt-10 grid gap-5 md:grid-cols-2">
          <div className="rounded-[20px] bg-night p-6 text-jasmine">
            <h2 className="text-xl font-bold">AI with limits</h2>
            <p className="mt-2 text-mist">Review text goes to our AI provider only to read it and draft a reply, and isn't used to train its models. Every number you
              see is counted by Virundhu, not guessed by the AI.</p>
          </div>
          <div className="rounded-[20px] border-2 border-line bg-white p-6">
            <h2 className="text-xl font-bold">Found a problem?</h2>
            <p className="mt-2 text-ink-soft">If you think you've found a security issue, please tell us privately{c.email ? <> at <a className="underline" href={`mailto:${c.email}`}>{c.email}</a></> : null} and we'll fix it fast.
              Read the full <Link to="/privacy" className="underline">Privacy Policy</Link>.</p>
          </div>
        </div>
      </section>
    </>
  );
}
