# Aaina catalogue — data structure

The product feed the Ask Aaina chatbot and the engine both read from.

Two layers:

1. **Source of truth** — `PS-14_catalogue.xlsx` (806 products × 23 columns;
   597 shades × 7 columns). The PS-14 synthetic dataset.
2. **Runtime catalogue** — `data/catalogue.json` (same data, compressed field
   names, one array of 806 objects, inlined into `index.html` by `build.py`).
   This is what `engine.js` queries at runtime.

Everything downstream — the recommendation engine, the chatbot, the RAG
embedding index — reads only from the runtime JSON. The .xlsx is read once at
data-prep time.

---

## 1. Source schema (`PS-14_catalogue.xlsx`)

### Sheet: `products` — 806 rows × 23 columns

| Column | Type | Description | Example |
|---|---|---|---|
| `product_id` | string | Primary key | `P1000` |
| `brand` | string | Fictional brand | `Nordic Ray` |
| `product_name` | string | Full product name | `Nordic Ray Cream Cleanser` |
| `category` | enum | One of: Cleanser, Toner, Serum, Moisturiser, Sunscreen, Face oil, Mask, Eye cream, Lip balm, Foundation, Concealer, Compact powder, BB / CC cream | `Cleanser` |
| `key_actives` | string | Headline actives with % where declared | `Niacinamide 10%` |
| `ingredients_inci` | string | **Full INCI list, concentration-ordered.** The source of truth for every ingredient check. | `Aqua, Sodium Cocoyl Glycinate, Niacinamide, ...` |
| `concerns_targeted` | csv | Concerns the product is built for (lowercase, comma-separated) | `acne, dullness, oiliness, pigmentation` |
| `skin_types_suited` | csv | Skin types (oily, combination, normal, dry, sensitive) | `oily, combination, normal, dry` |
| `contains_fragrance` | bool | TRUE if Parfum / declared fragrance allergen in INCI | `False` |
| `contains_essential_oils` | bool | TRUE if any essential oil in INCI | `False` |
| `contains_drying_alcohol` | bool | TRUE if Alcohol Denat. in INCI | `False` |
| `contains_retinoid` | bool | TRUE if retinol or retinyl ester in INCI | `False` |
| `contains_aha` | bool | TRUE if glycolic/lactic acid in INCI | `False` |
| `contains_bha` | bool | TRUE if salicylic acid in INCI | `False` |
| `comedogenic_risk` | enum | `low` / `medium` / `high` | `low` |
| `pregnancy_caution` | bool | TRUE if advisers commonly flag it (retinoids, 2% leave-on BHA) | `False` |
| `spf` | float? | Declared SPF (sunscreens, BB/CC) | `30.0` |
| `pa_rating` | string? | UVA grade | `PA+++` |
| `finish` | enum? | `matte` / `natural` / `dewy` | `natural` |
| `price_inr` | int | MRP in rupees | `829` |
| `size` | string | Pack size | `200 ml` |
| `is_sponsored_placement` | bool | TRUE if the brand pays for promoted placement | `False` |
| `launch_date` | date | First listed | `2023-01-31` |

### Sheet: `shades` — 597 rows × 7 columns

Every foundation, concealer, compact powder, and BB/CC cream shade.

| Column | Type | Description | Example |
|---|---|---|---|
| `shade_id` | string | Primary key | `P1614-S01` |
| `product_id` | string | FK → `products.product_id` | `P1614` |
| `shade_name` | string | Consumer-facing name | `111 Cool Porcelain` |
| `depth_level` | int (1–10) | Monk Skin Tone scale (1 lightest, 10 deepest) | `1` |
| `undertone` | enum | `warm` / `neutral` / `cool` / `olive` | `cool` |
| `hex_colour` | string | Approx colour (illustrative) | `#fce7e8` |
| `coverage` | enum | `sheer` / `medium` / `full` | `sheer` |

Joins on `product_id`.

### Deliberate data quality issues

Per the catalogue README — the chatbot and engine must handle these:

| Issue | Count | How we handle it |
|---|---|---|
| Prices stored as text (`'Rs. 449'`) instead of numbers | 30 | Parsed with a regex → int during data-prep; rows failing to parse are flagged and never shown to a user with a budget set. |
| Blank `ingredients_inci` | 12 | **Any user with a stated constraint sees zero of these products.** The `check()` function treats blank INCI as "unknown-composition → refuse" whenever `avoidFrag`, `avoidEO`, `reactions`, `sensitive`, `noClog` or `pregnancy` is set. |
| Boolean flags disagree with the INCI list | some | **Trust the INCI list.** Data-prep re-derives flags from INCI and overwrites the source flag when they diverge. A diff report goes to `reports/flag_discrepancies.csv`. |
| Deep shades (depth 8–10) are scarce | — | The shade matcher honestly says "no close shade available" rather than returning a bad near-match. |

---

## 2. Runtime schema (`data/catalogue.json`)

Compressed because the whole catalogue is inlined into a single-page app. 806
objects, one per product. Field names are short to keep `index.html` small.

```json
{
  "id":  "P1000",                          // product_id
  "b":   "Nordic Ray",                     // brand
  "n":   "Nordic Ray Cream Cleanser",      // product_name
  "c":   "Cleanser",                       // category
  "a":   "Niacinamide 10%",                // key_actives
  "i":   "Aqua, Sodium Cocoyl ...",        // ingredients_inci (FULL)
  "con": ["acne","dullness","oiliness"],   // concerns_targeted (array)
  "st":  ["oily","combination","normal"],  // skin_types_suited (array)
  "fl":  "0000000",                        // packed flag string (see below)
  "com": "low",                            // comedogenic_risk
  "p":   829,                              // price_inr
  "sz":  "200 ml",                         // size
  "sp":  false,                            // is_sponsored_placement
  "spf": 30,                               // optional, sunscreens / BB-CC only
  "pa":  "PA+++",                          // optional
  "fin": "natural",                        // optional
  "s":   [                                 // optional: shades array for foundation/concealer/compact/bb-cc
    { "sid":"P1000-S01", "nm":"111 Cool Porcelain",
      "d":1, "u":"cool", "hex":"#fce7e8", "cov":"sheer" }
  ]
}
```

