#!/usr/bin/env node
/* Unit tests for Continue with Google (PKCE) in src/db.js. No browser, no network.

    node tests/oauth_unit_test.js

Loads the real src/db.js in a sandbox with a fake window (location, history, storage, fetch).
*/
const fs = require("fs"), path = require("path"), vm = require("vm"), nodeCrypto = require("crypto");
const SRC = fs.readFileSync(path.join(__dirname, "../src/db.js"), "utf8");
const API = "https://mock.supabase.test";
let pass = 0, fail = 0;
const check = (name, cond, detail = "") => { cond ? pass++ : fail++; console.log((cond ? "PASS " : "FAIL ") + name + (cond ? "" : "   " + detail)) };

function memStore() { const m = new Map(); return { getItem: k => m.has(k) ? m.get(k) : null, setItem: (k, v) => m.set(k, String(v)), removeItem: k => m.delete(k), _m: m } }

/* a fresh page: url, saved storage, and a fake Supabase that answers fetch */
function page(url, { session = {}, local = {}, token } = {}) {
  const env = { assigned: null, replaced: [], fetches: [], logs: [] };
  const loc = {};
  const setURL = u => { const x = new URL(u, loc.origin || undefined); Object.assign(loc, { href: x.href, origin: x.origin, pathname: x.pathname, search: x.search, hash: x.hash }) };
  setURL(url);
  loc.assign = u => { env.assigned = u };
  const ss = memStore(), ls = memStore();
  for (const [k, v] of Object.entries(session)) ss.setItem(k, JSON.stringify(v));
  for (const [k, v] of Object.entries(local)) ls.setItem(k, JSON.stringify(v));
  const fetch = async (u, opts) => {
    env.fetches.push({ url: u, body: opts.body ? JSON.parse(opts.body) : null });
    let st = 404, out = {};
    if (u.startsWith(API + "/auth/v1/token?grant_type=pkce")) [st, out] = token ? token(JSON.parse(opts.body)) : [400, { error: "invalid_grant" }];
    if (u.startsWith(API + "/auth/v1/user")) [st, out] = [200, { id: "u-1", email: "asha@example.com" }];
    return { ok: st < 300, status: st, text: async () => JSON.stringify(out), headers: new Map() };
  };
  const quiet = (...a) => env.logs.push(a.join(" "));
  const ctx = {
    AAINA_DB_CONFIG: { url: API, anonKey: "anon-test-key-0123456789abcdef" },
    location: loc, history: { state: null, replaceState: (s, t, u) => { env.replaced.push(u); setURL(new URL(u, loc.origin).href) } },
    sessionStorage: ss, localStorage: ls, fetch, crypto: globalThis.crypto, TextEncoder, URL, URLSearchParams, btoa, AbortController, setTimeout, clearTimeout,
    console: { log: quiet, info: quiet, warn: quiet, error: quiet, debug: quiet }, navigator: {}, JSON, Date, Math, Promise, Uint8Array, String, Object, Array,
  };
  ctx.window = ctx;
  vm.createContext(ctx);
  vm.runInContext(SRC + "\nthis.DB=DB;", ctx);
  return { DB: ctx.DB, env, loc, ss, ls };
}
const okToken = body => [200, { access_token: "AT-secret", refresh_token: "RT-secret", expires_in: 3600, expires_at: 2000000000,
  user: { id: "u-1", email: "asha@example.com", user_metadata: { full_name: "From Google", avatar_url: "https://x/a.png" } }, _seen: body }];

