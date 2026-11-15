# Test-set evaluation (2026-11-15)

Engine: `src/engine.js` run in Node by `tools/eval_testset.py` on the 220 profiles of `PS-14_recommendation_test_set.xlsx` (synthetic, from the challenge organisers), using only the self-reported answers. Ground truth is used for scoring only.

## A. Try-on shade accuracy ("Your match")

"Your match" in the try-on is `bestShade(product, self tone, self undertone or neutral)`, the same call the plan page uses. Scored on each customer's BEST_SHADE foundation. Bands are by measured (true) tone.

**Try-on today**

| Band | n | Exact shade | Depth error vs true tone (mean) | MAE | Within 1 | Off by 2+ | Undertone match | Within 1 of labelled best |
|---|---|---|---|---|---|---|---|---|
| All | 220 | 39.1% | -0.89 | 1.15 | 71.4% | 28.6% | 45.9% | 79.5% |
| 1–3 | 18 | 44.4% | -0.28 | 0.72 | 94.4% | 5.6% | 38.9% | 94.4% |
| 4–7 | 176 | 33.0% | -0.8 | 1.07 | 72.7% | 27.3% | 46.0% | 75.6% |
| 8–10 | 26 | 76.9% | -1.92 | 2.0 | 46.2% | 53.8% | 50.0% | 96.2% |

Band gap (best minus worst): exact shade 43.9 pts, within 1 step of true tone 48.2 pts, within 1 of labelled best 20.6 pts, undertone 11.1 pts. Target: under 5 pts.

**Naive baseline: depth = self tone, same undertone**

| Band | n | Exact shade | Depth error vs true tone (mean) | MAE | Within 1 | Off by 2+ | Undertone match | Within 1 of labelled best |
|---|---|---|---|---|---|---|---|---|
| All | 220 | 47.7% | -0.85 | 1.06 | 75.0% | 25.0% | 38.6% | 82.7% |
| 1–3 | 18 | 55.6% | -0.28 | 0.61 | 100.0% | 0.0% | 38.9% | 94.4% |
| 4–7 | 176 | 40.9% | -0.77 | 0.98 | 76.1% | 23.9% | 38.6% | 79.5% |
| 8–10 | 26 | 88.5% | -1.81 | 1.88 | 50.0% | 50.0% | 38.5% | 96.2% |

Band gap (best minus worst): exact shade 47.6 pts, within 1 step of true tone 50.0 pts, within 1 of labelled best 16.7 pts, undertone 0.4 pts. Target: under 5 pts.

**With the engine's self-report correction (correctedTone, not used by the app today)**

| Band | n | Exact shade | Depth error vs true tone (mean) | MAE | Within 1 | Off by 2+ | Undertone match | Within 1 of labelled best |
|---|---|---|---|---|---|---|---|---|
| All | 220 | 49.1% | -0.38 | 0.9 | 81.8% | 18.2% | 45.0% | 88.6% |
| 1–3 | 18 | 44.4% | +0.28 | 0.72 | 88.9% | 11.1% | 50.0% | 88.9% |
| 4–7 | 176 | 44.9% | -0.23 | 0.76 | 86.4% | 13.6% | 43.2% | 87.5% |
| 8–10 | 26 | 80.8% | -1.88 | 1.96 | 46.2% | 53.8% | 53.8% | 96.2% |

Band gap (best minus worst): exact shade 36.4 pts, within 1 step of true tone 42.7 pts, within 1 of labelled best 8.7 pts, undertone 10.6 pts. Target: under 5 pts.

**Ceiling: the labelled best shade itself (how close the catalogue can get)**

| Band | n | Exact shade | Depth error vs true tone (mean) | MAE | Within 1 | Off by 2+ | Undertone match | Within 1 of labelled best |
|---|---|---|---|---|---|---|---|---|
| All | 220 | 100.0% | -0.37 | 0.43 | 92.7% | 7.3% | 45.9% | 100.0% |
| 1–3 | 18 | 100.0% | +0.06 | 0.28 | 100.0% | 0.0% | 66.7% | 100.0% |
| 4–7 | 176 | 100.0% | -0.2 | 0.23 | 98.3% | 1.7% | 43.8% | 100.0% |
| 8–10 | 26 | 100.0% | -1.85 | 1.85 | 50.0% | 50.0% | 46.2% | 100.0% |

Band gap (best minus worst): exact shade 0.0 pts, within 1 step of true tone 50.0 pts, within 1 of labelled best 0.0 pts, undertone 22.9 pts. Target: under 5 pts.

