#!/usr/bin/env python3
"""Baseline walkthrough: screenshot every screen at desktop (1440x900) and mobile (390x844), run axe-core on each,
and record console errors and simple layout problems (sideways scroll, small tap targets, clipped text).

    AXE=path/to/axe.min.js python3 tools/audit/walkthrough.py [OUTDIR]     # default reports/baseline

Builds the page with the real config but blocks every request to Supabase and OpenAI, so nothing is written
to the live project. Writes OUTDIR/screens/<viewport>/<nn>_<screen>.png and OUTDIR/walkthrough.json.
Read-only: it never changes the app.
"""
import json
import os
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tests"))
import quiz_flow_test as Q  # noqa: E402

OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "reports/baseline"
AXE = Path(os.environ["AXE"]).read_text()
VIEWS = {"desktop": (1440, 900), "mobile": (390, 844)}

LAYOUT_JS = """(mobile)=>{
  const vw=document.documentElement.clientWidth, out={overflowX:document.documentElement.scrollWidth>vw+1, wide:[], small:[], clipped:[]};
  const vis=e=>{const r=e.getBoundingClientRect(),s=getComputedStyle(e);return r.width>0&&r.height>0&&s.visibility!=='hidden'&&s.display!=='none'};
  const name=e=>(e.getAttribute('aria-label')||e.innerText||e.value||e.className||e.tagName).toString().trim().replace(/\\s+/g,' ').slice(0,50);
  for(const e of document.querySelectorAll('body *')){if(!vis(e))continue;const r=e.getBoundingClientRect();
    if(r.right>vw+2&&getComputedStyle(e).position!=='fixed'&&!e.closest('[style*="overflow"],.to-models,.pvback'))out.wide.push(e.tagName.toLowerCase()+'.'+[...e.classList].join('.')+' '+Math.round(r.right)+'px');}
  if(mobile)for(const e of document.querySelectorAll('button,a[href],input:not([type=hidden]),select,[role=button],label.sc,label.opt,.opt')){
    if(!vis(e))continue;const r=e.getBoundingClientRect();if(r.top>innerHeight*3)continue;
    if((r.width<44||r.height<44)&&!(e.tagName==='INPUT'&&['checkbox','radio'].includes(e.type)&&e.closest('label')))out.small.push(`${name(e)} (${Math.round(r.width)}x${Math.round(r.height)})`);}
  for(const e of document.querySelectorAll('button,h1,h2,h3,h4,.chip,.badge')){if(!vis(e))continue;if(e.scrollWidth>e.clientWidth+2&&getComputedStyle(e).overflow!=='visible')out.clipped.push(name(e));}
  out.wide=[...new Set(out.wide)].slice(0,12);out.small=[...new Set(out.small)].slice(0,25);out.clipped=[...new Set(out.clipped)].slice(0,12);return out}"""


