# Phase 0 baseline audit

Branch `chore/baseline-audit`, from `main` at `c02cc89` (includes `7362fae` and PRs #12–#16). Run on 2026-11-18.
No app code was changed. New files: this report, `reports/baseline/**`, and the read-only walkthrough script `tools/audit/walkthrough.py`.

Contents: [1. Results at a glance](#1-results-at-a-glance) · [2. Tests and evals](#2-tests-and-evals) · [3. Regressions found](#3-regressions-found-on-main-not-fixed) ·
[4. Feature map](#4-feature-map) · [5. Accessibility](#5-accessibility) · [6. Layout bugs per screen](#6-layout-bugs-per-screen) · [7. Console errors](#7-console-errors) ·
[8. Performance and file sizes](#8-performance-and-file-sizes) · [9. Dead and duplicated code](#9-dead-and-duplicated-code) · [10. Unused files](#10-unused-files) ·
[11. Copy and compliance](#11-copy-and-compliance-for-phase-2) · [12. Security and privacy](#12-security-and-privacy-for-phase-7--8) · [13. How to re-run](#13-how-to-re-run)

---

## 1. Results at a glance

| Area | Baseline |
|---|---|
| Eval: shade "Your match" exact / within 1 / MAE | **52.3% / 84.1% / 0.86** (unchanged from 7362fae) |
| Eval: profiles with a MUST_NOT in top 5 / GOOD in top 5 | **0.9% / 74.2%** (unchanged) |
| Evidence check | OK: 26 entries, 35 checkpoints, 21 references |
| Test suites | 13 green, **4 with failures** (2 are new regressions from the #16 merge; see §3) |
| Lighthouse, live site, mobile | Perf **65** · A11y 96 · Best practices 96 · SEO 100 · LCP 5.6 s |
| Lighthouse, live site, desktop | Perf **89** · A11y 96 · Best practices 96 · SEO 100 · LCP 1.5 s |
| axe-core (31 screens × 2 viewports) | **1 critical** rule, **2 serious** rules (contrast on 30/31 screens; scrollable regions) |
| index.html | **1.80 MB** raw, 742 KB gzipped; 595 KB of it is 8 inline face photos |
| Sideways scroll at 390 px | None on any screen |
| Tap targets under 44 px (mobile) | 12–25 per screen |

## 2. Tests and evals

Logs for every suite are in [`tests/`](tests/) (`SUMMARY.txt` lists exit codes and timings).

| Suite | Result | Notes |
|---|---|---|
| `python3 build.py` | OK | 1,806 KB page; database ON; RAG off (no embeddings file) |
| `tests/oauth_unit_test.js` | 31/31 | |
| `tests/timeline_unit_test.js` | 35/35 | |
| `tests/tryon_colour_test.js` | 32/32 | |
| `tests/tryon_unit_test.py` | 26/26 | |
| `tests/timeline_test.py` | 35/35 | |
| `tests/rag_test.py` | 30/30 | |
| `tests/understand_test.py` | 17/17 | |
| `tests/verify_colorimetry_spec.py` (pytest) | 35/35 | needed `pip install pytest`; not documented |
| `tests/quiz_flow_test.py` | **FAIL, crashes at C** | B (old, heading text) + C (new, §3.2); sections D–G never run |
| `tests/tryon_test.py` | **59/60** | "A: lipstick changes the lips" (new, §3.1); same on a re-run |
| `tests/test_monk_service.py` (pytest) | **6/8** | synthetic image → tone 2 not 5; white-card workflow. Backend only, not on the site. Last touched 0ed53c7 (2026-11-16) |
| `supabase/tests` RLS + browser e2e | 36/36 + **62/63** | "new reaction from the check-in saved": known, also fails before #16 |
| `tests/rag_eval.py` | BM25 configs only | no OpenAI key: tuned P@5 0.985, held-out P@5 0.500 (BM25+filters+facets) |
| `tools/check_evidence.py` | OK | |
| `tools/eval_testset.py` | numbers above | full JSON in [`tests/eval_testset.json`](tests/eval_testset.json) |
| `tools/eval_recommendations.py` | Recall@3 30.8%, Precision@3 19.3%, safety 99.2% | 15 MUST_NOT in top 3. Uses a **Python port** of `check()`, not the real engine |
| `tools/catalogue_check.py` | 26 rows for review, 0 auto-fixed | |
| `tests/benchmark_skintone_internet.py`, `tests/evaluate_mste.py` | not run | need downloaded datasets and network |

Side effect to note: `tools/eval_testset.py` rewrites `reports/eval_testset.md` and drops its hand-written "Before and after" table. I restored the committed file; the fresh output is in `tests/`. Phase 8's CI must compare the JSON, not the markdown.

## 3. Regressions found on main (not fixed)

Per the ground rules, I've listed these and left them alone.

### 3.1 The #16 merge partly undid the photo-model try-on (#14 area). Severity: high (demo-visible, wrong claim)
`git diff 7362fae c02cc89 -- src/tryon.js` shows the RAG-chat branch was merged from an older copy of `tryon.js`:
- The picker says **"Six faces, fair to very deep"** but shows 8.
- The tip says **"Model faces are computer-rendered, not photos of real people"**. The faces are now licensed photos, so this is false.
- `thumbStyle()` (round thumbnails framed on the face) and the gender-preferring `closestModel()` were removed. A man can now be shown a woman's face as "Closest to you".
- A new face crop in the single view (`uCrop` from `faceCrop()`) was added. It moves the drawn face, so the test's lip landmark no longer lands on the lips. Either the crop or the test needs updating. I haven't checked by eye whether lipstick still lands on the lips.

### 3.2 Base-makeup flow no longer asks undertone or shows the shade preview. Severity: medium (likely intended, but tests and docs disagree)
`ASKED()` and the `answer("tone")` change in #16 mark `undertone`, `utHelp` and `preview` as done for makeup, with `undertoneSource="unsure"`. So every makeup plan uses a **Neutral** shade (screens show "158 Cool Deep" / "138 Neutral Deep"). The quiz test, README and the PS-14 brief all expect the undertone question. **Your decision:** keep the shortcut, or restore the undertone question for makeup.

### 3.3 Chat calls a backend that isn't deployed
The page calls `http://localhost:8000/api/understand/status` on load (`AAINA_API`, app.js:2218). That's `ERR_CONNECTION_REFUSED` locally and 404 at `…github.io/api/understand/status` on the live site. It fails quietly, but it's a console error on every load and the reason Lighthouse's best-practices score is 96.

## 4. Feature map

There's **one real hash route today: `#try-on`**. Everything else is in-page state saved in `localStorage` (`aaina.state…`), and `#access_token=…` is the OAuth callback, which is cleaned from the URL straight away. Refreshing a page in the middle of the quiz returns to Home with a "Welcome back" banner, not to the step you were on.

| Screen | How you reach it | How you get back | URL | Screenshot (desktop / mobile) |
|---|---|---|---|---|
| Home (welcome) | first visit; Back from Q1 | n/a | `/` | `01_home` |
| Home, returning | reload after any answer | "Start fresh" | `/` | `31_home_returning` |
| Quiz Q1 "About you" | name + Begin | header Back → Home | `/` | `02_routine_q1_about` |
| Routine: concerns → safety → location → skin → tone → undertone | Q1 = routine | in-card Back, header Back, journey dots | `/` | `04`–`09` |
| Sunscreen: follow → safety → location → skin | Q1 = sunscreen | same | `/` | `20`–`23` |
| Base makeup: finish → safety → skin → tone (→ plan) | Q1 = makeup | same | `/` | `25`–`29` |
| Plan | last answer | journey dots to edit a step; "Plan for another concern" | `/` | `10`, `24`, `30` (+ `11` full page) |
| Tune your plan | plan → "Change" | "Close" | `/` | `12` |
| Results timeline | product card → "What to expect" | collapse | `/` | `13` |
| Compare (modal) | timeline → "Compare with alternatives" | ✕, Esc, backdrop | `/` | `14` |
| Illustration (modal) | timeline → "See an illustration" | ✕ | `/` | covered by `tests/timeline_test.py --shots` |
| Progress check-in (modal) | plan → "Track my progress" | ✕ | `/` | covered by the timeline test |
| Check-in | plan → "How's it going? Check in"; banner on return | "Not now" | `/` | `17` |
| Try-on | product "Try it on"; makeup "Try your shades on" | ✕, browser Back | **`#try-on`** | `18` |
| Ask Aaina chat (side panel) | floating "Ask Aaina" button | ×, no Esc | `/` | `19` |
| Typed ask bar (bottom of quiz) | always visible during the quiz | n/a | `/` | in `04`–`09` |
| Sign-in panel | inside plan (Google / email link); "Saved a plan before?" on Home | n/a | `/`, `#access_token` on return | `15` |
| Before you go (modal) | pointer leaves the top of the window; phone Back mid-quiz | "Later", Esc | `/` | `03`, `16` |
| Consultation Standards | Home link | toggle | `/` | in `01` |
| Delete my answers | footer link | confirm dialog | `/` | n/a |

**Duplicate entry points** (for Phase 1):
- **Two chat inputs.** The bottom "Describe your skin concern…" bar (app.js `handleTyped`) and the Ask Aaina panel (voice.js) do overlapping jobs.
- **Three progress indicators that disagree.** Journey dots ("Q2"), the card header ("Q1 of 6 · Your skin", which counts *remaining* questions so it always says Q1) and the footer ("Question 1 of 7").
- **Two sign-in places.** Home "Saved a plan before?" and the in-plan panel.
- **Two ways back.** Header "Back" and in-card "Back".
- **The "Your skin" label is wrong.** It appears on the concerns, sunscreen-follow and makeup-finish steps.

## 5. Accessibility

axe-core 4.10 (WCAG 2.0/2.1/2.2 A+AA + best practice) on every screen. Full detail per screen is in [`walkthrough.json`](walkthrough.json).

| Impact | Rule | Where | Screens |
|---|---|---|---|
| **critical** | aria-required-children | `.vanity-tray[role=tablist]` (Morning/Evening toggle) has no `role=tab` children | 11/31 (every plan) |
| **serious** | color-contrast | `.qnav-step`, WhatsApp `.wa`, try-on/compare small text, tune budget `<small>`, disabled "Begin consultation", "Delete my answers", "Consultation Standards", `.aa-note` | 30/31 |
| **serious** | scrollable-region-focusable (mobile) | `#journey` dots bar, `.tl-cmpwrap` compare table | 5 |
| moderate | region | brand title, footer text outside landmarks | 30/31 |
| moderate | heading-order | shortlist `h5` after `h3` | 10 |
| minor | empty-table-header | compare table corner cell | 1 |

From Lighthouse and manual checks:
- **Label/name mismatch.** The journey dots have `aria-label="Q1 About you"` but visible text "01"/"About you". The dots are disabled buttons.
- **Ask Aaina panel.** No Esc to close, no focus trap, and it stays in the tab order while off-screen (`transform`, not `hidden`).
- **Before-you-go dialog.** Has Esc and initial focus, but no focus trap.
- **Disabled buttons don't say why.** "Begin consultation" (grey on cream, under 3:1), "Continue" and "Update my plan".
- **`<html lang="en">` is set,** but Hindi/Hinglish chat replies aren't marked `lang`.
- **No `prefers-reduced-motion` handling.** Smooth scrolling, the fab hover lift and the panel slide.

## 6. Layout bugs per screen

Mobile is 390×844; desktop is 1440×900. There's **no page-level sideways scroll at 390 px anywhere** (`overflowX:false` on all 62 screenshots).

| Screen | Bug |
|---|---|
| All, desktop | **Ask Aaina button covers the ask bar's "Send" button** (bottom right). |
| All, mobile | Ask Aaina button sits over content: the Google button on Home, "Not sure? Take a selfie", "Ever reacted to…", plan cards. |
| All, mobile | Tap targets under 44 px: header Back 90×32, journey dots 36 px wide, chips 40 px, "Delete my answers" 125×25, panel close 29×30, example chips 26 px tall, "Sign in with email" 120×26, Morning/Evening 33 px tall, "Substitute" 26 px. |
| Home, mobile | Name placeholder cut off ("e.g. Pri"); "Begin consultation" disabled with low contrast and no reason given; brand tagline wraps as "DIAGNOSTIC SUR- / MESURE". |
| Home, desktop | Footer says "AI-powered skin diagnostic" in the same line as "not a diagnosis"-style wording. |
| Quiz cards | Counter reads "Q1 of N" on every step; footer says "Question 1 of 7"; the title "Your skin" is reused on unrelated steps. |
| Quiz, desktop | The shortlist side panel is dense 9–10 px text. |
| Location | Three ways to answer at once (search, state dropdown, city dropdown); the disabled "Continue" is low contrast. |
| Plan | "Tune your plan" banner is a heavy gradient block above the products; Morning/Evening "Protocol" toggle; product art is an empty placeholder bottle ("01"/"02"). |
| Plan, mobile | The first product card starts below the fold. |
| Compare, mobile | The third column is cut off and only reachable by sideways scrolling inside the table (not keyboard-reachable). |
| Sign-in | Disabled Google button and email field (until consent) look broken (light grey, no reason shown). |
| Try-on, mobile | Opens on the picker first; the "Six faces" count is wrong (§3.1). |
| Try-on, desktop | The face and panel fill only the top half of the overlay; the lower ~450 px is empty. |
| Ask Aaina, mobile | Full-screen panel; placeholder cut off; no route, so phone Back leaves the page and the before-you-go dialog appears. |
| Before you go | Fine on both sizes. |

## 7. Console errors

| Error | Where | Cause |
|---|---|---|
| `ERR_CONNECTION_REFUSED` (localhost:8000) | load, first answer | §3.3 understand/ask backend |
| 404 `/api/understand/status` | live site, every load | same |
| 404 `/favicon.ico` | live site | no favicon |
| (`ERR_FAILED` to supabase.co in the walkthrough) | | my own request blocking, not a bug |

No uncaught JavaScript errors (`pageerror`) on any screen. `catalogue_meta?select=version` is fetched **twice** on load.

## 8. Performance and file sizes

Lighthouse 12.2.1, headless Chrome. JSON reports are in [`lighthouse/`](lighthouse/). The live site is GitHub Pages (gzip on). "Local" is `python -m http.server` (no gzip) on the same `index.html`, offline build.

| | Perf | A11y | BP | SEO | FCP | LCP | TBT | CLS |
|---|---|---|---|---|---|---|---|---|
| Live, mobile | **65** | 96 | 96 | 100 | 5.6 s | 5.6 s | 0 ms | 0 |
| Live, desktop | 89 | 96 | 96 | 100 | 1.5 s | 1.5 s | 0 ms | 0.017 |
| Local, mobile (no gzip) | 55 | 96 | 96 | 100 | 11.7 s | 11.7 s | 0 ms | 0 |
| Local, desktop | 76 | 96 | 96 | 100 | 2.2 s | 2.2 s | 0 ms | 0.017 |

The whole app is one 1.8 MB HTML file that has to download before anything paints. Total transfer is 817 KB, and 731 KB of that is the page. Phase 5 target: ≥85 mobile.

| File | Bytes | Lines |
|---|---|---|
| `index.html` (built) | 1,848,934 (742,166 gzip) | n/a |
| of which: 8 inline face JPEGs (base64) | ~609,000 | n/a |
| of which: `data/catalogue.json` | 342,348 | n/a |
| of which: `sample_product_studies.json` / `actives_timeline.json` / `model_faces_landmarks.json` | 77,182 / 45,145 / 68,082 | n/a |
| `src/app.js` | 285,156 | 2,816 |
| `src/shell.html` (≈118 KB CSS + markup) | 118,351 | 1,313 |
| `src/tryon.js` | 58,405 | 662 |
| `src/engine.js` | 52,848 | 695 |
| `src/voice.js` | 49,059 | 945 |
| `src/climate.js` | 19,544 | 94 |
| `src/timeline.js` | 17,748 | 226 |
| `src/db.js` | 17,664 | 262 |
| `src/india.js` | 15,426 | 40 |
| `src/rag.js` | 4,974 | 134 |

Lighthouse opportunities: unused JS ~124 KB, unminified CSS, unused CSS rules, preconnect to fonts.gstatic.com, three Google Font families (Cormorant Garamond, Plus Jakarta Sans, IBM Plex Mono). Mobile TTI = LCP = 5.6 s on the live site (target <2.5 s).

## 9. Dead and duplicated code

Only definitions with **no other reference anywhere in `src/`, `tests/` or `tools/`** are listed.

**Never called:**
- `app.js`: `scaleHTML`, `QUALITY_ONLY`, `thumbOf`, `spReason`, `planHeading`.
- `engine.js`: `buildRoutine`, `findSclera`, `bgIlluminant`, `autoCropFace`, `sessionRead`, `applySlots`, `makeExample`.
  - `readPhotoV1` is used only by `tools/tone_eval.py`.
  - `skinRG` is used only by `tests/verify_colorimetry_spec.py`.
  - engine.js is off-limits for scoring changes, so these stay unless you approve removing unused helpers.

**Duplicated helpers:**
- `store()` in `db.js` and `app.js`.
- `fmt`, `cap` in `timeline.js` and `app.js`.
- `uniq` in `timeline.js` and `engine.js`.
- `lin` (sRGB linearise) in `engine.js` and `tryon.js`.
- `botSay`/`meSay` in `voice.js` and `app.js`. They have the same names but are different functions (one per chat UI), which is confusing to read.
- The fallbacks `esc`/`rupee` in `tryon.js` re-implement the ones in `app.js`.

**Other:**
- `voice.js` injects its own ~70-line CSS string, separate from `shell.html`'s design system (`.aa-*`: black pill, system font).
- `#askForm` has `style="display:none !important"` in an older revision, and the ask bar is now live again. That's two code paths for typed input.
- `index.html` is committed **and** generated. Every PR diff includes the 1.8 MB build.

## 10. Unused files

Each was checked by `git grep` for any reference outside itself.

| File | Referenced by | Suggestion (Phase 8) |
|---|---|---|
| `chanel_luxury_demo.html` | nothing | delete (also a brand-name risk) |
| `docs/PRD_GEMINI_SKIN_TONE_PALETTE_ARTIFACT.md` | nothing | archive |
| `docs/MARKET_RESEARCH_REPORT.md`, `docs/TECHNICAL_SOLUTION_SPECIFICATION.md` | nothing | keep or move to `docs/archive/` |
| `docs/oauth_signin_desktop.png`, `oauth_signin_mobile.png` | nothing | delete or link from `oauth-setup.md` |
| `vercel.json` | nothing (teammate's Vercel deploy) | keep if Vercel stays; it rewrites `/assets/*` |
| `tools/nocache_server.py` | nothing | keep as a dev tool, or document it |
| `tests/benchmark_skintone_internet.py`, `tests/evaluate_mste.py` | nothing / itself | move to `tools/` (not tests; need datasets) |
| `backend/` | `tests/rag_test.py`, `understand_test.py`, `test_monk_service.py`; the page calls `/api/understand` + `/api/ask` | **used**, but not deployed anywhere. Document it in Phase 8 |
| `assets/*.jpg` (6 files) | only `vercel.json`; added for the old deck | **see §12, privacy** |
| `deck/` | untracked locally (deck branch) | not in main; nothing to do |

## 11. Copy and compliance (for Phase 2)

Counts are of matches in `src/app.js`, `shell.html`, `voice.js` and `tryon.js`.

| Term | Matches | Examples |
|---|---|---|
| diagnos* | 14 | "Aaina Skin Diagnostic" title, "private diagnostic", "Haute Diagnostic", "algorithmic diagnostic accuracy" |
| Client | 9 | "Client First Name" |
| precision | 6 | "Precision Diagnostic" |
| clinical | 5 | "Clinical Safety Filter", "clinical safety cross-checks" |
| protocol | 5 | "Morning/Evening Protocol", "Formulated Protocol" |
| Prescription / Ordonnance / GESTE | 2 / 1 / 2 | "Prescription № 3", "L'Ordonnance de Soin", "GESTE 01" |
| atelier, sur-mesure, "Reflect · Reveal · Radiate" | 1 each | French tagline |
| dermatological guidance | 1 | |
| cures/treats/removes/lightens/brightens | 3 | INGR explainer: "brightens dull skin", "calms redness and brightens", "smoother, brighter skin" |

- **Disclaimers:** "Cosmetic advice only, not medical advice" appears in the footer, the PDF and the chat answer, and the chat panel adds "won't diagnose skin conditions". That's four variants.
- **Sample studies:** the fictional studies show for everyone today (Phase 2: only with `?demo=1`).
- **README is stale in places:** Q1 still lists "non-binary, prefer not to say"; the makeup row lists undertone and preview (see §3.2); the "What it does" list numbering.

## 12. Security and privacy (for Phase 7 / 8)

- **Real people's photos in the public repo.** `assets/manasvi_test.jpg`, `real_user_photo.jpg`, `user_actual_photo.jpg`, `actual_webcam.jpg` and the before/after whitepaper shots were committed on 2026-11-15/16 and are still in git history. The app doesn't use them. I recommend removing them now and, if the people in them want, purging history (that needs a force-push, so it's your call).
- **API key prompt.** `voice.js:36` asks the visitor for an OpenAI key with `window.prompt` and keeps it in `localStorage["aaina_openai_key"]`. That's Phase 7's job.
- `data/openai.example.json` holds placeholders only, and `data/openai.json` is gitignored. A full history scan for keys is part of Phase 7.
- There's no CSP meta tag yet.
- The anon Supabase key is in the build. That's by design: row-level security is on, and the 36/36 RLS tests pass.

## 13. How to re-run

```bash
CHROME="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" PGBIN=/opt/homebrew/opt/postgresql@16/bin bash tools/audit/run_all.sh
AXE=node_modules/axe-core/axe.min.js python3 tools/audit/walkthrough.py reports/baseline
npx lighthouse@12.2.1 <url> [--preset=desktop] --only-categories=performance,accessibility,best-practices,seo
```

Screenshots: [`screens/desktop/`](screens/desktop/) and [`screens/mobile/`](screens/mobile/), 31 each, numbered in walkthrough order.
