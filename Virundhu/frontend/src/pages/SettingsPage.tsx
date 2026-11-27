import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Download, Handshake, KeyRound, MapPin, Plus, Trash2, Upload } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";
import { useState, type FormEvent } from "react";
import { toast } from "sonner";
import { Button, buttonVariants } from "@/components/ui/button";
import { Field } from "@/components/ui/input";
import { Skeleton, Spinner } from "@/components/ui/misc";
import { cn } from "@/lib/utils";
import { TwoStepCard } from "@/components/security/TwoStepCard";
import { useWorkspace } from "@/lib/workspace";
import { accountApi, appApi, errorMessage } from "@/services/api";
import type { OrgSettings, Outlet, OutletInput } from "@/types";

const TABS = [["restaurant", "Restaurant"], ["outlets", "Outlets"], ["account", "Account and privacy"]] as const;
type Tab = (typeof TABS)[number][0];

function RestaurantTab() {
  const { data } = useQuery({ queryKey: ["settings"], queryFn: appApi.settings });
  if (!data) return <Skeleton className="h-[380px]" />;
  return <RestaurantForm initial={data} />;
}

function RestaurantForm({ initial }: { initial: OrgSettings }) {
  const qc = useQueryClient();
  const [form, setForm] = useState<OrgSettings>(initial);
  const [emails, setEmails] = useState(initial.alert_emails.join(", "));
  const [busy, setBusy] = useState(false);

  async function save(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    try {
      const alert_emails = emails.split(/[,\s]+/).map((s) => s.trim()).filter(Boolean);
      await appApi.saveSettings({
        name: form.name, city: form.city, reply_tone: form.reply_tone, reply_signature: form.reply_signature, alert_emails,
        owner_phone: form.owner_phone ?? "", business_type: form.business_type ?? "", cuisine: form.cuisine ?? "",
        gstin: (form.gstin ?? "").toUpperCase(), head_office: form.head_office ?? "", outlets_declared: form.outlets_declared || undefined,
      });
      toast.success("Settings saved");
      void qc.invalidateQueries({ queryKey: ["settings"] });
    } catch (err) { toast.error(errorMessage(err)); } finally { setBusy(false); }
  }

  return (
    <form onSubmit={save} className="space-y-5 rounded-[20px] border-2 border-line bg-white p-5 sm:p-6">
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <Field id="s-name" label="Restaurant or brand name" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
        <Field id="s-city" label="City" value={form.city ?? ""} onChange={(e) => setForm({ ...form, city: e.target.value })} />
        <Field id="s-phone" label="Owner mobile (WhatsApp)" value={form.owner_phone ?? ""} onChange={(e) => setForm({ ...form, owner_phone: e.target.value })} />
        <Field id="s-outlets" label="How many outlets do you run in total?" type="number" min={1} value={form.outlets_declared ?? ""} onChange={(e) => setForm({ ...form, outlets_declared: Number(e.target.value) || null })} />
        <Field id="s-cuisine" label="Cuisine" placeholder="Biryani, South Indian" value={form.cuisine ?? ""} onChange={(e) => setForm({ ...form, cuisine: e.target.value })} />
        <Field id="s-gstin" label="GSTIN (optional, for your invoice)" value={form.gstin ?? ""} onChange={(e) => setForm({ ...form, gstin: e.target.value })} />
        <Field id="s-ho" label="Head office address" className="sm:col-span-2" value={form.head_office ?? ""} onChange={(e) => setForm({ ...form, head_office: e.target.value })} />
      </div>
      <div>
        <p className="mb-1.5 text-sm font-semibold">Type of business</p>
        <div className="flex flex-wrap gap-2">
          {([["dine_in", "Dine-in"], ["cloud_kitchen", "Cloud kitchen"], ["both", "Both"]] as const).map(([k, label]) => (
            <button key={k} type="button" onClick={() => setForm({ ...form, business_type: k })}
              className={cn("rounded-full px-4 py-2 text-sm font-semibold cursor-pointer", form.business_type === k ? "bg-night text-jasmine" : "bg-jasmine-2 text-ink-soft")}>{label}</button>
          ))}
        </div>
      </div>
      <div>
        <p className="mb-1.5 text-sm font-semibold">Tone of reply drafts</p>
        <div className="flex flex-wrap gap-2">
          {(["warm", "professional", "short"] as const).map((t) => (
            <button key={t} type="button" onClick={() => setForm({ ...form, reply_tone: t })}
              className={cn("rounded-full px-4 py-2 text-sm font-semibold capitalize cursor-pointer", form.reply_tone === t ? "bg-night text-jasmine" : "bg-jasmine-2 text-ink-soft")}>{t}</button>
          ))}
        </div>
      </div>
      <Field id="s-sign" label="Sign replies as" hint='For example "- Team Vaasam"' value={form.reply_signature ?? ""} onChange={(e) => setForm({ ...form, reply_signature: e.target.value })} />
      <Field id="s-alerts" label="Extra emails for urgent alerts" hint="Owners and managers always get alerts. Add more emails separated by commas, e.g. your outlet managers."
        value={emails} onChange={(e) => setEmails(e.target.value)} />
      <div className="flex flex-wrap items-center justify-between gap-3 border-t-2 border-jasmine-2 pt-4">
        <p className="text-sm text-ink-soft">Plan: <b className="capitalize text-ink">{form.plan}</b>{form.trial_ends_at && form.plan === "trial" ? `, trial ends ${new Date(form.trial_ends_at).toLocaleDateString("en-IN", { day: "numeric", month: "short" })}` : ""}</p>
        <Button type="submit" disabled={busy}>{busy ? <><Spinner /> Saving...</> : "Save changes"}</Button>
      </div>
    </form>
  );
}

