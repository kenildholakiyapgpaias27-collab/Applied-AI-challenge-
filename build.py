#!/usr/bin/env python3
"""Build index.html: one self-contained page from the source files. No dependencies.

    python3 build.py
"""
from pathlib import Path

ROOT = Path(__file__).parent
read = lambda p: (ROOT / p).read_text(encoding="utf-8")

page = (read("src/shell.html")
        .replace("__CATALOGUE__", read("data/catalogue.json"))
        .replace("__INDIA__", read("src/india.js") + "\n" + read("src/climate.js"))
        .replace("__ENGINE__", "const AAINA_CAL=" + (read("data/calibration.json") if (ROOT / "data/calibration.json").exists() else "null") + ";\n" + read("src/engine.js"))
        .replace("__APP__", read("src/app.js")))

html = ("<!doctype html><html lang=\"en\"><head><meta charset=\"utf-8\">"
        "<meta name=\"viewport\" content=\"width=device-width,initial-scale=1,viewport-fit=cover\">"
        "<meta name=\"description\" content=\"Aaina AI Skin Advisor: a guided, guardrail-checked 3-product skincare plan.\">"
        "<style>[hidden]{display:none!important}</style></head><body>" + page + "</body></html>")

(ROOT / "index.html").write_text(html, encoding="utf-8")
print(f"Built index.html ({len(html)/1024:.0f} KB)")