(async () => {
  const P0 = page("https://site.test/app/index.html").DB._pkce;

  // ---------- PKCE helpers ----------
  const vs = Array.from({ length: 50 }, () => P0.makeVerifier());
  check("verifier: 43-128 characters (RFC 7636)", vs.every(v => v.length >= 43 && v.length <= 128), vs[0].length);
  check("verifier: only unreserved characters A-Z a-z 0-9 - . _ ~", vs.every(v => /^[A-Za-z0-9\-._~]+$/.test(v)));
  check("verifier: random (50 all different)", new Set(vs).size === 50);
  check("S256 challenge matches the RFC 7636 appendix B vector",
    await P0.challengeFor("dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk") === "E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM");
  const v = vs[0];
  check("S256 challenge matches Node's own SHA-256", await P0.challengeFor(v) === nodeCrypto.createHash("sha256").update(v).digest("base64url"));

  // ---------- starting the sign-in ----------
  {
    const { DB, env, ss } = page("https://site.test/app/index.html?redirect_to=https%3A%2F%2Fevil.example&utm=x#try-on");
    const r = await DB.startGoogle();
    const u = new URL(env.assigned || "https://none/");
    const stored = JSON.parse(ss.getItem(P0.PKCE_KEY));
    check("start: goes to {BASE}/auth/v1/authorize with provider=google", r.ok && u.origin + u.pathname === API + "/auth/v1/authorize" && u.searchParams.get("provider") === "google", env.assigned);
    check("start: redirect_to is our own page, never the ?redirect_to in the URL", u.searchParams.get("redirect_to") === "https://site.test/app/index.html", u.searchParams.get("redirect_to"));
    check("start: S256 challenge of the stored verifier", u.searchParams.get("code_challenge_method") === "s256" && u.searchParams.get("code_challenge") === await P0.challengeFor(stored.v));
    check("start: scopes are openid email profile only", u.searchParams.get("scopes") === "openid email profile");
    check("start: verifier kept in sessionStorage, not localStorage", !!stored.v);
    check("start: #route saved for the way back", JSON.parse(ss.getItem(P0.ROUTE_KEY)) === "#try-on");
    const { DB: D2, ss: s2 } = page("https://site.test/app/index.html#access_token=zzz&x=1");
    await D2.startGoogle();
    check("start: a token-looking #hash is never saved as the route", s2.getItem(P0.ROUTE_KEY) === null);
  }

  // ---------- the callback ----------
  {
    const { DB, env, loc, ss, ls } = page("https://site.test/app/index.html?code=abc123&state=s1&utm=x",
      { session: { [P0.PKCE_KEY]: { v, at: Date.now() }, [P0.ROUTE_KEY]: "#try-on" }, token: okToken });
    const r = await DB.init();
    const tok = env.fetches.find(f => f.url.includes("grant_type=pkce"));
    check("callback success: POST /token?grant_type=pkce with auth_code and code_verifier", tok && tok.body.auth_code === "abc123" && tok.body.code_verifier === v, JSON.stringify(tok && tok.body));
    check("callback success: signed in", r.signedIn === true && DB.user().email === "asha@example.com");
    const saved = JSON.parse(ls.getItem("aaina.auth.v1"));
    check("callback success: session saved in the same shape as the email link",
      JSON.stringify(Object.keys(saved).sort()) === '["access_token","expires_at","refresh_token","user"]' && JSON.stringify(saved.user) === '{"id":"u-1","email":"asha@example.com"}', JSON.stringify(saved));
    check("callback success: nothing extra from Google kept (no name, no avatar)", !JSON.stringify(saved).includes("From Google") && !JSON.stringify(saved).includes("avatar"));
    check("callback success: verifier deleted", ss.getItem(P0.PKCE_KEY) === null);
    check("URL cleanup: no code or state left, other params kept", !/code=|state=/.test(loc.href) && loc.search === "?utm=x", loc.href);
    check("URL cleanup: done with replaceState (no extra history entry)", env.replaced.length === 1 && !/code=|state=/.test(env.replaced[0]), env.replaced.join());
    check("route restore: back on #try-on", loc.hash === "#try-on" && ss.getItem(P0.ROUTE_KEY) === null, loc.hash);
    check("no tokens, codes or verifiers in console output", !env.logs.some(l => /AT-secret|RT-secret|abc123/.test(l) || l.includes(v)), env.logs.join(" | "));
  }
  {
    const { DB, env, loc, ss } = page("https://site.test/app/index.html?error=access_denied&error_code=provider_error&error_description=The+user+denied",
      { session: { [P0.PKCE_KEY]: { v, at: Date.now() } }, token: okToken });
    const r = await DB.init();
    check("callback cancelled: calm message, still signed out", /cancelled/.test(r.error || "") && !DB.user() && r.provider === "google", r.error);
    check("callback cancelled: no token request", !env.fetches.some(f => f.url.includes("grant_type=pkce")));
    check("callback cancelled: error params removed, verifier deleted", !/error/.test(loc.href) && ss.getItem(P0.PKCE_KEY) === null, loc.href);
  }
  {
    const { DB, env, loc } = page("https://site.test/app/index.html?code=abc123", { token: okToken });
    const r = await DB.init();
    check("callback missing verifier: refused, no token request", /expired or was already used/.test(r.error || "") && !DB.user() && !env.fetches.some(f => f.url.includes("grant_type=pkce")), r.error);
    check("callback missing verifier: code still removed from the URL", !/code=/.test(loc.href));
  }
  {
    const { DB } = page("https://site.test/app/index.html?code=abc123", { session: { [P0.PKCE_KEY]: { v, at: Date.now() - 20 * 60 * 1000 } }, token: okToken });
    const r = await DB.init();
    check("callback stale verifier (over 15 min): refused", /expired/.test(r.error || "") && !DB.user());
  }
  {
    // the same code twice: the first use deletes the verifier, so the second has nothing to prove it with
    const used = new Set();
    const tokenOnce = body => used.has(body.auth_code) ? [400, { error: "invalid_grant" }] : (used.add(body.auth_code), okToken(body));
    const first = page("https://site.test/app/index.html?code=abc123", { session: { [P0.PKCE_KEY]: { v, at: Date.now() } }, token: tokenOnce });
    await first.DB.init();
    const again = page("https://site.test/app/index.html?code=abc123", { session: Object.fromEntries([...first.ss._m].map(([k, x]) => [k, JSON.parse(x)])), token: tokenOnce });
    const r2 = await again.DB.init();
    check("callback reused code: refused (verifier already gone)", /already used/.test(r2.error || "") && !again.env.fetches.some(f => f.url.includes("grant_type=pkce")), r2.error);
    const replay = page("https://site.test/app/index.html?code=abc123", { session: { [P0.PKCE_KEY]: { v, at: Date.now() } }, token: tokenOnce });
    const r3 = await replay.DB.init();
    check("callback reused code with a fresh verifier: server refuses, still signed out", /already used/.test(r3.error || "") && !replay.DB.user(), r3.error);
  }

  // ---------- the email link is unchanged ----------
  {
    const { DB, loc } = page("https://site.test/app/index.html#access_token=AT2&refresh_token=RT2&expires_in=3600&type=magiclink");
    const r = await DB.init();
    check("email link: still signs in from the #hash", r.signedIn === true && DB.user().email === "asha@example.com" && !/access_token/.test(loc.href));
    const e = page("https://site.test/app/index.html#error=access_denied&error_code=otp_expired&error_description=Email+link+is+invalid+or+has+expired");
    const r2 = await e.DB.init();
    check("email link error: still handled by the email-link code, not as a Google error", r2.error === "Email link is invalid or has expired" && !r2.provider, JSON.stringify(r2));
  }

  console.log(`\n${pass}/${pass + fail} passed`);
  process.exit(fail ? 1 : 0);
})();
