import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Plus } from "lucide-react";
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Chip, Skeleton } from "@/components/ui/misc";
import { useAuth } from "@/context/AuthContext";
import { cn } from "@/lib/utils";
import { agencyApi, clientOrg, errorMessage, type ClientRow } from "@/services/api";

/** Agencies and restaurant groups: every restaurant this login looks after, the ones needing a reply first. */
export default function Agency() {
  const { user, refreshUser } = useAuth();
  const qc = useQueryClient();
  const navigate = useNavigate();
  const { data, isLoading } = useQuery({ queryKey: ["agency"], queryFn: agencyApi.list, refetchInterval: 60_000 });
  const [name, setName] = useState("");
  const [city, setCity] = useState("");
  const add = useMutation({
    mutationFn: () => agencyApi.add({ name: name.trim(), city: city.trim() }),
    onSuccess: async (r) => {
      toast.success(`${r.name} added with its own 14-day trial`);
      setName(""); setCity("");
      await refreshUser();
      void qc.invalidateQueries({ queryKey: ["agency"] });
    },
    onError: (e) => toast.error(errorMessage(e)),
  });

  async function open(r: ClientRow) {
    clientOrg.set({ id: r.id, name: r.name });
    qc.clear();
    await refreshUser();
    navigate(r.waiting ? "/app/inbox?view=clock" : "/app");
  }

  const rows = data?.items ?? [];
  const openNow = user?.organization?.id;
  return (
    <div className="mx-auto max-w-[1280px]">
      <h1 className="text-[2.3rem] font-bold">All your restaurants</h1>
      <p className="mt-1 max-w-2xl text-ink-soft">
        For agencies and groups that look after several restaurants. Each one keeps its own reviews, settings and plan;
        you switch between them with one login. The ones with bad reviews waiting come first.
      </p>

      {data && data.total > 1 ? (
        <div className="mt-5 flex flex-wrap gap-3">
          <Chip tone={data.overdue ? "chilli" : "leaf"}>{data.overdue ? `${data.overdue} bad reviews past their time` : "Nothing overdue"}</Chip>
          <Chip>{data.waiting} waiting for a reply across {data.total} restaurants</Chip>
        </div>
      ) : null}

      <div className="mt-6 overflow-x-auto rounded-[20px] border-2 border-line bg-white">
        {isLoading ? <Skeleton className="h-[200px]" /> : (
          <table className="w-full min-w-[760px] text-left text-sm">
            <thead className="bg-jasmine text-ink-soft">
              <tr>{["Restaurant", "Reviews this week", "Average", "Waiting", "In time", "Plan", ""].map((h) => <th key={h} className="px-4 py-3 font-semibold">{h}</th>)}</tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.id} className={cn("border-t border-line", r.id === openNow && "bg-jasmine/50")}>
                  <td className="px-4 py-3"><p className="font-semibold">{r.name}</p><p className="text-xs text-ink-soft">{[r.city, `${r.outlets} outlet${r.outlets === 1 ? "" : "s"}`].filter(Boolean).join(", ")}</p></td>
                  <td className="px-4 py-3 tabular">{r.reviews_7d}</td>
                  <td className="px-4 py-3 tabular">{r.avg_rating_7d === null ? "-" : `${r.avg_rating_7d.toFixed(1)}★`}</td>
                  <td className="px-4 py-3 tabular">
                    {r.waiting ? <span className={cn("rounded-full px-2 py-0.5 font-semibold", r.overdue ? "bg-chilli text-white" : "bg-[#fdefc9] text-[#8a5a00]")}>{r.waiting}{r.overdue ? `, ${r.overdue} late` : ""}</span> : "0"}
                  </td>
                  <td className="px-4 py-3 tabular">{r.pct_within === null ? "-" : `${Math.round(r.pct_within)}%`}</td>
                  <td className="px-4 py-3">{r.locked ? <span className="font-semibold text-[#b32f12]">Unpaid</span> : r.plan === "trial" ? "Trial" : r.plan}</td>
                  <td className="px-4 py-3 text-right">
                    {r.id === openNow ? <span className="text-xs font-semibold text-ink-soft">Open now</span> : (
                      <Button size="sm" variant="outline" onClick={() => void open(r)}>Open</Button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      <section className="mt-8 rounded-[20px] bg-night p-6 text-jasmine" aria-labelledby="add-client">
        <h2 id="add-client" className="text-xl font-bold">Add a client restaurant</h2>
        <p className="mt-1 max-w-2xl text-sm text-mist">
          It gets its own 14-day free trial and its own plan. You become its owner; you can invite the restaurant's own
          people later from its Settings. Already a Virundhu customer? Ask them to invite your email from their Settings instead.
        </p>
        <form className="mt-4 flex flex-wrap gap-3" onSubmit={(e) => { e.preventDefault(); if (name.trim().length >= 2) add.mutate(); }}>
          <label className="min-w-[220px] flex-1"><span className="sr-only">Restaurant name</span>
            <input value={name} onChange={(e) => setName(e.target.value)} placeholder="Restaurant name" maxLength={120}
              className="h-11 w-full rounded-full border-2 border-white/15 bg-white/[0.06] px-4 text-jasmine placeholder:text-mist/60 focus:border-turmeric focus:outline-none" />
          </label>
          <label className="w-[200px]"><span className="sr-only">City</span>
            <input value={city} onChange={(e) => setCity(e.target.value)} placeholder="City" maxLength={80}
              className="h-11 w-full rounded-full border-2 border-white/15 bg-white/[0.06] px-4 text-jasmine placeholder:text-mist/60 focus:border-turmeric focus:outline-none" />
          </label>
          <Button type="submit" disabled={add.isPending || name.trim().length < 2}><Plus className="h-4 w-4" /> Add restaurant</Button>
        </form>
      </section>
    </div>
  );
}
