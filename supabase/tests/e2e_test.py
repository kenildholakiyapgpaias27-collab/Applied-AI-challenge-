#!/usr/bin/env python3
"""End-to-end test: the real page, the real schema and RLS, a mocked Supabase API.

    supabase/tests/run_db_tests.sh      (starts Postgres, loads schema + seed, runs this)

The page is built pointing at https://mock.supabase.test; Playwright routes those
requests to MockSupabase, which runs them in Postgres as anon/authenticated.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import http.server
import functools
from pathlib import Path

from playwright.sync_api import sync_playwright

sys.path.insert(0, str(Path(__file__).parent))
from mock_supabase import MockSupabase  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
DSN = os.environ.get("AAINA_TEST_DSN", "host=/tmp/pg port=5544 user=postgres dbname=aaina")
API = "https://mock.supabase.test"
CHROME = os.environ.get("CHROME", "/usr/bin/google-chrome")
RESULTS = []


def check(name, cond, detail=""):
    RESULTS.append((name, bool(cond)))
    print(("PASS " if cond else "FAIL ") + name + ("" if cond else f"   {detail}"))


def build_page(url, key):
    """Build index.html into a temp folder with the given database settings."""
    tmp = Path(tempfile.mkdtemp(prefix="aaina_"))
    for p in ["build.py", "src", "data"]:
        (shutil.copytree if (ROOT / p).is_dir() else shutil.copy)(ROOT / p, tmp / p)
    (tmp / "data/supabase.json").write_text(json.dumps({"url": url, "anonKey": key}))
    subprocess.run([sys.executable, "build.py"], cwd=tmp, check=True, capture_output=True)
    return tmp


def serve(folder, port):
    h = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(folder))
    http.server.ThreadingHTTPServer.allow_reuse_address = True
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", port), h)
    srv.RequestHandlerClass.log_message = lambda *a: None
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


def journey(pg):
    """Same answers as the manual test: woman, routine, acne, fragrance-free, sensitive, pregnant, Pune, oily, tone 6, warm."""
    pg.fill("#nameInput", "Manasvi"); pg.keyboard.press("Enter"); pg.wait_for_timeout(600)
    pg.locator('.q:not(.answered) input[name="agender"][value="woman"]').check()
    pg.locator('.q:not(.answered) [data-goal="routine"]').click()
    pg.locator(".q:not(.answered) [data-go]").click(); pg.wait_for_timeout(700)
    pg.locator("label:visible, button:visible").filter(has_text="Breakouts and acne").last.click()
    pg.locator("label.sc:visible:has-text('Blackheads and whiteheads')").first.click()
    pg.locator("button:visible:has-text('Continue')").first.click(); pg.wait_for_timeout(700)
    pg.evaluate("""()=>{const ins=[...document.querySelectorAll('.q:not(.answered) input')];
      for(const [v,n] of [["frag",0],["sens",0],["pores",0],["__none",1],["true",0],["__none",2]])
        (ins.filter(i=>i.value===v)[n].closest('label')).click()}""")
    pg.locator("button:visible:has-text('Continue')").first.click(); pg.wait_for_timeout(900)
    pg.fill("input[placeholder^='Start typing']", "Pune"); pg.wait_for_timeout(600)
    pg.locator("button:visible:has-text('Continue')").first.click(); pg.wait_for_timeout(900)
    pg.locator("button:visible:has-text('Shiny all over')").first.click(); pg.wait_for_timeout(900)
    pg.locator("button[aria-label='Skin tone 6, Medium Tan']").first.click(); pg.wait_for_timeout(900)
    pg.locator("button:visible:has-text('Warm')").first.click(); pg.wait_for_timeout(1500)


def sql(q, *a):
    import psycopg
    with psycopg.connect(DSN, autocommit=True) as c:
        cur = c.execute(q, a)
        return cur.fetchall() if cur.description else []


def google_journey(b, mock, base, new_page, errors):
    """Google sign-in round trip: consent -> /authorize -> ?code -> /token (pkce) -> signed in -> plan saved -> sign out -> delete."""
    sql("delete from auth.users")
    logs = []
    ctx = b.new_context(); pg = new_page(ctx); pg.on("console", lambda m: logs.append(m.text))
    pg.goto(base + "?redirect_to=https%3A%2F%2Fevil.example%2Fsteal"); pg.wait_for_timeout(1200)   # a hostile redirect_to in the URL must be ignored
    journey(pg)
    card = pg.locator(".plan:not(.old) .acct"); gbtn = card.locator("[data-google]")
    txt = card.inner_text()
    check("google: panel has Google button, email option and the privacy note",
          gbtn.count() == 1 and "Continue with Google" in gbtn.inner_text() and card.locator(".acct-email").count() == 1
          and "We only get your name and email from Google." in txt, txt[:200])
    check("google: consent box comes before both sign-in options",
          pg.evaluate("""()=>{const c=document.querySelector('.plan:not(.old) .acct [data-consent]'),g=document.querySelector('.plan:not(.old) .acct [data-google]'),
            e=document.querySelector('.plan:not(.old) .acct .acct-email');return !!(c.compareDocumentPosition(g)&4)&&!!(c.compareDocumentPosition(e)&4)}"""))
    check("google: button off until consent is ticked", gbtn.is_disabled())
    n0 = len(mock.authorize_calls)
    pg.evaluate("document.querySelector('.plan:not(.old) .acct [data-google]').click()"); pg.wait_for_timeout(400)
    check("google: no redirect without consent", len(mock.authorize_calls) == n0 and "127.0.0.1" in pg.url)

    # user cancels on Google's screen
    mock.google = {"email": "asha@example.com", "cancel": True}
    card.locator("[data-consent]").check(); gbtn.click(); pg.wait_for_timeout(2500)
    body = pg.locator("body").inner_text()
    check("google cancel: calm message, still signed out", "cancelled" in body and pg.evaluate("DB.user()===null"), body[:160])
    check("google cancel: error removed from the address bar", "error" not in pg.url and "code=" not in pg.url, pg.url)
    check("google cancel: consent not left pending, nothing stored", pg.evaluate("DB.pendingConsent()===null") and sql("select count(*) from profiles")[0][0] == 0)

    # success
    mock.google = {"email": "asha@example.com", "cancel": False}
    pg.locator("#resume button.primary").first.click(); pg.wait_for_timeout(1500)
    card = pg.locator(".plan:not(.old) .acct"); card.locator("[data-consent]").check()
    card.locator("[data-google]").click(); pg.wait_for_timeout(3000)
    a = mock.authorize_calls[-1]
    check("google: redirect_to is this page, not the URL's ?redirect_to", a.get("redirect_to") == base, a.get("redirect_to"))
    check("google: PKCE S256 challenge and scopes openid email profile",
          a.get("code_challenge_method") == "s256" and len(a.get("code_challenge", "")) == 43 and a.get("scopes") == "openid email profile", a)
    check("google: code removed from the address bar", "code=" not in pg.url and "state=" not in pg.url, pg.url)
    check("google: signed in as the Google email", pg.evaluate("DB.user()&&DB.user().email") == "asha@example.com")
    sess = pg.evaluate("JSON.parse(localStorage.getItem('aaina.auth.v1'))")
    check("google: session saved in the same shape as the email link",
          sorted(sess) == ["access_token", "expires_at", "refresh_token", "user"] and sorted(sess["user"]) == ["email", "id"], sess and sorted(sess))
    check("google: verifier deleted after use", pg.evaluate("sessionStorage.getItem('aaina.pkce.v1')") is None)
    prof = sql("select display_name, consent_at is not null, state::text from profiles")
    check("google: plan and profile saved after consent", len(prof) == 1 and prof[0][1] and sql("select count(*) from plans")[0][0] == 1, prof[:1])
    check("google: nothing extra from Google stored (name is the one typed, no avatar)",
          prof and prof[0][0] == "Manasvi" and "Google Name" not in prof[0][2] and "avatar" not in prof[0][2])
    meta = sql("select u.raw_user_meta_data::text || i.identity_data::text from auth.users u join auth.identities i on i.user_id=u.id where u.email='asha@example.com'")
    check("google: no Google name or photo kept in the auth tables (sub, email kept for linking)",
          meta and not any(k in meta[0][0] for k in ["Google Name", "picture", "avatar_url", "full_name"]) and '"sub"' in meta[0][0], meta[:1])
    pg.go_back(); pg.wait_for_timeout(800)
    check("google: no code in the previous history entry either", "code=" not in pg.url, pg.url)
    pg.go_forward(); pg.wait_for_timeout(1200)

    # the same code again (e.g. a reload of an old URL, or a stolen code): refused, no token request
    used = mock.token_calls[-1]
    n_tok = len(mock.token_calls)
    pg.goto(base + "?code=" + str(used)); pg.wait_for_timeout(2000)
    check("google: reused code refused without a verifier, no token request",
          len(mock.token_calls) == n_tok and "expired or was already used" in pg.locator("body").inner_text(), len(mock.token_calls) - n_tok)

    # route restore: start on #try-on, come back to #try-on
    pg.goto(base + "#try-on"); pg.wait_for_timeout(1500)
    pg.evaluate("DB.startGoogle()"); pg.wait_for_timeout(3000)
    check("google: returns to the #route the user was on", pg.url.endswith("#try-on") and "code=" not in pg.url, pg.url)

    # same person, two methods: the email link for the Google address lands in the same account
    ctx2 = b.new_context(); pg2 = new_page(ctx2); pg2.goto(base); pg2.wait_for_timeout(1200)
    pg2.locator("#acctLine [data-win]").click(); pg2.locator("#acctLine .acct-email").fill("asha@example.com")
    pg2.locator("#acctLine [data-wsend]").click(); pg2.wait_for_timeout(600)
    pg2.evaluate("u=>location.href=u", mock.outbox[-1][1]); pg2.wait_for_timeout(2500)
    ids = sql("select u.id, array_agg(i.provider order by i.provider) from auth.users u join auth.identities i on i.user_id=u.id where u.email='asha@example.com' group by u.id")
    check("google + email link: one account with both sign-in methods", len(ids) == 1 and ids[0][1] == ["email", "google"], ids)
    check("google + email link: same user id in the browser", pg2.evaluate("DB.user().id") == pg.evaluate("DB.user().id"))
    check("google + email link: the Google-saved plan comes back", "Welcome back, Manasvi" in pg2.locator("#resume").inner_text())
    ctx2.close()

    # a guest plan on a new device, and a different plan already in the account: ask, never overwrite silently
    acct = lambda: sql("select state::text from profiles")
    before = acct()
    ctx3 = b.new_context(); pg3 = new_page(ctx3); pg3.goto(base); pg3.wait_for_timeout(1200); journey(pg3)
    card3 = pg3.locator(".plan:not(.old) .acct"); card3.locator("[data-consent]").check(); card3.locator("[data-google]").click(); pg3.wait_for_timeout(3000)
    dlg = pg3.locator(".acct-merge")
    check("guest plan + account plan: asks 'Save this plan to your account?'", dlg.count() == 1 and "Save this plan to your account?" in dlg.inner_text(),
          dlg.inner_text()[:80] if dlg.count() else "no dialog")
    check("guest plan + account plan: account untouched while asking", acct() == before)
    dlg.locator('[data-keep="remote"]').click(); pg3.wait_for_timeout(2000)
    check("guest plan + account plan: 'Use my account's plan' leaves the account as it was", acct() == before)
    ctx3.close()

    # sign out
    pg.goto(base); pg.wait_for_timeout(1500)
    pg.locator("#acctLine [data-wout]").click(); pg.wait_for_timeout(800)
    check("google: sign out clears the session", pg.evaluate("localStorage.getItem('aaina.auth.v1')===null&&DB.user()===null"))

    # sign back in with Google from the welcome page (no consent needed to sign in; account already has consent), then delete
    pg.locator("#acctLine [data-google]").click(); pg.wait_for_timeout(3000)
    check("google from welcome: signed in again", pg.evaluate("DB.user()&&DB.user().email") == "asha@example.com")
    pg.locator("#deleteBtn").click(); pg.wait_for_timeout(300); pg.locator(".exitm [data-yes]").click(); pg.wait_for_timeout(1500)
    left = sql("select (select count(*) from auth.users where email='asha@example.com')+(select count(*) from auth.identities where email='asha@example.com')+(select count(*) from profiles)+(select count(*) from plans)")[0][0]
    check("google: delete removes account rows, the login and both identities", left == 0, left)
    toks = [t for t in list(mock.tokens) + list(mock.refresh)]
    leaked = [l for l in logs if any(t in l for t in toks) or "code_" in l or "code_verifier" in l]
    check("google: no tokens, codes or verifiers in the console", not leaked, leaked[:2])
    ctx.close()


def main():
    mock = MockSupabase(DSN)
    site = build_page(API, "anon-test-key-0123456789abcdef")
    srv = serve(site, 8791)
    base = "http://127.0.0.1:8791/index.html"
    errors = []

    def route(r):
        req = r.request
        if "/auth/v1/authorize" in req.url:      # the browser leaves for "Google" and comes straight back
            r.fulfill(status=200, content_type="text/html", body=f"<script>location.replace({json.dumps(mock.authorize(req.url))})</script>")
            return
        st, out = mock.handle(req.method, req.url, req.headers, req.post_data)
        r.fulfill(status=st, body="" if out is None else json.dumps(out), content_type="application/json",
                  headers={"Access-Control-Allow-Origin": "*", "Access-Control-Allow-Headers": "*", "Access-Control-Allow-Methods": "*"})

    def new_page(ctx):
        pg = ctx.new_page()
        pg.on("pageerror", lambda e: errors.append(str(e)))
        pg.route(API + "/**", route)
        return pg

    sql("delete from public.events"); sql("delete from auth.users")
    with sync_playwright() as p:
        b = p.chromium.launch(executable_path=CHROME, args=["--no-sandbox"])

        # 1. catalogue: a newer version in the database replaces the bundled one
        old = sql("select price_inr, (select version from catalogue_meta) from products where id='P1029'")[0]
        sql("update products set price_inr=199 where id='P1029'"); sql("update catalogue_meta set version='test-v2'")
        ctx = b.new_context(); pg = new_page(ctx); pg.goto(base); pg.wait_for_timeout(1500)
        check("catalogue: newer DB version is loaded", pg.evaluate("BY_ID.P1029.p") == 199, pg.evaluate("BY_ID.P1029.p"))
        check("catalogue: engine re-prepared (flags, lookup)", pg.evaluate("CAT.length===806&&BY_ID.P1029.leaveOn===false&&BRANDS.length>10"))
        sql("update products set price_inr=%s where id='P1029'", old[0]); sql("update catalogue_meta set version=%s", old[1])
        ctx.close()
        ctx = b.new_context(); pg = new_page(ctx); pg.goto(base); pg.wait_for_timeout(1200)
        n_prod_calls = sum(1 for m, u, s in mock.log if "/rest/v1/products" in u)
        check("catalogue: same version means no download", pg.evaluate("BY_ID.P1029.p") == old[0] and n_prod_calls == 1, n_prod_calls)

        # 2. journey -> plan -> account card (signed out)
        journey(pg)
        card = pg.locator(".plan:not(.old) .acct")
        check("plan shows the save-to-account card", card.count() == 1 and card.locator(".acct-email").count() == 1)
        go = card.locator("[data-go]")
        card.locator(".acct-email").fill("asha@example.com")
        check("link button stays off until consent is ticked", go.is_disabled())
        card.locator("[data-consent]").check()
        check("link button enabled after email + consent", go.is_enabled())
        check("nothing stored in an account before sign-in", sql("select count(*) from profiles")[0][0] == 0)
        go.click(); pg.wait_for_timeout(600)
        check("sign-in email 'sent'", len(mock.outbox) == 1 and mock.outbox[0][0] == "asha@example.com")
        check("card says check your inbox", "Check your inbox" in pg.locator(".plan:not(.old) .acct").inner_text())

        # 3. open the magic link on the same device
        link = mock.outbox[-1][1]
        pg.close(); pg = new_page(ctx)          # like a mail app opening the link in a new tab
        pg.goto(link); pg.wait_for_timeout(2200)
        check("token removed from the address bar", "access_token" not in pg.url)
        prof = sql("select display_name, state->>'NAME', consent_version, consent_at is not null, state->'P'->>'pregnancy' from profiles")
        check("profile saved after sign-in, with consent recorded", len(prof) == 1 and prof[0][1] == "Manasvi" and prof[0][3] and prof[0][2] == "v1-2026-11", prof)
        plans = sql("select concern, product_ids from plans")
        check("plan saved to account", len(plans) == 1 and plans[0][0] == "acne" and len(plans[0][1]) == 3, plans)
        check("welcome shows who is signed in", "Signed in as asha@example.com" in pg.locator("#acctLine").inner_text(), pg.locator("#acctLine").inner_text())

        # resume, swap a product -> plan row and state follow
        pg.locator("#resume button.primary").first.click(); pg.wait_for_timeout(1500)
        check("signed-in card on the plan", "Saved to your account" in pg.locator(".plan:not(.old) .acct").inner_text())
        before = sql("select product_ids from plans")[0][0]
        pg.locator("button.swap:visible").first.click(); pg.wait_for_timeout(2500)
        after = sql("select product_ids from plans")
        check("swap updates the same plan row", len(after) == 1 and after[0][0] != before, (before, after))
        st_ids = sql("select state->'planIds' from profiles")[0][0]
        check("saved answers follow the swap (debounced sync)", st_ids == after[0][0], (st_ids, after))

        # check-in with a stinging product -> checkin row + reaction row
        pg.locator("button:visible:has-text('Check in')").first.click(); pg.wait_for_timeout(600)
        pg.evaluate("""()=>{const box=[...document.querySelectorAll('.checkin')].pop();
          box.querySelectorAll('.ckrow').forEach((r,i)=>{const v=i===1?'sting':'good';const inp=r.querySelector(`input[value="${v}"]`)||r.querySelector('input');(inp.closest('label')||inp).click()})}""")
        pg.locator(".checkin button[data-save]").last.click(); pg.wait_for_timeout(1500)
        ck = sql("select stage, results, plan_id is not null from checkins")
        check("check-in saved and linked to the plan", len(ck) == 1 and ck[0][2] and "sting" in json.dumps(ck[0][1]), ck)
        rx = sql("select reaction, source from reactions")
        check("new reaction from the check-in saved", any(s == "checkin" for _, s in rx), rx)

        # 4. a second device: sign in from the welcome page, saved plan comes back
        ctx2 = b.new_context(); pg2 = new_page(ctx2); pg2.goto(base); pg2.wait_for_timeout(1200)
        pg2.locator("#acctLine [data-win]").click()
        pg2.locator("#acctLine .acct-email").fill("asha@example.com"); pg2.locator("#acctLine [data-wsend]").click(); pg2.wait_for_timeout(600)
        pg2.evaluate("u=>location.href=u", mock.outbox[-1][1]); pg2.wait_for_timeout(2500)   # same tab: hash-only change
        check("second device: saved plan offered on welcome", "Welcome back, Manasvi" in pg2.locator("#resume").inner_text(), pg2.locator("#resume").inner_text()[:120])
        pg2.locator("#resume button.primary").first.click(); pg2.wait_for_timeout(1500)
        ids2 = pg2.evaluate("PL&&PL.slots.map(s=>s.p&&s.p.id)")
        check("second device: same products as the first", ids2 == sql("select product_ids from plans")[0][0], ids2)
        ctx2.close()

        # 5. another user sees nothing
        ctx3 = b.new_context(); pg3 = new_page(ctx3); pg3.goto(base); pg3.wait_for_timeout(1000)
        pg3.locator("#acctLine [data-win]").click(); pg3.locator("#acctLine .acct-email").fill("ravi@example.com")
        pg3.locator("#acctLine [data-wsend]").click(); pg3.wait_for_timeout(500); pg3.close(); pg3 = new_page(ctx3); pg3.goto(mock.outbox[-1][1]); pg3.wait_for_timeout(2000)
        check("other user: no saved plan offered", pg3.locator("#resume").is_hidden())
        check("other user: no profile created without consent", sql("select count(*) from profiles p join auth.users u on u.id=p.user_id where u.email='ravi@example.com'")[0][0] == 0)
        ctx3.close()

        # 6. analytics are anonymous
        ev = sql("select name, props::text from events")
        names = {n for n, _ in ev}
        check("analytics: plan_shown / set_aside / product_swapped / checkin_saved / catalogue_refreshed logged",
              {"plan_shown", "set_aside", "product_swapped", "checkin_saved", "catalogue_refreshed"} <= names, names)
        blob = " ".join(p for _, p in ev).lower()
        bad = [w for w in ["manasvi", "asha", "pune", "pregnan", "\"a2\"", "\"b3\"", "\"b4\"", "@"] if w in blob]
        check("analytics: no name, email, city, pregnancy or reaction rules", not bad, bad)

        # 7. the chat delete trap now asks first
        # the chat box is hidden in the current design; send the text through the same handler its form uses
        pg.evaluate("handleTyped('how do I remove tan from my face? I can share a photo')"); pg.wait_for_timeout(600)
        dlg = pg.locator(".exitm")
        check("chat 'remove tan... photo' opens a confirm, deletes nothing", dlg.count() == 1 and pg.evaluate("!!PL") and sql("select count(*) from profiles")[0][0] == 1)
        dlg.locator("[data-no]").click(); pg.wait_for_timeout(300)

        # 8. delete everything
        pg.locator("#deleteBtn").click(); pg.wait_for_timeout(300)
        check("delete dialog mentions the account", "Aaina account" in pg.locator(".exitm").inner_text())
        pg.locator(".exitm [data-yes]").click(); pg.wait_for_timeout(1500)
        left = sql("select (select count(*) from profiles)+(select count(*) from plans)+(select count(*) from checkins)+(select count(*) from reactions)+(select count(*) from auth.users where email='asha@example.com')")[0][0]
        check("delete: account rows and login erased", left == 0, left)
        check("delete: this device cleared and signed out", pg.evaluate("localStorage.getItem('aaina.advisor.v1')===null&&localStorage.getItem('aaina.auth.v1')===null"))
        check("delete: events kept (they were never linked to the account)", sql("select count(*) from events")[0][0] > 0)
        ctx.close()

        # 8b. Continue with Google (PKCE), same mocked Supabase
        google_journey(b, mock, base, new_page, errors)

        # 9. database unreachable -> app still works
        ctx = b.new_context(); pg = ctx.new_page(); pg.on("pageerror", lambda e: errors.append(str(e)))
        pg.route(API + "/**", lambda r: r.abort())
        pg.goto(base); pg.wait_for_timeout(1000); journey(pg)
        check("offline: plan still built from the bundled catalogue", pg.evaluate("!!PL&&PL.slots.length===3"))
        card = pg.locator(".plan:not(.old) .acct")
        card.locator(".acct-email").fill("x@example.com"); card.locator("[data-consent]").check(); card.locator("[data-go]").click(); pg.wait_for_timeout(1500)
        err = pg.locator(".plan:not(.old) .acct [data-err]")
        check("offline: sign-in failure shown politely", err.is_visible() and "try again" in err.inner_text().lower(), err.inner_text() if err.count() else "")
        ctx.close()
        b.close()

    # 10. no database configured -> no account UI at all
    site2 = build_page("", "")
    srv2 = serve(site2, 8792)
    with sync_playwright() as p:
        b = p.chromium.launch(executable_path=CHROME, args=["--no-sandbox"])
        ctx = b.new_context(); pg = ctx.new_page(); pg.on("pageerror", lambda e: errors.append(str(e)))
        reqs = []
        pg.on("request", lambda r: reqs.append(r.url) if "supabase" in r.url else None)
        pg.goto("http://127.0.0.1:8792/index.html"); pg.wait_for_timeout(800); journey(pg)
        check("no config: no account card or sign-in link", pg.locator(".acct").count() == 0 and pg.locator("#acctLine").is_hidden())
        check("no config: no database requests", not reqs, reqs[:3])
        b.close()
    srv.shutdown(); srv2.shutdown()

    check("no JavaScript errors in any page", not errors, errors[:3])
    passed = sum(ok for _, ok in RESULTS)
    print(f"\n{passed}/{len(RESULTS)} passed")
    sys.exit(0 if passed == len(RESULTS) else 1)


if __name__ == "__main__":
    main()
