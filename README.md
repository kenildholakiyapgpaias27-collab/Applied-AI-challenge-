# Aaina AI Skin Advisor

> **Reflect. Reveal. Radiate.**
> A guided skincare advisor that asks a few short questions, adapted to who the user is and what they want, and builds a **3-product plan** (treat → hydrate → protect), a single sunscreen pick, or base makeup in their shade, then explains exactly why each product was chosen.

Built for **PS-14, Masters' Union Applied AI Challenge**. Aaina and all products in the catalogue are fictional (demo data).

## What it does

- **Personal start:** asks your first name and greets you by time of day.
- **"About you" first (Q1):** gender (woman, man, non-binary, prefer not to say) and what the user is looking for: a skincare routine, just a sunscreen, or foundation/base makeup. The rest of the quiz adapts to these answers:

  | Looking for | Steps after Q1 | Result |
  |---|---|---|
  | Skincare routine | concerns → safety → location → skin type → skin tone → undertone (undertone skipped for men) | 3-step plan (treat → hydrate → protect) |
  | Just a sunscreen | where they wear it → safety → location → skin type (no shade or undertone) | One sunscreen pick |
  | Base makeup | preferred finish → safety → skin type → skin tone → undertone | Foundation, concealer and powder in the matched shade |

  Men are not asked the pregnancy question. Undertone (warm, cool, neutral, olive, not sure) comes straight after skin shade; a selfie read pre-selects it. Shade matching uses tone + undertone, and the finish preference (natural, matte, dewy) nudges base products. Saved answers from the older 5-step version are migrated automatically.
