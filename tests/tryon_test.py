#!/usr/bin/env python3
"""Browser test for the virtual try-on.

    python3 tests/tryon_test.py [--shots DIR]

Builds the page offline (no database) into a temp folder, serves it and drives it in
Chrome with Playwright. Needs: pip install playwright, Chrome, Pillow, and internet for
the face-tracking checks (MediaPipe loads from the CDN; model faces work offline).
--shots DIR also saves before/after screenshots of the same foundation and lipstick on a
light, a medium and a deep face.
"""
import base64
import io
import json
import os
import sys
import tempfile
from pathlib import Path

from PIL import Image
from playwright.sync_api import sync_playwright

sys.path.insert(0, str(Path(__file__).resolve().parent))
import quiz_flow_test as Q  # noqa: E402  (reuses its offline build, server and quiz helpers)

ROOT = Q.ROOT
CHROME = Q.CHROME
check, RESULTS, ERRORS = Q.check, Q.RESULTS, Q.ERRORS
MODELS = json.loads((ROOT / "data/model_faces.json").read_text())["faces"]
_LM = json.loads((ROOT / "data/model_faces_landmarks.json").read_text())
for _m in MODELS:
    _m["landmarks"] = _LM[_m["id"]]
BY = {m["id"]: m for m in MODELS}
FOUNDATION_SHADE = "165 Warm Light Medium"   # same shade on every face for the screenshots
LIPSTICK_SHADE = "Gulmohar Red"


