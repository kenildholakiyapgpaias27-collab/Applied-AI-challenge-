#!/usr/bin/env python3
"""Browser test for the adaptive quiz: Q1 (gender + what they're looking for) decides the rest.

    python3 tests/quiz_flow_test.py

Builds the page with no database (offline mode) into a temp folder, serves it and
drives it in Chrome with Playwright. Needs: pip install playwright, and Chrome.
"""
import functools
import http.server
import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
CHROME = os.environ.get("CHROME", "/usr/bin/google-chrome")
RESULTS, ERRORS = [], []


def check(name, cond, detail=""):
    RESULTS.append(bool(cond))
    print(("PASS " if cond else "FAIL ") + name + ("" if cond else f"   {detail}"))


def build_offline():
    tmp = Path(tempfile.mkdtemp(prefix="aaina_quiz_"))
    for p in ["build.py", "src", "data"]:
        (shutil.copytree if (ROOT / p).is_dir() else shutil.copy)(ROOT / p, tmp / p)
    (tmp / "data/supabase.json").write_text(json.dumps({"url": "", "anonKey": ""}))
    subprocess.run([sys.executable, "build.py"], cwd=tmp, check=True, capture_output=True)
    return tmp


def serve(folder, port):
    class Quiet(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *a):
            pass
    h = functools.partial(Quiet, directory=str(folder))
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", port), h)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


# ---------- helpers that answer each kind of question ----------
def current(pg):
    return pg.evaluate("stepNow")


def asked(pg):
    """Every question key shown so far, in order."""
    return pg.evaluate("[...document.querySelectorAll('.q[data-step]')].map(q=>q.dataset.step)")


def about(pg, gender, goal):
    pg.locator(f'.q:not(.answered) input[name="agender"][value="{gender}"]').check()
    pg.locator(f'.q:not(.answered) [data-goal="{goal}"]').click()
    pg.locator(".q:not(.answered) [data-go]").click()
    pg.wait_for_timeout(500)


def pick(pg, text):
    pg.locator(".q:not(.answered) .opt").filter(has_text=text).first.click()
    pg.wait_for_timeout(500)


def concerns_acne(pg):
    pg.locator("label:visible, button:visible").filter(has_text="Breakouts and acne").last.click()
    pg.locator("label.sc:visible:has-text('Blackheads and whiteheads')").first.click()
    pg.locator(".q:not(.answered) button:visible:has-text('Continue')").first.click()
    pg.wait_for_timeout(500)


def safety(pg, preg=None):
    """None everywhere; pregnancy answer only if that question is shown."""
    has_preg = pg.locator('.q:not(.answered) input[name="spreg"]').count() > 0
    pg.evaluate("""p=>{const q=document.querySelector('.q:not(.answered)');
      for(const g of ['avoid','react','sym']){const n=q.querySelector(`input[data-sec="${g}"][value="__none"]`);(n.closest('label')||n).click()}
      if(p!==null){const r=q.querySelector(`input[name="spreg"][value="${p}"]`);if(r)(r.closest('label')||r).click()}}""", preg)
    pg.locator(".q:not(.answered) [data-go]").click()
    pg.wait_for_timeout(500)
    return has_preg


def location(pg, city="Pune"):
    pg.fill("input[placeholder^='Start typing']", city)
    pg.wait_for_timeout(500)
    pg.locator(".q:not(.answered) button:visible:has-text('Continue')").first.click()
    pg.wait_for_timeout(600)


def skin(pg, label="Shiny all over"):
    pick(pg, label)


def tone(pg, t=6):
    pg.locator(f".q:not(.answered) button[aria-label^='Skin tone {t},']").click()
    pg.wait_for_timeout(500)


def plan_ids(pg):
    return pg.evaluate("PL&&PL.slots.map(s=>s.p&&s.p.id)")


