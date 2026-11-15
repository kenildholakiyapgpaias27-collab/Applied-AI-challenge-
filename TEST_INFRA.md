# AAINA AI Skin Tone & Shade Detection: Test Infrastructure & Philosophy

## 1. Executive Summary & Mission

The AAINA AI Skin Tone & Shade Detection engine provides continuous, scientifically objective skin shade, undertone, and phototype classification for clinical skincare personalization and complexion makeup matching. Because classification results directly drive dermatological safety guardrails—such as blocking high-strength chemical exfoliants for phototypes prone to Post-Inflammatory Hyperpigmentation (PIH) or penalizing mineral sunscreens for deep skin to avoid unsightly white-casts—the underlying computer vision, colorimetry, and data integration must adhere to the highest standard of mathematical and architectural verification.

This document establishes the project-wide **4-Tier Testing Philosophy** and architectural test infrastructure for AAINA. It defines the formal verification principles, mathematical oracles, piecewise continuity proofs, boundary inequality guarantees, cross-module contracts, and real-world environmental stress scenarios that govern our test suites.

---

## 2. The 4-Tier Testing Philosophy

The AAINA testing architecture is structured into four distinct, progressive tiers. Each tier targets a specific layer of system integrity, starting from atomic mathematical invariants up to complex, end-to-end multi-environmental stress conditions.