const EMPTY_OUTLET: OutletInput = {
  name: "", area: "", city: "", district: "", address: "", pincode: "", phone: "", manager_name: "", manager_phone: "",
  manager_email: "", google_maps_url: "", zomato_url: "", swiggy_url: "",
};

function OutletForm({ initial, onDone }: { initial?: Outlet; onDone: () => void }) {
  const qc = useQueryClient();
  const [f, setF] = useState<OutletInput>(() => ({ ...EMPTY_OUTLET, ...Object.fromEntries(Object.entries(initial ?? {}).map(([k, v]) => [k, v ?? ""])) }) as OutletInput);
  const [busy, setBusy] = useState(false);
  const set = (k: keyof OutletInput) => (e: React.ChangeEvent<HTMLInputElement>) => setF({ ...f, [k]: e.target.value });
  const v = (k: keyof OutletInput) => (f[k] as string | null | undefined) ?? "";

  async function save(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    const body = { ...f, name: f.name.trim() };
    try {
      if (initial) await appApi.updateOutlet(initial.id, body); else await appApi.addOutlet(body);
      toast.success(initial ? "Outlet saved" : "Outlet added");
      void qc.invalidateQueries({ queryKey: ["outlets"] });
      void qc.invalidateQueries({ queryKey: ["overview"] });
      onDone();
    } catch (err) { toast.error(errorMessage(err)); } finally { setBusy(false); }
  }

  return (
    <form onSubmit={save} className="space-y-5 rounded-[20px] border-2 border-line bg-white p-5 sm:p-6">
      <h2 className="font-display text-xl font-bold">{initial ? `Edit ${initial.name}` : "Add an outlet"}</h2>
      <fieldset className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <legend className="mb-2 font-semibold">Where it is</legend>
        <Field id="o-name" label="Outlet name" placeholder="RS Puram" value={v("name")} onChange={set("name")} />
        <Field id="o-area" label="Area" placeholder="DB Road" value={v("area")} onChange={set("area")} />
        <Field id="o-city" label="City" placeholder="Coimbatore" value={v("city")} onChange={set("city")} />
        <Field id="o-district" label="District" placeholder="Coimbatore" value={v("district")} onChange={set("district")} />
        <Field id="o-address" label="Full address" value={v("address")} onChange={set("address")} />
        <Field id="o-pin" label="Pincode" inputMode="numeric" placeholder="641002" value={v("pincode")} onChange={set("pincode")} />
        <Field id="o-phone" label="Outlet phone" hint="Used in the polite reply to unhappy guests." value={v("phone")} onChange={set("phone")} />
      </fieldset>
      <fieldset className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <legend className="mb-2 font-semibold">Outlet manager</legend>
        <Field id="o-mname" label="Name" value={v("manager_name")} onChange={set("manager_name")} />
        <Field id="o-mphone" label="Mobile (WhatsApp)" value={v("manager_phone")} onChange={set("manager_phone")} />
        <Field id="o-memail" label="Email" type="email" value={v("manager_email")} onChange={set("manager_email")} />
        <p className="text-sm text-ink-soft sm:col-span-3">Urgent complaints about this outlet go straight to its manager too.</p>
      </fieldset>
      <fieldset className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <legend className="mb-2 font-semibold">Listing links (optional)</legend>
        <Field id="o-gmap" label="Google Maps link" placeholder="https://" value={v("google_maps_url")} onChange={set("google_maps_url")} />
        <Field id="o-zom" label="Zomato page" placeholder="https://www.zomato.com/..." value={v("zomato_url")} onChange={set("zomato_url")} />
        <Field id="o-swg" label="Swiggy page" placeholder="https://www.swiggy.com/..." value={v("swiggy_url")} onChange={set("swiggy_url")} />
      </fieldset>
      <div className="flex flex-wrap gap-3">
        <Button type="submit" disabled={busy || f.name.trim().length < 2}>{busy ? <Spinner /> : initial ? null : <Plus className="h-4 w-4" />} {initial ? "Save outlet" : "Add outlet"}</Button>
        {initial ? <Button type="button" variant="ghost" onClick={onDone}>Cancel</Button> : null}
      </div>
    </form>
  );
}

