"""Silent how-to video in full HD: headed Chrome on a virtual screen at 1.5x scale, captured at 30 fps.
usage: rec.py OWNER_EMAIL FEED_URL -> /tmp/howto/screen.mp4"""
import json, os, signal, subprocess, sys, time
from playwright.sync_api import sync_playwright
W = "http://localhost:5450"; EMAIL, FEED = sys.argv[1], sys.argv[2]
JS = open("/tmp/howto/overlay.js").read()
DISP, SCALE = ":78", 1.5
xvfb = subprocess.Popen(["Xvfb", DISP, "-screen", "0", "1920x1400x24", "-nolisten", "tcp"]); time.sleep(1.5)
env = dict(os.environ, DISPLAY=DISP)

def hold(body): return max(4.5, 2.6 + len(body.split()) * 0.32)  # time to read the caption
def show(p, k, t, b):
    try: p.evaluate("([k,t,b]) => window.__demo.cap(k,t,b)", [k, t, b])
    except Exception: pass
def dot(p, loc, press=True):
    loc.scroll_into_view_if_needed(); bb = loc.bounding_box()
    if not bb: return
    x, y = bb["x"] + bb["width"] / 2, bb["y"] + bb["height"] / 2
    p.evaluate("([x,y]) => window.__demo.dot(x,y,false)", [x, y]); p.wait_for_timeout(800)
    if press: p.evaluate("([x,y]) => window.__demo.dot(x,y,true)", [x, y])
def click(p, sel, after=700):
    loc = p.locator(sel).first; dot(p, loc); loc.click(); p.wait_for_timeout(after)
def typein(p, sel, text, delay=45):
    loc = p.locator(sel).first; dot(p, loc, False); loc.click(); p.keyboard.type(text, delay=delay); p.wait_for_timeout(250)
def scroll(p, dy, ms=1500):
    p.evaluate("([dy,ms]) => { const s=scrollY, t0=performance.now(); const f=t=>{const k=Math.min(1,(t-t0)/ms); const e=k<.5?2*k*k:1-Math.pow(-2*k+2,2)/2; scrollTo(0,s+dy*e); if(k<1) requestAnimationFrame(f)}; requestAnimationFrame(f) }", [dy, ms])
    p.wait_for_timeout(ms + 200)
CUR = ["", "", ""]
def go(p, path, settle=600):
    p.goto(W + path, wait_until="domcontentloaded")
    show(p, *CUR)  # keep the step's caption on screen while the page opens
    p.wait_for_load_state("networkidle"); show(p, *CUR); p.wait_for_timeout(settle)
def nodot(p):
    try: p.evaluate("window.__demo.hideDot()")
    except Exception: pass

STEPS = []
def step(title, body):
    def deco(fn): STEPS.append((title, body, fn)); return fn
    return deco

@step("Create your account", "Restaurant name, city, mobile and how many outlets you run. 14 days free, no card needed.")
def _(p):
    go(p, "/register", 900)
    typein(p, "#full_name", "Kumar"); typein(p, "#org", "Annapoorna Mess"); typein(p, "#city", "Coimbatore")
    typein(p, "#r_phone", "98765 43210"); typein(p, "#r_outlets", "3")
@step("Sign in any time", "Use your email and password. Forgot it? Reset it from the sign-in page.")
def _(p):
    go(p, "/login", 700); typein(p, "#email", EMAIL, 25); typein(p, "#password", "Demo#Pass123", 40); click(p, "button[type=submit]", 300)
    p.wait_for_url("**/app**"); show(p, *CUR); p.wait_for_timeout(1800)
@step("Add your outlets", "Settings → Outlets. Add each branch with its district and manager, or upload them all from Excel.")
def _(p):
    go(p, "/app/settings", 600); click(p, "text=Outlets", 1600); scroll(p, 300, 1500)
@step("Print a QR code for each outlet", "Click QR code next to an outlet. Put it on the bill and the food packet so guests can tell you first.")
def _(p):
    loc = p.locator("button:has-text('QR code')").first; dot(p, loc, False)
@step("Connect Google", "Connections → Connect Google. New Google reviews arrive every 10 minutes for every outlet.")
def _(p):
    nodot(p); go(p, "/app/connections", 1200)
@step("Add Zomato and Swiggy reviews", "Add reviews → paste a review, upload a file, or upload a screenshot from the partner app. The AI picks out every review.")
def _(p):
    go(p, "/app/import", 1200); scroll(p, 700, 2200)
@step("See everything on the dashboard", "Every review from every outlet, already read: happy vs unhappy, average rating, and the top complaints.")
def _(p):
    go(p, "/app", 1200); scroll(p, 520, 2400)
@step("Urgent complaints alert you", "Hair in the food or food poisoning? The bell lights up within a minute, and you and the branch manager get an email.")
def _(p):
    scroll(p, -2000, 800); click(p, "[aria-label^='Alerts']", 600)
@step("Reply to guests", "Reviews to reply → Reply today shows what needs an answer now. Open a review to see a summary and a ready reply.")
def _(p):
    p.keyboard.press("Escape"); nodot(p); go(p, "/app/inbox?view=today", 1000); click(p, "ul[aria-label='Reviews'] li >> nth=0", 900)