```
┌─────────────────────────────────────────────────────────────────────────┐
│                     THE 4-TIER TESTING ARCHITECTURE                     │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │ TIER 4: REAL-WORLD SCENARIOS                                      │  │
│  │ • Unilateral side-shadow drop (|ΔL*| > 8.0)                        │  │
│  │ • Red-channel sensor saturation & empirical repair (skinRG)       │  │
│  │ • Deep-skin chroma compression & low-light sensor noise           │  │
│  │ • Non-standard illuminants (Tungsten 2700K, Fluorescent F11, Sun) │  │
│  │ • Sclera corruption & automatic fallback to background Shades-4   │  │
│  └─────────────────────────────────┬─────────────────────────────────┘  │
│                                    │                                    │
│  ┌─────────────────────────────────┴─────────────────────────────────┐  │
│  │ TIER 3: CROSS-FEATURE COMBINATIONS                                │  │
│  │ • End-to-end pipeline: Raw sRGB → Sclera WB → Lab → ITA → FST     │  │
│  │ • Vision Engine ↔ Recommendation Engine contract triggers         │  │
│  │   - P.tone >= 7: Sunscreen white-cast penalty (-2.5)              │  │
│  │   - P.tone >= 4: PIH protection (glycolic >= 10%, sal >= 2%)      │  │
│  │ • Complexion makeup shade matching (depth ± 1, ΔE <= 12)          │  │
│  │ • Complete JSON diagnostic payload schema validation              │  │
│  └─────────────────────────────────┬─────────────────────────────────┘  │
│                                    │                                    │
│  ┌─────────────────────────────────┴─────────────────────────────────┐  │
│  │ TIER 2: BOUNDARY & CORNER CASES                                   │  │
│  │ • Companding inflection knot (Csrgb = 0.04045, Clin = 0.0031308)  │  │
│  │ • Piecewise CIELAB rational knot (δ = 6/29, δ³ = 216/24389)       │  │
│  │ • C¹ smoothness proof (1st derivative match: 841/108 ≈ 7.787037)  │  │
│  │ • Atan2 singularity protection against b* → 0 (pure grayscale)    │  │
│  │ • Exact Fitzpatrick boundary inequalities (55°, 41°, 28°, 10°, -30°)│
│  │ • Undertone boundary transitions (50°, 60°, 72°) & Olive chroma   │  │
│  │ • Sclera gain clamp enforcement [0.3, 4.5] & [0.72, 1.45]         │  │
│  │ • Pure black (0,0,0) and pure white (255,255,255) boundary points │  │
│  └─────────────────────────────────┬─────────────────────────────────┘  │
│                                    │                                    │
│  ┌─────────────────────────────────┴─────────────────────────────────┐  │
│  │ TIER 1: FEATURE COVERAGE                                          │  │
│  │ • IEC 61966-2-1 sRGB gamma linearization & companding roundtrip   │  │
│  │ • CIE 1931 D65 chromaticity matrix multiplication & row-sum proofs │  │
│  │ • Normalized XYZ to CIE 1976 L*a*b* forward & inverse mapping     │  │
│  │ • Continuous Individual Typology Angle (ITA°) derivation          │  │
│  │ • Clinical Fitzpatrick phototype (FST I–VI) centroids             │  │
│  │ • Polar (C*, h°) undertone categorization                         │  │
│  │ • Organic physiological sclera white-balance gain derivation      │  │
│  │ • Baseline schema conformance for all required payload keys       │  │
│  └───────────────────────────────────────────────────────────────────┘  │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

### Tier 1: Feature Coverage (Unit Invariants & Core Algorithms)

**Objective**: Verify the fundamental mathematical transformations and classification primitives in isolation against authoritative international standards.

- **Scope**:
  1. *sRGB Linearization & Companding*: Verification of the piecewise inverse companding equations mapping non-linear 8-bit digital signals to physical photon intensity per IEC 61966-2-1.
  2. *CIE 1931 XYZ Conversion*: Verification of the linear $3 \times 3$ transformation under standard illuminant D65 ($[X_n, Y_n, Z_n] = [0.95047, 1.00000, 1.08883]$), verifying row sums equal white-point coordinates.
  3. *CIE 1976 $L^*a^*b^*$ Mapping*: Verification of the forward and inverse cube-root color space transformations per ISO/CIE 11664-4:2019.
  4. *Individual Typology Angle ($\text{ITA}^\circ$)*: Verification of the continuous pigmentation angle equation $\text{ITA}^\circ = \arctan((L^* - 50)/b^*) \times 180/\pi$.
  5. *Fitzpatrick Phototype Mapping*: Verification of the six dermatological bins (FST I through VI) using authoritative clinical centroids from Chardon et al. (1991) and Del Bino et al. (2013, 2018).
  6. *Polar Undertone Classification*: Verification of chroma $C^* = \sqrt{a^{*2} + b^{*2}}$ and hue angle $h^\circ = \operatorname{atan2}(b^*, a^*) \times 180/\pi$ across Cool, Neutral, Warm, and Olive categories.
  7. *Organic Sclera White-Balance Gain Derivation*: Verification of channel gain calculation against the physiological reference $\mathbf{r}_{sclera} = [0.86, 0.84, 0.79]$.
  8. *Data Contract Schema Baseline*: Structural verification ensuring that output payloads contain all required keys with valid types.

---

### Tier 2: Boundary & Corner Cases (Knots, Singularities & Limits)

**Objective**: Guarantee numerical stability, zero-division immunity, and flawless boundary transition behavior across mathematical inflection points and piecewise knots.

- **Scope**:
  1. *sRGB Transition Knot Continuity*:
     - Verify continuity of value ($C^0$) across $C_{srgb} = 0.04045$ ($C_{linear} \approx 0.0031308$).
     - Verify derivative matching ($C^1$) across the linear and exponential branches ($|S_{lin} - S_{exp}| < 10^{-4}$).
  2. *CIE $L^*a^*b^*$ Rational Knot $\delta = 6/29$*:
     - Verify exact value matching at the rational threshold $t_0 = \delta^3 = 216/24389 \approx 0.008856451679$:
       $$\lim_{t \to (\delta^3)^+} t^{1/3} = \frac{6}{29} = \lim_{t \to (\delta^3)^-} \left(\frac{841}{108} t + \frac{4}{29}\right)$$
     - Verify exact first-derivative matching ($C^1$ smoothness):
       $$\left.\frac{d}{dt} t^{1/3}\right|_{t=\delta^3} = \frac{1}{3\delta^2} = \frac{841}{108} \approx 7.787037037...$$
       ensuring zero gradient discontinuity or numerical instability during optimization.
     - Verify deep shadow linear asymptote coefficient $\kappa = 24389/27 \approx 903.2963$ when $y_r \le \delta^3$.
  3. *$\text{ITA}^\circ$ Singularity & Zero-Division Immunity*:
     - Verify behavior as $b^* \to 0$ (achromatic grayscale). Test $b^* \in \{0.0, 10^{-6}, -10^{-6}\}$.
     - Confirm that $\operatorname{atan2}(L^* - 50, \max(b^*, 10^{-5}))$ safely returns $+90.0^\circ$ for $L^* > 50$, $-90.0^\circ$ for $L^* < 50$, and $0.0^\circ$ for $L^* = 50$, avoiding `ZeroDivisionError` or `NaN`.
  4. *Exact Fitzpatrick Boundary Inequalities*:
     - Test adjacent boundary coordinates across exact thresholds:
       * $55.0001^\circ$ (FST I) vs $55.0000^\circ$ (FST II)
       * $41.0001^\circ$ (FST II) vs $41.0000^\circ$ (FST III)
       * $28.0001^\circ$ (FST III) vs $28.0000^\circ$ (FST IV)
       * $10.0001^\circ$ (FST IV) vs $10.0000^\circ$ (FST V)
       * $-29.9999^\circ$ (FST V) vs $-30.0000^\circ$ (FST VI)
       * $-30.0001^\circ$ (FST VI)
  5. *Polar Undertone Transition Boundaries*:
     - Test exact angular thresholds at $49.99^\circ$ (Cool) vs $50.00^\circ$ (Neutral), $59.99^\circ$ (Neutral) vs $60.00^\circ$ (Warm), and $71.99^\circ$ (Warm) vs $72.00^\circ$ (Olive).
     - Test chroma constraint gating for Olive: $h^\circ \ge 72^\circ$ with $C^* \le 16.5$ (Olive) vs $C^* > 16.5$.
  6. *Illumination Gain Clamping Boundaries*:
     - Enforce sclera gain boundaries: $g_c \in [0.3, 4.5]$.
     - Enforce background Shades-of-Grey gain boundaries: $g_{bg} \in [0.72, 1.45]$.
  7. *Extreme Gamut Limits*:
     - Pure White $(255, 255, 255) \implies L^*=100.0, a^*=0.0, b^*=0.0, \text{ITA} = 90.0^\circ$.
     - Pure Black $(0, 0, 0) \implies L^*=0.0, a^*=0.0, b^*=0.0, \text{ITA} = -90.0^\circ$.

---

### Tier 3: Cross-Feature Combinations (Integration & Contract Handshakes)

**Objective**: Verify the multi-stage integration of vision extraction, colorimetric computation, schema serialization, and downstream clinical recommendation rules.

- **Scope**:
  1. *End-to-End Image Processing Pipeline*:
     - Raw sRGB $\to$ Sclera WB Gain Scaling $\to$ Red Highlight Repair $\to$ CIE XYZ D65 $\to$ CIE Lab $\to$ $\text{ITA}^\circ$ $\to$ Fitzpatrick $\to$ Polar Undertone $\to$ Payload Generation.
     - Verification across the 10-level Monk skin tone scale swatches.
  2. *Vision Engine ↔ Recommendation Engine Contract Triggers*:
     - In `src/app.js:746-750`, recommendation rules inspect `P.tone` and `P.undertone`:
       * **Deep Tone Trigger (`P.tone >= 7`)**: Mineral sunscreens receive severe score penalty ($-2.5$), while invisible/hybrid formulations receive a bonus ($+2.5$) to prevent white-cast on melanin-rich skin.
       * **Medium/Deep Tone PIH Guardrail (`P.tone >= 4`)**: High-strength chemical exfoliants (glycolic acid $\ge 10\%$, leave-on salicylic acid $\ge 2\%$) receive safety penalties ($-1.0$ for medium, $-2.5$ for deep) to prevent Post-Inflammatory Hyperpigmentation.
  3. *Complexion Shade Matching Contract*:
     - In `src/engine.js:302-308`, foundation candidate shades must satisfy $|depth - P.tone| \le 1$ and achieve colorimetric $\Delta E \le 12.0$, modulated by undertone mismatch penalties ($+0.0$ exact match, $+0.5$ neutral bridge, $+1.0$ warm/olive, $+1.5$ warm/cool clash).
  4. *Schema Validation Engine*:
     - Rigorous schema validation rejecting malformed payloads: missing keys, invalid data types, out-of-range ITA values, or inconsistent FST phototypes.

---

### Tier 4: Real-World Scenarios (Hardware, Lighting & Physical Stressors)

**Objective**: Test system resilience against non-ideal, noisy, and hostile real-world capture conditions encountered by consumer smartphone cameras.

- **Scope**:
  1. *Unilateral Facial Side-Lighting & Shadow Drop*:
     - When directional light creates an asymmetric shadow drop $|\Delta L^*| = |L^*_{left} - L^*_{right}| > 8.0$ (or $> 9.0$ per engine threshold), verify that the shadowed hemisphere is automatically discarded, and skin tone is sampled exclusively from the lit facial zones.
  2. *Red-Channel Highlight Saturation Repair*:
     - On sun-lit skin highlights where the red channel saturates ($R = 255$) while green and blue remain linear ($G < 254, B < 254$), verify that empirical skin reconstruction $R_{lin} = G_{lin} \times \operatorname{skinRG}(G_{lin})$ recovers the true reflectance ratio, preventing false greenish-yellow color shift.
  3. *Deep Skin Low-Chroma Ambiguity*:
     - In deep skin (FST VI, $L^* < 32$), high broadband melanin absorption compresses chroma to $C^* < 8.0$. Verify that undertone confidence weighting dampens angular noise and flags ambiguous readings (`conf < 0.60`) when $C^* < 6.0$.
  4. *Pathological Sclera Detection & Automatic Fallback*:
     - In the presence of conjunctivitis, eye fatigue, or bloodshot sclera (where measured $s_R$ abnormally exceeds baseline $0.86$), verify that chromaticity validation rejects the candidate eye white ($C^*_{sclera} > 12.0$) and gracefully triggers fallback to peripheral background Shades-of-Grey ($p=4$) normalization.
  5. *Non-Standard Illuminant Compensation*:
     - Evaluate calibration stability under extreme illuminant color temperatures:
       * Warm Tungsten ($2700\text{K}$, $s_R \gg s_B$)
       * Cool Shade / Daylight ($6500\text{K} - 7500\text{K}$)
       * Fluorescent ($546\text{nm}$ mercury spike)

---

## 3. Test Suite Architecture & Directory Layout

The executable test infrastructure is hosted under `tests/` and integrated into the project's verification suite.

```
Applied-AI-challenge--main/
├── TEST_INFRA.md                   # 4-Tier Testing Philosophy & Architecture Specification
├── tests/
│   ├── verify_colorimetry_spec.py  # Executable 4-Tier Python Verification Suite (Self-Contained)
│   └── quiz_flow_test.py           # End-to-End Playwright UI Flow Test
├── tools/
│   ├── catalogue_check.py          # INCI & Product Flag Integrity Linter
│   ├── tone_eval.py                # Synthetic Lighting Evaluator
│   └── tone_eval_occlusions.py     # Occlusion & Glare Evaluator
└── src/
    ├── app.js                      # UI Controller & Recommendation Logic
    └── engine.js                   # Colorimetry, Face Reader & Shade Matching Engine