async function downloadQr(url: string, name: string) {
  const QRCode = (await import("qrcode")).default;
  const data = await QRCode.toDataURL(url, { width: 640, margin: 2, color: { dark: "#11132A", light: "#FFFFFF" } });
  const a = document.createElement("a");
  a.href = data; a.download = `virundhu-qr-${name.toLowerCase().replace(/[^a-z0-9]+/g, "-")}.png`; a.click();
}

function OutletUpload() {
  const qc = useQueryClient();
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<{ added: string[]; updated: string[]; skipped: string[] } | null>(null);

  function template() {
    const csv = "name,area,city,district,address,pincode,phone,manager_name,manager_phone,manager_email,google_maps_url,zomato_url,swiggy_url\n"
      + "RS Puram,DB Road,Coimbatore,Coimbatore,12 DB Road,641002,0422 2541234,Ravi,98765 00001,ravi@example.com,,,\n";
    const a = document.createElement("a");
    a.href = URL.createObjectURL(new Blob(["\ufeff" + csv], { type: "text/csv" }));
    a.download = "virundhu-outlets-template.csv"; a.click();
  }

  async function send(f: File | undefined) {
    if (!f) return;
    setBusy(true);
    try {
      const r = await appApi.importOutlets(f);
      setResult(r);
      toast.success(`${r.added.length} added, ${r.updated.length} updated`);
      void qc.invalidateQueries({ queryKey: ["outlets"] });
    } catch (err) { toast.error(errorMessage(err)); } finally { setBusy(false); }
  }

  return (
    <div className="mt-5 rounded-[16px] border-2 border-dashed border-ink/20 p-4">
      <p className="font-semibold">Many outlets? Upload them all at once</p>
      <p className="text-sm text-ink-soft">One row per outlet in Excel or CSV. Outlets with the same name are updated, not added twice.</p>
      <div className="mt-3 flex flex-wrap gap-2">
        <label className={cn(buttonVariants({ size: "sm" }), "cursor-pointer")}>
          {busy ? <Spinner /> : <Upload className="h-4 w-4" />} Upload outlets
          <input type="file" accept=".csv,.xlsx,.xls" className="sr-only" onChange={(e) => { void send(e.target.files?.[0]); e.target.value = ""; }} />
        </label>
        <Button size="sm" variant="outline" onClick={template}><Download className="h-4 w-4" /> Template</Button>
      </div>
      {result?.skipped.length ? (
        <ul className="mt-3 space-y-1 text-sm text-chilli">{result.skipped.slice(0, 8).map((x) => <li key={x}>{x}</li>)}</ul>
      ) : null}
    </div>
  );
}

