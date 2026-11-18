import { useState } from "react";

const MANUAL_MIN = 3; // open the right app, read, think, type a reply
const WITH_MIN = 0.5; // glance at the summary, approve or tweak the draft

/** Rough estimate of team time saved. The assumptions are shown, not hidden. */
export function SavingsCalculator() {
  const [outlets, setOutlets] = useState(3);
  const [perDay, setPerDay] = useState(10);
  const monthly = outlets * perDay * 30;
  const hoursSaved = Math.round((monthly * (MANUAL_MIN - WITH_MIN)) / 60);

  return (
    <div className="grid gap-8 rounded-[26px] border-2 border-night bg-white p-6 shadow-[8px_8px_0_#0c3b2e] sm:p-8 lg:grid-cols-2">
      <div className="space-y-7">
        <label className="block">
          <span className="flex justify-between font-semibold"><span>Outlets</span><span className="tabular font-display text-2xl">{outlets}</span></span>
          <input type="range" min={1} max={10} value={outlets} onChange={(e) => setOutlets(Number(e.target.value))} className="mt-2 h-8 w-full cursor-pointer accent-[#0c3b2e]" />
        </label>
        <label className="block">
          <span className="flex justify-between font-semibold"><span>Reviews per outlet, per day</span><span className="tabular font-display text-2xl">{perDay}</span></span>
          <input type="range" min={2} max={40} value={perDay} onChange={(e) => setPerDay(Number(e.target.value))} className="mt-2 h-8 w-full cursor-pointer accent-[#0c3b2e]" />
        </label>
        <p className="text-sm text-ink-soft">
          Our estimate: about {MANUAL_MIN} minutes per review by hand (open the app, read, type a reply) and about {WITH_MIN * 60} seconds
          with Virundhu (check the summary, approve the draft). Your numbers will differ.
        </p>
      </div>
      <div className="flex flex-col justify-center rounded-[20px] bg-night p-6 text-jasmine">
        <p className="text-mist">Every month your team handles</p>
        <p className="tabular font-display text-[2.6rem] font-bold leading-none">{monthly.toLocaleString("en-IN")} reviews</p>
        <p className="mt-6 text-mist">and gets back about</p>
        <p className="tabular font-display text-[3.6rem] font-bold leading-none text-turmeric">{hoursSaved} hours</p>
        <p className="mt-2 text-mist">That's roughly {Math.max(1, Math.round(hoursSaved / 8))} working day{hoursSaved >= 12 ? "s" : ""} a month back in the kitchen.</p>
      </div>
    </div>
  );
}
