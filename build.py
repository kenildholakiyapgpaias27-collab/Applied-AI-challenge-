#!/usr/bin/env python3
"""Build index.html: one self-contained page from the source files. No dependencies.

    python3 build.py
"""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).parent
read = lambda p: (ROOT / p).read_text(encoding="utf-8")

# Database settings. The anon key is public by design (row-level security
# protects the data), so it is fine to commit. Leave both empty for offline mode.
db_cfg_path = ROOT / "data/supabase.json"
db_cfg = json.loads(read("data/supabase.json")) if db_cfg_path.exists() else {}
db_cfg = {"url": db_cfg.get("url", ""), "anonKey": db_cfg.get("anonKey", "")}
# same hash tools/seed_catalogue.py writes into the database
cat_version = hashlib.sha256((ROOT / "data/catalogue.json").read_bytes()).hexdigest()[:12]

page = (read("src/shell.html")
        .replace("__CATALOGUE__", read("data/catalogue.json"))
        .replace("__INDIA__", read("src/india.js") + "\n" + read("src/climate.js"))
        .replace("__ENGINE__", "const AAINA_CAL=" + (read("data/calibration.json") if (ROOT / "data/calibration.json").exists() else "null") + ";\n" + read("src/engine.js")
                  + "\nconst AAINA_DB_CONFIG=" + json.dumps(db_cfg) + ";\nconst CAT_VERSION=" + json.dumps(cat_version) + ";\n" + read("src/db.js"))
        .replace("__APP__", read("src/app.js")))

html = ("<!doctype html><html lang=\"en\"><head><meta charset=\"utf-8\">"
        "<meta name=\"viewport\" content=\"width=device-width,initial-scale=1,viewport-fit=cover\">"
        "<meta name=\"description\" content=\"Aaina AI Skin Advisor: a guided, guardrail-checked 3-product skincare plan.\">"
        "<style>[hidden]{display:none!important}</style></head><body>" + page + "</body></html>")

(ROOT / "index.html").write_text(html, encoding="utf-8")
print(f"Built index.html ({len(html)/1024:.0f} KB), catalogue {cat_version}, database {'ON: ' + db_cfg['url'] if db_cfg['url'] else 'off (offline mode)'}")