function OutletsTab() {
  const qc = useQueryClient();
  const { data, isLoading } = useQuery({ queryKey: ["outlets"], queryFn: appApi.outlets });
  const [editing, setEditing] = useState<Outlet | null>(null);
  const [formKey, setFormKey] = useState(0); // a fresh, empty form after each outlet is added
  const groups = new Map<string, Outlet[]>();
  for (const o of data ?? []) {
    const key = o.district || o.city || "District not set";
    groups.set(key, [...(groups.get(key) ?? []), o]);
  }

  async function remove(o: Outlet) {
    if (!window.confirm(`Hide ${o.name}? Its old reviews stay in your reports.`)) return;
    try { await appApi.removeOutlet(o.id); toast.success("Outlet hidden"); void qc.invalidateQueries({ queryKey: ["outlets"] }); }
    catch (err) { toast.error(errorMessage(err)); }
  }

  return (
    <div className="grid grid-cols-1 gap-5 xl:grid-cols-[1fr_1.2fr]">
      <div className="rounded-[20px] border-2 border-line bg-white p-5 sm:p-6">
        <h2 className="font-display text-xl font-bold">Your outlets{data ? ` (${data.length})` : ""}</h2>
        <p className="mt-1 text-sm text-ink-soft">Each outlet has its own QR code, so guest feedback is tagged to the right branch.</p>
        <OutletUpload />
        {isLoading ? <Skeleton className="mt-3 h-24" /> : null}
        {[...groups.entries()].map(([district, list]) => (
          <section key={district} className="mt-4">
            <h3 className="text-sm font-semibold text-ink-soft">{district} · {list.length} outlet{list.length === 1 ? "" : "s"}</h3>
            <ul className="mt-2 space-y-2">
              {list.map((o) => (
                <li key={o.id} className="rounded-[14px] bg-jasmine px-4 py-3">
                  <div className="flex items-start gap-3">
                    <MapPin className="mt-1 h-5 w-5 shrink-0 text-chilli" />
                    <div className="min-w-0 flex-1">
                      <p className="font-semibold">{o.name}</p>
                      <p className="text-sm text-ink-soft">{[o.area, o.city, o.pincode].filter(Boolean).join(", ") || "Add the address"}</p>
                      <p className="text-sm text-ink-soft">{o.manager_name ? `Manager: ${o.manager_name}${o.manager_phone ? `, ${o.manager_phone}` : ""}` : "No manager set"}</p>
                      <p className="text-sm">{o.on_google_maps ? <span className="font-semibold text-[#16784a]">On Google Maps</span> : <span className="text-ink-soft">Not linked to Google Maps yet: Edit → paste the outlet's Google Maps link</span>}</p>
                    </div>
                  </div>
                  {o.map_embed_url ? <iframe title={`Map of ${o.name}`} src={o.map_embed_url} loading="lazy" referrerPolicy="no-referrer-when-downgrade" className="mt-2 ml-8 h-48 w-[calc(100%-2rem)] rounded-[12px] border-2 border-line" /> : null}
                  <div className="mt-2 flex flex-wrap gap-2 pl-8 text-sm">
                    <button type="button" onClick={() => setEditing(o)} className="rounded-[10px] bg-white px-2.5 py-1.5 font-semibold cursor-pointer">Edit</button>
                    {o.feedback_url ? <button type="button" onClick={() => void downloadQr(o.feedback_url as string, o.name)} className="inline-flex items-center gap-1 rounded-[10px] bg-white px-2.5 py-1.5 font-semibold cursor-pointer"><Download className="h-3.5 w-3.5" /> QR code</button> : null}
                    {o.directions_url ? <a href={o.directions_url} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 rounded-[10px] bg-white px-2.5 py-1.5 font-semibold">{o.on_google_maps ? "Open in Google Maps" : "Directions"}</a> : null}
                    {o.feedback_url ? <button type="button" onClick={() => void copyWidget(o.feedback_url as string)} title="Copies a code to paste into your own website, which shows your reviews and branch directions there" className="rounded-[10px] bg-white px-2.5 py-1.5 font-semibold cursor-pointer">Copy review widget for your website</button> : null}
                    {(data?.length ?? 0) > 1 ? <button type="button" onClick={() => void remove(o)} className="rounded-[10px] px-2.5 py-1.5 font-semibold text-chilli cursor-pointer">Hide</button> : null}
                  </div>
                </li>
              ))}
            </ul>
          </section>
        ))}
      </div>
      {editing ? <OutletForm key={editing.id} initial={editing} onDone={() => setEditing(null)} /> : <OutletForm key={`new-${formKey}`} onDone={() => setFormKey((k) => k + 1)} />}
    </div>
  );
}

/** Restaurants that use a PR or reputation agency: give the agency its own login to this restaurant. */
function AgencyAccess() {
  const qc = useQueryClient();
  const { data } = useQuery({ queryKey: ["team"], queryFn: appApi.team });
  const [email, setEmail] = useState("");
  const [busy, setBusy] = useState(false);
  const people = (data?.members ?? []).filter((m) => !m.is_you);
  async function invite(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    try {
      const inv = await appApi.invite(email.trim(), "manager", null);
      toast.success(`Invite sent to ${inv.email}. It works for 7 days.`);
      setEmail("");
      void qc.invalidateQueries({ queryKey: ["team"] });
    } catch (err) { toast.error(errorMessage(err)); } finally { setBusy(false); }
  }
  async function remove(id: number) {
    try { await appApi.removeMember(id); void qc.invalidateQueries({ queryKey: ["team"] }); toast.success("Access removed"); }
    catch (err) { toast.error(errorMessage(err)); }
  }
  return (
    <section className="rounded-[20px] border-2 border-line bg-white p-5 sm:p-6" aria-labelledby="agency-access">
      <h2 id="agency-access" className="flex items-center gap-2 font-display text-xl font-bold"><Handshake className="h-5 w-5" /> Your agency or manager</h2>
      <p className="mt-1 max-w-2xl text-sm text-ink-soft">
        Does a PR agency or a manager reply to your reviews? Invite them by email. They reply and see the numbers for this
        restaurant only; they can't change your plan, billing or these settings. Remove them here any time.
      </p>
      <form onSubmit={invite} className="mt-4 flex flex-wrap gap-3">
        <label className="min-w-[240px] flex-1"><span className="sr-only">Their email</span>
          <input type="email" required value={email} onChange={(e) => setEmail(e.target.value)} placeholder="name@agency.com" maxLength={160}
            className="h-11 w-full rounded-full border-2 border-line px-4 focus:border-night focus:outline-none" />
        </label>
        <Button type="submit" variant="dark" disabled={busy || !email.includes("@")}>{busy ? <Spinner /> : null} Send invite</Button>
      </form>
      {people.length || data?.invitations.length ? (
        <ul className="mt-4 divide-y divide-line text-sm">
          {people.map((m) => (
            <li key={m.membership_id} className="flex items-center justify-between gap-3 py-2">
              <span><b>{m.full_name}</b> <span className="text-ink-soft">{m.email}</span></span>
              <button type="button" onClick={() => void remove(m.membership_id)} className="cursor-pointer font-semibold text-[#b32f12] hover:underline">Remove</button>
            </li>
          ))}
          {data?.invitations.map((i) => (
            <li key={`i${i.id}`} className="flex items-center justify-between gap-3 py-2">
              <span>{i.email} <span className="text-ink-soft">invited, not joined yet</span></span>
              <button type="button" onClick={() => void appApi.cancelInvite(i.id).then(() => qc.invalidateQueries({ queryKey: ["team"] }))} className="cursor-pointer font-semibold text-ink-soft hover:underline">Cancel</button>
            </li>
          ))}
        </ul>
      ) : null}
    </section>
  );
}

function AccountTab() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [busy, setBusy] = useState<"pw" | "export" | "delete" | null>(null);
  const [confirmName, setConfirmName] = useState("");
  const [delPw, setDelPw] = useState("");
  const orgName = user?.organization?.name ?? "";

  async function changePw(e: FormEvent) {
    e.preventDefault();
    if (next.length < 8) { toast.error("Use at least 8 characters for the new password."); return; }
    setBusy("pw");
    try { const r = await accountApi.changePassword(current, next); toast.success(r.message); setCurrent(""); setNext(""); }
    catch (err) { toast.error(errorMessage(err)); } finally { setBusy(null); }
  }
  async function signOutAll() {
    if (!window.confirm("Sign out of Virundhu on every phone and computer, this one included?")) return;
    try { await accountApi.signOutEverywhere(); } catch (err) { toast.error(errorMessage(err)); return; }
    await logout();
    navigate("/login", { replace: true });
  }
  async function exportAll() {
    setBusy("export");
    try {
      const blob = await accountApi.exportCsv();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url; a.download = `virundhu-${user?.organization?.slug ?? "data"}.csv`; a.click();
      URL.revokeObjectURL(url);
    } catch (err) { toast.error(errorMessage(err)); } finally { setBusy(null); }
  }
  async function deleteAll(e: FormEvent) {
    e.preventDefault();
    setBusy("delete");
    try {
      await accountApi.deleteAll(confirmName, delPw);
      await logout();
      navigate("/account-deleted", { replace: true });
    } catch (err) { toast.error(errorMessage(err)); setBusy(null); }
  }

  return (
    <div className="space-y-5">
      <form onSubmit={changePw} className="space-y-4 rounded-[20px] border-2 border-line bg-white p-5 sm:p-6">
        <h2 className="flex items-center gap-2 font-display text-xl font-bold"><KeyRound className="h-5 w-5" /> Change password</h2>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <Field id="cur-pw" label="Current password" type="password" autoComplete="current-password" hint="Leave empty if you signed up with Google." value={current} onChange={(e) => setCurrent(e.target.value)} />
          <Field id="new-pw" label="New password" type="password" autoComplete="new-password" hint="At least 8 characters. Not a common password, and not your name or email." value={next} onChange={(e) => setNext(e.target.value)} />
        </div>
        <p className="text-sm text-ink-soft">For safety, every other device is signed out the moment you change it.</p>
        <div className="flex flex-wrap items-center gap-3">
          <Button type="submit" variant="dark" disabled={busy !== null}>{busy === "pw" ? <Spinner /> : null} Change password</Button>
          <button type="button" onClick={() => void signOutAll()} className="cursor-pointer text-sm font-semibold text-[#b32f12] hover:underline">Lost a phone? Sign out of every device</button>
        </div>
      </form>

      <TwoStepCard />

      {user?.role === "owner" ? <AgencyAccess /> : null}

      <section className="rounded-[20px] border-2 border-line bg-white p-5 sm:p-6">
        <h2 className="flex items-center gap-2 font-display text-xl font-bold"><Download className="h-5 w-5" /> Download all my data</h2>
        <p className="mt-1 max-w-2xl text-ink-soft">Every review with its tags, summary, reply draft and status, as a spreadsheet that opens in Excel (Tamil text included).</p>
        <Button className="mt-4" variant="outline" onClick={exportAll} disabled={busy !== null}>{busy === "export" ? <Spinner /> : <Download className="h-4 w-4" />} Download CSV</Button>
      </section>

      <form onSubmit={deleteAll} className="space-y-4 rounded-[20px] border-2 border-chilli/40 bg-chilli-soft/40 p-5 sm:p-6">
        <h2 className="flex items-center gap-2 font-display text-xl font-bold text-[#b32f12]"><Trash2 className="h-5 w-5" /> Delete my restaurant</h2>
        <p className="max-w-2xl">This deletes <b>{orgName}</b>, every review, reply, setting and login, straight away. It can't be undone. Download your data first if you want a copy.</p>
        <DeleteMoneyNote />
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <Field id="del-name" label={`Type "${orgName}" to confirm`} value={confirmName} onChange={(e) => setConfirmName(e.target.value)} />
          <Field id="del-pw" label="Your password" type="password" autoComplete="current-password" hint="Leave empty if you signed up with Google." value={delPw} onChange={(e) => setDelPw(e.target.value)} />
        </div>
        <Button type="submit" className="bg-chilli text-white shadow-none hover:bg-[#e54a2b]" disabled={busy !== null || confirmName.trim().toLowerCase() !== orgName.trim().toLowerCase()}>
          {busy === "delete" ? <Spinner /> : <Trash2 className="h-4 w-4" />} Delete everything
        </Button>
      </form>
    </div>
  );
}

async function copyWidget(feedbackUrl: string) {
  const token = feedbackUrl.split("/f/")[1]?.split("?")[0];
  const code = `<iframe src="${window.location.origin}/w/${token}" title="Guest reviews" style="width:100%;max-width:720px;height:520px;border:0" loading="lazy"></iframe>`;
  try { await navigator.clipboard.writeText(code); toast.success("Widget code copied. Paste it into your website."); }
  catch { toast.error("Couldn't copy. Open /w/" + token + " to see the widget."); }
}

function DeleteMoneyNote() {
  const { data } = useQuery({ queryKey: ["delete-check"], queryFn: accountApi.deleteCheck });
  if (!data) return null;
  const day = (d: string) => new Date(d).toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric" });
  return (
    <div className="max-w-2xl rounded-[14px] bg-white p-4 text-sm">
      {data.balance_due > 0 ? (
        <p className="font-semibold text-[#b32f12]">You have a balance of ₹{data.balance_due.toLocaleString("en-IN")} to pay. Please pay it on Plan and billing first, then delete.</p>
      ) : (
        <p><b>Balance to pay: ₹0.</b> Virundhu is paid in advance and never renews by itself, so nothing more will be charged after you delete.</p>
      )}
      {data.paid_until && data.paid_days_left > 0 ? (
        <p className="mt-1">Your paid plan runs until <b>{day(data.paid_until)}</b> ({data.paid_days_left} days left). Deleting gives up those days; refunds follow the <a href="/refunds" target="_blank" rel="noreferrer" className="underline">Refund Policy</a>.</p>
      ) : null}
      {data.last_payment ? <p className="mt-1 text-ink-soft">Last payment: ₹{data.last_payment.amount.toLocaleString("en-IN")} on {day(data.last_payment.date)}{data.last_payment.invoice_no ? ` (${data.last_payment.invoice_no})` : ""}.</p> : null}
      <p className="mt-1 text-ink-soft">You'll get an email confirming the deletion.</p>
    </div>
  );
}

export default function SettingsPage() {
  const { isOwner, org } = useWorkspace();
  const [tab, setTab] = useState<Tab>("restaurant");
  if (!isOwner) {
    return (
      <div className="mx-auto max-w-3xl">
        <h1 className="text-[2.3rem] font-bold">Settings</h1>
        <p className="mt-4 rounded-[16px] bg-jasmine-2 p-5">Only the owner of {org?.name ?? "this restaurant"} can change restaurant settings, outlets and the team. Ask them if something needs changing.</p>
      </div>
    );
  }
  return (
    <div className="mx-auto max-w-5xl">
      <h1 className="text-[2.3rem] font-bold">Settings</h1>
      <div className="mt-5 inline-flex flex-wrap gap-1.5 rounded-full bg-jasmine-2 p-1" role="tablist">
        {TABS.map(([key, label]) => (
          <button key={key} role="tab" aria-selected={tab === key} onClick={() => setTab(key)}
            className={cn("rounded-full px-4 py-2 text-sm font-semibold cursor-pointer", tab === key ? "bg-night text-jasmine" : "text-ink-soft hover:text-ink")}>{label}</button>
        ))}
      </div>
      <div className="mt-5">{tab === "restaurant" ? <RestaurantTab /> : tab === "outlets" ? <OutletsTab /> : <AccountTab />}</div>
    </div>
  );
}
