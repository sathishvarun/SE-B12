import { useEffect } from "react";
import { useLocation } from "react-router-dom";
import { SEO, SITE_URL } from "@/lib/seo";

const TITLES: Record<string, string> = {
  "/": "Virundhu - Every guest, heard",
  "/how-it-works": "How it works - Virundhu",
  "/about": "Why Virundhu",
  "/pricing": "Pricing per outlet - Virundhu",
  "/contact": "Contact and demo - Virundhu",
  "/privacy": "Privacy Policy - Virundhu",
  "/terms": "Terms of Service - Virundhu",
  "/refunds": "Refunds and cancellation - Virundhu",
  "/security": "Security - Virundhu",
  "/login": "Sign in - Virundhu",
  "/register": "Start your free trial - Virundhu",
  "/forgot-password": "Forgot password - Virundhu",
  "/app": "Dashboard - Virundhu",
  "/app/inbox": "Inbox - Virundhu",
  "/app/alerts": "Alerts - Virundhu",
  "/app/import": "Add reviews - Virundhu",
  "/app/connections": "Connections - Virundhu",
  "/app/automation": "Automation - Virundhu",
  "/app/ask": "Ask Virundhu",
  "/app/insights": "Dishes and staff",
  "/app/support": "Help and support",
  "/app/settings": "Settings - Virundhu",
  "/app/billing": "Plan and billing - Virundhu",
  "/app/admin": "Admin console - Virundhu",
};

/** Gives every page its own browser-tab title (helps people and Google tell the pages apart). */
export function PageTitle() {
  const { pathname } = useLocation();
  useEffect(() => {
    const path = pathname.replace(/\/$/, "") || "/";
    const seo = SEO[path];
    document.title = seo?.title ?? TITLES[path] ?? (path.startsWith("/f/") ? "Tell us about your visit" : "Virundhu");
    if (!seo) return;
    const set = (sel: string, attr: string, value: string) => document.querySelector(sel)?.setAttribute(attr, value);
    set('meta[name="description"]', "content", seo.description);
    set('meta[property="og:title"]', "content", seo.title);
    set('meta[property="og:description"]', "content", seo.description);
    set('link[rel="canonical"]', "href", `${SITE_URL}${path}`);
  }, [pathname]);
  return null;
}