```

### Test Suite Execution Command
To execute the comprehensive test suite with 100% standard library compliance:
```bash
python3 tests/verify_colorimetry_spec.py
```

Expected Output:
```
======================================================================
AAINA COLORIMETRY & SPECIFICATION VERIFICATION SUITE
Executing 4-Tier Test Matrix...
----------------------------------------------------------------------
Tier 1: Feature Coverage ......................... [PASS]
Tier 2: Boundary & Corner Cases .................. [PASS]
Tier 3: Cross-Feature Combinations ............... [PASS]
Tier 4: Real-World Scenarios ..................... [PASS]
----------------------------------------------------------------------
Ran 30+ tests in 0.045s

OK (100% Pass Rate - Exit Code 0)
```

---

## 4. Authoritative Mathematical Oracles & Equations

For every test case implemented in `tests/verify_colorimetry_spec.py`, expected values and behaviors are derived from documented international standards and peer-reviewed dermatological literature.

### 4.1 IEC 61966-2-1 sRGB Companding

Piecewise inverse companding (decoding 8-bit non-linear sRGB into linear intensity):
$$C_{linear} = \begin{cases} \frac{C_{srgb}}{12.92}, & C_{srgb} \le 0.04045 \\ \left(\frac{C_{srgb} + 0.055}{1.055}\right)^{2.4}, & C_{srgb} > 0.04045 \end{cases}$$

Piecewise forward companding (encoding linear intensity into sRGB):
$$C_{srgb} = \begin{cases} 12.92 \cdot C_{linear}, & C_{linear} \le 0.0031308 \\ 1.055 \cdot C_{linear}^{1/2.4} - 0.055, & C_{linear} > 0.0031308 \end{cases}$$

---

### 4.2 Linear RGB to CIE 1931 XYZ Matrix (Illuminant D65)

Transformation matrix $\mathbf{M}_{sRGB \to XYZ}$:
$$\begin{bmatrix} X \\ Y \\ Z \end{bmatrix} = \begin{bmatrix}
0.4124564 & 0.3575761 & 0.1804375 \\
0.2126729 & 0.7151522 & 0.0721750 \\
0.0193339 & 0.1191920 & 0.9503041
\end{bmatrix} \begin{bmatrix} R_{lin} \\ G_{lin} \\ B_{lin} \end{bmatrix}$$

Reference White Point ($Y_n = 1.0$):
$$\mathbf{W}_{D65} = \begin{bmatrix} X_n \\ Y_n \\ Z_n \end{bmatrix} = \begin{bmatrix} 0.95047 \\ 1.00000 \\ 1.08883 \end{bmatrix}$$

Inverse transformation matrix $\mathbf{M}_{XYZ \to sRGB}$:
$$\begin{bmatrix} R_{lin} \\ G_{lin} \\ B_{lin} \end{bmatrix} = \begin{bmatrix}
3.2404542 & -1.5371385 & -0.4985314 \\
-0.9692660 & 1.8760108 & 0.0415560 \\
0.0556434 & -0.2040259 & 1.0572252
\end{bmatrix} \begin{bmatrix} X \\ Y \\ Z \end{bmatrix}$$

---

### 4.3 CIE 1976 $L^*a^*b^*$ Non-Linear Transformation

Normalized stimuli:
$$x_r = \frac{X}{X_n}, \quad y_r = \frac{Y}{Y_n}, \quad z_r = \frac{Z}{Z_n}$$

Rational knot and piecewise function:
$$\delta = \frac{6}{29}, \quad \delta^3 = \frac{216}{24389} \approx 0.008856451679$$
$$f(t) = \begin{cases} t^{1/3}, & t > \delta^3 \\ \frac{841}{108} t + \frac{4}{29}, & t \le \delta^3 \end{cases}$$

Coordinates:
$$L^* = 116 \cdot f(y_r) - 16$$
$$a^* = 500 \cdot [f(x_r) - f(y_r)]$$
$$b^* = 200 \cdot [f(y_r) - f(z_r)]$$

---

### 4.4 Individual Typology Angle ($\text{ITA}^\circ$) & Fitzpatrick Thresholds

Mathematical formulation:
$$\text{ITA}^\circ = \left[ \arctan\left(\frac{L^* - 50}{b^*}\right) \right] \times \frac{180}{\pi} = \operatorname{atan2}(L^* - 50, \max(b^*, 10^{-5})) \times \frac{180}{\pi}$$

Fitzpatrick mapping per Chardon et al. (1991) and Del Bino et al. (2013, 2018):
- **FST I (Very Light)**: $\text{ITA}^\circ > 55^\circ$ (Centroid $[75.2, 8.4, 13.8] \implies \text{ITA} = 61.3^\circ$)
- **FST II (Light)**: $41^\circ < \text{ITA}^\circ \le 55^\circ$ (Centroid $[68.5, 10.2, 16.1] \implies \text{ITA} = 49.0^\circ$)
- **FST III (Intermediate)**: $28^\circ < \text{ITA}^\circ \le 41^\circ$ (Centroid $[62.1, 11.8, 18.5] \implies \text{ITA} = 33.2^\circ$)
- **FST IV (Tan / Matt)**: $10^\circ < \text{ITA}^\circ \le 28^\circ$ (Centroid $[55.4, 12.9, 19.8] \implies \text{ITA} = 15.3^\circ$)
- **FST V (Brown)**: $-30^\circ < \text{ITA}^\circ \le 10^\circ$ (Centroid $[44.6, 12.1, 17.2] \implies \text{ITA} = -17.4^\circ$)
- **FST VI (Dark)**: $\text{ITA}^\circ \le -30^\circ$ (Centroid $[31.2, 9.5, 12.4] \implies \text{ITA} = -56.6^\circ$)

---

### 4.5 Polar Undertone Categorization Schema

Polar coordinates:
$$\text{Chroma } C^* = \sqrt{a^{*2} + b^{*2}}, \quad \text{Hue Angle } h^\circ = \operatorname{atan2}(b^*, a^*) \times \frac{180}{\pi} \pmod{360}$$

Classification schema:
- **Cool (Pink / Rosy)**: $h^\circ < 50^\circ$
- **Neutral (Balanced)**: $50^\circ \le h^\circ < 60^\circ$
- **Warm (Golden / Yellow)**: $60^\circ \le h^\circ < 72^\circ$
- **Olive (Muted Green-Golden)**: $h^\circ \ge 72^\circ$ with $C^* \le 16.5$

---

### 4.6 Organic Sclera Illumination Gains

Ground-truth sclera reference: $\mathbf{r}_{sclera} = [0.86, 0.84, 0.79]$ in linear sRGB.
For detected unclipped sclera $\mathbf{s} = [s_R, s_G, s_B]$:
$$g_c = \operatorname{clamp}\left(\frac{r_{sclera, c}}{\max(s_c, 10^{-4})}, 0.3, 4.5\right)$$

---

## 5. Traceability Matrix

| Requirement / Milestone Feature | Tier 1 (Coverage) | Tier 2 (Boundary) | Tier 3 (Combination) | Tier 4 (Real-World) |
|---|:---:|:---:|:---:|:---:|
| **Feature 5**: sRGB to CIE $L^*a^*b^*$ Derivations | `test_srgb_gamma_linearization_and_companding`, `test_linear_rgb_to_cie_xyz_d65_transformation`, `test_xyz_to_cielab_piecewise_transformation` | `test_companding_knot_continuity`, `test_cielab_rational_knot_delta_c1_continuity`, `test_cielab_deep_shadow_slope_kappa` | `test_end_to_end_srgb_to_fitzpatrick_pipeline` | `test_pure_white_and_pure_black_extremes`, `test_pure_grayscale_b_zero_robustness` |
| **Feature 6**: ITA° Formulation | `test_ita_formula_and_dermatological_properties` | `test_ita_atan2_b_zero_protection` | `test_end_to_end_srgb_to_fitzpatrick_pipeline` | `test_deep_skin_chroma_compression_handling` |
| **Feature 7**: Fitzpatrick Phototype Mapping | `test_fitzpatrick_mapping_literature_centroids` | `test_fitzpatrick_exact_boundary_inequalities` | `test_end_to_end_srgb_to_fitzpatrick_pipeline` | `test_deep_skin_chroma_compression_handling` |
| **Feature 8**: Polar Undertone Schema | `test_polar_undertone_classification_schema` | `test_undertone_boundary_transitions`, `test_undertone_olive_chroma_constraint` | `test_complexion_shade_matching_depth_filtering` | `test_deep_skin_chroma_compression_handling` |
| **Feature 9**: Illumination Calibration & Sclera WB | `test_organic_sclera_white_balance_gain_derivation` | `test_sclera_gain_clamping_extremes` | `test_white_balance_interaction_with_skin_tone` | `test_bloodshot_sclera_and_fallback_to_background`, `test_non_standard_illuminant_compensation` |
| **Feature 4 / 12**: Artifact Filtering & Edge Cases | `test_data_contract_schema_validation` | `test_pure_grayscale_b_zero_robustness` | `test_downstream_recommendation_guardrail_triggers` | `test_unilateral_side_lighting_shadow_drop`, `test_red_channel_sensor_highlight_recovery` |
| **Feature 13**: Integration Blueprint & Data Contracts | `test_data_contract_schema_validation` | `test_payload_validation_extremes` | `test_data_contract_cross_validation`, `test_downstream_recommendation_guardrail_triggers` | `test_complexion_shade_matching_depth_filtering` |

---

## 6. Verification & Forensic Audit Instructions

An independent auditor or reviewer can verify the test suite and all mathematical claims using the following terminal procedure:

```bash
# 1. Verify that TEST_INFRA.md exists at project root
test -f TEST_INFRA.md && echo "TEST_INFRA.md verified"

# 2. Execute the verification suite
python3 tests/verify_colorimetry_spec.py -v

# 3. Verify exit code equals 0
echo "Exit code: $?"
```

Any assertion error, floating-point divergence ($\Delta E > 0.05$), knot discontinuity, or contract schema violation indicates a failure of mathematical or architectural compliance.
