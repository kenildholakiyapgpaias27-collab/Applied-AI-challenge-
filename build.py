#!/usr/bin/env python3
"""Build index.html: one self-contained page from the source files. No dependencies.

    python3 build.py
"""
import base64
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

# OpenAI settings for the Ask Aaina chat/voice module. The file is gitignored,
# so the key never lands in the repo. Absent file => chat is silently disabled.
openai_cfg_path = ROOT / "data/openai.json"
openai_cfg = json.loads(read("data/openai.json")) if openai_cfg_path.exists() else {}
openai_cfg = {
    "apiKey": openai_cfg.get("apiKey", ""),
    "chatModel": openai_cfg.get("chatModel", "gpt-4o-mini"),
    "sttModel": openai_cfg.get("sttModel", "whisper-1"),
    "maxRecordingMs": openai_cfg.get("maxRecordingMs", 15000),
}

# Virtual try-on: demo shade colours (never part of the catalogue) and the illustrated model faces, inlined
model_faces = json.loads(read("data/model_faces.json"))
face_landmarks = json.loads(read("data/model_faces_landmarks.json"))
for f in model_faces["faces"]:
    f["src"] = "data:image/jpeg;base64," + base64.b64encode((ROOT / f.pop("file")).read_bytes()).decode()
    f["landmarks"] = face_landmarks[f["id"]]
tryon_js = ("const TRYON_DEMO=" + read("data/demo_colours.json") + ";\nconst TRYON_MODELS=" + json.dumps({"models": model_faces["faces"], "size": model_faces.get("size")}, separators=(",", ":"))
            + ";\n" + read("src/tryon.js"))

# RAG embeddings (opt-in): built by tools/build_embeddings.py.
# File absent => RAG disabled; voice chat falls back to engine-only ranking.
emb_path = ROOT / "data/embeddings.json"
if emb_path.exists():
    emb_raw = read("data/embeddings.json")
    emb_obj = json.loads(emb_raw)
    rag_status = f"ON ({len(emb_obj.get('items', []))} vectors, hash {emb_obj.get('cat_hash', '?')})"
    emb_inline = emb_raw
else:
    rag_status = "off (run tools/build_embeddings.py)"
    emb_inline = "null"

rag_js = "const AAINA_EMBEDDINGS=" + emb_inline + ";\n" + read("src/rag.js")

# Ask Aaina voice/chat module (opt-in: no-op without a key)
voice_js = "const AAINA_OPENAI_CONFIG=" + json.dumps(openai_cfg) + ";\n" + rag_js + "\n" + read("src/voice.js")

page = (read("src/shell.html")
        .replace("__CATALOGUE__", read("data/catalogue.json"))
        .replace("__INDIA__", read("src/india.js") + "\n" + read("src/climate.js"))
        .replace("__ENGINE__", "const AAINA_CAL=" + (read("data/calibration.json") if (ROOT / "data/calibration.json").exists() else "null") + ";\n" + read("src/engine.js")
                  + "\nconst AAINA_DB_CONFIG=" + json.dumps(db_cfg) + ";\nconst CAT_VERSION=" + json.dumps(cat_version) + ";\n" + read("src/db.js"))
        .replace("__APP__", read("src/app.js") + "\n" + voice_js)
        .replace("__TRYON__", tryon_js))

html = ("<!doctype html><html lang=\"en\"><head><meta charset=\"utf-8\">"
        "<meta name=\"viewport\" content=\"width=device-width,initial-scale=1,viewport-fit=cover\">"
        "<meta name=\"description\" content=\"Aaina AI Skin Advisor: a guided, guardrail-checked 3-product skincare plan.\">"
        "<style>[hidden]{display:none!important}</style></head><body>" + page + "</body></html>")

(ROOT / "index.html").write_text(html, encoding="utf-8")
print(f"Built index.html ({len(html)/1024:.0f} KB), catalogue {cat_version}, database {'ON: ' + db_cfg['url'] if db_cfg['url'] else 'off (offline mode)'}, voice chat {'ON' if openai_cfg['apiKey'] else 'ON (browser key)'}, RAG {rag_status}")
