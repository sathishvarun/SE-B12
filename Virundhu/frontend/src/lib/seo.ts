/**
 * Search-engine details for every public page: title, description and structured data.
 * Used twice: by `scripts/prerender.mjs` to write real HTML for Google at build time, and by `PageTitle` to keep the
 * browser tab and meta tags right when people move between pages.
 */
import { HOW_FAQS, PRICING_FAQS } from "@/lib/faqs";
import type { PublicConfig } from "@/types";

export const SITE_URL = "https://virundhu.sathishsakthivel.tech";
export const OG_IMAGE = `${SITE_URL}/og-image.png`;

/** Company details baked into prerendered pages (the live app still reads them from /public/config). */
export const STATIC_CONFIG: PublicConfig = {
  company: {
    name: "Virundhu", email: "virundhu.info@skminimart.com", phone: null, address: "Ganapathy, Coimbatore, Tamil Nadu, India",
    grievance_officer: "Virundhu", parent: "SK Mini Mart", demo_email: "virundhu.demo@skminimart.com",
    founded: "July 2026", parent_gstin: null,
  },
  app_name: "Virundhu", google_enabled: true, google_client_id: null, payments_enabled: true, razorpay_key_id: null,
  ai_ready: true, llm_provider: "openai",
};

export interface PageSeo {
  title: string;
  description: string;
  /** Extra JSON-LD objects for this page. */
  schema?: object[];
}

const faqSchema = (qa: [string, string][]) => ({
  "@context": "https://schema.org",
  "@type": "FAQPage",
  mainEntity: qa.map(([q, a]) => ({ "@type": "Question", name: q, acceptedAnswer: { "@type": "Answer", text: a } })),
});

const ORG = {
  "@context": "https://schema.org",
  "@type": "Organization",
  name: "Virundhu",
  url: SITE_URL,
  logo: `${SITE_URL}/icon-512.png`,
  email: "virundhu.info@skminimart.com",
  parentOrganization: { "@type": "Organization", name: "SK Mini Mart" },
  address: { "@type": "PostalAddress", addressLocality: "Coimbatore", addressRegion: "Tamil Nadu", streetAddress: "Ganapathy", addressCountry: "IN" },
  areaServed: "IN",
};

const APP = {
  "@context": "https://schema.org",
  "@type": "SoftwareApplication",
  name: "Virundhu",
  applicationCategory: "BusinessApplication",
  operatingSystem: "Web, Android, iOS",
  url: SITE_URL,
  description:
    "AI review management for restaurants and cloud kitchens: reads Google, Zomato and Swiggy reviews in Tamil, Tanglish and English, drafts replies and alerts the owner within a minute.",
  offers: { "@type": "Offer", price: "0", priceCurrency: "INR", description: "14-day free trial, then priced per outlet" },
  inLanguage: ["en", "ta"],
};