### Packed flags (`fl`)

A fixed-length string where each character is `'0'` or `'1'`, in this order:

```
position 0 → contains_fragrance
position 1 → contains_essential_oils
position 2 → contains_drying_alcohol
position 3 → contains_retinoid
position 4 → contains_aha
position 5 → contains_bha
position 6 → pregnancy_caution
```

Example `"0000000"` = no flags set. `"1001001"` = fragrance + retinoid +
pregnancy-caution. Packed because it saves ~30 KB over named booleans in
every product.

### Catalogue version hash

`build.py` writes `CAT_VERSION` into the page — the first 12 chars of a
SHA-256 over `data/catalogue.json`. The DB layer compares the hash to decide
whether to re-sync; the embedding index does the same (see §4). Any edit to
the catalogue invalidates both.

---

## 3. The query the chatbot sees

When the user types a message, the chatbot assembles a **query profile** in
exactly the shape the engine already expects. Nothing new; the chat is just
another way to fill the same object the quiz fills.

```js
{
  goal:       "routine" | "sunscreen" | "makeup" | null,
  gender:     "woman" | "man" | null,
  skin:       "dry" | "normal" | "combination" | "oily" | null,
  concerns:   ["acne","pigmentation", ...],        // keys from PROBLEMS in app.js
  sensitive:  bool,
  avoidFrag:  bool,
  avoidEO:    bool,
  noClog:     bool,
  reactions:  ["fragrance","retinoids", ...],      // free-text ingredient names
  pregnancy:  true | false | null,
  city:       "Mumbai" | null,
  state:      "Maharashtra" | null,
  climate:    "humid coastal" | ...,               // derived from city when possible
  budget:     500 | 1000 | 2000 | null,            // null = no limit
  tone:       1..10 | null,                        // Monk depth
  undertone:  "warm" | "neutral" | "cool" | "olive" | null
}
```

Anything not stated stays `null` / `false` and is interpreted as "no
constraint", not "unknown-therefore-safe". See the guardrails doc, §7.

---

## 4. RAG index (`data/embeddings.json`)

Built once per catalogue version by `tools/build_embeddings.py` and inlined
into `index.html`. See `src/rag.js` for the retrieval code.

```json
{
  "model":      "text-embedding-3-small",
  "dim":        1536,
  "cat_hash":   "b2a79f7566a5",
  "built_at":   "2026-11-18T12:00:00Z",
  "items": [
    {
      "id":       "P1000",
      "text":     "Nordic Ray Cream Cleanser (Cleanser) | key actives: Niacinamide 10% | concerns: acne, dullness, oiliness, pigmentation | suits: oily, combination, normal, dry | fragrance-free, no essential oils, low comedogenic risk | ₹829 for 200 ml",
      "vec":      [0.0123, -0.0456, ...]             // 1536 floats
    }
  ]
}
```

### Chunking strategy

**One chunk per product.** Deliberately coarse, for two reasons:

1. A product is the atomic unit a user ends up buying. Chunking finer (per
   ingredient, per section of the INCI list) scatters a product's signal
   across many chunks, which then compete with each other in retrieval.
2. Adding the engine-relevant facts (category, actives, concerns, flags,
   price) as a short structured string before the INCI list means the
   embedding captures *why* this product exists, not just the chemistry.

### The chunk text (built in `tools/build_embeddings.py`)

```
{brand} {product_name} ({category}) | key actives: {key_actives}
| concerns: {concerns_targeted}
| suits: {skin_types_suited}
| {pretty_flags}       e.g. "fragrance-free, no essential oils, low comedogenic risk"
| {climate_fit}        e.g. "light texture suits humid coastal"
| {size_and_price}     e.g. "₹829 for 200 ml"
| ingredients: {first_12_inci_items}
```

Ingredients are truncated to the top 12 INCI entries because concentration
order means those are the ones that drive effect and skin compatibility. The
full INCI stays in `data/catalogue.json` for the engine's hard-constraint
check — it is not needed for semantic similarity.

### Fusion with the rule engine

Retrieval returns the top-50 products by cosine similarity. Those 50 pass
through `engine.check()` (hard constraints — see guardrails §2) and then are
ranked by a **Reciprocal Rank Fusion** of two scores:

```
RRF(product) = 1 / (k + rank_embedding(product))
             + 1 / (k + rank_engine(product))
```

with `k = 60` per the RRF default. Products the engine rejects outright are
dropped before fusion, not down-weighted. The final top-3 per slot is what
the plan page shows.

This gives the RAG layer veto power over *irrelevance* (a sunscreen for a
query about acne) and the rule engine veto power over *unsafety* (a
fragranced product for a user who avoids fragrance). Neither can override the
other in its own domain.

### Rebuilding the index

Whenever `data/catalogue.json` changes:

```bash
export OPENAI_API_KEY=sk-...
python3 tools/build_embeddings.py        # ~15 seconds, ~$0.02 for 806 items
python3 build.py                         # rebuild index.html
```

The catalogue hash check in `build.py` warns if the embeddings file is out of
date. Stale embeddings never ship: `rag.js` refuses to load an index whose
`cat_hash` doesn't match the current `CAT_VERSION`.
