import type { Category, Language, Platform, Sentiment, Urgency } from "@/types";

export interface SampleReview {
  id: string;
  platform: Platform;
  rating: number;
  outlet: string;
  text: string;
  sentiment: Sentiment;
  category: Category;
  urgency: Urgency;
  language: Language;
  summary: string;
}

/** Fictional restaurant, realistic reviews. Tags show exactly what Virundhu returns. */
export const streamReviews: SampleReview[] = [
  { id: "s1", platform: "swiggy", rating: 1, outlet: "RS Puram", text: "Chicken la mudi irundhuchu. Very disgusting, need refund.", sentiment: "negative", category: "hygiene", urgency: "high", language: "tanglish", summary: "Hair found in the chicken; wants a refund." },
  { id: "s2", platform: "google", rating: 5, outlet: "KK Nagar", text: "Biryani was really tasty and the staff were so warm. Will come again.", sentiment: "positive", category: "food_quality", urgency: "low", language: "english", summary: "Loved the biryani and the friendly staff." },
  { id: "s3", platform: "google", rating: 2, outlet: "Anna Nagar", text: "Saapadu nalla irundhuchu but bill la extra charge pottanga", sentiment: "negative", category: "price", urgency: "medium", language: "tanglish", summary: "Good food, but charged extra on the bill." },
  { id: "s4", platform: "zomato", rating: 5, outlet: "Anna Nagar", text: "Best chicken 65 in town. Crispy and hot every time.", sentiment: "positive", category: "food_quality", urgency: "low", language: "english", summary: "Loved the crispy, hot chicken 65." },
  { id: "s5", platform: "swiggy", rating: 1, outlet: "Anna Nagar", text: "Ordered at 8pm, came at 9:10. Food fully cold.", sentiment: "negative", category: "delivery", urgency: "high", language: "english", summary: "70 minutes late and the food was cold." },
  { id: "s6", platform: "zomato", rating: 3, outlet: "KK Nagar", text: "Food nalla irundhuchu, but delivery romba late.", sentiment: "neutral", category: "delivery", urgency: "medium", language: "tanglish", summary: "Food was good, delivery was very late." },
  { id: "s7", platform: "google", rating: 5, outlet: "RS Puram", text: "Staff romba friendly, service fast ah irundhuchu", sentiment: "positive", category: "staff", urgency: "low", language: "tanglish", summary: "Friendly staff and fast service." },
  { id: "s8", platform: "zomato", rating: 2, outlet: "RS Puram", text: "Parcel la gravy leak aagiduchu, bag full ah spoil", sentiment: "negative", category: "packaging", urgency: "medium", language: "tanglish", summary: "Gravy leaked and spoiled the bag." },
  { id: "s9", platform: "google", rating: 1, outlet: "KK Nagar", text: "The manager was rude when I asked for a fresh plate.", sentiment: "negative", category: "staff", urgency: "high", language: "english", summary: "Manager was rude about a fresh plate." },
  { id: "s10", platform: "swiggy", rating: 5, outlet: "Anna Nagar", text: "Parcel was packed very neatly. Thank you!", sentiment: "positive", category: "packaging", urgency: "low", language: "english", summary: "Parcel was packed well." },
];

export const trySamples = [
  { label: "Tanglish", text: "Biryani taste super, aana delivery 1 hour late, food cold aagiduchu" },
  { label: "Complaint", text: "Found a hair in the parotta. Very disappointing, the manager didn't even apologise." },
  { label: "English", text: "Lovely ghee roast and the staff remembered our order from last time!" },
];
