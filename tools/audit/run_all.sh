#!/bin/bash
# Run every test and eval; one log per suite in $OUT (default reports/baseline/tests), summary in $OUT/SUMMARY.txt.
#   CHROME=/path/to/chrome PGBIN=/path/to/postgres/bin bash tools/audit/run_all.sh
# Needs: python3 with playwright, psycopg, pytest, openpyxl, fastapi; node; PostgreSQL 15+ for the DB tests.
cd "$(dirname "$0")/../.."
export LC_ALL=${LC_ALL:-en_US.UTF-8} PGDIR=${PGDIR:-/tmp/aaina-pg}
OUT=${OUT:-reports/baseline/tests}; mkdir -p "$OUT"; : > "$OUT/SUMMARY.txt"
run(){ n=$1; shift; s=$(date +%s); "$@" > "$OUT/$n.log" 2>&1; rc=$?; echo "$n rc=$rc $(( $(date +%s)-s ))s :: $(grep -E 'passed|OK|FAILED|Ran [0-9]|^[0-9]+/[0-9]+' "$OUT/$n.log" | tail -2 | tr '\n' ' ')" >> "$OUT/SUMMARY.txt"; }
run build python3 build.py
run oauth_unit node tests/oauth_unit_test.js
run timeline_unit node tests/timeline_unit_test.js
run tryon_colour node tests/tryon_colour_test.js
run quiz_flow python3 tests/quiz_flow_test.py
run tryon python3 tests/tryon_test.py
run tryon_unit python3 tests/tryon_unit_test.py
run timeline python3 tests/timeline_test.py
run rag_test python3 tests/rag_test.py
run understand_test python3 tests/understand_test.py
run rag_eval python3 tests/rag_eval.py
run monk_service python3 -m pytest -q tests/test_monk_service.py
run verify_colorimetry python3 -m pytest -q tests/verify_colorimetry_spec.py
run db_rls_e2e bash supabase/tests/run_db_tests.sh
run check_evidence python3 tools/check_evidence.py
run eval_testset python3 tools/eval_testset.py
run eval_recommendations python3 tools/eval_recommendations.py
run catalogue_check python3 tools/catalogue_check.py
# the evals rewrite tracked reports; keep a copy here and restore the committed ones
cp reports/eval_testset.json reports/eval_testset.md reports/eval.md reports/eval_per_profile.csv "$OUT/" 2>/dev/null
git checkout -- reports/eval_testset.json reports/eval_testset.md reports/eval.md reports/eval_per_profile.csv 2>/dev/null
cat "$OUT/SUMMARY.txt"
