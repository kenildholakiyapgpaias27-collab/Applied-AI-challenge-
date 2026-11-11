#!/usr/bin/env python3
"""Step 3 - run the advisor's own skin tone reader (index.html, unmodified) on every frame.

Loads each frame into a canvas in headless Chromium and calls readPhoto(canvas, oval), the same call the
app makes. Records the reader's measured skin colour (corrected Lab), tone, confidence, method and status.

    python3 run_reader.py work/manifest.csv --page ../../index.html --out work/features.csv
"""
import argparse, csv, json, pathlib, base64
from playwright.sync_api import sync_playwright
JS = """async ([url,oval])=>{const im=new Image();im.src=url;await im.decode();const s=Math.min(1,1200/Math.max(im.width,im.height));
  const c=document.createElement('canvas');c.width=Math.round(im.width*s);c.height=Math.round(im.height*s);c.getContext('2d').drawImage(im,0,0,c.width,c.height);
  const r=readPhoto(c,oval);const f=typeof detectFilter==='function'?detectFilter(c,oval).flags.map(x=>x.k).join('+'):'';
  return {status:r.status,tone:r.tone??'',L:r.lab?r.lab[0]:'',a:r.lab?r.lab[1]:'',b:r.lab?r.lab[2]:'',conf:r.conf??'',method:r.method||'',coverage:r.coverage??'',issues:(r.issues||[]).join('+'),filter:f}}"""
def main():
    ap = argparse.ArgumentParser(); ap.add_argument("manifest"); ap.add_argument("--page", default=str(pathlib.Path(__file__).resolve().parents[2] / "index.html")); ap.add_argument("--out", default="features.csv"); a = ap.parse_args()
    rows = list(csv.DictReader(open(a.manifest))); out = []
    with sync_playwright() as pw:
        b = pw.chromium.launch(); pg = b.new_page(); pg.route("https://**/*", lambda r: r.abort()); pg.goto("file://" + str(pathlib.Path(a.page).resolve())); pg.wait_for_timeout(300)
        for i, r in enumerate(rows):
            data = pathlib.Path(r["frame"]).read_bytes(); mime = "image/png" if r["frame"].lower().endswith(".png") else "image/jpeg"
            res = pg.evaluate(JS, [f"data:{mime};base64," + base64.b64encode(data).decode(), json.loads(r["oval"])]); out.append({**r, **res})
            if (i + 1) % 200 == 0: print(f"{i+1}/{len(rows)}", flush=True)
    with open(a.out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(out[0])); w.writeheader(); w.writerows(out)
    print(f"Read {len(out)} frames -> {a.out}")
if __name__ == "__main__": main()