def main():
    site = Q.build_offline()
    # real config, so the sign-in panel exists; network to the backend is blocked below
    (site / "data/supabase.json").write_text((ROOT / "data/supabase.json").read_text())
    import subprocess
    subprocess.run([sys.executable, "build.py"], cwd=site, check=True, capture_output=True)
    srv = Q.serve(site, 8811)
    url = "http://127.0.0.1:8811/index.html"
    report = {}
    with sync_playwright() as p:
        b = p.chromium.launch(executable_path=Q.CHROME, args=["--no-sandbox"])
        for view, (w, h) in VIEWS.items():
            shots = OUT / "screens" / view
            shots.mkdir(parents=True, exist_ok=True)
            rec = report[view] = []
            n = [0]

            def new_page():
                ctx = b.new_context(viewport={"width": w, "height": h}, device_scale_factor=1,
                                    is_mobile=view == "mobile", has_touch=view == "mobile")
                pg = ctx.new_page()
                errs = []
                pg.on("console", lambda m: errs.append(f"console.{m.type}: {m.text[:200]}") if m.type in ("error", "warning") else None)
                pg.on("pageerror", lambda e: errs.append(f"pageerror: {str(e)[:200]}"))
                pg.route("**/*supabase.co/**", lambda r: r.abort())
                pg.route("**/api.openai.com/**", lambda r: r.abort())
                pg.goto(url)
                pg.wait_for_timeout(700)
                return ctx, pg, errs

            def shot(pg, errs, name, full=False, axe=True):
                n[0] += 1
                pg.wait_for_timeout(350)
                f = shots / f"{n[0]:02d}_{name}.png"
                pg.screenshot(path=str(f), full_page=full)
                item = {"screen": name, "file": str(f.relative_to(OUT)), "errors": list(errs), "layout": pg.evaluate(LAYOUT_JS, view == "mobile")}
                errs.clear()
                if axe:
                    if not pg.evaluate("typeof axe!=='undefined'"):
                        pg.add_script_tag(content=AXE)
                    r = pg.evaluate("""async()=>{const r=await axe.run(document,{resultTypes:['violations'],runOnly:{type:'tag',values:['wcag2a','wcag2aa','wcag21a','wcag21aa','wcag22aa','best-practice']}});
                      return r.violations.map(v=>({id:v.id,impact:v.impact,help:v.help,n:v.nodes.length,targets:v.nodes.slice(0,4).map(x=>x.target.join(' '))}))}""")
                    item["axe"] = r
                rec.append(item)
                print(f"  {view} {n[0]:02d} {name}: axe {len(item.get('axe', []))} rules, errors {len(item['errors'])}, overflowX {item['layout']['overflowX']}")

            def cur(pg):
                return pg.locator(".q:not(.answered)").last

            def scroll_q(pg):
                pg.evaluate("(()=>{const q=[...document.querySelectorAll('.q:not(.answered)')].pop();if(q)q.scrollIntoView({block:'start'})})()")

            # ---- home + before-you-go
            ctx, pg, errs = new_page()
            shot(pg, errs, "home")
            pg.fill("#nameInput", "Asha"); pg.keyboard.press("Enter"); pg.wait_for_timeout(500)

            # ---- ROUTINE
            scroll_q(pg); shot(pg, errs, "routine_q1_about")
            pg.evaluate("showExit('progress')"); shot(pg, errs, "before_you_go_progress")
            pg.keyboard.press("Escape"); pg.wait_for_timeout(200)
            Q.about(pg, "woman", "routine"); scroll_q(pg); shot(pg, errs, "routine_q2_concerns")
            Q.concerns_acne(pg); scroll_q(pg); shot(pg, errs, "routine_q3_safety")
            Q.safety(pg, "false"); scroll_q(pg); shot(pg, errs, "routine_q4_location")
            Q.location(pg); scroll_q(pg); shot(pg, errs, "routine_q5_skin")
            Q.skin(pg, "Shiny all over"); scroll_q(pg); shot(pg, errs, "routine_q6_tone")
            Q.tone(pg, 6); scroll_q(pg); shot(pg, errs, "routine_q7_undertone")
            Q.pick(pg, "Warm"); pg.wait_for_timeout(900)
            pg.evaluate("document.querySelector('.plan:not(.old)')?.scrollIntoView({block:'start'})")
            shot(pg, errs, "routine_plan")
            shot(pg, errs, "routine_plan_full", full=True, axe=False)
            tune = pg.locator(".plan:not(.old) .tune, .plan:not(.old) details:has-text('Tune')").first
            if tune.count():
                tune.scroll_into_view_if_needed()
                s = tune.locator("summary")
                if s.count(): s.first.click()
                shot(pg, errs, "routine_tune_your_plan")
            tl = pg.locator(".plan:not(.old) .tl").first
            if tl.count():
                tl.locator(":scope > summary").click(); tl.scroll_into_view_if_needed(); shot(pg, errs, "results_timeline")
                tl.locator("[data-tl-compare]").first.click(); pg.wait_for_timeout(300); shot(pg, errs, "compare_view")
                pg.locator(".tl-modal .tl-x").first.click(); pg.wait_for_timeout(200)
            # sign-in panel lives in the plan
            ac = pg.locator(".plan:not(.old) .acct").first
            if ac.count():
                ac.scroll_into_view_if_needed(); shot(pg, errs, "sign_in_panel")
            pg.evaluate("showExit('plan')"); shot(pg, errs, "before_you_go_plan")
            pg.keyboard.press("Escape"); pg.wait_for_timeout(200)
            pg.evaluate("openCheckin()"); pg.wait_for_timeout(400); scroll_q(pg); shot(pg, errs, "check_in")
            pg.locator(".checkin [data-cancel]").click(); pg.wait_for_timeout(500)
            # try-on, model face
            btn = pg.locator(".plan:not(.old) [data-tryon]").first
            if btn.count():
                btn.click()
            else:
                pg.evaluate("TRYON.open({base:true})")
            pg.wait_for_timeout(2500)
            if pg.locator(".to-model:visible").count():   # picker shown first (phones): choose the closest model face
                m = pg.locator(".to-model.closest:visible")
                (m if m.count() else pg.locator(".to-model:visible")).first.click(); pg.wait_for_timeout(2500)
            shot(pg, errs, "try_on_model_face")
            pg.locator("[data-to=close]").click(); pg.wait_for_timeout(400)
            # chat
            pg.locator(".aa-fab").click(); pg.wait_for_timeout(500); shot(pg, errs, "chat_ask_aaina")
            pg.locator(".aa-panel .aa-x").click(); pg.wait_for_timeout(300)
            ctx.close()

            # ---- SUNSCREEN
            ctx, pg, errs = new_page()
            pg.fill("#nameInput", "Ravi"); pg.keyboard.press("Enter"); pg.wait_for_timeout(500)
            Q.about(pg, "man", "sunscreen"); scroll_q(pg); shot(pg, errs, "sunscreen_q2_follow")
            Q.pick(pg, "Daily commute"); scroll_q(pg); shot(pg, errs, "sunscreen_q3_safety")
            Q.safety(pg, None); scroll_q(pg); shot(pg, errs, "sunscreen_q4_location")
            Q.location(pg, "Chennai"); scroll_q(pg); shot(pg, errs, "sunscreen_q5_skin")
            Q.skin(pg, "Shiny all over"); pg.wait_for_timeout(900)
            pg.evaluate("document.querySelector('.plan:not(.old)')?.scrollIntoView({block:'start'})")
            shot(pg, errs, "sunscreen_plan")
            ctx.close()

            # ---- BASE MAKEUP
            ctx, pg, errs = new_page()
            pg.fill("#nameInput", "Meera"); pg.keyboard.press("Enter"); pg.wait_for_timeout(500)
            Q.about(pg, "woman", "makeup"); scroll_q(pg); shot(pg, errs, "makeup_q2_finish")
            Q.pick(pg, "Natural"); scroll_q(pg); shot(pg, errs, "makeup_q3_safety")
            Q.safety(pg, "false"); scroll_q(pg); shot(pg, errs, "makeup_q4_skin")
            Q.skin(pg, "Comfortable"); scroll_q(pg); shot(pg, errs, "makeup_q5_tone")
            Q.tone(pg, 8); scroll_q(pg); shot(pg, errs, "makeup_q6_undertone")
            if Q.current(pg) == "undertone":
                Q.pick(pg, "Warm"); scroll_q(pg); shot(pg, errs, "makeup_q7_preview")
            if Q.current(pg) == "preview":
                pg.locator(".q:not(.answered) [data-pv=keep]").click(); pg.wait_for_timeout(900)
            print("   makeup steps asked:", Q.asked(pg))
            pg.evaluate("document.querySelector('.plan:not(.old)')?.scrollIntoView({block:'start'})")
            shot(pg, errs, "makeup_plan")
            ctx.close()

            # ---- resume banner (returning visitor)
            ctx, pg, errs = new_page()
            pg.fill("#nameInput", "Asha"); pg.keyboard.press("Enter"); pg.wait_for_timeout(400)
            Q.about(pg, "woman", "sunscreen"); Q.pick(pg, "Daily commute"); Q.safety(pg, "false"); Q.location(pg); Q.skin(pg, "Comfortable")
            pg.wait_for_timeout(500); pg.reload(); pg.wait_for_timeout(800)
            shot(pg, errs, "home_returning")
            ctx.close()
        b.close()
    srv.shutdown()
    (OUT / "walkthrough.json").write_text(json.dumps(report, indent=1, ensure_ascii=False))
    print("wrote", OUT / "walkthrough.json")


if __name__ == "__main__":
    main()
