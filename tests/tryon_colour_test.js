#!/usr/bin/env node
/* Unit tests for the try-on colour and blend maths (TRYON_COLOUR in src/tryon.js).

    node tests/tryon_colour_test.js

The fragment shader mirrors these functions, so they define how makeup looks. */
const fs = require("fs"), path = require("path"), vm = require("vm");
const src = fs.readFileSync(path.join(__dirname, "..", "src", "tryon.js"), "utf8");
const ctx = {console, Math, JSON, Number, String, Object, Array};
vm.createContext(ctx);
vm.runInContext(src + "\nthis.C=TRYON_COLOUR;this.T=TRYON;this.LM=TRYON_LM;", ctx);
const C = ctx.C;
let pass = 0, fail = 0;
function check(name, cond, detail = "") { if (cond) { pass++; console.log("PASS " + name) } else { fail++; console.log("FAIL " + name + "   " + detail) } }
const near = (a, b, t) => Math.abs(a - b) <= t;
const MONK = {1: "#f6ede4", 2: "#f3e7db", 3: "#f7ead0", 4: "#eadaba", 5: "#d7bd96", 6: "#a07e56", 7: "#825c43", 8: "#604134", 9: "#3a312a", 10: "#292420"};
const L = h => C.hexToLin(h), ok = h => C.oklab(L(h));

// conversions
check("module loads without a DOM (no UI built)", ctx.T === null);
check("hex parses and round-trips", ["#000000", "#ffffff", "#a07e56", "#3a312a"].every(h => C.rgbToHex(C.hexToRgb(h)) === h));
check("bad hex is rejected", C.hexToRgb("#12345") === null && C.hexToRgb("red") === null && C.hexToLin("") === null);
check("sRGB <-> linear round-trips", [0, 1, 17, 128, 254, 255].every(v => near(C.l2s(C.s2l(v)), v, 0.01)));
check("OKLab round-trips", Object.values(MONK).every(h => { const l = L(h), r = C.fromOklab(C.oklab(l)); return r.every((v, i) => near(v, l[i], 1e-4)) }));
check("OKLab: white is L=1, black is L=0", near(C.oklab([1, 1, 1])[0], 1, 1e-3) && near(C.oklab([0, 0, 0])[0], 0, 1e-6));

// product data -> parameters
check("coverage: sheer < medium < full", C.coverageAlpha("sheer") < C.coverageAlpha("medium") && C.coverageAlpha("medium") < C.coverageAlpha("full"));
check("coverage: unknown falls back to medium", C.coverageAlpha("weird") === C.coverageAlpha("medium") && C.coverageAlpha(undefined) === C.coverageAlpha("medium"));
check("finish codes", C.baseFinish("matte") === 0 && C.baseFinish("natural") === 1 && C.baseFinish("dewy") === 2 && C.baseFinish(null) === 1);
check("lip finishes: sheer is the most see-through", C.lipAlpha("sheer") < C.lipAlpha("gloss") && C.lipAlpha("gloss") < C.lipAlpha("matte"));

