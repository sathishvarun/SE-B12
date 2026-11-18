"""Visit every page on desktop and two phones; record console errors/warnings, failed requests, sideways scroll, hidden content."""
import json, sys, time
from playwright.sync_api import sync_playwright

BASE = "http://localhost:5450"
OWNER, OWNER_PW, FEED = sys.argv[1], "Demo#Pass123", sys.argv[2]
ADMIN, ADMIN_PW = "admin@virundhu.local", "Virundhu@Admin2026"
PUBLIC = ["/", "/how-it-works", "/about", "/pricing", "/contact", "/privacy", "/terms", "/data-processing", "/refunds",
          "/security", "/login", "/register", "/forgot-password", "/no-such-page", FEED.replace(BASE, "")]
OWNER_PAGES = ["/app", "/app/inbox", "/app/alerts", "/app/import", "/app/connections", "/app/settings", "/app/billing",
               "/app/ask", "/app/automation"]
ADMIN_PAGES = ["/app/admin"]
DEVICES = {"desktop": dict(viewport={"width": 1440, "height": 900}),
           "iphone": dict(viewport={"width": 390, "height": 844}, device_scale_factor=3, is_mobile=True, has_touch=True),
           "android": dict(viewport={"width": 360, "height": 780}, device_scale_factor=3, is_mobile=True, has_touch=True)}
results = []

def check(page, dev, path, log):
    log.clear()
    page.goto(BASE + path, wait_until="networkidle")
    time.sleep(0.8)
    h = page.evaluate("document.documentElement.scrollHeight")
    for y in range(0, h, 500):  # scroll through so on-scroll animations run
        page.evaluate(f"window.scrollTo(0,{y})"); time.sleep(0.12)
    time.sleep(0.9)
    info = page.evaluate("""() => {
      const w = window.innerWidth, over = [];
      for (const el of document.querySelectorAll('body *')) {
        const r = el.getBoundingClientRect();
        if (r.width && r.right > w + 1 && getComputedStyle(el).position !== 'fixed') {
          let p = el.parentElement, clipped = false;
          while (p) { const o = getComputedStyle(p).overflowX; if (o === 'auto' || o === 'hidden' || o === 'scroll' || o === 'clip') { clipped = true; break; } p = p.parentElement; }
          if (!clipped) over.push((el.tagName + '.' + (el.className.baseVal ?? el.className)).slice(0, 80));
        }
      }
      const hidden = [...document.querySelectorAll('h1,h2,h3,p,a,button')].filter(e => {
        const s = getComputedStyle(e); const r = e.getBoundingClientRect();
        return r.width > 0 && e.innerText.trim() && (parseFloat(s.opacity) < 0.05) && s.visibility !== 'hidden' && !e.closest('[aria-hidden=true]');
      }).map(e => e.innerText.trim().slice(0, 40));
      const small = [...document.querySelectorAll('a,button,input,select,textarea')].filter(e => {
        const r = e.getBoundingClientRect(); return r.width > 0 && r.height > 0 && (r.height < 24 || r.width < 24) && e.offsetParent;
      }).length;
      return { sideways: document.documentElement.scrollWidth - w, over: [...new Set(over)].slice(0, 5), hidden: hidden.slice(0, 6), small };
    }""")
    safe = path.strip("/").replace("/", "_").split("?")[0] or "home"
    page.evaluate("window.scrollTo(0,0)"); time.sleep(0.3)
    page.screenshot(path=f"/tmp/virundhu-qa-{dev}_{safe}.png", full_page=dev != "desktop")
    results.append({"device": dev, "page": path.split("?")[0], "console": list(log), **info})

def login(page, email, pw):
    page.goto(BASE + "/login", wait_until="networkidle")
    page.fill("#email", email); page.fill("#password", pw)
    page.click("button[type=submit]")
    page.wait_for_url("**/app**", timeout=15000); page.wait_for_load_state("networkidle")

with sync_playwright() as p:
    b = p.chromium.launch()
    for dev, opts in DEVICES.items():
        for who, pages in (("public", PUBLIC), ("owner", OWNER_PAGES), ("admin", ADMIN_PAGES)):
            ctx = b.new_context(**opts); page = ctx.new_page(); log = []
            page.on("console", lambda m, log=log: log.append(f"{m.type}: {m.text[:220]}") if m.type in ("error", "warning") else None)
            page.on("pageerror", lambda e, log=log: log.append(f"pageerror: {str(e)[:220]}"))
            page.on("requestfailed", lambda r, log=log: log.append(f"failed: {r.url[:120]} {r.failure}"))
            page.on("response", lambda r, log=log: log.append(f"http {r.status}: {r.url[:120]}") if r.status >= 400 else None)
            if who == "owner": login(page, OWNER, OWNER_PW)
            if who == "admin": login(page, ADMIN, ADMIN_PW)
            for path in pages: check(page, dev, path, log)
            ctx.close()
    b.close()
json.dump(results, open("/tmp/virundhu-qa-results.json", "w"), indent=1)
bad = [r for r in results if r["console"] or r["sideways"] > 0 or r["hidden"]]
print(len(results), "page views;", len(bad), "with issues")
for r in bad: print(json.dumps(r)[:600])
