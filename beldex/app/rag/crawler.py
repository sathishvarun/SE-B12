"""Playwright crawler: reads beldex.io (and its sub-sites) like a real browser and saves the text.

Run it:  python -m app.rag.crawler      (or the "Refresh knowledge" button in the admin dashboard)
Output:  data/knowledge/beldex_site.jsonl  +  data/knowledge/news_feed.jsonl
"""
from __future__ import annotations

import html
import io
import json
import os
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from urllib.parse import urldefrag, urljoin, urlparse

import httpx

from app.config import settings

OUT = settings.data_dir / "knowledge"
UA = "Mozilla/5.0 (BDX-Insight knowledge crawler; +https://beldex.io)"
NEWS_FEEDS = [u.strip() for u in os.getenv("NEWS_FEEDS", "https://beldexcoin.medium.com/feed,https://medium.com/feed/@beldexcoin").split(",") if u.strip()]


def _stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _allowed(url: str) -> bool:
    host = urlparse(url).hostname or ""
    return host == settings.crawl_allowed_domain or host.endswith("." + settings.crawl_allowed_domain)


def _pdf_text(url: str) -> str:
    from pypdf import PdfReader
    r = httpx.get(url, headers={"User-Agent": UA}, timeout=httpx.Timeout(240, connect=30), follow_redirects=True)
    r.raise_for_status()
    return "\n".join((p.extract_text() or "") for p in PdfReader(io.BytesIO(r.content)).pages)


def crawl_site(log=print) -> int:
    from playwright.sync_api import sync_playwright
    queue = list(settings.crawl_start_urls)
    seen: set[str] = set()
    rows = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                                           "(KHTML, like Gecko) Chrome/130.0 Safari/537.36")
        while queue and len(rows) < settings.crawl_max_pages:
            url = urldefrag(queue.pop(0))[0]
            if url in seen or not _allowed(url):
                continue
            seen.add(url)
            try:
                if url.lower().endswith(".pdf"):
                    text, title = _pdf_text(url), url.rsplit("/", 1)[-1]
                else:
                    page.goto(url, wait_until="domcontentloaded", timeout=60_000)
                    page.wait_for_timeout(3500)          # let the JavaScript render the content
                    for _ in range(4):                  # scroll so lazy sections load
                        page.mouse.wheel(0, 2500)
                        page.wait_for_timeout(400)
                    title = page.title() or url
                    text = page.inner_text("body")
                    for href in page.eval_on_selector_all("a[href]", "els => els.map(e => e.href)"):
                        nxt = urldefrag(urljoin(url, href))[0]
                        if _allowed(nxt) and nxt not in seen and not nxt.lower().endswith((".apk", ".zip", ".png", ".jpg")):
                            queue.append(nxt)
                text = "\n".join(l.strip() for l in text.splitlines() if l.strip())
                rows.append({"url": url, "title": title.strip(), "text": text, "kind": "official",
                             "published": "", "fetched_at": _stamp()})
                log(f"  saved {url}  ({len(text)} chars)")
            except Exception as exc:
                log(f"  skipped {url}: {exc}")
        browser.close()
    (OUT / "beldex_site.jsonl").write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows), encoding="utf-8")
    return len(rows)


def crawl_news(log=print) -> int:
    """Latest posts from the official Beldex blog feed (titles, dates and text, with links)."""
    rows = []
    for feed in NEWS_FEEDS:
        try:
            r = httpx.get(feed, headers={"User-Agent": UA}, timeout=30, follow_redirects=True)
            r.raise_for_status()
            for item in ET.fromstring(r.content).iter("item"):
                link = (item.findtext("link") or "").split("?")[0]
                body = item.findtext("{http://purl.org/rss/1.0/modules/content/}encoded") or item.findtext("description") or ""
                text = [html.unescape(re.sub(r"<[^>]+>", " ", body))]
                try:
                    published = parsedate_to_datetime(item.findtext("pubDate") or "").date().isoformat()
                except (TypeError, ValueError):
                    published = ""
                rows.append({"url": link, "title": item.findtext("title") or link, "kind": "news",
                             "text": " ".join(" ".join(text).split()), "published": published,
                             "fetched_at": _stamp()})
            log(f"  feed {feed}: {len(rows)} posts")
        except Exception as exc:
            log(f"  feed skipped {feed}: {exc}")
    if rows:
        (OUT / "news_feed.jsonl").write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows), encoding="utf-8")
    return len(rows)


def refresh(log=print) -> dict:
    log("Crawling beldex.io with Playwright...")
    pages = crawl_site(log)
    log("Reading the news feed...")
    posts = crawl_news(log)
    from app.rag.knowledge import kb
    kb.ensure()
    return {"pages": pages, "posts": posts, "chunks": len(kb.chunks)}


if __name__ == "__main__":
    print(refresh())
