/** All user-facing words in one place, so tone stays consistent (and a Tamil UI is easy later). */
import type { Category, Language, Platform, Sentiment, Urgency } from "@/types";

export const categoryLabel: Record<Category, string> = {
  food_quality: "Food quality",
  delivery: "Delivery",
  price: "Price and billing",
  staff: "Staff",
  packaging: "Packaging",
  hygiene: "Hygiene",
  app: "App or ordering",
  other: "Other",
};

export const sentimentLabel: Record<Sentiment, string> = {
  positive: "Happy guest",
  neutral: "Mixed feelings",
  negative: "Unhappy guest",
};

export const urgencyLabel: Record<Urgency, string> = {
  high: "Reply today",
  medium: "Reply this week",
  low: "All good",
};

export const languageLabel: Record<Language, string> = {
  english: "English",
  tamil: "Tamil",
  tanglish: "Tanglish",
  other: "Other",
};

export const platformLabel: Record<Platform, string> = {
  google: "Google",
  zomato: "Zomato",
  swiggy: "Swiggy",
  direct: "QR feedback",
  other: "Other",
  tripadvisor: "Tripadvisor",
  instagram: "Instagram",
  facebook: "Facebook",
};

export function greeting(): string {
  const h = new Date().getHours();
  if (h < 12) return "Good morning";
  if (h < 17) return "Good afternoon";
  return "Good evening";
}

export function shortDate(iso: string): string {
  return new Date(iso + "T00:00:00").toLocaleDateString("en-IN", { day: "numeric", month: "short" });
}