// foundation behaviour
const flat = (skin, shade, cov, fin = "natural") => C.onSkin(skin, shade, cov, fin);
check("a matching shade barely changes the skin (dE < 3)", C.deltaE(flat(MONK[6], MONK[6], "full"), MONK[6]) < 3, C.deltaE(flat(MONK[6], MONK[6], "full"), MONK[6]).toFixed(2));
const cov = ["sheer", "medium", "full"].map(c => C.deltaE(flat(MONK[9], MONK[5], c), MONK[9]));
check("more coverage moves the colour further from the skin", cov[0] < cov[1] && cov[1] < cov[2], cov.map(x => x.toFixed(1)).join(" < "));
{
  // too light on deep skin: lighter AND greyer (ashy) than a plain colour mix would be
  const res = L(flat(MONK[9], MONK[3], "medium")), a = C.coverageAlpha("medium");
  const plain = C.fromOklab([0, 1, 2].map(i => ok(MONK[9])[i] + (ok(MONK[3])[i] - ok(MONK[9])[i]) * a));
  check("too-light shade on deep skin is lighter", C.oklab(res)[0] > ok(MONK[9])[0] + 0.1);
  check("too-light shade on deep skin looks ashy (chroma below a plain mix)", C.chroma(res) < 0.75 * C.chroma(plain), `${C.chroma(res).toFixed(3)} vs ${C.chroma(plain).toFixed(3)}`);
  check("too-light shade on deep skin is greyer than the skin itself", C.chroma(res) < C.chroma(L(MONK[9])), `${C.chroma(res).toFixed(3)} vs ${C.chroma(L(MONK[9])).toFixed(3)}`);
  const res2 = L(flat(MONK[2], MONK[3], "medium"));
  check("a near-match on light skin is not ashy", C.chroma(res2) > 0.8 * C.chroma(L(MONK[2])));
  const res3 = L(flat(MONK[3], MONK[9], "medium"));
  const plain3 = C.fromOklab([0, 1, 2].map(i => ok(MONK[3])[i] + (ok(MONK[9])[i] - ok(MONK[3])[i]) * a));
  check("too-dark shade on light skin darkens with no extra ashy greying", C.oklab(res3)[0] < ok(MONK[3])[0] - 0.1 && near(C.chroma(res3), C.chroma(plain3), 0.004),
    `${C.chroma(res3).toFixed(3)} vs plain ${C.chroma(plain3).toFixed(3)}`);
}
{
  // texture and shading are kept
  const M = L(MONK[6]), B = M.slice(), shade = L(MONK[5]), a = C.coverageAlpha("full");
  const pore = B.map(v => v * 0.8), hi = B.map(v => v * 1.25), shadow = M.map(v => v * 0.5);
  const o0 = C.base(B, B, M, shade, a, 1), oPore = C.base(pore, B, M, shade, a, 1), oHi = C.base(hi, B, M, shade, a, 1);
  check("texture kept: a darker pore stays darker", C.lum(oPore) < C.lum(o0) * 0.95);
  check("texture kept: highlight stays brighter", C.lum(oHi) > C.lum(o0) * 1.05);
  check("full coverage softens texture a little (not erased)", C.lum(oPore) / C.lum(o0) > 0.8 && C.lum(oPore) / C.lum(o0) < 0.95);
  const oSh = C.base(shadow, shadow, M, shade, a, 1);
  check("shading kept: a shadowed area stays darker", C.lum(oSh) < 0.7 * C.lum(o0));
  const matte = C.base(hi, B, M, shade, a, 0), dewy = C.base(hi, B, M, shade, a, 2);
  check("matte flattens highlights", C.lum(matte) < C.lum(oHi));
  const bright = M.map(v => v * 1.3), dewyHi = C.base(bright, bright, M, shade, a, 2), natHi = C.base(bright, bright, M, shade, a, 1);
  check("dewy adds glow on lit areas", C.lum(dewyHi) > C.lum(natHi));
  check("every output is a valid colour", [o0, oPore, oHi, oSh, matte, dewy].every(c => c.every(v => Number.isFinite(v) && v >= 0)));
}
{
  // lips, blush, liner
  const lipM = L("#9a5a55"), lipc = L("#b3262f");
  const flatL = C.lip(lipM, lipM, lipM, lipc, C.lipAlpha("matte"), 0), crease = C.lip(lipM.map(v => v * 0.7), lipM, lipM, lipc, C.lipAlpha("matte"), 0);
  check("lipstick moves the lip towards the shade", C.deltaE(C.linToHex(flatL), "#b3262f") < C.deltaE("#9a5a55", "#b3262f"));
  check("lip creases stay visible", C.lum(crease) < C.lum(flatL));
  const sheen = C.lip(lipM.map(v => v * 1.2), lipM, lipM, lipc, C.lipAlpha("gloss"), 3), noSheen = C.lip(lipM.map(v => v * 1.2), lipM, lipM, lipc, C.lipAlpha("gloss"), 0);
  check("gloss adds a highlight", C.lum(sheen) > C.lum(noSheen));
  const skin = L(MONK[4]), bl = C.blush(skin, skin, skin, L("#d07985"), 0.75, 0);
  check("blush adds warmth (redder than the skin)", bl[0] / bl[1] > skin[0] / skin[1]);
  const deep = L(MONK[9]), blD = C.blush(deep, deep, deep, L("#d07985"), 0.75, 0);
  check("blush stays subtle on deep skin (no pink mask)", C.deltaE(C.linToHex(blD), MONK[9]) < 15, C.deltaE(C.linToHex(blD), MONK[9]).toFixed(1));
  const ln = C.liner(skin, skin, skin, L("#141112"), 0.9, false);
  check("kajal darkens the lash line", C.lum(ln) < 0.2 * C.lum(skin));
}
// landmark sets are well formed
const LM = ctx.LM;
const all = [].concat(LM.oval, LM.lipsOut, LM.lipsIn, LM.eyeR.up, LM.eyeR.lo, LM.eyeL.up, LM.eyeL.lo, LM.browR, LM.browL, LM.cheekR, LM.cheekL, LM.skin, LM.lip);
check("landmark indices are within the 478-point mesh", all.every(i => Number.isInteger(i) && i >= 0 && i < 478));
check("face oval is a closed 36-point contour", LM.oval.length === 36 && new Set(LM.oval).size === 36);

console.log(`\n${pass}/${pass + fail} passed`);
process.exit(fail ? 1 : 0);
