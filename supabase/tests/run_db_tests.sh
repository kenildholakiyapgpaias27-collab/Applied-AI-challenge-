#!/usr/bin/env bash
# Local database tests: schema + seed, row-level security (SQL), then the full
# page against the real schema through a mocked Supabase API (Playwright).
#   Needs: PostgreSQL 15+ server binaries, python3 with psycopg + playwright, Chrome.
#   Usage: supabase/tests/run_db_tests.sh
set -euo pipefail
cd "$(dirname "$0")/../.."
PGBIN=${PGBIN:-$(ls -d /usr/lib/postgresql/*/bin 2>/dev/null | sort -V | tail -1)}
DIR=${PGDIR:-/tmp/aaina-pg}; PORT=${PGPORT:-5544}
export PGHOST=$DIR PGPORT=$PORT PGUSER=postgres
if ! "$PGBIN/pg_isready" -q -h "$DIR" -p "$PORT" 2>/dev/null; then
  rm -rf "$DIR"; mkdir -p "$DIR"
  RUN=(bash -c); if [ "$(id -u)" = 0 ]; then chown postgres "$DIR"; RUN=(su postgres -c); fi
  "${RUN[@]}" "$PGBIN/initdb -D $DIR/data -A trust -U postgres >/dev/null && $PGBIN/pg_ctl -D $DIR/data -o '-k $DIR -p $PORT -c listen_addresses=' -l $DIR/log start >/dev/null"
fi
dropdb --if-exists aaina_test && createdb aaina_test
load(){ psql -q -v ON_ERROR_STOP=1 -d aaina_test -f "$1" 2>&1 | grep -v NOTICE || true; }
load supabase/tests/supabase_shim.sql
load supabase/migrations/20261112000000_init.sql
load supabase/seed.sql
echo "== migration + seed loaded: $(psql -tAc 'select count(*) from products' -d aaina_test) products, $(psql -tAc 'select count(*) from shades' -d aaina_test) shades"
echo "== row-level security"
OUT=$(psql -d aaina_test -f supabase/tests/rls_test.sql 2>&1)
echo "$OUT" | grep -E "^ (PASS|FAIL)|^ +[0-9]+ \| +[0-9]+$"
if echo "$OUT" | grep -q "^ FAIL"; then echo "RLS tests failed"; exit 1; fi
# rls_test.sql adds two users; start the browser test clean
psql -q -d aaina_test -c "delete from auth.users; delete from public.events;"
echo "== end-to-end (browser)"
AAINA_TEST_DSN="host=$DIR port=$PORT user=postgres dbname=aaina_test" python3 supabase/tests/e2e_test.py
