import { CalendarCheck, Clock, MessageCircle } from "lucide-react";
import { useState, type FormEvent } from "react";
import { Link } from "react-router-dom";
import { PageHero } from "@/components/site/SiteLayout";
import { Button, buttonVariants } from "@/components/ui/button";
import { Spinner } from "@/components/ui/misc";
import { usePublicConfig } from "@/hooks/usePublicConfig";
import { errorMessage, siteApi } from "@/services/api";

const EMPTY = { name: "", restaurant: "", phone: "", email: "", city: "", outlets: "", message: "", website: "" };

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
    if (!form.phone.trim() && !form.email.includes("@")) { setError("Give us a phone number or an email so we can reach you."); return; }
    setBusy(true); setError(null);
    try {
      await siteApi.contact({ ...form, outlets: form.outlets ? Number(form.outlets) : null });
      setSent(true);
    } catch (err) { setError(errorMessage(err)); } finally { setBusy(false); }
  }

  return (
    <>
      <PageHero title="Talk to us" intro="Want a 10-minute demo with your own reviews? Tell us about your restaurant and we'll get back to you within one working day." />
      <section className="mx-auto grid max-w-7xl gap-10 px-5 py-16 sm:px-8 lg:grid-cols-[1.2fr_0.8fr] lg:py-20">
        <div className="rounded-[24px] border-2 border-night bg-white p-6 shadow-[8px_8px_0_#0c3b2e] sm:p-8">
          {sent ? (
            <div className="py-10 text-center">
              <CalendarCheck className="mx-auto h-12 w-12 text-leaf" />
              <h2 className="mt-4 text-3xl font-bold">Thank you, we'll be in touch</h2>
              <p className="mt-2 text-ink-soft">We usually reply within one working day. Meanwhile you can start the free trial and try it yourself.</p>
              <Link to="/register" className={`${buttonVariants({ size: "lg" })} mt-6`}>Start free trial</Link>
            </div>
          ) : (
            <form onSubmit={submit} className="space-y-4" noValidate>
              <div className="grid gap-4 sm:grid-cols-2">
                <Input label="Your name" value={form.name} onChange={set("name")} autoComplete="name" />
                <Input label="Restaurant or brand" value={form.restaurant} onChange={set("restaurant")} />
                <Input label="Phone (WhatsApp)" value={form.phone} onChange={set("phone")} inputMode="tel" autoComplete="tel" placeholder="+91" />
                <Input label="Email" value={form.email} onChange={set("email")} type="email" autoComplete="email" />
                <Input label="City" value={form.city} onChange={set("city")} placeholder="Coimbatore" />
                <Input label="Number of outlets" value={form.outlets} onChange={set("outlets")} inputMode="numeric" />
              </div>
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
          {company?.email || company?.phone ? (
            <div className="rounded-[20px] bg-night p-5 text-jasmine">
              <h3 className="text-xl font-bold">Reach us directly</h3>
              {company.email ? <p className="mt-2"><a className="underline" href={`mailto:${company.email}`}>{company.email}</a></p> : null}
              {company.phone ? <p className="mt-1"><a className="underline" href={`https://wa.me/${company.phone.replace(/[^0-9]/g, "")}`} target="_blank" rel="noreferrer">WhatsApp {company.phone}</a></p> : null}
              {company.address ? <p className="mt-1 text-mist">{company.address}</p> : null}
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