def make_y4m(jpg, path, frames=4):
    """A tiny Y4M clip of a face for Chrome's fake camera (no ffmpeg needed)."""
    im = Image.open(jpg).convert("RGB")
    w, h = im.size
    ycc = im.convert("YCbCr")
    y, cb, cr = ycc.split()
    cb, cr = cb.resize((w // 2, h // 2)), cr.resize((w // 2, h // 2))
    with open(path, "wb") as f:
        f.write(f"YUV4MPEG2 W{w} H{h} F15:1 Ip A1:1 C420jpeg\n".encode())
        for _ in range(frames):
            f.write(b"FRAME\n" + y.tobytes() + cb.tobytes() + cr.tobytes())


def wait_for(pg, js, timeout=90000):
    pg.wait_for_function(js, timeout=timeout)


def pixel(pg, x, y):
    return pg.evaluate("""([x,y])=>{const c=document.querySelector('.to-cv');const t=document.createElement('canvas');t.width=c.width;t.height=c.height;
      const g=t.getContext('2d');g.drawImage(c,0,0);return [...g.getImageData(Math.round(x*c.width),Math.round(y*c.height),1,1).data].slice(0,3)}""", [x, y])


def canvas_png(pg):
    url = pg.evaluate("TRYON._draw(),document.querySelector('.to-cv').toDataURL('image/png')")
    return Image.open(io.BytesIO(base64.b64decode(url.split(",", 1)[1]))).convert("RGB")


def pick(pg, tab, pid, shade_name):
    pg.click(f".tryon [data-tab='{tab}']")
    if tab == "face":
        cat = pg.evaluate(f"BY_ID['{pid}'].c")
        pg.click(f".to-cats [data-cat='{cat}']")
    pg.click(f".to-prod[data-pid='{pid}']")
    i = pg.evaluate("([pid,n])=>{const p=BY_ID[pid];return (p.s?p.s.map(s=>s[0]):TRYON_DEMO.products[pid].shades.map(s=>s.name)).indexOf(n)}", [pid, shade_name])
    pg.click(f".to-sw[data-shade='{i}']")
    pg.wait_for_timeout(150)


def main():
    shots = None
    if "--shots" in sys.argv:
        shots = Path(sys.argv[sys.argv.index("--shots") + 1])
        shots.mkdir(parents=True, exist_ok=True)
    site = Q.build_offline()
    srv = Q.serve(site, 8795)
    url = "http://127.0.0.1:8795/index.html"
    tmp = Path(tempfile.mkdtemp(prefix="aaina_tryon_"))
    face_jpg = ROOT / BY["medium-olive"]["file"]
    y4m = tmp / "face.y4m"
    make_y4m(face_jpg, y4m)
    blank = tmp / "blank.png"
    Image.new("RGB", (400, 500), (210, 200, 190)).save(blank)
    found = None
    with sync_playwright() as p:
        b = p.chromium.launch(executable_path=CHROME, args=["--no-sandbox"])

        def fresh(offline=False, hash_="#try-on"):
            ctx = b.new_context(viewport={"width": 1280, "height": 860}, accept_downloads=True)
            if offline:
                ctx.route("**/*", lambda r: r.continue_() if r.request.url.startswith("http://127.0.0.1") or r.request.url.startswith("data:") else r.abort())
            pg = ctx.new_page()
            pg.on("pageerror", lambda e: ERRORS.append(str(e)))
            pg.goto(url + hash_)
            pg.wait_for_timeout(500)
            return ctx, pg

        # pick a foundation that has the screenshot shade, and a lipstick with the demo shade
        ctx, pg = fresh()
        found = pg.evaluate(f"""(()=>{{const f=CAT.find(p=>p.c==='Foundation'&&p.s&&p.s.some(s=>s[0]==={json.dumps(FOUNDATION_SHADE)}));
            const l=CAT.find(p=>p.c==='Lipstick'&&TRYON_DEMO.products[p.id]&&TRYON_DEMO.products[p.id].shades.some(s=>s.name==={json.dumps(LIPSTICK_SHADE)}));
            const bad=CAT.find(p=>p.c==='Lipstick'&&TRYON_DEMO.products[p.id]&&(p.frag||p.eo));return{{f:f&&f.id,l:l&&l.id,bad:bad&&bad.id}}}})()""")
        check("route: #try-on opens the try-on", pg.is_visible("#tryon") and pg.is_visible(".to-start"))
        check("all three ways to start are offered", pg.locator(".to-way").count() == 3 and pg.locator(".to-model").count() == len(MODELS))
        ctx.close()

        # A. model face, fully offline (no CDN at all)
        ctx, pg = fresh(offline=True)
        outside = []
        pg.on("request", lambda r: outside.append(r.url) if not (r.url.startswith("http://127.0.0.1") or r.url.startswith("data:") or r.url.startswith("blob:")) else None)
        pg.click(".to-model >> nth=0")
        pg.wait_for_timeout(500)
        check("A: model face renders offline with WebGL", pg.evaluate("TRYON.state.mode==='model'&&!!TRYON.state.gl&&!!TRYON.state.lmS"))
        m = BY[pg.evaluate("TRYON.state.model.id")]
        check("A: before/after handle starts down the middle", pg.evaluate("TRYON.state.split") == 0.5 and pg.is_visible(".to-handle"))
        check("A: tool buttons on the canvas", all(pg.is_visible(f".to-tools [data-to={t}]") for t in ("start", "compare", "snap", "clear")))
        pg.evaluate("TRYON.setSplit(0)")
        cx, cy = m["landmarks"][205]
        before = pixel(pg, cx, cy)
        pick(pg, "face", found["f"], FOUNDATION_SHADE)
        after = pixel(pg, cx, cy)
        check("A: foundation changes the cheek colour", sum(abs(a - b_) for a, b_ in zip(before, after)) > 6, (before, after))
        lx, ly = m["landmarks"][0][0], (m["landmarks"][0][1] + m["landmarks"][13][1]) / 2
        lb = pixel(pg, lx, ly)
        pick(pg, "lips", found["l"], LIPSTICK_SHADE)
        la = pixel(pg, lx, ly)
        check("A: lipstick changes the lips", la != lb and la[0] - la[1] > lb[0] - lb[1], (lb, la))
        check("A: demo shades are labelled", pg.locator(".to-demo").inner_text() == "Demo colour, not real product data")
        check("A: preview note shown", "Preview only. Screen colours vary" in pg.inner_text(".to-note"))
        check("A: full look across categories", sorted(pg.evaluate("Object.keys(TRYON.state.look)")) == ["base", "lips"])
        # before/after: drag the handle with the mouse, then the keyboard
        pg.evaluate("TRYON.setSplit(0.5)")
        box = pg.locator(".to-fit").bounding_box()
        hb = pg.locator(".to-handle").bounding_box()
        pg.mouse.move(hb["x"] + hb["width"] / 2, hb["y"] + hb["height"] / 2)
        pg.mouse.down(); pg.mouse.move(box["x"] + box["width"] * 0.6, hb["y"] + hb["height"] / 2, steps=6); pg.mouse.up()
        pg.wait_for_timeout(150)
        sp = pg.evaluate("TRYON.state.split")
        check("A: dragging the handle moves the before/after line", abs(sp - 0.6) < 0.02 and pg.get_attribute(".to-handle", "aria-valuenow") == str(round(sp * 100)), sp)
        check("A: left of the line shows the face without makeup", cx < sp and pixel(pg, cx, cy) == before, (cx, pixel(pg, cx, cy), before))
        pg.focus(".to-handle"); pg.keyboard.press("ArrowLeft")
        check("A: handle works with the keyboard", abs(pg.evaluate("TRYON.state.split") - (sp - 0.05)) < 1e-6)
        pg.evaluate("TRYON.setSplit(0)")
        # compare: opens with 4 shades of the current product, each with name, price and 'Pick this'
        pg.click(".tryon [data-tab='face']")
        pg.click(f".to-prod[data-pid='{found['f']}']")
        pg.click(".to-tools [data-to=compare]")
        pg.wait_for_timeout(200)
        caps = pg.locator(".to-tilecap:not(.empty)").all_inner_texts()
        check("A: compare shows a 2x2 grid of 4 shades", pg.locator(".to-tile").count() == 4 and len(caps) == 4 and all("₹" in c and "Pick this" in c for c in caps), caps)
        tiles = canvas_png(pg)
        w, h = tiles.size
        q = [tiles.getpixel((int(w * x), int(h * y))) for x, y in ((0.25, 0.3), (0.75, 0.3), (0.25, 0.8), (0.75, 0.8))]
        check("A: the four tiles show different shades", len(set(q)) >= 3, q)
        pick_name = pg.evaluate("TRYON.state.cmp[2].s.name")
        pg.click(".to-tile >> nth=2 >> .to-pick")
        pg.wait_for_timeout(200)
        check("A: 'Pick this' applies that shade and closes compare", pg.evaluate("TRYON.state.look.base.s.name") == pick_name and not pg.evaluate("TRYON.state.compare"))
        with pg.expect_download() as dl:
            pg.click(".to-tools [data-to=snap]")
        check("A: snapshot is saved as a file on the device", dl.value.suggested_filename.startswith("aaina-look-") and "this device" in pg.inner_text(".to-toast"))
        check("A: 'Your look' bar shows chips and a total", pg.locator(".to-foot .to-lc").count() == 2 and "₹" in pg.inner_text(".to-total"))
        pg.click(".to-foot .to-lc >> nth=1")
        check("A: tapping a look chip removes it", pg.locator(".to-foot .to-lc").count() == 1)
        check("A: model faces need no network (nothing requested off the device)", not outside, outside[:3])
        ctx.close()

        # B. uploaded photos -> MediaPipe tracking (needs the CDN), on every model face, at two sizes
        ctx, pg = fresh()
        keys = [33, 133, 263, 362, 1, 152, 61, 291, 10, 234, 454, 13, 14, 105, 334]
        errs = {}
        for m in MODELS:
            for scale in (1.0, 0.8):
                src = ROOT / m["file"]
                if scale != 1.0:
                    im = Image.open(src)
                    src = tmp / f"{m['id']}_{int(scale * 100)}.jpg"
                    im.resize((int(im.width * scale), int(im.height * scale)), Image.LANCZOS).save(src, quality=90)
                pg.evaluate("TRYON.state.lmS=null")
                pg.set_input_files(".tryon input[type=file]", str(src))
                try:
                    wait_for(pg, "TRYON.state.lmS||document.querySelector('[data-pane=fallback]:not([hidden])')")
                    got = pg.evaluate("TRYON.state.lmS")
                except Exception:
                    got = None
                if not got:
                    errs[(m["id"], scale)] = None
                    pg.click(".to-fallback [data-to=start]") if pg.is_visible(".to-fallback [data-to=start]") else None
                    continue
                known = m["landmarks"]
                errs[(m["id"], scale)] = sum(((got[i][0] - known[i][0]) ** 2 + (got[i][1] - known[i][1]) ** 2) ** 0.5 for i in keys) / len(keys)
                pg.click(".to-tools [data-to=start]")
        bad = {k: v for k, v in errs.items() if v is None or v >= 0.03}
        print("     tracking error (mean of 15 key points, fraction of image):", ", ".join(f"{k[0]}@{int(k[1]*100)}%={v:.3f}" if v is not None else f"{k[0]}@{int(k[1]*100)}%=none" for k, v in errs.items()))
        check("B: tracking finds every model face (6 faces x 2 sizes)", all(v is not None for v in errs.values()), bad)
        check("B: tracked landmarks land on each face (mean error < 3% of the image)", not bad, bad)
        stable = all(errs.get((m["id"], 1.0)) is not None and errs.get((m["id"], 0.8)) is not None and abs(errs[(m["id"], 1.0)] - errs[(m["id"], 0.8)]) < 0.015 for m in MODELS)
        check("B: landmarks are stable across image sizes", stable)
        pg.set_input_files(".tryon input[type=file]", str(face_jpg))
        wait_for(pg, "TRYON.state.lmS||document.querySelector('[data-pane=fallback]:not([hidden])')")
        pick(pg, "face", found["f"], FOUNDATION_SHADE)
        check("B: a shade can be applied to the photo", pg.evaluate("!!TRYON.state.look.base"))
        pg.set_input_files(".tryon input[type=file]", str(blank))
        wait_for(pg, "document.querySelector('[data-pane=fallback]:not([hidden])')", 60000)
        check("B: no face found -> friendly message and swatches", "No face found" in pg.inner_text("[data-pane=fallback]"))
        ctx.close()

        # C. a product that fails check() can be previewed but never added
        ctx, pg = fresh(hash_="")
        pg.evaluate("""P.avoidFrag=true;P.pregnancy=false;P.skin='normal';P.skinConfirmed=true;DONE.add('safety');location.hash='try-on'""")
        pg.wait_for_timeout(400)
        pg.evaluate("P.tone=7;P.undertone='warm';TRYON.close();TRYON.open()")
        pg.wait_for_timeout(300)
        k = [m["id"] for m in MODELS].index("deep-warm")
        check("C: the model face closest to the user's tone is pre-selected", pg.locator(".to-model.closest").count() == 1 and pg.get_attribute(".to-model.closest", "data-i") == str(k)
              and "Closest to you" in pg.inner_text(".to-model.closest"))
        check("C: model faces show as round thumbnails with labels", pg.locator(".to-model .to-mimg").count() == 6 and "Medium · olive" in pg.inner_text(".to-models"))
        pg.click(".to-model >> nth=0")
        pg.click(".tryon [data-tab='lips']")
        pg.click(f".to-prod[data-pid='{found['bad']}']")
        txt = pg.inner_text(".to-detail")
        check("C: product failing check() shows 'Not suitable for you'", "Not suitable for you" in txt and "fragrance" in txt, txt[:160])
        check("C: it can still be previewed", pg.evaluate(f"TRYON.state.look.lips&&TRYON.state.look.lips.p.id==='{found['bad']}'"))
        check("C: look bar says it won't be added", "isn't suitable for you and won't be added" in pg.inner_text(".to-foot"), pg.inner_text(".to-foot"))
        check("C: product list flags it too", "Not suitable for you" in pg.inner_text(f".to-prod[data-pid='{found['bad']}']"))
        ctx.close()

        # D. advisor tie-in: makeup plan -> 'Try it on' -> 'Your match' -> add to plan
        ctx, pg = fresh(hash_="")
        pg.fill("#nameInput", "Asha"); pg.keyboard.press("Enter"); pg.wait_for_timeout(400)
        Q.about(pg, "woman", "makeup"); Q.pick(pg, "Natural")
        Q.safety(pg, "false"); Q.skin(pg, "Comfortable"); Q.tone(pg, 6); Q.pick(pg, "Warm")
        # shade preview step: keep, try on a face, use another shade
        check("D: base-makeup quiz ends with the shade preview", Q.current(pg) == "preview" and pg.is_visible(".q:not(.answered) .pvcard"), Q.current(pg))
        pv = pg.evaluate("(()=>{const x=previewPick();return{pid:x.p.id,name:x.m.name}})()")
        pg.click(".q:not(.answered) [data-pv=try]"); pg.wait_for_timeout(600)
        k = [m["id"] for m in MODELS].index("tan-warm")
        st = pg.evaluate("({open:!document.querySelector('#tryon').hidden,mode:TRYON.state.mode,model:TRYON.state.model&&TRYON.state.model.id,base:TRYON.state.look.base&&{pid:TRYON.state.look.base.p.id,name:TRYON.state.look.base.s.name}})")
        check("D: 'See it on a face' opens the try-on on the matched shade and the closest model face",
              st["open"] and st["mode"] == "model" and st["model"] == "tan-warm" and st["base"] == pv, (st, pv))
        other = pg.evaluate(f"(()=>{{const p=BY_ID['{pv['pid']}'];const i=p.s.findIndex(s=>s[0]==='{pv['name']}');return p.s[(i+1)%p.s.length][0]}})()")
        i2 = pg.evaluate(f"BY_ID['{pv['pid']}'].s.findIndex(s=>s[0]==={json.dumps(other)})")
        pg.click(f".to-sw[data-shade='{i2}']"); pg.click(".to-x"); pg.wait_for_timeout(400)
        check("D: back in the quiz, it offers the shade you tried", pg.is_visible(".q:not(.answered) .pvback") and other in pg.inner_text(".q:not(.answered) .pvback"))
        pg.click(".q:not(.answered) [data-pv=use]"); pg.wait_for_timeout(500)
        res = pg.evaluate(f"(()=>{{const s=PL.slots.find(x=>x.slot.primary);return{{pid:s.p&&s.p.id,shade:shadeFor(s.p).name}}}})()")
        check("D: the plan uses the shade picked in the preview", res == {"pid": pv["pid"], "shade": other} and "You picked this in the shade preview" in pg.inner_text(".plan:not(.old)"), res)
        check("D: makeup plan has a 'Try it on' button", pg.locator(".plan:not(.old) .tryon-btn").count() >= 2)
        pid = pg.evaluate("PL.slots.find(s=>s.p&&s.p.s).p.id")
        pg.click(f".plan:not(.old) .pcard [data-tryon='{pid}']")
        pg.wait_for_timeout(400)
        check("D: card button opens the try-on on that product", pg.is_visible("#tryon") and pg.evaluate("TRYON.state.pid") == pid and "#try-on" in pg.url)
        match = pg.evaluate(f"bestShade(BY_ID['{pid}'],6,'warm').name")
        sel = pg.locator(".to-sw.match")
        lab = sel.get_attribute("aria-label") if sel.count() == 1 else ""
        check("D: user's best shade is marked 'Your match'", sel.count() == 1 and match in lab and "Your match" in lab, lab)
        check("D: product list shows a 'Your match' chip", "Your match" in pg.inner_text(f".to-prod[data-pid='{pid}']"))
        check("D: and the plan's shade (here, the one picked in the preview) is pre-selected",
              pg.evaluate("TRYON.state.look.base&&TRYON.state.look.base.s.name") == pg.evaluate(f"shadeFor(BY_ID['{pid}']).name"))
        lip = pg.evaluate("TRYON._products('Lipstick').find(x=>x.st.ok&&!PL.extras?.some(e=>e.p.id===x.p.id)).p.id")
        if not pg.is_visible(".to-start"):
            pg.click(".to-tools [data-to=start]")
        pg.click(".to-model >> nth=0")
        pg.click(".tryon [data-tab='lips']"); pg.click(f".to-prod[data-pid='{lip}']")
        pg.click(".to-foot [data-to=addlook]")
        pg.wait_for_timeout(300)
        check("D: 'Add look to my plan' adds the look to the plan", pg.evaluate(f"PL.extras.some(x=>x.p.id==='{lip}')") and pg.evaluate(f"META.extraIds.some(x=>x.id==='{lip}')"))
        check("D: the bar then shows it is in your plan", "In your plan" in pg.inner_text(".to-foot") and pg.is_disabled(".to-foot [data-to=addlook]"))
        pg.click(".to-x")
        pg.wait_for_timeout(300)
        check("D: closing hides it and clears the route", not pg.is_visible("#tryon") and "#try-on" not in pg.url)
        check("D: the add-on shows on the plan page", pg.locator(".plan:not(.old) .extras .pcard").count() >= 1)
        ctx.close()
        b.close()

        # D2. undertone helper: "Not sure" adds one question; "Still not sure" shows a second shade
        b2 = p.chromium.launch(executable_path=CHROME, args=["--no-sandbox"])
        for answer, want in (("Still not sure", None), ("Gold suits me", "warm")):
            pg = b2.new_page(viewport={"width": 1280, "height": 860}); pg.on("pageerror", lambda e: ERRORS.append(str(e)))
            pg.goto(url); pg.wait_for_timeout(400)
            pg.fill("#nameInput", "Asha"); pg.keyboard.press("Enter"); pg.wait_for_timeout(400)
            Q.about(pg, "woman", "makeup"); Q.pick(pg, "Natural")
            Q.safety(pg, "false"); Q.skin(pg, "Comfortable"); Q.tone(pg, 4); Q.pick(pg, "Not sure")
            check(f"D2: 'Not sure' adds the undertone helper ({answer})", Q.current(pg) == "utHelp" and "veins" in pg.inner_text(".q:not(.answered)"), Q.current(pg))
            Q.pick(pg, answer)
            pg.wait_for_timeout(400)
            if Q.current(pg) == "preview":
                pg.locator(".q:not(.answered) [data-pv=keep]").click(); pg.wait_for_timeout(400)
            st = pg.evaluate("({ut:P.undertone,src:P.undertoneSource,plan:!!PL})")
            if want:
                check("D2: a helper answer sets the undertone", st["ut"] == want and st["src"] == "helper" and st["plan"], st)
            else:
                check("D2: 'Still not sure' keeps undertone unknown and builds the plan", st["ut"] is None and st["plan"], st)
                alts = pg.evaluate("PL.slots.filter(s=>s.p&&s.p.s).map(s=>{const a=altShadeFor(s.p);return a&&a.und})")
                check("D2: plan cards show an 'also try' line exactly where the warm match differs",
                      all(x in (None, "warm") for x in alts) and pg.locator(".plan:not(.old) .shadealt").count() == sum(1 for x in alts if x), alts)
                pid = pg.evaluate("(CAT.find(p=>p.c==='Foundation'&&p.s&&altShadeFor(p))||{}).id||null")
                check("D2: some foundations have a different warm match for this profile", bool(pid))
                pg.evaluate(f"TRYON.open({{pid:'{pid}'}})"); pg.wait_for_timeout(300)
                pg.click(".to-model >> nth=0"); pg.wait_for_timeout(400)
                pg.click(".tryon [data-tab='face']"); pg.click(f".to-prod[data-pid='{pid}']"); pg.wait_for_timeout(200)
                alt = pg.evaluate(f"altShadeFor(BY_ID['{pid}']).name")
                check("D2: the try-on rings the warm 'also try' shade and explains it",
                      pg.locator(".to-sw.alt").count() == 1 and alt in (pg.get_attribute(".to-sw.alt", "aria-label") or "") and "warm match" in pg.inner_text(".to-althint"))
            pg.close()
        b2.close()

        # E. live camera with Chrome's fake camera playing a face
        bc = p.chromium.launch(executable_path=CHROME, args=["--no-sandbox", "--use-fake-ui-for-media-stream", "--use-fake-device-for-media-stream", f"--use-file-for-fake-video-capture={y4m}"])
        ctx = bc.new_context(viewport={"width": 1280, "height": 860}, permissions=["camera"])
        pg = ctx.new_page(); pg.on("pageerror", lambda e: ERRORS.append(str(e)))
        pg.goto(url + "#try-on"); pg.wait_for_timeout(400)
        pg.click(".to-way[data-to=consent]")
        check("E: consent screen shows before the camera opens", pg.is_visible(".to-consent") and pg.evaluate("!TRYON.state.stream") and "never uploaded or stored" in pg.inner_text(".to-consent"))
        pg.click("[data-to=camera]")
        try:
            wait_for(pg, "TRYON.state.lmS||document.querySelector('[data-pane=fallback]:not([hidden])')")
            ok = pg.evaluate("!!TRYON.state.lmS")
        except Exception:
            ok = False
        check("E: tracking starts on the live camera", ok, pg.inner_text(".tryon .to-left")[:200])
        check("E: camera view is mirrored", pg.evaluate("TRYON.state.mode") == "camera")
        check("E: 'Stop camera' button is shown", pg.is_visible("[data-to=stop]"))
        if ok:
            pick(pg, "face", found["f"], FOUNDATION_SHADE)
            pg.wait_for_timeout(1500)
            ms = pg.evaluate("TRYON.state.detMs.reduce((a,b)=>a+b,0)/Math.max(1,TRYON.state.detMs.length)")
            print(f"     tracking time per frame on this machine: {ms:.1f} ms")
            check("E: a shade applies on the live camera", pg.evaluate("!!TRYON.state.look.base"))
        pg.click("[data-to=stop]")
        pg.wait_for_timeout(200)
        check("E: 'Stop camera' turns the camera off", pg.evaluate("!TRYON.state.stream") and pg.is_visible(".to-start"))
        ctx.close(); bc.close()

        # F. no WebGL -> friendly message and swatches
        bf = p.chromium.launch(executable_path=CHROME, args=["--no-sandbox", "--disable-webgl", "--disable-3d-apis"])
        pg = bf.new_page(); pg.on("pageerror", lambda e: ERRORS.append(str(e)))
        pg.goto(url + "#try-on"); pg.wait_for_timeout(400)
        pg.click(".to-model >> nth=0"); pg.wait_for_timeout(300)
        pick(pg, "face", found["f"], FOUNDATION_SHADE)
        check("F: no WebGL -> falls back to shade swatches", pg.is_visible("[data-pane=fallback]") and "WebGL" in pg.inner_text("[data-pane=fallback]") and pg.locator(".to-fsl li").count() >= 1)
        bf.close()

        # screenshots: every model face x (bare, light, medium and deep foundation), all with the same lipstick
        if shots:
            from PIL import ImageDraw as _D
            bs = p.chromium.launch(executable_path=CHROME, args=["--no-sandbox"])
            pg = bs.new_page(viewport={"width": 1280, "height": 900}); pg.goto(url + "#try-on"); pg.wait_for_timeout(400)
            # one foundation with a light, a medium and a deep shade (depth 2-3, 5, 9-10)
            fp = pg.evaluate("""(()=>{let best=null;for(const p of CAT.filter(p=>p.c==='Foundation'&&p.s&&p.s.length)){
                const pick=ds=>p.s.find(s=>ds.includes(s[1]));const l=pick([2,3,1]),m=pick([5,6]),d=pick([9,10,8]);
                if(l&&m&&d&&(!best||d[1]-l[1]>best.span))best={id:p.id,n:p.n,span:d[1]-l[1],shades:[l[0],m[0],d[0]],depth:[l[1],m[1],d[1]]}}return best})()""")
            rows = []
            for m in MODELS:
                if pg.is_visible(".to-tools [data-to=start]"):
                    pg.click(".to-tools [data-to=start]")
                pg.click(f".to-model[data-i='{MODELS.index(m)}']"); pg.wait_for_timeout(300)
                pg.evaluate("TRYON.state.look={};TRYON.setSplit(0);TRYON._draw()")
                cells = [canvas_png(pg)]
                pick(pg, "lips", found["l"], LIPSTICK_SHADE)
                for sh in fp["shades"]:
                    pick(pg, "face", fp["id"], sh)
                    cells.append(canvas_png(pg))
                rows.append((m, cells))
                for tag, im in zip(("bare", "light", "medium", "deep"), cells):
                    im.save(shots / f"{m['id']}_{tag}.png")
            cw, ch, head, lab = 240, 300, 40, 150
            sheet = Image.new("RGB", (lab + cw * 4, head + ch * len(rows)), "white")
            dr = _D.Draw(sheet)
            for c, t in enumerate(["No makeup", f"Light: {fp['shades'][0]}", f"Medium: {fp['shades'][1]}", f"Deep: {fp['shades'][2]}"]):
                dr.text((lab + c * cw + 8, 12), t, fill=(60, 50, 40))
            for r, (m, cells) in enumerate(rows):
                dr.text((10, head + r * ch + ch // 2 - 10), m["label"], fill=(40, 30, 20))
                dr.text((10, head + r * ch + ch // 2 + 6), f"base {m['hex']} ~Monk {m['monk']}", fill=(110, 100, 90))
                for c, im in enumerate(cells):
                    sheet.paste(im.resize((cw, ch)), (lab + c * cw, head + r * ch))
            sheet.save(shots / "tryon_grid.png")
            (shots / "tryon_grid.json").write_text(json.dumps({"foundation": fp, "lipstick": {"product": found["l"], "shade": LIPSTICK_SHADE}}, indent=1))
            print(f"     screenshots saved to {shots} (foundation {fp['id']}: {fp['shades']})")
            bs.close()
    check("no JavaScript errors", not ERRORS, ERRORS[:3])
    print(f"\n{sum(RESULTS)}/{len(RESULTS)} passed")
    sys.exit(0 if all(RESULTS) else 1)


if __name__ == "__main__":
    main()
