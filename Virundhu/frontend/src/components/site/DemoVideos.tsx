import { useQuery } from "@tanstack/react-query";
import { PlayCircle } from "lucide-react";
import { useRef, useState } from "react";
import { cn } from "@/lib/utils";

interface Timeline { starts: number[]; titles: string[] }

const mmss = (s: number) => `${Math.floor(s / 60)}:${String(Math.floor(s % 60)).padStart(2, "0")}`;

/** The silent how-to video (public/demo/howto.mp4) with one chapter per step; times come from howto.json. */
export function DemoVideos() {
  const ref = useRef<HTMLVideoElement>(null);
  const [now, setNow] = useState(0);
  const { data } = useQuery({
    queryKey: ["howto-times"],
    queryFn: () => fetch("/demo/howto.json").then((r) => r.json() as Promise<Timeline>),
    staleTime: Infinity,
  });
  const steps = (data?.titles ?? []).map((title, i) => ({ title, at: Math.max(0, (data?.starts[i] ?? 0) - 0.3) }));
  const active = steps.reduce((acc, s, i) => (now >= s.at ? i : acc), -1);

  function jump(at: number) {
    const v = ref.current;
    if (!v) return;
    v.currentTime = at;
    void v.play().catch(() => undefined);
  }

  return (
    <div className="grid gap-6 lg:grid-cols-[minmax(0,1.75fr)_minmax(0,1fr)]">
      <div className="overflow-hidden rounded-[24px] border-2 border-white/10 bg-night-2 shadow-[0_30px_80px_-30px_rgba(0,0,0,0.6)]">
        <video ref={ref} controls playsInline muted preload="none" poster="/demo/howto.jpg" className="block aspect-video w-full"
          onTimeUpdate={(e) => setNow(e.currentTarget.currentTime)}>
          <source src="/demo/howto.mp4" type="video/mp4" />
          Your browser can't play this video.
        </video>
      </div>
      <ol className="max-h-[560px] space-y-1 overflow-y-auto pr-1" aria-label="Steps">
        {steps.map((s, i) => (
          <li key={s.title}>
            <button type="button" onClick={() => jump(s.at)} aria-current={i === active}
              className={cn("flex w-full items-center gap-3 rounded-[12px] px-3 py-2 text-left transition-colors cursor-pointer",
                i === active ? "bg-turmeric text-night" : "text-jasmine hover:bg-white/10")}>
              <span className={cn("grid h-7 w-7 shrink-0 place-items-center rounded-full text-sm font-bold",
                i === active ? "bg-night text-turmeric" : "bg-white/10")}>{i + 1}</span>
              <span className="min-w-0 flex-1 font-semibold">{s.title}</span>
              <span className="tabular text-xs opacity-70">{mmss(s.at)}</span>
              <PlayCircle className="h-4 w-4 shrink-0 opacity-70" />
            </button>
          </li>
        ))}
      </ol>
    </div>
  );
}
