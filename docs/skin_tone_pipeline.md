# Skin tone pipeline: design and test results

## How it works

1. **Light reference and colour correction** (`readPhoto` in `src/engine.js`): the whites of the eyes, found beside the iris, give the colour and brightness of the light; skin is divided by it in linear light. With no usable eye whites, a partial colour balance from the background is used. A red channel clipped by bright light is rebuilt from green using real skin's red/green ratio.
2. **Skin mask**: one colour model per side of the face, seeded from the cheeks, keeps only facial skin, so hair, brows, eyes, lips, beard, glasses frames and background inside the oval are excluded. Six zones (forehead, cheeks and chin, left and right) are read through the mask; a side in shadow is set aside and the lit side is read.
3. **Filter check** (`detectFilter` in `src/app.js`): flags beauty smoothing, black-and-white, boosted saturation and colour tints before reading, and asks for an unfiltered photo.
4. **Mapping layer onto the shade library**: one centroid per Aaina tone (1-10) in the reader's corrected colour space; by default the centroids are the library swatches. `tools/ccv2/train_mapping.py` learns them from labelled photos (per-person averages, shrunk towards the swatch, lightness kept in order) and the build injects `data/calibration.json`. A photo always maps to the closest existing tone: there is no way to produce a new category.
5. **Product shades**: the measured colour is moved into the library's colour space and compared with every shade of a product within one depth of the tone (colour difference plus undertone); the exact library name is returned (e.g. `176 Neutral Medium`), or "no close shade" when none is within reach.
6. **Confidence and recapture**: an internal confidence combines how clearly one tone wins, the light reference used, skin coverage and agreement between zones. Below 0.22, or when the photo is unreadable (no face, face too small, blown out, too dark), the user is asked to retake.

Why not a deep network: the page runs on the phone with no libraries, the only face dataset with Monk labels that includes India restricts training, and its labels are annotators' judgement of apparent tone. A measured-colour pipeline with a small learned mapping layer uses the data where it is reliable (where each tone lands in real camera colour) and keeps the shade library as the final authority.

## Test 1: simulated selfies (40 people x 12 conditions, light applied to face, eyes and wall together)

| reader | recapture | exact | within one | off by 2+ | same answer across conditions |
|---|---|---|---|---|---|
| previous | 2.9% | 78.5% | 87.8% | 12.2% | 79.6% |
| new (mask + mapping layer) | 3.3% | 84.1% | 93.5% | 6.5% | 85.0% |

| condition | previous: recapture, exact, within one, off by 2+ | new |
|---|---|---|
| daylight | 0.0% | 90.0% | 95.0% | 5.0% | 0.0% | 90.0% | 95.0% | 5.0% |
| warm bulb | 0.0% | 82.5% | 95.0% | 5.0% | 0.0% | 82.5% | 95.0% | 5.0% |
| dim room | 0.0% | 92.5% | 97.5% | 2.5% | 0.0% | 92.5% | 97.5% | 2.5% |
| side shadow | 0.0% | 85.0% | 95.0% | 5.0% | 0.0% | 87.5% | 95.0% | 5.0% |
| hair fringe | 0.0% | 92.5% | 95.0% | 5.0% | 0.0% | 92.5% | 95.0% | 5.0% |
| beard | 0.0% | 92.5% | 95.0% | 5.0% | 0.0% | 92.5% | 95.0% | 5.0% |
| lipstick | 0.0% | 92.5% | 92.5% | 7.5% | 0.0% | 92.5% | 92.5% | 7.5% |
| glasses | 0.0% | 87.5% | 92.5% | 7.5% | 0.0% | 90.0% | 92.5% | 7.5% |
| fringe beard warm | 0.0% | 7.5% | 15.0% | 85.0% | 0.0% | 67.5% | 82.5% | 17.5% |
| vivid camera | 0.0% | 90.0% | 97.5% | 2.5% | 5.0% | 89.5% | 97.4% | 2.6% |
| beauty filter | 27.5% | 27.6% | 86.2% | 13.8% | 27.5% | 27.6% | 86.2% | 13.8% |
| colour filter | 7.5% | 89.2% | 97.3% | 2.7% | 7.5% | 89.2% | 97.3% | 2.7% |

**Product shades** (12 base-makeup products per photo, 464 photos): the exact closest library shade was chosen 80.0% of the time; when it wasn't, the pick was on average only 0.74 ΔE further away; average depth error 0.21.
**Filters**: the beauty filter was flagged in 40 of 40 photos (the app then asks for an unfiltered selfie); colour tints were caught in only 4 of 40, but the light correction kept those readings accurate.
**Confidence**: average 0.84 when exact vs 0.7 when off by two or more: it separates only weakly, so it is used for recapture of clearly poor photos, not to fine-tune.

## Test 2: dry run of the dataset pipeline (stand-in data, not Casual Conversations v2)

80 simulated people (8 per tone), 160 short videos under four lighting set-ups, filmed by a 'camera' that brightens mid-tones and boosts saturation. Steps 1-4 ran unchanged; the inspector mapped every field of an unfamiliar annotation layout; the face finder located 79 of 80 people.

| mapping (held-out people, 5-fold) | exact | within one | off by 2+ |
|---|---|---|---|
| current (library swatches) | 49.5% | 91.3% | 8.7% |
| learned from the data | 78.9% | 92.0% | 8.0% |

This shows the pipeline works and can learn a camera's bias. It says nothing about accuracy on real faces: that needs step 4 on the real dataset. The stand-in calibration is not shipped.

## Limits
- All results above are on simulated images. Real faces add makeup, uneven skin, motion blur and compression.
- Very light tones (1-3) have near-identical library swatches, so neighbours are often confused; the mapping keeps light-tone readings within one shade most of the time.
- The confidence score separates right from wrong only weakly.
- Casual Conversations v2's licence limits training; confirm it allows fitting this mapping layer before shipping a calibration learned from it.