@step("Send the reply in one tap", "Copy reply, paste it on Zomato or Swiggy, then Mark as replied. Google replies are posted for you.")
def _(p):
    click(p, "button:text-is('Copy reply')", 1800); click(p, "button:has-text('Mark as replied')", 900)
@step("Let it run by itself", "Automation → auto-reply to happy Google reviews, and a polite first reply to complaints nobody answered.")
def _(p):
    nodot(p); go(p, "/app/automation", 1500); scroll(p, 620, 2400)
@step("Ask every guest for a review", "Paste mobile numbers from today's bills, tick that guests agreed, and send. WhatsApp links are ready in one tap.")
def _(p):
    loc = p.locator("#ask-numbers"); loc.scroll_into_view_if_needed(); p.evaluate("scrollBy(0,-160)"); p.wait_for_timeout(500)
    typein(p, "#ask-numbers", "98765 43210\n91234 56789", 55)
@step("What your guest sees", "They scan the QR code, pick the stars and write a line. No app and no sign-in. It reaches you before Zomato.")
def _(p):
    nodot(p); go(p, FEED.replace(W, ""), 1200); click(p, "[aria-label='2 stars']", 500)
    typein(p, "textarea", "Food was cold and the parotta was hard.", 50); click(p, "button:has-text('Send feedback')", 1200)
@step("Choose your plan", "Plan and billing → enter your outlets and months. Bigger chains pay less per outlet; 9 and 12 months add free months.")
def _(p):
    nodot(p); go(p, "/app/billing", 1500); scroll(p, 260, 1200)
    loc = p.locator("#outlets"); dot(p, loc); loc.fill("12"); p.wait_for_timeout(1500)

try:
    with sync_playwright() as pw:
        b = pw.chromium.launch(headless=False, env=env, args=["--window-position=0,0", f"--force-device-scale-factor={SCALE}",
                                                             "--window-size=1280,900", "--disable-infobars", "--hide-scrollbars"])
        ctx = b.new_context(no_viewport=True)
        ctx.on("page", lambda pg: pg.close() if pg != ctx.pages[0] else None)
        p = ctx.new_page(); p.add_init_script(JS); p.goto("about:blank")
        ui = round(p.evaluate("outerHeight - innerHeight") * SCALE)
        p.set_viewport_size({"width": 1280, "height": 720})
        # Warm up every page (signed in), then sign out, so nothing loads blank on camera.
        p.goto(W + "/login"); p.fill("#email", EMAIL); p.fill("#password", "Demo#Pass123"); p.click("button[type=submit]"); p.wait_for_timeout(2500)
        for path in ["/app", "/app/inbox?view=today", "/app/import", "/app/automation", "/app/settings", "/app/connections", "/app/billing", "/register", FEED.replace(W, "")]:
            p.goto(W + path, wait_until="networkidle"); p.wait_for_timeout(400)
        ctx.clear_cookies(); p.evaluate("() => { try { localStorage.clear(); sessionStorage.clear() } catch (e) {} }")
        p.goto(W + "/", wait_until="networkidle"); p.wait_for_timeout(1500)
        ffstart = time.time()
        ff = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-use_wallclock_as_timestamps", "1", "-f", "x11grab", "-framerate", "30", "-video_size", "1920x1080", "-draw_mouse", "0",
                               "-i", f"{DISP}.0+0,{ui}", "-fps_mode", "cfr", "-r", "30", "-c:v", "libx264", "-preset", "ultrafast", "-crf", "16", "-pix_fmt", "yuv420p", "/tmp/howto/screen.mp4"],
                              stdin=subprocess.PIPE)
        time.sleep(0.8); v0 = ffstart + 0.25; starts = []
        # Opening card with the founder's photo.
        p.evaluate("([h,s,m,i]) => window.__demo.title(h,s,m,i)", ["How to use Virundhu", "Every guest, heard. Every complaint, caught.", "A quick tour by Sathish, Founder", "/demo/presenter.jpg"])
        p.wait_for_timeout(4200)
        n = len(STEPS)
        for i, (title, body, fn) in enumerate(STEPS, 1):
            t0 = time.time(); starts.append(round(t0 - v0, 2))
            CUR[:] = [f"STEP {i} OF {n}", title, body]
            show(p, *CUR)
            if i == 1: p.evaluate("window.__demo.untitle()")
            fn(p)
            show(p, f"STEP {i} OF {n}", title, body)
            left = hold(body) - (time.time() - t0)
            if left > 0: p.wait_for_timeout(int(left * 1000))
        show(p, "", "", ""); nodot(p)
        p.evaluate("([h,s,m,i]) => window.__demo.title(h,s,m,i)", ["Start your 14-day free trial", "virundhu · Every guest, heard.", "Questions? Use the Contact page.", "/demo/presenter.jpg"])
        p.wait_for_timeout(4500)
        end_real = time.time() - v0
        ff.stdin.write(b"q"); ff.stdin.flush(); ff.wait(timeout=30); b.close()
finally:
    xvfb.send_signal(signal.SIGTERM)
json.dump({"starts": starts, "titles": [s[0] for s in STEPS], "end": round(end_real, 2)}, open("/tmp/howto/timeline.json", "w"))
print("done")