def main():
    site = build_offline()
    srv = serve(site, 8794)
    url = "http://127.0.0.1:8794/index.html"
    with sync_playwright() as p:
        b = p.chromium.launch(executable_path=CHROME, args=["--no-sandbox"])

        def fresh():
            ctx = b.new_context(viewport={"width": 1280, "height": 860})
            pg = ctx.new_page()
            pg.on("pageerror", lambda e: ERRORS.append(str(e)))
            pg.goto(url)
            pg.wait_for_timeout(500)
            pg.fill("#nameInput", "Asha")
            pg.keyboard.press("Enter")
            pg.wait_for_timeout(500)
            return ctx, pg

        # A. woman + skincare routine: concerns ... tone, then undertone; base-makeup shades shown
        ctx, pg = fresh()
        check("Q1 is 'about you'", current(pg) == "about")
        about(pg, "woman", "routine")
        check("A: routine goes to concerns next", current(pg) == "concerns")
        concerns_acne(pg)
        check("A: woman is asked the pregnancy question", safety(pg, "false"))
        location(pg); skin(pg); tone(pg, 6)
        check("A: undertone asked right after skin shade", current(pg) == "undertone", current(pg))
        pick(pg, "Warm")
        check("A: question order", asked(pg) == ["about", "concerns", "safety", "location", "skin", "tone", "undertone"], asked(pg))
        check("A: three-step plan", len(plan_ids(pg) or []) == 3)
        check("A: undertone saved", pg.evaluate("P.undertone") == "warm")
        check("A: base-makeup shades section shown", pg.locator(".plan:not(.old) .baseshades").count() == 1)
        ctx.close()

        # B. man + sunscreen: no shade, no undertone, no pregnancy; a single sunscreen
        ctx, pg = fresh()
        about(pg, "man", "sunscreen")
        check("B: sunscreen asks where they'll wear it", current(pg) == "follow" and "sunscreen" in pg.locator(".q:not(.answered) .qtitle").inner_text().lower())
        pick(pg, "Long hours outdoors")
        check("B: man is NOT asked the pregnancy question", not safety(pg))
        check("B: pregnancy set to not-cautious", pg.evaluate("P.pregnancy") is False)
        location(pg); skin(pg, "Shiny T-zone")
        steps = asked(pg)
        check("B: never asked skin shade or undertone", "tone" not in steps and "undertone" not in steps and current(pg) is None, steps)
        ids = plan_ids(pg)
        cats = pg.evaluate("PL.slots.map(s=>s.p&&s.p.c)")
        check("B: one product, and it's a sunscreen", ids and len(ids) == 1 and cats == ["Sunscreen"], cats)
        check("B: SPF 50 for long hours outdoors", pg.evaluate("PL.slots[0].p.spf") >= 50, pg.evaluate("PL.slots[0].p.spf"))
        check("B: heading and title fit a sunscreen search", "sunscreen" in pg.locator(".plan:not(.old) .phero h3").inner_text().lower() and "sunscreen" in pg.inner_text("#advTitle").lower())
        check("B: no base-makeup shades section", pg.locator(".baseshades").count() == 0)
        check("B: no pregnancy chip on plan", "Pregnancy" not in pg.locator(".plan:not(.old) .applied").inner_text())
        ctx.close()

        # C. non-binary + base makeup: finish, safety, skin, tone, undertone -> shade-matched picks
        ctx, pg = fresh()
        about(pg, "nonbinary", "makeup")
        pick(pg, "Matte")
        safety(pg, "false"); skin(pg, "Shiny all over"); tone(pg, 8)
        check("C: undertone after shade", current(pg) == "undertone")
        pick(pg, "Cool")
        check("C: question order", asked(pg) == ["about", "follow", "safety", "skin", "tone", "undertone"], asked(pg))
        res = pg.evaluate("""PL.slots.map(s=>{if(!s.p)return null;const m=shadeFor(s.p);return{c:s.p.c,depth:m.depth,und:m.und,good:m.good,fin:s.p.fin}})""")
        check("C: base, concealer and powder slots", [r and r["c"] for r in res][:1] in (["Foundation"], ["BB / CC cream"]) and len(res) == 3, res)
        check("C: every pick is a good shade match (within 1 of tone 8)", all(r and r["good"] and abs(r["depth"] - 8) <= 1 for r in res), res)
        check("C: cards show the exact shade name", pg.locator(".plan:not(.old) .shadeline").count() == sum(1 for r in res if r))
        check("C: matte finish preferred for the base", res[0] and res[0]["fin"] == "matte", res[0])
        ctx.close()

        # D. man + routine: shade asked (sunscreen cast on deeper skin), no undertone, no makeup section
        ctx, pg = fresh()
        about(pg, "man", "routine")
        concerns_acne(pg)
        check("D: man not asked pregnancy", not safety(pg))
        location(pg); skin(pg); tone(pg, 8)
        steps = asked(pg)
        check("D: no undertone for a man's skincare routine", "undertone" not in steps and current(pg) is None, steps)
        check("D: no base-makeup section", pg.locator(".baseshades").count() == 0)
        ctx.close()

        # E. change Q1 midway: sunscreen -> routine; changing gender man -> woman re-asks pregnancy
        ctx, pg = fresh()
        about(pg, "man", "sunscreen")
        pick(pg, "Daily commute")
        safety(pg)
        pg.evaluate("editStep('about')"); pg.wait_for_timeout(500)
        about(pg, "woman", "routine")
        check("E: switching to a routine asks concerns", current(pg) == "concerns", current(pg))
        check("E: sunscreen follow-up no longer in the quiz", "follow" not in pg.evaluate("STEPS"))
        concerns_acne(pg)
        check("E: man->woman asks the pregnancy question again", current(pg) == "safety" and pg.locator('.q:not(.answered) input[name="spreg"]').count() == 3)
        ctx.close()

        # F. a save from before Q1 existed resumes as a finished routine, no extra questions
        ctx = b.new_context(viewport={"width": 1280, "height": 860})
        pg = ctx.new_page(); pg.on("pageerror", lambda e: ERRORS.append(str(e)))
        pg.goto(url); pg.wait_for_timeout(300)
        old = {"v": 1, "NAME": "Ravi", "PROB": "acne", "SUB": "Blackheads and whiteheads", "FOLLOW_IDX": 1,
               "P": {"concerns": ["acne"], "concernFU": {"acne": 1}, "skin": "oily", "skinConfirmed": True, "tone": 6, "pregnancy": False,
                     "avoidFrag": False, "reactions": [], "city": "Pune", "state": "Maharashtra", "climate": "temperate"},
               "DONE": ["concerns", "safety", "location", "skin", "tone"], "STEPS": ["concerns", "safety", "location", "skin", "tone"],
               "planIds": None, "META": {"planAt": 1790000000000, "planProb": "acne", "checks": []}, "updated": 1790000000000}
        pg.evaluate("s=>localStorage.setItem('aaina.advisor.v1',JSON.stringify(s))", old)
        pg.reload(); pg.wait_for_timeout(800)
        txt = pg.locator("#resume").inner_text()
        check("F: old save shows as a finished plan", "Welcome back, Ravi" in txt and "plan for" in txt.lower(), txt[:120])
        pg.locator("#resume button.primary").first.click(); pg.wait_for_timeout(1200)
        check("F: resumes straight to the plan", current(pg) is None and len(plan_ids(pg) or []) == 3, pg.evaluate("STEPS"))
        ctx.close()

        # G. phone width: Q1 fits without sideways scrolling
        ctx = b.new_context(viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=True)
        pg = ctx.new_page(); pg.on("pageerror", lambda e: ERRORS.append(str(e)))
        pg.goto(url); pg.wait_for_timeout(400); pg.fill("#nameInput", "Asha"); pg.keyboard.press("Enter"); pg.wait_for_timeout(500)
        pg.screenshot(path="/tmp/quiz_q1_mobile.png")
        check("G: Q1 fits a phone screen", not pg.evaluate("document.documentElement.scrollWidth>innerWidth+1"))
        labels = pg.evaluate("[...document.querySelectorAll('#journey .jl')].filter(e=>getComputedStyle(e).visibility!=='hidden').map(e=>e.textContent)")
        check("G: only the current step is named on a phone", labels == ["About you"], labels)
        ctx.close()
        b.close()
    srv.shutdown()
    check("no JavaScript errors", not ERRORS, ERRORS[:3])
    print(f"\n{sum(RESULTS)}/{len(RESULTS)} passed")
    sys.exit(0 if all(RESULTS) else 1)


if __name__ == "__main__":
    main()
