"""A tiny stand-in for Supabase's Auth + REST API, backed by a real Postgres.

Only the calls src/db.js makes are implemented. Every REST request runs as the
`anon` or `authenticated` role with the user's id in request.jwt.claim.sub,
exactly like Supabase, so the migration's row-level security is what decides.
Used by supabase/tests/e2e_test.py; not for production.
"""
import json
import re
import secrets
import time
import urllib.parse

import psycopg
from psycopg import sql

IDENT = re.compile(r"^[a-z_][a-z0-9_]*$")


class MockSupabase:
    def __init__(self, dsn):
        self.dsn = dsn
        self.tokens = {}    # access_token -> (user_id, email, expires_at)
        self.refresh = {}   # refresh_token -> user_id
        self.outbox = []    # magic links "sent" by email: (email, url)
        self.log = []       # (method, path, status)

    # ---------- helpers ----------
    def _conn(self):
        return psycopg.connect(self.dsn, autocommit=False)

    def _issue(self, uid, email):
        at, rt = "at_" + secrets.token_hex(12), "rt_" + secrets.token_hex(12)
        exp = int(time.time()) + 3600
        self.tokens[at] = (uid, email, exp)
        self.refresh[rt] = uid
        return {"access_token": at, "refresh_token": rt, "expires_in": 3600, "expires_at": exp, "token_type": "bearer"}

    def _who(self, headers):
        auth = headers.get("authorization", "")
        tok = auth[7:] if auth.lower().startswith("bearer ") else ""
        if tok in self.tokens:
            uid, email, exp = self.tokens[tok]
            if exp > time.time():
                return uid, email
            return "expired", None
        return None, None

    # ---------- entry point ----------
    def handle(self, method, url, headers, body):
        headers = {k.lower(): v for k, v in headers.items()}
        u = urllib.parse.urlsplit(url)
        qs = urllib.parse.parse_qsl(u.query, keep_blank_values=True)
        data = json.loads(body) if body else None
        try:
            if u.path.startswith("/auth/v1/"):
                st, out = self._auth(method, u.path[9:], dict(qs), headers, data)
            elif u.path.startswith("/rest/v1/"):
                st, out = self._rest(method, u.path[9:], qs, headers, data)
            else:
                st, out = 404, {"message": "not found"}
        except psycopg.errors.InsufficientPrivilege as e:
            st, out = 403, {"message": str(e).split("\n")[0], "code": "42501"}
        except psycopg.Error as e:
            st, out = 400, {"message": str(e).split("\n")[0]}
        self.log.append((method, u.path + ("?" + u.query if u.query else ""), st))
        return st, out

    # ---------- auth ----------
    def _auth(self, method, path, q, headers, data):
        if path == "otp" and method == "POST":
            email = (data or {}).get("email", "").lower()
            with self._conn() as c:
                row = c.execute("select id from auth.users where email=%s", (email,)).fetchone()
                uid = row[0] if row else c.execute("insert into auth.users(email) values (%s) returning id", (email,)).fetchone()[0]
            t = self._issue(str(uid), email)
            frag = urllib.parse.urlencode({**t, "type": "magiclink"})
            self.outbox.append((email, q.get("redirect_to", "") + "#" + frag))
            return 200, {}
        if path == "user" and method == "GET":
            uid, email = self._who(headers)
            return (200, {"id": uid, "email": email}) if uid and uid != "expired" else (401, {"msg": "invalid token"})
        if path == "token" and q.get("grant_type") == "refresh_token":
            uid = self.refresh.pop((data or {}).get("refresh_token"), None)
            if not uid:
                return 400, {"error_description": "Invalid Refresh Token"}
            email = next((e for (u_, e, _) in self.tokens.values() if u_ == uid), None)
            return 200, self._issue(uid, email)
        if path == "logout":
            auth = headers.get("authorization", "")[7:]
            self.tokens.pop(auth, None)
            return 204, None
        return 404, {"message": "auth route not mocked"}

    # ---------- PostgREST subset ----------
    def _rest(self, method, path, qs, headers, data):
        uid, _ = self._who(headers)
        if uid == "expired":
            return 401, {"message": "JWT expired"}
        role = "authenticated" if uid else "anon"
        with self._conn() as c:
            c.execute(sql.SQL("set local role {}").format(sql.Identifier(role)))
            c.execute("select set_config('request.jwt.claim.sub', %s, true)", (uid or "",))
            if path.startswith("rpc/"):
                fn = path[4:]
                assert IDENT.match(fn)
                c.execute(sql.SQL("select public.{}()").format(sql.Identifier(fn)))
                return 200, None
            table = path
            assert IDENT.match(table), table
            t = sql.Identifier("public", table)
            params = [(k, v) for k, v in qs if k not in ("select", "order", "on_conflict", "limit", "offset")]
            where, args = [], []
            for k, v in params:
                assert IDENT.match(k)
                op, val = v.split(".", 1)
                assert op == "eq"
                where.append(sql.SQL("{}::text = %s").format(sql.Identifier(k)))
                args.append(val)
            wsql = sql.SQL(" where ") + sql.SQL(" and ").join(where) if where else sql.SQL("")
            prefer = headers.get("prefer", "")
            if method == "GET":
                sel = dict(qs).get("select", "*")
                cols = sql.SQL("*") if sel == "*" else sql.SQL(",").join(sql.Identifier(x) for x in sel.split(","))
                order = dict(qs).get("order")
                osql = sql.SQL("")
                if order:
                    osql = sql.SQL(" order by ") + sql.SQL(",").join(sql.Identifier(x.split(".")[0]) for x in order.split(","))
                lim = sql.SQL("")
                rng = headers.get("range")
                if rng:
                    a, b = map(int, rng.split("-"))
                    lim = sql.SQL(" limit {} offset {}").format(sql.Literal(min(b - a + 1, 1000)), sql.Literal(a))
                elif dict(qs).get("limit"):
                    lim = sql.SQL(" limit {}").format(sql.Literal(int(dict(qs)["limit"])))
                else:
                    lim = sql.SQL(" limit 1000")     # Supabase's default max-rows
                q = sql.SQL("select coalesce(json_agg(x),'[]') from (select {} from {}{}{}{}) x").format(cols, t, wsql, osql, lim)
                return 200, c.execute(q, args).fetchone()[0]
            if method == "POST":
                rows = data if isinstance(data, list) else [data]
                keys = sorted({k for r in rows for k in r})
                for k in keys:
                    assert IDENT.match(k)
                kl = sql.SQL(",").join(sql.Identifier(k) for k in keys)
                ins = sql.SQL("insert into {} ({}) select {} from json_populate_recordset(null::{}, %s::json)").format(t, kl, kl, t)
                oc = dict(qs).get("on_conflict")
                if oc:
                    occ = [x for x in oc.split(",")]
                    if "ignore-duplicates" in prefer:
                        ins += sql.SQL(" on conflict ({}) do nothing").format(sql.SQL(",").join(map(sql.Identifier, occ)))
                    else:
                        upd = [k for k in keys if k not in occ]
                        ins += sql.SQL(" on conflict ({}) do update set {}").format(
                            sql.SQL(",").join(map(sql.Identifier, occ)),
                            sql.SQL(",").join(sql.SQL("{}=excluded.{}").format(sql.Identifier(k), sql.Identifier(k)) for k in upd))
                elif "merge-duplicates" in prefer and table == "profiles":
                    upd = [k for k in keys if k != "user_id"]
                    ins += sql.SQL(" on conflict (user_id) do update set {}").format(
                        sql.SQL(",").join(sql.SQL("{}=excluded.{}").format(sql.Identifier(k), sql.Identifier(k)) for k in upd))
                if "return=representation" in prefer:
                    out = c.execute(sql.SQL("with r as ({} returning *) select coalesce(json_agg(r),'[]') from r").format(ins), [json.dumps(rows)]).fetchone()[0]
                    return 201, out
                c.execute(ins, [json.dumps(rows)])
                return 201, None
            if method == "PATCH":
                keys = [k for k in data if IDENT.match(k)]
                sets = sql.SQL(",").join(sql.SQL("{} = (%s::json->>{})::{}").format(
                    sql.Identifier(k), sql.Literal(k), sql.SQL(self._coltype(c, table, k))) if not isinstance(data[k], (dict, list))
                    else sql.SQL("{} = %s::jsonb").format(sql.Identifier(k)) for k in keys)
                vals = [json.dumps(data) if not isinstance(data[k], (dict, list)) else json.dumps(data[k]) for k in keys]
                c.execute(sql.SQL("update {} set {}{}").format(t, sets, wsql), vals + args)
                return 204, None
        return 405, {"message": "method not mocked"}

    @staticmethod
    def _coltype(c, table, col):
        r = c.execute("select format_type(atttypid, atttypmod) from pg_attribute where attrelid=%s::regclass and attname=%s",
                      (f"public.{table}", col)).fetchone()
        return r[0]
