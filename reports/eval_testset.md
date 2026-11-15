# Test-set evaluation (2026-11-15)

Engine: `src/engine.js` run in Node by `tools/eval_testset.py` on the 220 profiles of `PS-14_recommendation_test_set.xlsx` (synthetic, from the challenge organisers), using only the self-reported answers. Ground truth is used for scoring only.

## Before and after (vs `80c2665`)

| Measure | Before | After |
|---|---|---|
| "Your match" = labelled best shade | 39.1% | 52.3% |
| Within 1 step of measured tone | 71.4% | 84.1% |
| Depth MAE | 1.15 | 0.86 |
| Band gap, within 1 of labelled best | 20.6 pts | 7.3 pts |
| Band gap, exact shade | 43.9 pts | 45.7 pts |
| Profiles with a MUST_NOT in a top 5 | 0.5% | 0.9% |
| MUST_NOT blocked by check() | 96.4% | 97.3% |
|   on labels the quiz can know | 98.2% | 100.0% |
| GOOD in top 5 (hit rate) | 65.5% | 74.2% |

## A. Try-on shade accuracy ("Your match")

"Your match" in the try-on is `bestShade(product, self tone, self undertone or neutral)`, the same call the plan page uses. Scored on each customer's BEST_SHADE foundation. Bands are by measured (true) tone.

**Try-on "Your match"**

| Band | n | Exact shade | Depth error vs true tone (mean) | MAE | Within 1 | Off by 2+ | Undertone match | Within 1 of labelled best |
|---|---|---|---|---|---|---|---|---|
| All | 220 | 52.3% | -0.34 | 0.86 | 84.1% | 15.9% | 40.0% | 90.0% |
| 1–3 | 18 | 50.0% | +0.33 | 0.67 | 94.4% | 5.6% | 44.4% | 88.9% |
| 4–7 | 176 | 46.6% | -0.2 | 0.73 | 88.1% | 11.9% | 38.6% | 89.2% |
| 8–10 | 26 | 92.3% | -1.77 | 1.85 | 50.0% | 50.0% | 46.2% | 96.2% |

Band gap (best minus worst): exact shade 45.7 pts, within 1 step of true tone 44.4 pts, within 1 of labelled best 7.3 pts, undertone 7.6 pts. Target: under 5 pts.

**Naive baseline: depth = self tone, same undertone**

| Band | n | Exact shade | Depth error vs true tone (mean) | MAE | Within 1 | Off by 2+ | Undertone match | Within 1 of labelled best |
|---|---|---|---|---|---|---|---|---|
| All | 220 | 47.7% | -0.85 | 1.06 | 75.0% | 25.0% | 38.6% | 82.7% |
| 1–3 | 18 | 55.6% | -0.28 | 0.61 | 100.0% | 0.0% | 38.9% | 94.4% |
| 4–7 | 176 | 40.9% | -0.77 | 0.98 | 76.1% | 23.9% | 38.6% | 79.5% |
| 8–10 | 26 | 88.5% | -1.81 | 1.88 | 50.0% | 50.0% | 38.5% | 96.2% |

Band gap (best minus worst): exact shade 47.6 pts, within 1 step of true tone 50.0 pts, within 1 of labelled best 16.7 pts, undertone 0.4 pts. Target: under 5 pts.

**Ceiling: the labelled best shade itself (how close the catalogue can get)**

| Band | n | Exact shade | Depth error vs true tone (mean) | MAE | Within 1 | Off by 2+ | Undertone match | Within 1 of labelled best |
|---|---|---|---|---|---|---|---|---|
| All | 220 | 100.0% | -0.37 | 0.43 | 92.7% | 7.3% | 45.9% | 100.0% |
| 1–3 | 18 | 100.0% | +0.06 | 0.28 | 100.0% | 0.0% | 66.7% | 100.0% |
| 4–7 | 176 | 100.0% | -0.2 | 0.23 | 98.3% | 1.7% | 43.8% | 100.0% |
| 8–10 | 26 | 100.0% | -1.85 | 1.85 | 50.0% | 50.0% | 46.2% | 100.0% |

Band gap (best minus worst): exact shade 0.0 pts, within 1 step of true tone 50.0 pts, within 1 of labelled best 0.0 pts, undertone 22.9 pts. Target: under 5 pts.

Customers who said "don't know" for undertone (n=38): exact 50.0%, best shade among the two shown (match + "also try") 60.5%, undertone matches measured 39.5%.

**10 worst misses (try-on)**

| Customer | Self tone / undertone | True tone / undertone | Predicted | Labelled best | Depth error |
|---|---|---|---|---|---|
| C100988 | 9 / warm | 10 / neutral | P1624-S06 166 Neutral Medium (depth 6, neutral) | P1624-S06 166 Neutral Medium (depth 6, neutral) | -4 |
| C101122 | 8 / cool | 9 / cool | P1616-S13 235 Neutral Light Medium (depth 5, neutral) | P1616-S13 235 Neutral Light Medium (depth 5, neutral) | -4 |
| C102051 | 7 / cool | 9 / cool | P1637-S07 175 Warm Light Medium (depth 5, warm) | P1637-S07 175 Warm Light Medium (depth 5, warm) | -4 |
| C103679 | 8 / don't know | 8 / cool | P1625-S08 184 Warm Light (depth 4, warm) | P1625-S08 184 Warm Light (depth 4, warm) | -4 |
| C107631 | 9 / don't know | 8 / warm | P1625-S08 184 Warm Light (depth 4, warm) | P1625-S08 184 Warm Light (depth 4, warm) | -4 |
| C104333 | 2 / cool | 5 / cool | P1637-S01 112 Cool Ivory (depth 2, cool) | P1637-S07 175 Warm Light Medium (depth 5, warm) | -3 |
| C107072 | 7 / warm | 5 / warm | P1638-S14 248 Warm Deep (depth 8, warm) | P1638-S10 205 Warm Light Medium (depth 5, warm) | +3 |
| C100481 | 8 / warm | 7 / warm | P1625-S08 184 Warm Light (depth 4, warm) | P1625-S08 184 Warm Light (depth 4, warm) | -3 |
| C101660 | 10 / warm | 10 / warm | P1619-S08 187 Cool Tan (depth 7, cool) | P1619-S08 187 Cool Tan (depth 7, cool) | -3 |
| C103418 | 7 / cool | 9 / cool | P1629-S07 176 Cool Medium (depth 6, cool) | P1629-S07 176 Cool Medium (depth 6, cool) | -3 |

