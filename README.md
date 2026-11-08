# Aaina AI Skin Advisor

> **Reflect. Reveal. Radiate.**
> A guided skincare advisor that asks ten short questions and builds a **3-product plan** (treat → hydrate → protect), then explains exactly why each product was chosen.

Built for **PS-14, Masters' Union Applied AI Challenge**. Aaina and all products in the catalogue are fictional (demo data).

## What it does

- **Personal start:** asks your first name and greets you by time of day.
- **A 10-step journey (Q1–Q10):** a progress bar shows each step, one question at a time, with a Back button on every screen.
  1. Main concern (illustrated cards)
  2. Concern-specific follow-up
  3. Anything else to help with
  4. Ingredients to avoid
  5. Past reactions
  6. Pregnancy caution
  7. State and city (962 Indian cities, with search; climate shapes texture choices)
  8. Skin type
  9. Skin tone (Monk 1–10 scale, or a selfie)
  10. Budget
- **Selfie skin-tone reader:** uses the camera or a photo upload after explicit consent. It reads skin tone and undertone from the face region, asks for a retake when lighting is poor, and offers 3 or 5 photos when the reading falls between two shades.
- **Filter check:** warns when a photo looks filtered (airbrushed skin with a sharp background, black-and-white, boosted colour or colour casts) and asks for a retake without a filter.
- **The plan:** three products that work together, a total price, two clearly labelled sponsored suggestions with relevance reasons, and a detailed "Why I recommended these" section.

## Guardrails enforced in code

Every product passes a hard filter before it can be ranked (`check()` in `src/engine.js`):

| Area | Rule |
|---|---|
| Safety | No retinoids or strong salicylic acid when pregnancy-cautious; no ingredient you've reacted to; products with no ingredient list are excluded |
| Preferences | Fragrance-free (including hidden fragrance such as linalool and limonene); no essential oils; no pore-clogging formulas; gentle picks for sensitive skin |
| Fit | Skin-type match; no drying alcohol for dry skin in dry, cold weather; within budget |
| Combinations | No retinoid together with acids; no two retinoids in one plan |
| Honesty | Sponsored items are labelled, pass the same checks and never affect ranking; no skin-lightening advice; no guarantees; red-flag symptoms and prescription questions go to a dermatologist; prompt-injection attempts are refused |

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
