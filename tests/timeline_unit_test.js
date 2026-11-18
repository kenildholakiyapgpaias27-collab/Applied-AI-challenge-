#!/usr/bin/env node
/* Unit tests for the Results timeline (src/timeline.js + data/evidence/actives_timeline.json). No browser.

    node tests/timeline_unit_test.js
*/
const fs = require("fs"), path = require("path"), vm = require("vm"), cp = require("child_process");
const ROOT = path.join(__dirname, "..");
const EV = JSON.parse(fs.readFileSync(path.join(ROOT, "data/evidence/actives_timeline.json"), "utf8"));
const CAT = JSON.parse(fs.readFileSync(path.join(ROOT, "data/catalogue.json"), "utf8"));
const ctx = { console, Math, JSON, Set, Map, Float32Array, Uint8ClampedArray, Number, String, Object, Array, RegExp };
vm.createContext(ctx);
vm.runInContext("const TIMELINE_EVIDENCE=" + JSON.stringify(EV) + ";\n" + fs.readFileSync(path.join(ROOT, "src/timeline.js"), "utf8") + "\nthis.T=TIMELINE;", ctx);
const T = ctx.T;
let pass = 0, fail = 0;
const check = (name, cond, detail = "") => { cond ? pass++ : fail++; console.log((cond ? "PASS " : "FAIL ") + name + (cond ? "" : "   " + String(detail).slice(0, 300))) };

// ---------- evidence schema (the Python checker is the source of truth) ----------
const r = cp.spawnSync("python3", [path.join(ROOT, "tools/check_evidence.py")], { encoding: "utf8" });
check("evidence schema, references and wording pass tools/check_evidence.py", r.status === 0, (r.stdout || "") + (r.stderr || ""));

// ---------- productTimeline invariants over the whole catalogue ----------
const SKIN = new Set(["Serum", "Moisturiser", "Sunscreen", "Cleanser", "Toner", "Exfoliant", "Face mask", "Eye cream", "Spot treatment", "Lip care", "Face oil"]);
const CONCERNS = ["pigmentation", "tanning", "acne", "oiliness", "dullness", "dehydration", "fine lines", "redness", "dark circles"];
const byId = Object.fromEntries(EV.entries.map(e => [e.id, e]));
let n = 0, pastLast = [], overHigh = [], notLow = [], badStops = [], banned = [], rinse = [];
for (const p of CAT.filter(p => SKIN.has(p.c))) {
  for (const c of CONCERNS) {
    for (const prof of [{}, { sensitive: true }]) {
      const t = T.productTimeline(p, prof, { concern: c }); n++;
      for (const s of T.textsOf(t)) if (T.BANNED.test(s)) banned.push(`${p.id}/${c}: ${s.match(T.BANNED)[0]} in "${s.slice(0, 60)}"`);
      if (t.grade === "D") { if (p.c === "Cleanser" || p.c === "Face mask") rinse.push(p.id); if (t.stops) badStops.push(p.id + " D with stops"); continue }
      if (!t.stops || t.stops.length !== 5) { badStops.push(p.id); continue }
      const e = byId[t.entryId], cps = e.checkpoints.filter(x => x.representative !== false), last = Math.max(...cps.map(x => x.weeks));
      for (const s of t.stops) {
        // a number may only be one a study measured at or before this stop (labelled with its real week), never one after the last study point
        if (s.value != null && (s.measuredAt == null || s.measuredAt > last || s.measuredAt > s.w + 1)) pastLast.push(`${p.id} ${e.id} @${s.w}w`);
        if (s.value != null && Math.abs(s.measuredAt - s.w) > 1.01 && !/measured at/.test(s.short)) pastLast.push(`${p.id} ${e.id} @${s.w}w not labelled with its real week`);
        if (s.status !== "measured" && s.value != null) pastLast.push(`${p.id} ${e.id} @${s.w}w ${s.status} has a number`);
        if (s.status === "measured" && s.value != null) {
          const ck = cps.find(x => x.weeks === s.measuredAt && (x.change_low === s.value || x.change_typical === s.value || x.change_high === s.value));
          const hi = ck && Math.max(...[ck.change_high, ck.change_typical, ck.change_low].filter(v => v != null));
          if (!ck || s.value > hi) overHigh.push(`${p.id} ${e.id} @${s.w}w ${s.value}`);
          const pct = T.strengthOf(p, e), down = e.active !== "Sunscreen" && (pct == null || (e.studied_pct != null && pct < e.studied_pct));
          if (down && ck && s.value !== ck.change_low) notLow.push(`${p.id} ${e.id} ${pct}% -> ${s.value}`);
        }
      }
    }
  }
}
check(`checked ${n} product x concern x profile combinations`, n > 1000, n);
check("no number past the last study week: only measured numbers, labelled with their real week; none at early/gap/maintenance points", !pastLast.length, pastLast.slice(0, 5));
check("no number above the study's own figures (never exceeds change_high)", !overHigh.length, overHigh.slice(0, 5));
check("unknown or lower strength uses change_low, or shows no number", !notLow.length, notLow.slice(0, 5));
check("every timeline has exactly 5 stops (2w, 4w, 3m, 6m, 1y), grade D has none", !badStops.length, badStops.slice(0, 5));
check("rinse-off cleansers and masks get no timeline", rinse.length > 0 && CAT.filter(p => p.c === "Cleanser" || p.c === "Face mask").every(p => T.productTimeline(p, {}, { concern: "acne" }).grade === "D"));
check("wording lint: no banned words in any timeline string", !banned.length, banned.slice(0, 5));

