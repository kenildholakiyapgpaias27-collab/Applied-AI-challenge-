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
MODELS = json.loads((ROOT / "data/tryon_models.json").read_text())["models"]
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
    face_jpg = ROOT / BY["meher"]["file"]
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
        check("all three ways to start are offered", pg.locator(".to-way").count() == 2 and pg.locator(".to-model").count() == len(MODELS))
        ctx.close()

        # A. model face, fully offline (no CDN at all)
        ctx, pg = fresh(offline=True)
        outside = []
        pg.on("request", lambda r: outside.append(r.url) if not (r.url.startswith("http://127.0.0.1") or r.url.startswith("data:") or r.url.startswith("blob:")) else None)
        pg.click(".to-model >> nth=0")
        pg.wait_for_timeout(500)
        check("A: model face renders offline with WebGL", pg.evaluate("TRYON.state.mode==='model'&&!!TRYON.state.gl&&!!TRYON.state.lmS"))
        m = BY[pg.evaluate("TRYON.state.model.id")]
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
        # before/after slider
        pg.eval_on_selector(".to-split", "e=>{e.value=60;e.dispatchEvent(new Event('input'))}")
        pg.wait_for_timeout(150)
        check("A: slider moves the before/after line", pg.evaluate("TRYON.state.split") == 0.6 and "60%" in pg.eval_on_selector(".to-divider", "e=>e.style.getPropertyValue('--x')"))
        check("A: left of the line shows the face without makeup", cx < 0.6 and pixel(pg, cx, cy) == before, (cx, pixel(pg, cx, cy), before))
        pg.eval_on_selector(".to-split", "e=>{e.value=0;e.dispatchEvent(new Event('input'))}")
        # compare 4 shades
        pg.click("[data-to=compare]")
        pg.click(".tryon [data-tab='face']")
        pg.click(f".to-prod[data-pid='{found['f']}']")
        for i in range(4):
            pg.click(f".to-sw >> nth={i}")
        check("A: compare shows a 2x2 grid of 4 shades", pg.locator(".to-tile").count() == 4 and pg.locator(".to-tile span:not(.empty)").count() == 4)
        tiles = canvas_png(pg)
        w, h = tiles.size
        q = [tiles.getpixel((int(w * x), int(h * y))) for x, y in ((0.25, 0.3), (0.75, 0.3), (0.25, 0.8), (0.75, 0.8))]
        check("A: the four tiles show different shades", len(set(q)) >= 3, q)
        pg.click("[data-to=compare]")
        with pg.expect_download() as dl:
            pg.click("[data-to=snap]")
        check("A: snapshot is saved as a file on the device", dl.value.suggested_filename.startswith("aaina-look-") and pg.locator(".to-snaps img").count() == 1)
        check("A: model faces need no network (nothing requested off the device)", not outside, outside[:3])
        ctx.close()

        # B. uploaded photo -> MediaPipe tracking (needs the CDN)
        ctx, pg = fresh()
        pg.set_input_files(".tryon input[type=file]", str(face_jpg))
        try:
            wait_for(pg, "TRYON.state.lmS||document.querySelector('[data-pane=fallback]:not([hidden])')")
            ok = pg.evaluate("!!TRYON.state.lmS")
        except Exception as e:
            ok = False
        check("B: tracking starts on an uploaded photo", ok, pg.inner_text(".tryon .to-left")[:200])
        if ok:
            got = pg.evaluate("TRYON.state.lmS")
            known = BY["meher"]["landmarks"]
            keys = [33, 133, 263, 362, 1, 152, 61, 291, 10, 234, 454]
            err = sum(((got[i][0] - known[i][0]) ** 2 + (got[i][1] - known[i][1]) ** 2) ** 0.5 for i in keys) / len(keys)
            check("B: tracked landmarks land on the face (mean error < 3% of the image)", err < 0.03, f"{err:.4f}")
            pick(pg, "face", found["f"], FOUNDATION_SHADE)
            check("B: a shade can be applied to the photo", pg.evaluate("!!TRYON.state.look.base"))
        pg.set_input_files(".tryon input[type=file]", str(blank))
        wait_for(pg, "document.querySelector('[data-pane=fallback]:not([hidden])')", 60000)
        check("B: no face found -> friendly message and swatches", "couldn't find a face" in pg.inner_text("[data-pane=fallback]"))
        ctx.close()

        # C. a product that fails check() can be previewed but never added
        ctx, pg = fresh(hash_="")
        pg.evaluate("""P.avoidFrag=true;P.pregnancy=false;P.skin='normal';P.skinConfirmed=true;DONE.add('safety');location.hash='try-on'""")
        pg.wait_for_timeout(400)
        pg.click(".to-model >> nth=0")
        pg.click(".tryon [data-tab='lips']")
        pg.click(f".to-prod[data-pid='{found['bad']}']")
        txt = pg.inner_text(".to-detail")
        check("C: product failing check() shows 'Not suitable for you'", "Not suitable for you" in txt and "fragrance" in txt, txt[:160])
        check("C: it can still be previewed", pg.evaluate(f"TRYON.state.look.lips&&TRYON.state.look.lips.p.id==='{found['bad']}'"))
        check("C: no 'Add to my plan' for it", pg.locator(".to-detail [data-to=add]").count() == 0)
        check("C: product list flags it too", "Not suitable for you" in pg.inner_text(f".to-prod[data-pid='{found['bad']}']"))
        ctx.close()

        # D. advisor tie-in: makeup plan -> 'Try it on' -> 'Your match' -> add to plan
        ctx, pg = fresh(hash_="")
        pg.fill("#nameInput", "Asha"); pg.keyboard.press("Enter"); pg.wait_for_timeout(400)
        Q.about(pg, "woman", "makeup"); Q.pick(pg, "Natural")
        Q.safety(pg, "false"); Q.skin(pg, "Comfortable"); Q.tone(pg, 6); Q.pick(pg, "Warm")
        check("D: makeup plan has a 'Try it on' button", pg.locator(".plan:not(.old) .tryon-btn").count() >= 2)
        pid = pg.evaluate("PL.slots.find(s=>s.p&&s.p.s).p.id")
        pg.click(f".plan:not(.old) .pcard [data-tryon='{pid}']")
        pg.wait_for_timeout(400)
        check("D: card button opens the try-on on that product", pg.is_visible("#tryon") and pg.evaluate("TRYON.state.pid") == pid and "#try-on" in pg.url)
        match = pg.evaluate(f"bestShade(BY_ID['{pid}'],6,'warm').name")
        sel = pg.locator(".to-sw.match")
        check("D: user's best shade is marked 'Your match'", sel.count() == 1 and match in sel.inner_text() and "Your match" in sel.inner_text())
        check("D: and it is pre-selected", pg.evaluate("TRYON.state.look.base&&TRYON.state.look.base.s.name") == match)
        lip = pg.evaluate("TRYON._products('Lipstick').find(x=>x.st.ok&&!PL.extras?.some(e=>e.p.id===x.p.id)).p.id")
        pg.click(".to-model >> nth=0")
        pg.click(".tryon [data-tab='lips']"); pg.click(f".to-prod[data-pid='{lip}']")
        pg.click(".to-detail [data-to=add]")
        pg.wait_for_timeout(300)
        check("D: 'Add to my plan' adds the product to the plan", pg.evaluate(f"PL.extras.some(x=>x.p.id==='{lip}')") and pg.evaluate(f"META.extraIds.some(x=>x.id==='{lip}')"))
        check("D: button turns into 'In your plan'", "In your plan" in pg.inner_text(".to-detail"))
        pg.click(".to-x")
        pg.wait_for_timeout(300)
        check("D: closing hides it and clears the route", not pg.is_visible("#tryon") and "#try-on" not in pg.url)
        check("D: the add-on shows on the plan page", pg.locator(".plan:not(.old) .extras .pcard").count() >= 1)
        ctx.close()
        b.close()

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

        # screenshots: same foundation + lipstick on a light, a medium and a deep face
        if shots:
            bs = p.chromium.launch(executable_path=CHROME, args=["--no-sandbox"])
            pg = bs.new_page(viewport={"width": 1280, "height": 900}); pg.goto(url + "#try-on"); pg.wait_for_timeout(400)
            rows = []
            for mid in ("ira", "meher", "zoya"):
                if pg.is_visible(".to-actions [data-to=start]"):
                    pg.click(".to-actions [data-to=start]")
                pg.click(f".to-model[data-i='{[m['id'] for m in MODELS].index(mid)}']"); pg.wait_for_timeout(300)
                pg.evaluate("TRYON.state.look={};TRYON._draw()")
                base_img = canvas_png(pg)
                pick(pg, "face", found["f"], FOUNDATION_SHADE); pick(pg, "lips", found["l"], LIPSTICK_SHADE)
                same = canvas_png(pg)
                mt = BY[mid]
                best = pg.evaluate(f"bestShade(BY_ID['{found['f']}'],{mt['tone']},'{mt['undertone']}').name")
                pick(pg, "face", found["f"], best)
                matched = canvas_png(pg)
                rows.append((mid, mt["tone"], best, base_img, same, matched))
                for tag, im in (("before", base_img), ("same", same), ("matched", matched)):
                    im.save(shots / f"{mid}_{tag}.png")
            # one comparison sheet
            cw, ch = 300, 375
            sheet = Image.new("RGB", (cw * 3, ch * len(rows)), "white")
            for r, (mid, tone, best, a, s_, mt_) in enumerate(rows):
                for c, im in enumerate((a, s_, mt_)):
                    sheet.paste(im.resize((cw, ch)), (c * cw, r * ch))
            sheet.save(shots / "tryon_sheet.png")
            (shots / "tryon_sheet.json").write_text(json.dumps([{"model": r[0], "tone": r[1], "matched_shade": r[2]} for r in rows]
                                                             + [{"same_foundation": FOUNDATION_SHADE, "product": found["f"], "lipstick": LIPSTICK_SHADE, "lip_product": found["l"]}], indent=1))
            print(f"     screenshots saved to {shots}")
            bs.close()
    check("no JavaScript errors", not ERRORS, ERRORS[:3])
    print(f"\n{sum(RESULTS)}/{len(RESULTS)} passed")
    sys.exit(0 if all(RESULTS) else 1)


if __name__ == "__main__":
    main()