- **A progress bar** shows each step, one question at a time, with a Back button on every screen. Editing Q1 later re-shapes the remaining steps without losing answers that still apply.
- **One-page skin concerns (routine goal):** tap a concern and its follow-up question opens inside the same card (for example, Breakouts → "What do your breakouts usually look like?"). Pick up to three concerns; the first is the main concern the plan is built around, and any other can be made the main one with one tap. Safety signals from every concern count (a "deep, painful lumps" answer triggers the dermatologist notice even when acne isn't the main concern), while ingredient nudges from the other concerns count at half weight. Continue unlocks once every picked concern's follow-up is answered.
- **One-page safety check (Q2):** everything that keeps a product safe is answered together: ingredients to avoid, past reactions, pregnancy caution and warning signs happening right now (pain, spreading, bleeding, a changing mole, fever). Every section must be answered (**None** counts) before Continue unlocks, and a live line sums up what will be skipped. Earlier answers carry in (for example "I'd rather avoid retinol" pre-ticks retinoids). Any warning sign shows a dermatologist notice and keeps the plan gentle.
- **Live shortlist on every step:** from Q2 on, a panel (beside the question on desktop, a tap-to-open bar on phones) shows how many products still match and how many are set aside, the product leading each step of the routine right now, and what has been set aside for the user, grouped by reason (fragrance, past reaction, pregnancy caution, skin type, over budget, missing ingredient list) with examples. It says what the last answer changed ("Your last answer set aside 88"), and on the safety page it updates live as boxes are ticked. Answers not given yet never set anything aside; final picks come after the last question.
- **A personal line on every question:** each step opens with a warm note that uses the user's name, concern, city and progress, such as empathy for their concern before the safety check, "129 products have already passed your safety checks" before location, and "Last one, Kenil" before skin tone. Escalation cases get a gentler, reassuring line.
- **Before-you-go note:** if someone tries to leave mid-way (pointer heading for the tab bar on desktop, the Back button on phones), a caring pop-up shows their progress, what's left, and how many products already passed their checks, and reassures them that their answers are saved on the device, with **Finish my plan** and **I'll come back later**. On the plan page, if they haven't saved it yet, it offers WhatsApp or PDF instead. It shows at most once per session for each case, closes with Esc or a tap outside, and never blocks leaving.
  1. Main concern (illustrated cards)
  2. Concern-specific follow-up
  3. Anything else to help with
  4. Ingredients to avoid
  5. Past reactions
  6. Pregnancy caution
  7. State and city (962 Indian cities, with search; climate shapes texture choices)
  8. Skin type
  5. Skin tone (Aaina 1–10 scale, or a selfie)

  Budget and "already using" are not questions any more: they live on the plan page (see **Tune your plan**).
- **Selfie skin-tone reader (v2):** after explicit consent, reads a camera photo or upload and returns exactly one shade on the fixed Aaina scale, shown as **SKIN TONE: N** (1 Very Light, 2–3 Light, 4 Light Medium, 5 Medium, 6 Medium Tan, 7 Tan, 8 Deep, 9 Dark, 10 Very Dark). No ranges, no undertone, no explanation; a "Not right? Choose another shade" link lets the user correct it.
- **Skin mask, shade mapping layer and product shades (v3):** a per-side skin colour model keeps only facial skin (no hair, eyes, lips, beard or background); a mapping layer maps the measured colour onto the closest Aaina tone (library swatches by default, or centroids learned from labelled photos in `data/calibration.json`); base-makeup products get their exact library shade name on the plan page, or "no close shade". Internal confidence asks for a retake only for clearly poor photos. `tools/ccv2/` holds the pipeline for learning and validating the mapping on Meta Casual Conversations v2 once you have access. Design and test results: [docs/skin_tone_pipeline.md](docs/skin_tone_pipeline.md).
  - **Lighting correction instead of retakes:** the whites of the eyes are used as a light reference (found next to the iris, so it works for very fair and very deep skin), which removes warm/cool casts and over/under-exposure together. If one eye is in shadow, the lit eye is used. With no usable eye whites it falls back to a partial colour balance from the background.
  - **Multi-region skin sampling:** forehead, cheeks and chin, split left and right; only skin-coloured pixels and the middle 70% by brightness are kept. If one side of the face is in shadow, the lit side is read. A red channel clipped by bright light is rebuilt from green using real skin's red/green ratio.
  - **Retakes only when unreadable:** no face in the oval, face too small, face blown out to white, or too dark to hold colour.
  - **Test (`tools/tone_eval.py`, 450 simulated selfies: 50 people x 9 lighting conditions, light applied to face, eyes and wall together):** retake rate 62.2% → 4.9%; of all photos, exact shade 16.9% → 62.2% and within one shade 26.2% → 84.0%; the same person got the same answer across lighting 23.8% → 73.3% of the time. Weakest cases: phone auto-exposure and photos with closed eyes. These are simulated photos, not real selfies, so validate on real labelled selfies before relying on the numbers.
- **Filter check:** warns when a photo looks filtered (airbrushed skin with a sharp background, black-and-white, boosted colour or colour casts) and asks for a retake without a filter.
- **Tune your plan (on the plan page):** one panel to change the budget per product and what you already use, together. Each budget option previews what it would give you (how many steps are covered and the total). Change several things, then press **Update my plan** once; the advisor rebuilds the plan, says how many steps changed, and keeps every safety rule. The plan starts at up to ₹700 per product.
- **Save and resume:** answers are saved on the device after every step. Returning users see "Continue where I left off" (or "View my plan"), and **Delete my answers** clears everything.
- **Builds around what you already use:** if you already own a product that covers a step and passes your checks, the plan keeps it instead of selling you another. New picks never clash with your routine (retinoid + acids, retinoid + benzoyl peroxide), avoid doubling up on actives you already use, and warn you about owned products that fail your safety answers.
- **Upgrade picks and combos for products you already own:** every "Already yours" step shows an **Upgrade pick**: the best product for that step that passes your checks, with reasons it's better than what you have (for example, it adds an ingredient that targets your concern, it's made for your concern or skin type, it has SPF 50, or it suits this week's weather). **Switch to this** swaps it in. When you already own one or more steps, the plan also offers two **combos** (a *Quick boost* and a *Full routine upgrade*) of add-on products, such as a lightweight moisturiser, a weekly exfoliant or a mask, chosen to work with your existing routine without clashing, with prices and how your morning, night and weekly routine would look. **Add to my plan** adds them as add-ons, which are counted in the total, saved, shared and included in the PDF.
- **Day-3 and week-2 check-ins:** the welcome screen asks how each product is going once the time comes, and a check-in can be started any time from the plan. "Stinging or redness" or "New breakouts" removes that product, swaps in the next safe option, and adds its main active to your reactions so future plans avoid it.
- **Live 7-day weather on the location step:** after choosing a city, the advisor looks up the last 7 days of real weather and air quality there ([Open-Meteo](https://open-meteo.com/), free, no API key): daily highs and lows, humidity, rain, UV and PM2.5. It sums the week up (for example "Warm, dry and smoggy"), explains what each reading means for skin, and uses it to rank textures: ceramide creams for dry air or cold nights, oil-free gels for humidity or rain, SPF 50 for high UV, antioxidant serums for pollution. The drying-alcohol guardrail also uses the live readings. Results are cached for 3 hours. If the weather service can't be reached, it falls back to the usual season for that region, and says so.
- **City climate when live weather can't load:** every city falls back to its own typical weather for the current month (`src/climate.js`): average highs and lows, humidity and rainfall for one reference station per state and climate type (60 in all), with an altitude correction for hill towns (6.5 °C per 1,000 m) and an estimated UV index from latitude, month, altitude and cloud cover. The location card shows a 12-month chart with this month highlighted and says which station the averages come from. The same data drives product ranking: dry or cold months favour hydrating serums, cream cleansers, gentler acids and richer moisturisers; humid, hot or rainy months favour oil-free moisturisers, niacinamide or salicylic serums and gel cleansers; high UV favours SPF 50 and vitamin C and holds back glycolic peels. Values are rounded long-term averages; replace them with official IMD normals before production use.
- **Season reminder:** with the reminder on, returning users are offered **Refresh for <season>** once the season in their city changes. The refresh pulls fresh weather and says exactly which products changed.
- **Share and save:** the plan page has **Share on WhatsApp** (opens WhatsApp with a ready message, or the phone's share sheet), **Save as PDF** (a branded A4 plan generated in the browser with no libraries), and **Copy plan**. Shared text includes only the products and routine, never safety answers like pregnancy or reactions.
- **Honest empty steps:** if nothing in the range is safe for a step, the card says how many products were checked, the top reasons they were ruled out, and what to do next, including a one-tap button to raise the budget when that would unlock safe options.
- **The plan:** three products that work together, a total price, two clearly labelled sponsored suggestions with relevance reasons, and a detailed "Why I recommended these" section.

## Guardrails enforced in code

Every product passes a hard filter before it can be ranked (`check()` in `src/engine.js`):

| Area | Rule |
|---|---|
| Safety | No retinoids or strong salicylic acid when pregnancy-cautious; no ingredient you've reacted to; products with no ingredient list are excluded |
| Preferences | Fragrance-free (including hidden fragrance such as linalool and limonene); no essential oils; no pore-clogging formulas; gentle picks for sensitive skin |
| Fit | Skin-type match; no drying alcohol for dry skin in dry, cold weather; within budget |
| Combinations | No retinoid together with acids or benzoyl peroxide, including products you already own; no two retinoids in one plan |
| Honesty | Sponsored items are labelled, pass the same checks and never affect ranking; no skin-lightening advice; no guarantees; red-flag symptoms and prescription questions go to a dermatologist; prompt-injection attempts are refused |

## Catalogue data check

The guardrails trust the catalogue's tags, so a wrong tag silently changes recommendations. Run the check on every catalogue update:

```bash
python3 tools/catalogue_check.py          # report only
python3 tools/catalogue_check.py --fix    # apply safe rule-based fixes (backup kept)
```

It flags skin-type tags that contradict a product's purpose (for example an acne or oil-control moisturiser not tagged for oily skin, or a hydrating product not tagged for dry skin), flags that disagree with the ingredient list, missing ingredient lists and sunscreens without an SPF. The 14 safe corrections it found have been applied to `data/catalogue.json`; the rest are listed for human review.

## Project structure

```
aaina-skin-advisor/
├── index.html          # built page (open this or deploy it)
├── build.py            # builds index.html from the sources
├── src/
│   ├── shell.html      # markup, styles, logo and illustration
│   ├── climate.js      # typical monthly climate per state + climate type (fallback for live weather)
│   ├── app.js          # journey, questions, selfie and filter check, plan and explanation
│   ├── engine.js       # guardrail filter, scoring, face reader, input safety checks
│   ├── db.js           # optional Supabase layer: catalogue, accounts, check-ins, analytics
│   └── india.js        # states, cities and climates
├── data/
│   ├── catalogue.json  # 806-product demo catalogue (bundled; also the database seed)
│   └── supabase.json   # database URL + public anon key (empty = offline mode)
├── supabase/
│   ├── migrations/     # schema, row-level security, erasure function, report views
│   ├── seed.sql        # generated catalogue upsert (tools/seed_catalogue.py)
│   └── tests/          # RLS tests + end-to-end browser test against a mocked API
└── tools/
    └── seed_catalogue.py
```

## Run locally

No install needed. Open `index.html` in a browser, or serve the folder:

```bash
python3 -m http.server 8000
# then open http://localhost:8000
```

The camera needs `https://` or `localhost`. If the camera can't open, **Upload a photo** still works, and on phones it also lets you take a new selfie.

## Edit and rebuild

Change files in `src/` or `data/`, then run:

```bash
python3 build.py
```

## Deploy on GitHub Pages

1. Push this folder to a GitHub repository.
2. Go to **Settings → Pages → Build and deployment**, and set **Source: Deploy from a branch**, **Branch: `main` / root**.
3. Your advisor will be live at `https://<your-username>.github.io/<repo-name>/`.

## Database (Supabase)

The app works with no database at all: leave `data/supabase.json` empty and everything stays in the browser, as before. Connect a free [Supabase](https://supabase.com) project and it gains:

| What | Stored when | Who can read it |
|---|---|---|
| **Catalogue** (`products`, `shades`) | Always; seeded from `data/catalogue.json` | Anyone (read-only). Pages load it only when the database version differs from the one they were built with, so a price or ingredient fix goes live without a rebuild. |
| **Saved answers and plans** (`profiles`, `plans`) | Only after the user signs in by email link **and** ticks the consent box | The signed-in owner only (row-level security) |
| **Check-ins and reactions** (`checkins`, `reactions`) | Same as above | The owner only |
| **Anonymous analytics** (`events`) | Plans shown, swaps, tuning, set-aside counts, check-in outcomes | Nobody through the API; you query it in the dashboard |

Analytics never include a name, email, city, pregnancy status or reaction answers, and the "set aside" counts drop the pregnancy and reaction rules (A2, B3, B4) because a count of those would reveal the answer. Events are sent with the public key, not the login, so they can't be linked to an account. Browsers with Do Not Track or Global Privacy Control send none. Selfies are never uploaded.

**Delete my answers** asks for confirmation, then erases this device's copy and, if signed in, every account row and the login itself (`delete_my_data()`). Typing "delete my data" in the chat now opens the same confirmation instead of deleting straight away, because ordinary questions such as "how do I remove tan… in this photo" also matched.

**Live project:** `aaina-skin-advisor` (Supabase, Mumbai `ap-south-1`) is set up with this schema and the full catalogue (806 products, 597 shades, version `f1d460ebf65d`), and `data/supabase.json` points at it. To finish sign-in, set the site's public address under **Authentication → URL Configuration** (step 3 below) once it is hosted.

### Set it up (about 10 minutes)

1. Create a project at [supabase.com](https://supabase.com) (the free tier is enough).
2. In **SQL Editor**, run `supabase/migrations/20261112000000_init.sql`, then `supabase/seed.sql`. Or from a terminal: `psql "$DATABASE_URL" -f supabase/migrations/20261112000000_init.sql -f supabase/seed.sql`.
3. In **Authentication → URL Configuration**, set **Site URL** to your GitHub Pages address (for example `https://<user>.github.io/<repo>/`) and add it, plus `http://localhost:8000/**` for testing, under **Redirect URLs**. Email sign-in is on by default.
4. In **Project Settings → API**, copy the **Project URL** and the **anon public** key into `data/supabase.json`:
   ```json
   { "url": "https://abcdefgh.supabase.co", "anonKey": "eyJhbGciOi..." }
   ```
   The anon key is meant to be public; row-level security is what protects the data. Never put the `service_role` key here.
5. Run `python3 build.py` (it prints `database ON`), commit and push.

Supabase's built-in email sender is limited to a few emails an hour, which is fine for a demo. For real users, add your own SMTP under **Authentication → Emails**.

**Updating the catalogue:** edit `data/catalogue.json`, run `python3 tools/seed_catalogue.py`, then run the new `supabase/seed.sql`. Live pages pick up the change on their next visit; rebuild when convenient so the bundled copy matches.

**Reports:** `report_checkin_outcomes` (how each product is going for people) and `report_daily_events` are views for the SQL editor.

### Tests

```bash
supabase/tests/run_db_tests.sh
```

Starts a throwaway local Postgres, loads the schema and seed, then runs:
- **36 row-level security tests** (`rls_test.sql`), under Supabase's default grants. For example: one user can't read or change another's data, nothing is accepted before consent, analytics are write-only, and `TRUNCATE` is blocked. Supabase's defaults would otherwise allow `TRUNCATE`, and row-level security doesn't apply to it.
- **34 end-to-end checks** (`e2e_test.py`): the real page in Chrome against the real schema, through a small mock of Supabase's API (`mock_supabase.py`). They cover:
  - catalogue refresh, sign-in, consent, plan and check-in sync
  - a second device, isolation from another user, and anonymous analytics
  - deletion, offline fallback and no-config mode

Needs PostgreSQL server binaries, `pip install psycopg playwright`, and Chrome.

## Privacy note

The selfie consent screen tells users their photo is stored for **18 months**. This demo does **not** store photos: they are analysed in the browser and discarded, and the database layer never uploads them. Answers are stored in an account only with explicit consent (recorded with a version and timestamp) and can be erased in one step. A production version would still need a full review against India's Digital Personal Data Protection Act, 2023.

## Disclaimer

Cosmetic advice only, not medical advice. For painful, spreading or persistent skin problems, see a dermatologist.