// spot checks
const find = (re, c) => CAT.find(p => re.test(p.a || "") && (!c || p.c === c));
const ret = find(/Retinol 0\.1%/), rt = T.productTimeline(ret, {}, { concern: "fine lines" });
check("retinol 0.1%: too early at 2 weeks, 44% at 1 year from the one-year study", rt.stops[0].status === "early" && rt.stops[4].value === 44 && rt.stops[4].ref === "25738849", JSON.stringify(rt.stops.map(s => [s.status, s.value])));
check("retinol: 6 months is a gap with no number (no study point there)", rt.stops[3].status === "gap" && rt.stops[3].value == null);
const ret2 = CAT.find(p => /retinol/i.test(p.a || "") && !/\d\s*%/.test((p.a || "").split(/retinol/i)[1] || "x"));
if (ret2) { const t2 = T.productTimeline(ret2, {}, { concern: "fine lines" }); check("retinol with no stated strength: the 1-year number is withheld (no change_low)", t2.stops[4].value == null && /smaller/.test(t2.stops[4].short)) }
const ha = find(/Hyaluronic/i, "Serum"), ht = T.productTimeline(ha, {}, { concern: "dehydration" });
check("hyaluronic acid: maintenance after the last study point (8 weeks)", ht.stops[3].status === "maintenance" && ht.stops[4].status === "maintenance" && ht.stops.every(s => s.value == null));
const sens = T.productTimeline(ret, { sensitive: true }, { concern: "fine lines" });
check("sensitive skin + an active that can sting: adjustment note added", sens.notes.some(x => /start slowly/.test(x)));
const lic = find(/Licorice/i), lt = T.productTimeline(lic, {}, { concern: "pigmentation" });
check("licorice only: grade D, no timeline, says not enough evidence", lt.grade === "D" && !lt.stops && /Not enough evidence/.test(lt.reason), lt.reason);
const spf = CAT.find(p => p.c === "Sunscreen"), plan = T.planTimeline([spf, ret], {}, ["fine lines"]);
check("plan timeline: best product drives each concern, sunscreen shows its long-term protective role",
  plan.lines[0].product === ret && plan.sunscreen && plan.sunscreen.protective.length && /24% less/.test(plan.sunscreen.protective[0].plain));
const txa = find(/Tranexamic/i), tt = T.productTimeline(txa, {}, { concern: "pigmentation" });
check("non-representative study (diagnosed condition) never drives the numbers", tt.stops.every(s => s.ref !== "40923777") && tt.side.some(x => x.ref === "40923777"));