**10 worst misses (try-on)**

| Customer | Self tone / undertone | True tone / undertone | Predicted | Labelled best | Depth error |
|---|---|---|---|---|---|
| C102051 | 7 / cool | 9 / cool | P1637-S05 154 Neutral Light (depth 4, neutral) | P1637-S07 175 Warm Light Medium (depth 5, warm) | -5 |
| C100025 | 3 / warm | 6 / warm | P1622-S04 142 Warm Ivory (depth 2, warm) | P1622-S09 195 Warm Light Medium (depth 5, warm) | -4 |
| C101660 | 10 / warm | 10 / warm | P1619-S06 166 Warm Medium (depth 6, warm) | P1619-S08 187 Cool Tan (depth 7, cool) | -4 |
| C100988 | 9 / warm | 10 / neutral | P1624-S06 166 Neutral Medium (depth 6, neutral) | P1624-S06 166 Neutral Medium (depth 6, neutral) | -4 |
| C101122 | 8 / cool | 9 / cool | P1616-S13 235 Neutral Light Medium (depth 5, neutral) | P1616-S13 235 Neutral Light Medium (depth 5, neutral) | -4 |
| C103679 | 8 / don't know | 8 / cool | P1625-S08 184 Warm Light (depth 4, warm) | P1625-S08 184 Warm Light (depth 4, warm) | -4 |
| C107631 | 9 / don't know | 8 / warm | P1625-S08 184 Warm Light (depth 4, warm) | P1625-S08 184 Warm Light (depth 4, warm) | -4 |
| C100321 | 5 / don't know | 8 / cool | P1629-S06 165 Warm Light Medium (depth 5, warm) | P1629-S07 176 Cool Medium (depth 6, cool) | -3 |
| C100625 | 3 / neutral | 5 / neutral | P1625-S04 142 Neutral Ivory (depth 2, neutral) | P1625-S08 184 Warm Light (depth 4, warm) | -3 |
| C101060 | 5 / cool | 7 / warm | P1626-S06 164 Cool Light (depth 4, cool) | P1626-S10 207 Warm Tan (depth 7, warm) | -3 |

## B. Safety

