# Skin tone mapping report (stand-in dry run (2026-11-11))

Photos: 572, readable: 564 (recapture rate 1.4%), participants: 79.
Validation: 5-fold, grouped by participant.

| mapping | exact | within one | off by 2+ | consistency |
|---|---|---|---|---|
| Current (library swatches) | 49.5% | 91.3% | 8.7% | 85.3% |
| Learned (this data) | 78.9% | 92.0% | 8.0% | 86.2% |

## Per tone

| tone | participants | current exact | learned exact | learned within one |
|---|---|---|---|---|
| 1 | 8 | 66.7% | 58.3% | 66.7% |
| 2 | 8 | 52.1% | 50.0% | 83.3% |
| 3 | 7 | 66.7% | 55.6% | 66.7% |
| 4 | 8 | 86.7% | 73.3% | 100.0% |
| 5 | 8 | 50.0% | 81.2% | 100.0% |
| 6 | 8 | 90.6% | 90.6% | 100.0% |
| 7 | 8 | 37.5% | 100.0% | 100.0% |
| 8 | 8 | 12.5% | 92.2% | 98.4% |
| 9 | 8 | 23.1% | 84.6% | 100.0% |
| 10 | 8 | 18.8% | 81.2% | 87.5% |

## By country

| value | photos | current exact | learned exact |
|---|---|---|---|
| Brazil | 140 | 46.4% | 77.9% |
| India | 424 | 50.5% | 79.2% |

## By lighting

| value | photos | current exact | learned exact |
|---|---|---|---|
| warm indoor | 164 | 43.9% | 80.5% |
| side lamp | 120 | 55.8% | 74.2% |
| daylight window | 124 | 54.8% | 77.4% |
| dim room | 156 | 46.2% | 82.1% |

Wrote `qa/ccv2_dryrun/work/calibration.json`. Rebuild the page (python3 build.py) to use it. Tones with few participants stay near the library swatch (k=3).