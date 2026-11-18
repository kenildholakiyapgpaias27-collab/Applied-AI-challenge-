# PS-14 Recommendation evaluation

- **Catalogue:** 806 products, 19 categories
- **Test set:** 220 customer profiles, 1984 labelled items across 660 (profile, category) slots
- **K (top-K per slot):** 3

## Overall metrics

- **Recall@3** — fraction of GOOD labels present in top-3 recommendations: **30.8%** (382 of 1241)
- **Precision@3** — fraction of top-3 picks that are GOOD: **19.3%**
- **Safety rate** — fraction of top-3 picks that are NOT MUST_NOT_RECOMMEND: **99.2%**
- **MUST_NOT violations in top-3:** 15
- **MUST_NOT that still appear anywhere in the passing set:** 9

## Per category

| Category | Slots | Recall@K | MUST_NOT in top-K |
|---|---:|---:|---:|
| Cleanser | 44 | 12.1% | 0 |
| Exfoliant | 40 | 27.5% | 0 |
| Eye cream | 37 | 50.5% | 4 |
| Face mask | 40 | 36.3% | 2 |
| Face oil | 42 | 45.3% | 5 |
| Foundation | 220 | 0.0% | 0 |
| Lip care | 44 | 34.1% | 0 |
| Moisturiser | 39 | 24.8% | 0 |
| Serum | 35 | 26.7% | 0 |
| Spot treatment | 35 | 8.0% | 4 |
| Sunscreen | 46 | 31.2% | 0 |
| Toner | 38 | 40.4% | 0 |

## Shade matching (foundation)

- Slots evaluated: **220**
- Exact BEST_SHADE match on the top foundation pick: **7 (3%)**

## Notes

- Labels: GOOD = recommender should rank highly; MUST_NOT_RECOMMEND = recommender must never surface for that profile; BEST_SHADE = exact foundation shade the profile should match on.
- Hard-constraint checks (`check()`) are ported verbatim from `src/engine.js`: fragrance/essential-oil avoidance, reactions, pregnancy (retinoids + caution flag), skin-type fit, comedogenic risk for oily+acne, budget.
- See `reports/eval_per_profile.csv` for the full per-(profile, category) breakdown.