#!/usr/bin/env node
/* Runs the REAL advisor engine (src/engine.js) on test-set profiles. Called by tools/eval_testset.py.

    node tools/eval_engine.js <inputs.json> <out.json>

inputs.json holds only what a customer tells the quiz (self-reported fields). If any key starting
with "true_" reaches this script, it stops: ground truth is for scoring only and lives in Python.

For each profile it maps the answers to the profile object P exactly as the quiz does, then records:
  - top-5 ranked products per category (engine rank(), which only returns products passing check())
  - every product that passes check() (the try-on shows the rest as "Not suitable for you")
  - for every foundation: the try-on's "Your match" (bestShade with the self-reported tone and
    undertone, as matchFor() in src/tryon.js calls it), plus the same call with the engine's own
    self-report tone correction (correctedTone, defined in engine.js but not used by the app today)
*/
const fs = require("fs"), path = require("path"), vm = require("vm");
const ROOT = path.join(__dirname, "..");
const [, , inPath, outPath, monthArg] = process.argv;
const input = JSON.parse(fs.readFileSync(inPath, "utf8"));

// guard: never let ground truth in
for (const row of input.profiles) for (const k of Object.keys(row)) if (/^true_/.test(k)) { console.error(`REFUSED: input field ${k} is ground truth`); process.exit(2) }

// guard: the try-on must still compute "Your match" the way this harness calls it
const tryon = fs.readFileSync(path.join(ROOT, "src/tryon.js"), "utf8");
if (!tryon.includes('bestShade(p,tone,P.undertone||"neutral")')) { console.error("src/tryon.js matchFor() changed: update the harness"); process.exit(3) }

const ctx = {console, Math, JSON, Number, String, Object, Array, Set, Map, RegExp, Date, parseFloat, parseInt, isNaN};
ctx.CAT = JSON.parse(fs.readFileSync(path.join(ROOT, "data/catalogue.json"), "utf8"));
const cal = path.join(ROOT, "data/calibration.json");
ctx.AAINA_CAL = fs.existsSync(cal) ? JSON.parse(fs.readFileSync(cal, "utf8")) : null;
vm.createContext(ctx);
vm.runInContext(fs.readFileSync(path.join(ROOT, "src/engine.js"), "utf8") +
  "\nthis.E={emptyProfile,check,rank,bestShade,correctedTone,REACTIONS,setP:v=>{P=v},getP:()=>P};", ctx);
const E = ctx.E;

const CONCERN_KEYS = new Set(["acne", "pigmentation", "dullness", "dehydration", "oiliness", "tanning", "redness"]);
const BUDGET_OPTS = [400, 700, 1200, null];      // the Tune-your-plan options in src/app.js
const bandMax = {"under ₹500": 500, "₹500–1,000": 1000, "₹1,000–2,000": 2000, "over ₹2,000": null};

function toProfile(r, month) {
  const P = E.emptyProfile();
  const notes = [];
  P.month = month;
  P.city = r.city; P.climate = r.climate;
  P.skin = r.skin_type_self; P.skinConfirmed = true;                     // skin step
  const cs = String(r.concerns || "").split(",").map(s => s.trim()).filter(Boolean);
  P.concerns = cs.filter(c => CONCERN_KEYS.has(c));
  const dropped = cs.filter(c => !CONCERN_KEYS.has(c)); if (dropped.length) notes.push(`concerns the quiz can't take: ${dropped.join(", ")}`);
  P.avoidFrag = !!r.avoid_fragrance; P.avoidEO = !!r.avoid_essential_oils; P.sensitive = !!r.sensitive_skin_self;   // avoid step
  P.reactions = [];
  if (r.known_reactions_to) {                                              // react step, typed answer matched like the quiz does
    const hit = Object.entries(E.REACTIONS).find(([, fam]) => fam.say.test(r.known_reactions_to));
    if (hit) P.reactions = [hit[0]]; else notes.push(`reaction not recognised: ${r.known_reactions_to}`);
  }
  P.pregnancy = !!r.pregnancy_caution_optin;                               // preg step: yes / no
  const mx = bandMax[r.budget_band];                                       // Tune panel: the largest option not above the band
  P.budget = mx == null ? null : BUDGET_OPTS.filter(b => b != null && b <= mx).pop() ?? BUDGET_OPTS[0];
  P.tone = r.monk_tone_self; P.toneSource = "you picked";                  // tone step
  const ut = String(r.undertone_self || "").toLowerCase();
  if (ut === "don't know" || ut === "dont know" || ut === "unsure" || !ut) { P.undertone = null; P.undertoneSource = "unsure" }
  else { P.undertone = ut; P.undertoneSource = "you picked" }
  return {P, notes};
}

const month = monthArg != null ? +monthArg : new Date().getMonth();
const cats = input.categories;
const foundations = ctx.CAT.filter(p => p.c === "Foundation" && p.s && p.s.length).map(p => p.id);
const out = {month, profiles: []};
for (const r of input.profiles) {
  const {P, notes} = toProfile(r, month);
  E.setP(P);
  const top5 = {};
  for (const c of cats) top5[c] = E.rank(c, P).slice(0, 5).map(p => p.id);
  const passing = ctx.CAT.filter(p => E.check(p, P).ok).map(p => p.id);
  const blocked = {};
  for (const p of ctx.CAT) { const res = E.check(p, P); if (!res.ok) blocked[p.id] = res.blocks.map(b => b[1]).join("; ") }
  const match = {};
  for (const id of foundations) {
    const p = ctx.CAT.find(x => x.id === id);
    const idx = m => m ? p.s.findIndex(s => s[0] === m.name && s[3] === m.hex) : -1;
    const tryon = E.bestShade(p, P.tone, P.undertone || "neutral");          // == matchFor() in src/tryon.js
    const corr = E.bestShade(p, E.correctedTone(P.tone), P.undertone || "neutral");
    match[id] = {tryon: idx(tryon), tryon_good: !!(tryon && tryon.good), corrected: idx(corr)};
  }
  out.profiles.push({customer_id: r.customer_id, P: JSON.parse(JSON.stringify(P)), notes, top5, passing, blocked, match});
}
fs.writeFileSync(outPath, JSON.stringify(out));
console.log(`engine run: ${out.profiles.length} profiles, month ${month}`);
