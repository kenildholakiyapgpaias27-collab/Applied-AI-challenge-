#!/usr/bin/env python3
"""Browser test for the Results timeline: open a product's timeline, compare 3 products, move the illustration
to 1 year, and check the progress check-in.

    python3 tests/timeline_test.py [--shots DIR]

Builds the page offline (no database) and drives it in Chrome with Playwright. With --shots, saves the report
screenshots: the timeline, the compare view, and the illustration at start / 4 weeks / 3 months / 1 year on a
light and a deep model face.
"""
import re
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

sys.path.insert(0, str(Path(__file__).parent))
import quiz_flow_test as Q  # noqa: E402

check = Q.check
BANNED = re.compile(r"\b(you will|guarantee\w*|cures?|cured|removes?|lighten\w*|brighten\w*|whiten\w*|fairer|treat(s|ed|ment|ing)?|heal\w*|eliminat\w*|"
                    r"permanent\w*|melasma|rosacea|eczema|psoriasis|dermatitis|acne|hyperpigmentation)\b", re.I)


def plan(pg, tone=6):
    Q.about(pg, "woman", "routine")
    pg.locator("label:visible, button:visible").filter(has_text="Dark spots").last.click()
    pg.locator(".q:not(.answered) .sc:visible").first.click()
    pg.locator(".q:not(.answered) button:visible:has-text('Continue')").first.click(); pg.wait_for_timeout(500)
    Q.safety(pg, "false"); Q.location(pg); Q.skin(pg, "Comfortable"); Q.tone(pg, tone); Q.pick(pg, "Warm")
    pg.wait_for_timeout(800)


def mean_L(pg):
    """mean CIE L* of the illustration canvas, leaving out the label band at the bottom"""
    return pg.evaluate("""(()=>{const c=document.querySelector('.tl-modal canvas'),g=c.getContext('2d'),h=c.height-40,d=g.getImageData(0,0,c.width,h).data;
      const l=v=>{v/=255;return v<=0.04045?v/12.92:((v+0.055)/1.055)**2.4};let s=0,n=0;
      for(let i=0;i<d.length;i+=16){const Y=0.2126*l(d[i])+0.7152*l(d[i+1])+0.0722*l(d[i+2]);s+=Y>216/24389?116*Math.cbrt(Y)-16:903.3*Y;n++}return s/n})()""")


