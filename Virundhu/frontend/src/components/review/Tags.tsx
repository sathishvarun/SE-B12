import { Chip } from "@/components/ui/misc";
import { categoryLabel, languageLabel, sentimentLabel, urgencyLabel } from "@/lib/copy";
import { sentimentTone, urgencyTone } from "@/lib/tones";
import type { Category, Language, Sentiment, Urgency } from "@/types";

export function UrgencyChip({ urgency }: { urgency: Urgency }) {
  return <Chip tone={urgencyTone[urgency]} dot>{urgencyLabel[urgency]}</Chip>;
}
export function SentimentChip({ sentiment }: { sentiment: Sentiment }) {
  return <Chip tone={sentimentTone[sentiment]}>{sentimentLabel[sentiment]}</Chip>;
}
export function CategoryChip({ category }: { category: Category }) {
  return <Chip tone="plain">{categoryLabel[category]}</Chip>;
}
export function LanguageChip({ language }: { language: Language }) {
  return <Chip tone="lotus">{languageLabel[language]}</Chip>;
}
