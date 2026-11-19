import { CalendarCheck, Clock, MessageCircle } from "lucide-react";
import { useState, type FormEvent } from "react";
import { Link } from "react-router-dom";
import { PageHero } from "@/components/site/SiteLayout";
import { Button, buttonVariants } from "@/components/ui/button";
import { Spinner } from "@/components/ui/misc";
import { usePublicConfig } from "@/hooks/usePublicConfig";
import { errorMessage, siteApi } from "@/services/api";

const EMPTY = { name: "", restaurant: "", phone: "", email: "", city: "", outlets: "", message: "", website: "", meet_mode: "meet" };
const MODES: [string, string][] = [["meet", "Google Meet"], ["zoom", "Zoom"], ["teams", "Microsoft Teams"], ["phone", "Phone call"], ["in_person", "In person, Coimbatore"]];

function Input({ label, ...props }: React.InputHTMLAttributes<HTMLInputElement> & { label: string }) {
  return (
    <label className="block">
      <span className="text-sm font-semibold">{label}</span>
      <input {...props} className="mt-1.5 w-full rounded-[12px] border-2 border-line bg-white px-3.5 py-3 focus:border-night focus:outline-none" />
    </label>
  );
}

export default function Contact() {
  const [form, setForm] = useState(EMPTY);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [sent, setSent] = useState(false);
  const company = usePublicConfig().data?.company;
  const set = (k: keyof typeof EMPTY) => (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => setForm({ ...form, [k]: e.target.value });

  async function submit(e: FormEvent) {
    e.preventDefault();
    if (form.name.trim().length < 2 || form.restaurant.trim().length < 2) { setError("Please give your name and your restaurant's name."); return; }
    if (!/^\S+@\S+\.\S+$/.test(form.email.trim())) { setError("Please give your email. Our demo agent sends you times to pick from within a minute."); return; }
    setBusy(true); setError(null);
    try {
      await siteApi.contact({ ...form, outlets: form.outlets ? Number(form.outlets) : null });
      setSent(true);
    } catch (err) { setError(errorMessage(err)); } finally { setBusy(false); }
  }

  return (
    <>
      <PageHero title="Talk to us" intro="Want a demo with your own reviews? Send this and within a minute Nila, our demo agent, emails you times to pick from. One tap books it." />
      <section className="mx-auto grid max-w-7xl gap-10 px-5 py-16 sm:px-8 lg:grid-cols-[1.2fr_0.8fr] lg:py-20">
        <div className="rounded-[24px] border-2 border-night bg-white p-6 shadow-[8px_8px_0_#0c3b2e] sm:p-8">
          {sent ? (
            <div className="py-10 text-center">
              <CalendarCheck className="mx-auto h-12 w-12 text-leaf" />
              <h2 className="mt-4 text-3xl font-bold">Check your inbox in a minute</h2>
              <p className="mt-2 text-ink-soft">Nila, our demo agent, is emailing you times to choose from. Tap one and it's booked, with a calendar invite. Meanwhile you can start the free trial.</p>
              <Link to="/register" className={`${buttonVariants({ size: "lg" })} mt-6`}>Start free trial</Link>
            </div>
          ) : (
            <form onSubmit={submit} className="space-y-4" noValidate>
              <div className="grid gap-4 sm:grid-cols-2">
                <Input label="Your name" value={form.name} onChange={set("name")} autoComplete="name" />
                <Input label="Restaurant or brand" value={form.restaurant} onChange={set("restaurant")} />
                <Input label="Phone (WhatsApp)" value={form.phone} onChange={set("phone")} inputMode="tel" autoComplete="tel" placeholder="+91" />
                <Input label="Email (we send the demo times here)" value={form.email} onChange={set("email")} type="email" autoComplete="email" required />
                <Input label="City" value={form.city} onChange={set("city")} placeholder="Coimbatore" />
                <Input label="Number of outlets" value={form.outlets} onChange={set("outlets")} inputMode="numeric" />
              </div>
              <fieldset>
                <legend className="text-sm font-semibold">How would you like to meet?</legend>
                <div className="mt-2 flex flex-wrap gap-2">
                  {MODES.map(([k, label]) => (
                    <button key={k} type="button" aria-pressed={form.meet_mode === k} onClick={() => setForm({ ...form, meet_mode: k })}
                      className={`rounded-full border-2 px-4 py-2 text-sm font-semibold transition-colors ${form.meet_mode === k ? "border-night bg-night text-jasmine" : "border-line bg-white hover:border-night"}`}>
                      {label}
                    </button>
                  ))}
                </div>
              </fieldset>
              <label className="block">
                <span className="text-sm font-semibold">Anything you'd like us to know? (optional)</span>
                <textarea value={form.message} onChange={set("message")} rows={4} maxLength={2000}
                  className="mt-1.5 w-full resize-none rounded-[12px] border-2 border-line bg-white p-3.5 focus:border-night focus:outline-none" />
              </label>
              <input tabIndex={-1} autoComplete="off" aria-hidden="true" value={form.website} onChange={set("website")} className="absolute -left-[9999px] h-0 w-0 opacity-0" />
              {error ? <p role="alert" className="rounded-[12px] bg-chilli-soft px-3.5 py-2.5 text-sm font-semibold text-[#b32f12]">{error}</p> : null}
              <p className="text-xs text-ink-soft">We use these details only to reply to you. See our <Link to="/privacy" className="underline">Privacy Policy</Link>.</p>
              <Button type="submit" size="lg" className="w-full sm:w-auto" disabled={busy}>{busy ? <><Spinner /> Sending...</> : "Request a demo"}</Button>
            </form>
          )}
        </div>
        <aside className="space-y-5">
          {company ? (
            <div className="rounded-[20px] bg-night p-6 text-jasmine">
              <h3 className="text-xl font-bold">Reach us directly</h3>
              <dl className="mt-4 space-y-3">
                {company.email ? <div><dt className="text-sm text-mist">Questions and support</dt><dd><a className="font-semibold underline" href={`mailto:${company.email}`}>{company.email}</a></dd></div> : null}
                {company.demo_email ? <div><dt className="text-sm text-mist">Book a demo</dt><dd><a className="font-semibold underline" href={`mailto:${company.demo_email}`}>{company.demo_email}</a></dd></div> : null}
                {company.phone ? <div><dt className="text-sm text-mist">WhatsApp</dt><dd><a className="font-semibold underline" href={`https://wa.me/${company.phone.replace(/[^0-9]/g, "")}`} target="_blank" rel="noreferrer">{company.phone}</a></dd></div> : null}
                {company.address ? <div><dt className="text-sm text-mist">Office</dt><dd className="font-semibold">{company.parent ? `${company.parent}, ` : ""}{company.address}</dd></div> : null}
                <div><dt className="text-sm text-mist">Hours</dt><dd className="font-semibold">Monday to Saturday, 10 am to 7 pm IST</dd></div>
              </dl>
              <p className="mt-4 text-sm text-mist">Our AI agents reply within minutes, day and night.</p>
            </div>
          ) : null}
          {[
            { icon: Clock, title: "10 minutes, your own reviews", body: "We load a few of your real Google, Zomato or Swiggy reviews and show you what Virundhu does with them." },
            { icon: MessageCircle, title: "In Tamil or English", body: "Whatever you're comfortable with. We'll call or message on WhatsApp, as you prefer." },
            { icon: CalendarCheck, title: "Or just try it", body: "The 14-day trial needs no card. Most owners are set up in two minutes." },
          ].map((c) => (
            <div key={c.title} className="flex gap-4 rounded-[20px] border-2 border-line bg-white p-5">
              <c.icon className="h-7 w-7 shrink-0 text-night" strokeWidth={1.7} />
              <div><h3 className="text-xl font-bold">{c.title}</h3><p className="mt-1 text-ink-soft">{c.body}</p></div>
            </div>
          ))}
        </aside>
      </section>
    </>
  );
}