## B. Safety

- Profiles with any MUST_NOT product in the top 5 of any category: **0.9%** (2 of 220). Target 0.
- MUST_NOT products blocked by `check()`: **509 of 523 (97.3%)**. Target 100%.
- On labels the quiz can know (all except skin-type labels where the customer's own answer differs from the measured skin type): **505 of 505 (100.0%)**.
- In a top 5: C106937 · Face oil · P1575: not suited to oily skin (told us normal, measured oily).
- In a top 5: C104378 · Spot treatment · P1552: not suited to dry skin (told us oily, measured dry).

| MUST_NOT reason | Labels | Leaked |
|---|---|---|
| fragrance — customer avoids fragrance | 209 | 0 |
| not suited to dry skin | 163 | 11 |
| not suited to oily skin | 57 | 3 |
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
| C106937 | Face oil | P1581 | not suited to oily skin | normal / oily | label uses the measured skin type; the customer told the quiz a different one |
| C106937 | Face oil | P1580 | not suited to oily skin | normal / oily | label uses the measured skin type; the customer told the quiz a different one |
| C106937 | Face oil | P1575 | not suited to oily skin | normal / oily | label uses the measured skin type; the customer told the quiz a different one |
| C102409 | Cleanser | P1073 | not suited to dry skin | oily / dry | label uses the measured skin type; the customer told the quiz a different one |
| C102409 | Cleanser | P1050 | not suited to dry skin | oily / dry | label uses the measured skin type; the customer told the quiz a different one |
| C102409 | Sunscreen | P1376 | not suited to dry skin | oily / dry | label uses the measured skin type; the customer told the quiz a different one |
| C102409 | Sunscreen | P1362 | not suited to dry skin | oily / dry | label uses the measured skin type; the customer told the quiz a different one |
| C102409 | Sunscreen | P1361 | not suited to dry skin | oily / dry | label uses the measured skin type; the customer told the quiz a different one |
| C104378 | Spot treatment | P1550 | not suited to dry skin | oily / dry | label uses the measured skin type; the customer told the quiz a different one |
| C104378 | Spot treatment | P1552 | not suited to dry skin | oily / dry | label uses the measured skin type; the customer told the quiz a different one |
| C104378 | Spot treatment | P1560 | not suited to dry skin | oily / dry | label uses the measured skin type; the customer told the quiz a different one |
| C104227 | Toner | P1102 | not suited to dry skin | normal / dry | label uses the measured skin type; the customer told the quiz a different one |
| C104227 | Toner | P1098 | not suited to dry skin | normal / dry | label uses the measured skin type; the customer told the quiz a different one |
| C104227 | Toner | P1119 | not suited to dry skin | normal / dry | label uses the measured skin type; the customer told the quiz a different one |

MUST_NOT labels cover skincare only; the try-on shows makeup. Its 'Not suitable for you' uses the same check(), and 'Add look to my plan' only adds products that pass check().

## C. Relevance

GOOD hit rate in the top 5 (a customer-category counts as a hit if any GOOD product is in our top 5): **74.2%** over 415 customer-categories; 37.8% of all GOOD products appear in a top 5.

| Category | Customer-categories | Hit rate | GOOD recall |
|---|---|---|---|
| Cleanser | 44 | 50.0% | 25.0% |
| Exfoliant | 40 | 90.0% | 42.5% |
| Eye cream | 37 | 94.6% | 55.9% |
| Face mask | 34 | 79.4% | 46.1% |
| Face oil | 33 | 81.8% | 41.1% |
| Lip care | 44 | 100.0% | 35.6% |
| Moisturiser | 39 | 76.9% | 40.2% |
| Serum | 35 | 60.0% | 31.4% |
| Spot treatment | 25 | 28.0% | 12.0% |
| Sunscreen | 46 | 52.2% | 21.7% |
| Toner | 38 | 92.1% | 62.3% |

## How profiles were mapped

- Skin type, sensitive, fragrance, essential oils, pregnancy caution: straight from the answers, as the quiz sets them.
- Known reaction: typed into the quiz's reaction box and matched with the engine's own REACTIONS patterns.
- Undertone "don't know": the quiz's "Not sure", then "Still not sure" in the undertone helper (the test set has no helper answers). Matching then uses the engine's default for unknown undertones and also shows a second shade.
- Budget band: the largest Tune-your-plan option (₹400 / ₹700 / ₹1,200 / no limit) not above the band.
- Season: month 10 (0 = January), which the engine uses for winter dryness.
- Concerns: all test-set concerns map to quiz concerns (read from PROBLEMS in src/app.js).
