# Aaina AI Skin Advisor

> **Reflect. Reveal. Radiate.**
> A guided skincare advisor that asks ten short questions and builds a **3-product plan** (treat → hydrate → protect), then explains exactly why each product was chosen.

Built for **PS-14, Masters' Union Applied AI Challenge**. Aaina and all products in the catalogue are fictional (demo data).

## What it does

- **Personal start:** asks your first name and greets you by time of day.
- **A 7-step journey (Q1–Q7):** concern, follow-up, other concerns, safety check, location, skin type, skin tone. A progress bar shows each step, one question at a time, with a Back button on every screen.
- **One-page safety check (Q4):** everything that keeps a product safe is answered together: ingredients to avoid, past reactions, pregnancy caution and warning signs happening right now (pain, spreading, bleeding, a changing mole, fever). Every section must be answered (**None** counts) before Continue unlocks, and a live line sums up what will be skipped. Earlier answers carry in (for example "I'd rather avoid retinol" pre-ticks retinoids). Any warning sign shows a dermatologist notice and keeps the plan gentle.
  1. Main concern (illustrated cards)
  2. Concern-specific follow-up
  3. Anything else to help with
  4. Ingredients to avoid
  5. Past reactions
  6. Pregnancy caution
  7. State and city (962 Indian cities, with search; climate shapes texture choices)
  8. Skin type
  9. Skin tone (Monk 1–10 scale, or a selfie)

  Budget and "already using" are not questions any more: they live on the plan page (see **Tune your plan**).
- **Selfie skin-tone reader:** uses the camera or a photo upload after explicit consent. It reads skin tone and undertone from the face region, asks for a retake when lighting is poor, and offers 3 or 5 photos when the reading falls between two shades.
- **Smarter photo checks:** a borderline undertone no longer forces a retake (you get one optional question instead), near-identical neighbouring tones (such as Monk 1 and 2) are shown side by side for a one-tap confirm, blown-out scenes and colour casts are named correctly so the retake advice fits the problem.
- **Filter check:** warns when a photo looks filtered (airbrushed skin with a sharp background, black-and-white, boosted colour or colour casts) and asks for a retake without a filter.
- **Tune your plan (on the plan page):** one panel to change the budget per product and what you already use, together. Each budget option previews what it would give you (how many steps are covered and the total). Change several things, then press **Update my plan** once; the advisor rebuilds the plan, says how many steps changed, and keeps every safety rule. The plan starts at up to ₹700 per product.
- **Save and resume:** answers are saved on the device after every step. Returning users see "Continue where I left off" (or "View my plan"), and **Delete my answers** clears everything.
- **Builds around what you already use:** if you already own a product that covers a step and passes your checks, the plan keeps it instead of selling you another. New picks never clash with your routine (retinoid + acids, retinoid + benzoyl peroxide), avoid doubling up on actives you already use, and warn you about owned products that fail your safety answers.
- **Upgrade picks and combos for products you already own:** every "Already yours" step shows an **Upgrade pick**: the best product for that step that passes your checks, with reasons it's better than what you have (for example, it adds an ingredient that targets your concern, it's made for your concern or skin type, it has SPF 50, or it suits this week's weather). **Switch to this** swaps it in. When you already own one or more steps, the plan also offers two **combos** (a *Quick boost* and a *Full routine upgrade*) of add-on products, such as a lightweight moisturiser, a weekly exfoliant or a mask, chosen to work with your existing routine without clashing, with prices and how your morning, night and weekly routine would look. **Add to my plan** adds them as add-ons, which are counted in the total, saved, shared and included in the PDF.
- **Day-3 and week-2 check-ins:** the welcome screen asks how each product is going once the time comes, and a check-in can be started any time from the plan. "Stinging or redness" or "New breakouts" removes that product, swaps in the next safe option, and adds its main active to your reactions so future plans avoid it.
- **Live 7-day weather on the location step:** after choosing a city, the advisor looks up the last 7 days of real weather and air quality there ([Open-Meteo](https://open-meteo.com/), free, no API key): daily highs and lows, humidity, rain, UV and PM2.5. It sums the week up (for example "Warm, dry and smoggy"), explains what each reading means for skin, and uses it to rank textures: ceramide creams for dry air or cold nights, oil-free gels for humidity or rain, SPF 50 for high UV, antioxidant serums for pollution. The drying-alcohol guardrail also uses the live readings. Results are cached for 3 hours. If the weather service can't be reached, it falls back to the usual season for that region, and says so.
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
│   ├── app.js          # journey, questions, selfie and filter check, plan and explanation
│   ├── engine.js       # guardrail filter, scoring, face reader, input safety checks
│   └── india.js        # states, cities and climates
└── data/
    └── catalogue.json  # 806-product demo catalogue
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

## Privacy note

The consent screen tells users their photo is stored for **18 months**. This demo does **not** store anything: photos are analysed in the browser and discarded. A production version must implement real storage, deletion on request, and consent records in line with India's Digital Personal Data Protection Act, 2023.

## Disclaimer

Cosmetic advice only, not medical advice. For painful, spreading or persistent skin problems, see a dermatologist.
