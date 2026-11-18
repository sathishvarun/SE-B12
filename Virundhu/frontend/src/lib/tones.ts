import type { Tone } from "@/components/ui/misc";
import type { Sentiment, Urgency } from "@/types";

export const urgencyTone: Record<Urgency, Tone> = { high: "chilli", medium: "turmeric", low: "leaf" };
export const sentimentTone: Record<Sentiment, Tone> = { positive: "leaf", neutral: "sky", negative: "chilli" };