// ---------- illustration: only the concern region changes, never overall lightness ----------
const W = 120, H = 140, data = new Uint8ClampedArray(W * H * 4), mask = new Float32Array(W * H);
let seed = 7; const rnd = () => (seed = (seed * 16807) % 2147483647) / 2147483647;
for (let y = 0; y < H; y++) for (let x = 0; x < W; x++) {
  const i = (y * W + x) * 4, spot = ((x - 60) ** 2 + (y - 60) ** 2 < 36) || ((x - 40) ** 2 + (y - 80) ** 2 < 16);
  const base = [196, 150, 120].map(v => v + (rnd() - 0.5) * 16 - (spot ? 45 : 0));
  data[i] = base[0]; data[i + 1] = base[1]; data[i + 2] = base[2]; data[i + 3] = 255;
  const inF = ((x - 60) / 45) ** 2 + ((y - 70) / 55) ** 2; mask[y * W + x] = inF < 0.8 ? 1 : inF < 1 ? (1 - inF) / 0.2 : 0;
}
const lstar = (r, g, b) => { const l = c => { c /= 255; return c <= 0.04045 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4 }; const Y = 0.2126 * l(r) + 0.7152 * l(g) + 0.0722 * l(b); return Y > 216 / 24389 ? 116 * Math.cbrt(Y) - 16 : 903.3 * Y };
const stats = (d, sel) => { let L = 0, n = 0, R = 0, G = 0, B = 0; for (let i = 0; i < W * H; i++) if (sel(i)) { L += lstar(d[i * 4], d[i * 4 + 1], d[i * 4 + 2]); R += d[i * 4]; G += d[i * 4 + 1]; B += d[i * 4 + 2]; n++ } return { L: L / n, R: R / n, G: G / n, B: B / n } };
for (const type of ["spots", "texture", "shine", "redness"]) {
  const out = T.illustrate(data, W, H, mask, type, 0.5);
  let outsideSame = true; for (let i = 0; i < W * H; i++) if (mask[i] === 0 && (out[i * 4] !== data[i * 4] || out[i * 4 + 1] !== data[i * 4 + 1] || out[i * 4 + 2] !== data[i * 4 + 2])) { outsideSame = false; break }
  const before = stats(data, i => mask[i] > 0), after = stats(out, i => mask[i] > 0), allB = stats(data, () => true), allA = stats(out, () => true);
  check(`illustration (${type}): pixels outside the concern mask are unchanged`, outsideSame);
  check(`illustration (${type}): overall L* does not increase (inside mask and whole image)`, after.L <= before.L + 0.05 && allA.L <= allB.L + 0.05, `${before.L.toFixed(2)} -> ${after.L.toFixed(2)}`);
  check(`illustration (${type}): average colour inside the mask stays within 2 levels (no tone/undertone shift)`,
    Math.abs(after.R - before.R) < 2 && Math.abs(after.G - before.G) < 2 && Math.abs(after.B - before.B) < 2, JSON.stringify([before, after]));
}
const sp = T.illustrate(data, W, H, mask, "spots", 0.5), spotSel = i => { const x = i % W, y = (i / W) | 0; return (x - 60) ** 2 + (y - 60) ** 2 < 36 };
check("illustration (spots): spots become less contrasting with the skin around them", stats(sp, spotSel).L > stats(data, spotSel).L);
check("illustration: zero strength returns the image untouched", T.illustrate(data, W, H, mask, "spots", 0).every((v, i) => v === data[i]));

// ---------- fictional product studies: present for every product, always marked, never mixed with real evidence ----------
const SAM = JSON.parse(fs.readFileSync(path.join(ROOT, "data/evidence/sample_product_studies.json"), "utf8"));
const ctx2 = { console, Math, JSON, Set, Map, Float32Array, Uint8ClampedArray, Number, String, Object, Array, RegExp };
vm.createContext(ctx2);
vm.runInContext("const TIMELINE_EVIDENCE=" + JSON.stringify(EV) + ";\nconst TIMELINE_SAMPLES=" + JSON.stringify(SAM) + ";\n" + fs.readFileSync(path.join(ROOT, "src/timeline.js"), "utf8") + "\nthis.T=TIMELINE;", ctx2);
const T2 = ctx2.T, skin = CAT.filter(p => SKIN.has(p.c));
check("every skincare product has a sample study, and the file is marked fictional", SAM.fictional === true && skin.every(p => SAM.studies[p.id]), skin.filter(p => !SAM.studies[p.id]).length);
const leaks = JSON.stringify(SAM).match(/pmid|doi|pubmed|journal|author|ncbi/i);
check("sample studies carry nothing that could pass for a real citation (no PMID, DOI, journal, author)", !leaks, leaks && leaks[0]);
let same = true, marked = true, sbanned = [];
for (const p of skin) for (const c of ["pigmentation", "acne", "dehydration"]) {
  const a = T.productTimeline(p, {}, { concern: c }), b = T2.productTimeline(p, {}, { concern: c });
  const strip = t => JSON.stringify({ g: t.grade, s: t.stops, n: t.notes, h: t.hasNumeric });
  if (strip(a) !== strip(b)) same = false;
  if (!b.sample || b.sample.fictional !== true || !/fictional/i.test(b.sample.label)) marked = false;
  for (const x of T2.textsOf(b)) if (T2.BANNED.test(x)) sbanned.push(`${p.id}: ${x.match(T2.BANNED)[0]}`);
}
check("sample studies never change the real timeline (grade, stops, numbers, illustration)", same);
check("every sample study is labelled 'Sample data · fictional'", marked);
check("wording lint passes for every sample-study sentence", !sbanned.length, sbanned.slice(0, 3));
const app = fs.readFileSync(path.join(ROOT, "src/app.js"), "utf8");
check("the compare view never ranks by the sample study (best fit uses real evidence only)", /fits\.sort\(\(a,b\)=>RK\[a\.t\.grade\]/.test(app) && !/fits\.sort[^;]*sample/.test(app));

console.log(`\n${pass}/${pass + fail} passed`);
process.exit(fail ? 1 : 0);