def main():
    shots = Path(sys.argv[sys.argv.index("--shots") + 1]) if "--shots" in sys.argv else None
    if shots: shots.mkdir(parents=True, exist_ok=True)
    site = Q.build_offline(); srv = Q.serve(site, 8796); url = "http://127.0.0.1:8796/index.html"
    with sync_playwright() as p:
        b = p.chromium.launch(executable_path=Q.CHROME, args=["--no-sandbox"])

        def fresh(w=1280, h=900):
            ctx = b.new_context(viewport={"width": w, "height": h}, device_scale_factor=2 if shots else 1)
            pg = ctx.new_page(); pg.on("pageerror", lambda e: Q.ERRORS.append(str(e)))
            pg.route("https://**/*", lambda r: r.abort())
            pg.goto(url); pg.wait_for_timeout(500); pg.fill("#nameInput", "Asha"); pg.keyboard.press("Enter"); pg.wait_for_timeout(500)
            return ctx, pg

        # A. a dark-spots plan: every skincare card has "What to expect"
        ctx, pg = fresh(); plan(pg)
        check("A: plan built for dark spots", pg.evaluate("PROB") == "pigmentation" and len(Q.plan_ids(pg) or []) == 3, pg.evaluate("PROB"))
        tl = pg.locator(".plan:not(.old) .tl")
        check("A: every skincare card has a 'What to expect' timeline", tl.count() == 3, tl.count())
        first = None
        for k in range(tl.count()):
            if tl.nth(k).locator(".tl-stop").count() == 5: first = tl.nth(k); break
        check("A: a product shows 5 stops: 2 weeks, 4 weeks, 3 months, 6 months, 1 year", first is not None)
        first.locator("summary").click(); pg.wait_for_timeout(200)
        labels = [first.locator(".tl-when").nth(i).inner_text() for i in range(5)]
        check("A: stop labels", labels == ["2 weeks", "4 weeks", "3 months", "6 months", "1 year"], labels)
        meas = first.locator(".tl-stop.measured").first; meas.click(); pg.wait_for_timeout(200)
        det = first.locator("[data-tl-detail]").inner_text()
        check("A: tapping a stop shows the study, who was studied and why it might differ", "Study:" in det and "Who was studied" in det and "Why this might differ" in det, det[:200])
        check("A: confidence chip on measured stops", first.locator(".tl-stop.measured .tl-chip").count() >= 1)
        check("A: plan summary 'What to expect from this plan' with sunscreen's long-term role",
              pg.locator(".tl-plan").count() == 1 and "Sunscreen, every morning" in pg.locator(".tl-plan").inner_text(), pg.locator(".tl-plan").inner_text()[:300] if pg.locator(".tl-plan").count() else "")
        txt = " ".join(pg.locator(sel).inner_text() for sel in [".plan:not(.old) .pcards", ".tl-plan"])
        check("A: no banned words in any timeline text on the page", not BANNED.search(txt), BANNED.search(txt).group(0) if BANNED.search(txt) else "")
        if shots: first.screenshot(path=str(shots / "timeline_card.png"))

        # B. compare up to 3 products
        first.locator("[data-tl-compare]").first.click(); pg.wait_for_timeout(300)
        m = pg.locator(".tl-modal.wide")
        cols = m.locator("thead th").count() - 1
        check("B: compare shows up to 3 products side by side", m.count() == 1 and 1 <= cols <= 3, cols)
        rows = [m.locator("tbody th").nth(i).inner_text() for i in range(m.locator("tbody th").count())]
        check("B: rows: first change, 3-month change, evidence, irritation, cost per month, safety check",
              rows == ["First visible change", "Typical change at 3 months", "Evidence", "Irritation risk", "Cost per month of use", "Your safety check"], rows)
        check("B: best fit for the main concern is highlighted (not the biggest number)", m.locator(".tl-best").count() <= 1 and "Not the biggest number" in m.inner_text())
        if shots: m.locator(".exbox").screenshot(path=str(shots / "timeline_compare.png"))
        m.locator(".tl-x").click()

        # C. the illustration, on an arbutin product (numbers at 3 months), light and deep model faces
        pid = pg.evaluate("""CAT.find(p=>/arbutin 2%/i.test(p.a||'')&&check(p).ok&&TIMELINE.productTimeline(p,P,{concern:'pigmentation'}).hasNumeric)?.id
          ||CAT.find(p=>TIMELINE.productTimeline(p,P,{concern:'pigmentation'}).hasNumeric&&p.c!=='Sunscreen')?.id""")
        check("C: found a product whose studies report a size of change", bool(pid), pid)
        for face, tone in (("light", 2), ("deep", 9)):
            pg.evaluate(f"P.tone={tone};P.gender='woman';openIllustration(BY_ID['{pid}'])"); pg.wait_for_timeout(1200)
            m = pg.locator(".tl-modal.illus")
            check(f"C ({face}): illustration opens with the label visible", m.count() == 1 and m.locator(".tl-ilabel").is_visible() and "not a prediction of your skin" in m.locator(".tl-ilabel").inner_text())
            sl = m.locator("input[type=range]"); L = {}
            for k, name in ((0, "start"), (2, "4w"), (3, "3m"), (5, "1y")):
                sl.fill(str(k)); pg.wait_for_timeout(250); L[name] = mean_L(pg)
                if shots: m.locator(".tl-canvas").screenshot(path=str(shots / f"illus_{face}_{name}.png"))
            say1y = m.locator("[data-say]").inner_text()
            check(f"C ({face}): at 1 year it says maintenance (no extra change)", "Maintenance" in say1y, say1y)
            check(f"C ({face}): 1 year looks the same as the last measured point", abs(L["1y"] - L["3m"]) < 0.01, L)
            check(f"C ({face}): before the first study point nothing changes", abs(L["4w"] - L["start"]) < 0.01, L)
            check(f"C ({face}): the face never gets lighter on average", L["3m"] <= L["start"] + 0.05 and L["1y"] <= L["start"] + 0.05, L)
            check(f"C ({face}): label stays visible at every point and there's no download", m.locator(".tl-ilabel").is_visible() and m.locator("a[download], [data-download]").count() == 0)
            m.locator(".tl-x").click(); pg.wait_for_timeout(200)
        ctx.close()

        # D. progress check-in at week 4: rating 1 -> expected vs yours, and a way to swap
        ctx, pg = fresh(); plan(pg)
        pg.evaluate("META.planAt=Date.now()-30*86400000;saveState()")
        pg.locator(".plan:not(.old) .next button:has-text('Track my progress')").click(); pg.wait_for_timeout(300)
        m = pg.locator(".tl-modal")
        check("D: progress check-in opens with a 1-5 self-rating", m.count() == 1 and m.locator("input[name=tlr]").count() == 5, m.inner_text()[:120] if m.count() else "")
        check("D: photo is optional, needs consent, and stays on the device", m.locator("[data-file]").is_disabled() and "never uploaded" in m.text_content())
        m.locator(".tl-rate label").first.click(); m.locator("[data-save]").click(); pg.wait_for_timeout(300)
        out = m.locator("[data-out]").inner_text()
        check("D: shows the expected range vs your check-in", "You rated 1 of 5" in out and ("studies of" in out or "evidence" in out), out[:200])
        before = Q.plan_ids(pg)
        if m.locator("[data-swap]").count():
            m.locator("[data-swap]").click(); pg.wait_for_timeout(600)
            check("D: 'no change past the expected point' routes to the swap", Q.plan_ids(pg) != before, (before, Q.plan_ids(pg)))
        else:
            check("D: no swap offered when studies hadn't measured anything yet", "normal to see little change" in out, out[:200])
        check("D: check-in kept on this device only (not signed in)", pg.evaluate("(META.progress||[]).length") == 1)
        pg.evaluate("localStorage.setItem('aaina.progress.photos.v1','[]')")
        pg.locator("#deleteBtn").click(); pg.wait_for_timeout(200); pg.locator(".exitm [data-yes]").click(); pg.wait_for_timeout(300)
        check("D: 'Delete my answers' also removes progress photos", pg.evaluate("localStorage.getItem('aaina.progress.photos.v1')") is None)
        ctx.close()

        # E. mobile layout
        ctx, pg = fresh(390, 844); plan(pg)
        t = pg.locator(".plan:not(.old) .tl").first; t.locator("summary").click(); pg.wait_for_timeout(200)
        over = pg.evaluate("document.documentElement.scrollWidth>window.innerWidth+1")
        check("E: phone: timeline fits the screen (no sideways scroll)", not over)
        if shots: t.screenshot(path=str(shots / "timeline_card_mobile.png"))
        ctx.close()
        b.close()
    srv.shutdown()
    check("no JavaScript errors", not Q.ERRORS, Q.ERRORS[:3])
    print(f"\n{sum(Q.RESULTS)}/{len(Q.RESULTS)} passed")
    sys.exit(0 if all(Q.RESULTS) else 1)


if __name__ == "__main__":
    main()