export const SEO: Record<string, PageSeo> = {
  "/": {
    title: "Virundhu – No bad Zomato, Swiggy or Google review unanswered for over an hour",
    description:
      "Every 1-3 star review gets a reply ready in seconds, in Tamil, Tanglish or English, and reminders to your branch manager and you until it's answered. Free 14-day trial.",
    schema: [ORG, APP],
  },
  "/how-it-works": {
    title: "How Virundhu works – restaurant review management in Tamil Nadu",
    description:
      "See how Virundhu brings Google, Zomato, Swiggy and QR feedback into one inbox, tags every review, drafts Tamil or English replies and flags food-safety complaints.",
    schema: [faqSchema(HOW_FAQS)],
  },
  "/about": {
    title: "Why Virundhu – AI review staff made in Tamil Nadu for restaurants",
    description:
      "Virundhu is the AI service of SK Mini Mart, Coimbatore. Seven AI staff read reviews, reply to guests, catch hygiene complaints and win back unhappy customers.",
  },
  "/compare": {
    title: "Virundhu vs review dashboards – AI review staff for restaurants",
    description:
      "How Virundhu compares with Restaverse, Famepilot and plain review dashboards: Tamil and Tanglish replies, food-safety alerts, rupees at risk and per-outlet pricing.",
  },
  "/agencies": {
    title: "For PR and reputation agencies – Virundhu restaurant reviews",
    description:
      "Manage Google, Zomato and Swiggy reviews for all your restaurant clients from one login: ready replies, a one-hour clock on bad reviews and a score per client.",
  },
  "/whats-next": {
    title: "What's next – Virundhu roadmap",
    description: "The features we're building next for restaurants and cloud kitchens, shaped by owners' feedback.",
  },
  "/pricing": {
    title: "Pricing per outlet – Virundhu restaurant review management India",
    description:
      "Simple per-outlet pricing in rupees for single restaurants, cloud kitchens and chains. 14-day free trial, no card needed, pay by UPI or card.",
    schema: [faqSchema(PRICING_FAQS)],
  },
  "/contact": {
    title: "Book a free demo – Virundhu, Coimbatore",
    description:
      "Book a free Virundhu demo with your own reviews. Pick a time in one tap: Google Meet, Zoom, Teams, phone, or in person in Coimbatore.",
  },
  "/share-feedback": {
    title: "Share feedback – Virundhu",
    description: "Tell us what you think of Virundhu: ideas, problems or praise. Every message is read and answered.",
  },
  "/security": {
    title: "Security – how Virundhu protects restaurant data",
    description: "How Virundhu keeps your reviews, guest contacts and account safe: encryption, access control, backups and more.",
  },
  "/privacy": { title: "Privacy Policy – Virundhu", description: "How Virundhu collects, uses and protects personal data." },
  "/terms": { title: "Terms of Service – Virundhu", description: "The terms for using Virundhu." },
  "/data-processing": {
    title: "Data processing agreement – Virundhu",
    description: "How Virundhu processes guest and review data on behalf of restaurants.",
  },
  "/refunds": { title: "Refunds and cancellation – Virundhu", description: "Virundhu's refund and cancellation policy." },
};

export const PUBLIC_PATHS = Object.keys(SEO);

export const NOT_FOUND_SEO: PageSeo = {
  title: "Page not found – Virundhu",
  description: "This page isn't on the menu. Head back to the Virundhu home page.",
};

/** The <head> tags for one page, as an HTML string (used by the prerender script). */
export function headHtml(path: string, seo: PageSeo, noindex = false): string {
  const url = `${SITE_URL}${path === "/" ? "/" : path}`;
  const esc = (s: string) => s.replace(/&/g, "&amp;").replace(/"/g, "&quot;").replace(/</g, "&lt;");
  const tags = [
    `<title>${esc(seo.title)}</title>`,
    `<meta name="description" content="${esc(seo.description)}" />`,
    noindex ? `<meta name="robots" content="noindex" />` : `<link rel="canonical" href="${url}" />`,
    `<meta property="og:type" content="website" />`,
    `<meta property="og:site_name" content="Virundhu" />`,
    `<meta property="og:title" content="${esc(seo.title)}" />`,
    `<meta property="og:description" content="${esc(seo.description)}" />`,
    `<meta property="og:url" content="${url}" />`,
    `<meta property="og:image" content="${OG_IMAGE}" />`,
    `<meta property="og:locale" content="en_IN" />`,
    `<meta name="twitter:card" content="summary_large_image" />`,
    `<meta name="twitter:title" content="${esc(seo.title)}" />`,
    `<meta name="twitter:description" content="${esc(seo.description)}" />`,
    `<meta name="twitter:image" content="${OG_IMAGE}" />`,
    ...(seo.schema ?? []).map((s) => `<script type="application/ld+json">${JSON.stringify(s).replace(/</g, "\\u003c")}</script>`),
  ];
  return tags.join("\n    ");
}