- Profiles with any MUST_NOT product in the top 5 of any category: **0.5%** (1 of 220). Target 0.
- MUST_NOT products blocked by `check()`: **504 of 523 (96.4%)**. Target 100%.
- On labels the quiz can know (all except skin-type labels where the customer's own answer differs from the measured skin type): **496 of 505 (98.2%)**.
- In a top 5: C103916 · Toner · P1098: not suited to dry skin (told us dry, measured dry).

| MUST_NOT reason | Labels | Leaked |
|---|---|---|
| fragrance — customer avoids fragrance | 209 | 0 |
| not suited to dry skin | 163 | 18 |
| not suited to oily skin | 57 | 1 |
| essential oil — customer avoids essential oils | 32 | 0 |
| contains <ingredient> — known reaction | 18 | 0 |
| retinoid/strong BHA — pregnancy caution opted in | 14 | 0 |
| not suited to oily skin; high comedogenic risk for acne-prone oily skin | 6 | 0 |
| fragrance — customer avoids fragrance; not suited to dry skin | 5 | 0 |
| essential oil — customer avoids essential oils; not suited to dry skin | 5 | 0 |
| fragrance — customer avoids fragrance; essential oil — customer avoids essential oils | 4 | 0 |
| fragrance — customer avoids fragrance; contains <ingredient> — known reaction | 4 | 0 |
| contains <ingredient> — known reaction; not suited to dry skin | 3 | 0 |
| essential oil — customer avoids essential oils; contains <ingredient> — known reaction | 1 | 0 |
| fragrance — customer avoids fragrance; essential oil — customer avoids essential oils; contains <ingredient> — known reaction | 1 | 0 |
| fragrance — customer avoids fragrance; essential oil — customer avoids essential oils; not suited to dry skin | 1 | 0 |

Leaks:

| Customer | Category | Product | Reason | Self / true skin | Cause |
|---|---|---|---|---|---|
| C103916 | Toner | P1098 | not suited to dry skin | dry / dry | our catalogue tags it for dry skin; the organisers' catalogue doesn't (added by tools/catalogue_check.py --fix) |
| C107568 | Toner | P1090 | not suited to dry skin | dry / dry | our catalogue tags it for dry skin; the organisers' catalogue doesn't (added by tools/catalogue_check.py --fix) |
| C107568 | Toner | P1119 | not suited to dry skin | dry / dry | our catalogue tags it for dry skin; the organisers' catalogue doesn't (added by tools/catalogue_check.py --fix) |
| C100885 | Moisturiser | P1320 | not suited to oily skin | oily / oily | our catalogue tags it for oily skin; the organisers' catalogue doesn't (added by tools/catalogue_check.py --fix) |
| C105783 | Toner | P1098 | not suited to dry skin | dry / dry | our catalogue tags it for dry skin; the organisers' catalogue doesn't (added by tools/catalogue_check.py --fix) |
| C102409 | Cleanser | P1073 | not suited to dry skin | oily / dry | label uses the measured skin type; the customer told the quiz a different one |
| C102409 | Cleanser | P1050 | not suited to dry skin | oily / dry | label uses the measured skin type; the customer told the quiz a different one |
| C102409 | Sunscreen | P1376 | not suited to dry skin | oily / dry | label uses the measured skin type; the customer told the quiz a different one |
| C102409 | Sunscreen | P1362 | not suited to dry skin | oily / dry | label uses the measured skin type; the customer told the quiz a different one |
| C102409 | Sunscreen | P1361 | not suited to dry skin | oily / dry | label uses the measured skin type; the customer told the quiz a different one |
| C100988 | Toner | P1090 | not suited to dry skin | dry / dry | our catalogue tags it for dry skin; the organisers' catalogue doesn't (added by tools/catalogue_check.py --fix) |
| C104378 | Spot treatment | P1550 | not suited to dry skin | oily / dry | label uses the measured skin type; the customer told the quiz a different one |
| C104378 | Spot treatment | P1560 | not suited to dry skin | oily / dry | label uses the measured skin type; the customer told the quiz a different one |
| C104227 | Toner | P1102 | not suited to dry skin | normal / dry | label uses the measured skin type; the customer told the quiz a different one |
| C104227 | Toner | P1098 | not suited to dry skin | normal / dry | label uses the measured skin type; the customer told the quiz a different one |
| C104227 | Toner | P1119 | not suited to dry skin | normal / dry | label uses the measured skin type; the customer told the quiz a different one |
| C102051 | Toner | P1098 | not suited to dry skin | dry / dry | our catalogue tags it for dry skin; the organisers' catalogue doesn't (added by tools/catalogue_check.py --fix) |
| C102051 | Toner | P1090 | not suited to dry skin | dry / dry | our catalogue tags it for dry skin; the organisers' catalogue doesn't (added by tools/catalogue_check.py --fix) |
| C106783 | Cleanser | P1062 | not suited to dry skin | dry / dry | our catalogue tags it for dry skin; the organisers' catalogue doesn't (added by tools/catalogue_check.py --fix) |

MUST_NOT labels cover skincare only; the try-on shows makeup. Its 'Not suitable for you' uses the same check(), and 'Add look to my plan' only adds products that pass check().

## C. Relevance

GOOD hit rate in the top 5 (a customer-category counts as a hit if any GOOD product is in our top 5): **65.3%** over 415 customer-categories; 30.9% of all GOOD products appear in a top 5.

| Category | Customer-categories | Hit rate | GOOD recall |
|---|---|---|---|
| Cleanser | 44 | 50.0% | 23.5% |
| Exfoliant | 40 | 72.5% | 33.3% |
| Eye cream | 37 | 83.8% | 36.0% |
| Face mask | 34 | 79.4% | 41.2% |
| Face oil | 33 | 27.3% | 11.6% |
| Lip care | 44 | 100.0% | 35.6% |
| Moisturiser | 39 | 76.9% | 41.0% |
| Serum | 35 | 57.1% | 26.7% |
| Spot treatment | 25 | 20.0% | 6.7% |
| Sunscreen | 46 | 41.3% | 15.9% |
| Toner | 38 | 92.1% | 61.4% |

## How profiles were mapped

- Skin type, sensitive, fragrance, essential oils, pregnancy caution: straight from the answers, as the quiz sets them.
- Known reaction: typed into the quiz's reaction box and matched with the engine's own REACTIONS patterns.
- Undertone "don't know": undertone not set (the quiz's "Not sure"), so matching assumes neutral.
- Budget band: the largest Tune-your-plan option (₹400 / ₹700 / ₹1,200 / no limit) not above the band.
- Season: month 10 (0 = January), which the engine uses for winter dryness.
- Concerns the quiz doesn't offer were dropped: concerns the quiz can't take: dark circles (45), concerns the quiz can't take: fine lines (16), concerns the quiz can't take: fine lines, dark circles (2), concerns the quiz can't take: dark circles, fine lines (2).
