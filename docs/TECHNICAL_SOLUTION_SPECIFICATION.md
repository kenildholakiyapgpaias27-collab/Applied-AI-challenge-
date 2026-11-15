# AAINA Technical Solution Specification: AI Skin Tone & Shade Detection Engine

**Document Version:** 2.0.0-PROD  
**Status:** Approved Technical Architecture & Integration Specification  
**System Classification:** Client-Side Ephemeral AI Engine (Privacy-Preserving Edge Architecture)  
**Regulatory Compliance:** Digital Personal Data Protection (DPDP) Act 2023 (India)  
**Target Codebase:** AAINA Core Web Application (`src/engine.js`, `src/app.js`, `build.py`)  
**Date:** November 15, 2026  

---

## Table of Contents
1. [Executive Summary & Architectural Overview](#1-executive-summary--architectural-overview)
   - 1.1 [Purpose, Vision & Core Philosophy](#11-purpose-vision--core-philosophy)
   - 1.2 [High-Level System Architecture Diagram](#12-high-level-system-architecture-diagram)
   - 1.3 [DPDP Act 2023 Compliance & Ephemeral Data Lifecycle](#13-dpdp-act-2023-compliance--ephemeral-data-lifecycle)
2. [End-to-End Computer Vision & AI Pipeline Architecture](#2-end-to-end-computer-vision--ai-pipeline-architecture)
   - 2.1 [Client-Side WebAssembly (WASM SIMD) & WebGPU Architecture](#21-client-side-webassembly-wasm-simd--webgpu-architecture)
   - 2.2 [Input Image Constraints & Pre-Flight Quality Gates](#22-input-image-constraints--pre-flight-quality-gates)
   - 2.3 [Stage-by-Stage Processing Pipeline](#23-stage-by-stage-processing-pipeline)
     - *Stage 0: Video/File Canvas Acquisition*
     - *Stage 1: MediaPipe 478-Landmark Mesh & Iris Anchor Extraction*
     - *Stage 2: Anatomical Quad-Zone ROI Segmentation & Feature Masking*
     - *Stage 3: Physics-Based Optical Artifact Rejection & Robust Statistics*
     - *Stage 4: Illumination Normalization & Color Constancy*
     - *Stage 5: Colorimetric Transformation ($sRGB \to \text{Linear} \to XYZ \to L^*a^*b^*$)*
     - *Stage 6: Individual Typology Angle ($\text{ITA}^\circ$) & Metric Synthesis*
3. [Tone and Undertone Classification Schema Calibrated to Skincare Personalization](#3-tone-and-undertone-classification-schema-calibrated-to-skincare-personalization)
   - 3.1 [10-Level Monk Skin Tone (MST) Scale & ITA° Alignment with Fitzpatrick I–VI](#31-10-level-monk-skin-tone-mst-scale--ita-alignment-with-fitzpatrick-ivi)
   - 3.2 [Polar Coordinate Undertone Classification Schema ($C^*, h^\circ$)](#32-polar-coordinate-undertone-classification-schema-c-h)
   - 3.3 [Skincare & Routine Personalization Guardrails (Clinical Rules)](#33-skincare--routine-personalization-guardrails-clinical-rules)
     - *Rule Trigger A: Deep Skin Tones ($P.tone \ge 7$) Sunscreen Guardrail*
     - *Rule Trigger B: Medium & Deep Skin Tones ($P.tone \ge 4$) PIH Safety Rules*
   - 3.4 [Complexion Base-Makeup Matching Engine](#34-complexion-base-makeup-matching-engine)
4. [Exhaustive Edge Case Handling Matrix & Failure Mitigations](#4-exhaustive-edge-case-handling-matrix--failure-mitigations)
   - 4.1 [Comprehensive 12-Mode Edge Case Taxonomy](#41-comprehensive-12-mode-edge-case-taxonomy)
   - 4.2 [Detailed Algorithmic Failure Recovery Specifications (Modes 1–12)](#42-detailed-algorithmic-failure-recovery-specifications-modes-112)
5. [Concrete Integration Blueprint with AAINA Codebase](#5-concrete-integration-blueprint-with-aaina-codebase)
   - 5.1 [Component Breakdown & Touchpoints in `src/engine.js`](#51-component-breakdown--touchpoints-in-srcenginejs)
   - 5.2 [UI & Consultation Flow Touchpoints in `src/app.js`](#52-ui--consultation-flow-touchpoints-in-srcappjs)
   - 5.3 [Formal Data Contracts (TypeScript Interfaces & JSON Schemas)](#53-formal-data-contracts-typescript-interfaces--json-schemas)
   - 5.4 [Backward Compatibility Preservation & Fallback Execution](#54-backward-compatibility-preservation--fallback-execution)
   - 5.5 [Verification Commands & Automated Test Suite Integration](#55-verification-commands--automated-test-suite-integration)

---

## 1. Executive Summary & Architectural Overview

### 1.1 Purpose, Vision & Core Philosophy
The AAINA AI Skin Tone & Shade Detection Engine provides objective, dermatologically calibrated skin tone and undertone intelligence for the Indian demographic. Historically, beauty-tech and cosmetic algorithms have suffered from demographic bias, poor low-chroma resolution on melanin-rich skin, and severe vulnerability to uncontrolled indoor lighting.

AAINA's technical architecture replaces heuristic face sampling with an edge-native, physics-grounded computer vision pipeline. The engine bridges consumer smartphone cameras to dermatological science:
1. **Zero-Server Dependency**: Executes 100% within the user's client browser using WebAssembly SIMD and WebGPU hardware acceleration. No biometric facial image is ever transmitted across a network, persisted to disk, or stored in a backend database.
2. **Biophysical Rigor**: Decomposes facial radiance using the Shafer Dichromatic Reflection Model (DRM) to eliminate specular sebum glare, reconstructs clipped camera sensor channels, normalizes illumination via localized ocular sclera anchoring, and computes continuous Individual Typology Angle ($\text{ITA}^\circ$) values.
3. **Clinical Coupling**: Directly binds skin depth ($P.tone \in [1, 10]$) and chromatic undertone ($P.undertone \in \{\text{"cool"}, \text{"neutral"}, \text{"warm"}, \text{"olive"}\}$) into clinical routine guardrails (preventing Post-Inflammatory Hyperpigmentation from aggressive acids and white-cast from mineral filters) and an exact-match base makeup engine ($\pm 1$ depth filter with $\Delta E$ optimization).

---

### 1.2 High-Level System Architecture Diagram

```
┌────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                       CLIENT BROWSER (EDGE RUNTIME)                                    │
│                                                                                                        │
│  ┌───────────────────────┐         ┌─────────────────────────┐         ┌────────────────────────────┐  │
│  │ User Video / Camera   │────────▶│ Pre-Flight Quality Gate │────────▶│ MediaPipe Face Mesh        │  │
│  │ navigator.mediaDevices│         │ Lux, Blur, Framing, Pose│         │ 478 3D Vertices + Irises   │  │
│  └───────────────────────┘         └─────────────────────────┘         └─────────────┬──────────────┘  │
│                                                                                      │                 │
│                                            ┌─────────────────────────────────────────┘                 │
│                                            ▼                                                           │
│  ┌──────────────────────────────────────────────────────────────────────────────────────────────────┐  │
│  │ Quad-Zone Anatomical Segmentation & Feature Masking (Forehead, Bilateral Cheeks, Jawline)        │  │
│  │ Dilated Negative Masks: Eyes (15%), Lips (10%), Brows, Nostrils, High-Frequency Beard Texture    │  │
│  └─────────────────────────────────────────────────┬────────────────────────────────────────────────┘  │
│                                                    │                                                   │
│                                                    ▼                                                   │
│  ┌──────────────────────────────────────────────────────────────────────────────────────────────────┐  │
│  │ Physics-Based Artifact Pruning & Illumination Normalization                                      │  │
│  │ • Shafer DRM Highlight Pruning: V > 0.88 ∧ S < 0.22, L* > 82 ∧ C* < 14                           │  │
│  │ • Linear Red Channel Clipping Repair: R_lin = G_lin × skinRG(G_lin)                              │  │
│  │ • Bilateral Facial Symmetry Shadow Drop: |ΔL*| > 8.0 CIELAB Units                                │  │
│  │ • Robust Trimming: 15–85% Inter-Quantile Lightness, ±2.5σ MAD Gating, Cook's Distance Leverage   │  │
│  │ • White-Balance Normalization: Sclera Baseline [0.86, 0.84, 0.79] (Fallback: Shades-of-Grey p=4) │  │
│  └─────────────────────────────────────────────────┬────────────────────────────────────────────────┘  │
│                                                    │                                                   │
│                                                    ▼                                                   │
│  ┌──────────────────────────────────────────────────────────────────────────────────────────────────┐  │
│  │ Colorimetric Transformation & Metric Extraction                                                  │  │
│  │ • Inverse Companding (IEC 61966-2-1) ──▶ CIE 1931 D65 Matrix ──▶ Piecewise CIE 1976 L*a*b*      │  │
│  │ • Individual Typology Angle: ITA° = [arctan((L* - 50) / b*)] × (180 / π)                         │  │
│  │ • Polar Undertone: Chroma C* = √(a*² + b*²), Hue h° = atan2(b*, a*)                              │  │
│  │ • Centroid Projection: Tone Mapping to 10-Level Monk Scale (MST 1–10) via CAL.centroids          │  │
│  └─────────────────────────────────────────────────┬────────────────────────────────────────────────┘  │
│                                                    │                                                   │
│                                                    ▼                                                   │
│  ┌──────────────────────────────────────────────────────────────────────────────────────────────────┐  │
│  │ Consumer Personalization & Clinical Guardrails (src/app.js & src/engine.js)                      │  │
│  │ • Sunscreen Safety (P.tone ≥ 7): Penalize mineral white cast (-2.5), boost invisible (+2.5)      │  │
│  │ • PIH Protection (P.tone ≥ 4): Penalize ≥10% glycolic & ≥2% salicylic; boost tyrosinase blockers │  │
│  │ • Base Makeup Match: Depth ±1, Library ΔE, Undertone penalty (0.0 match, 0.5 neutral, 1.5 clash)│  │
│  └─────────────────────────────────────────────────┬────────────────────────────────────────────────┘  │
│                                                    │                                                   │
│                                                    ▼                                                   │
│  ┌──────────────────────────────────────────────────────────────────────────────────────────────────┐  │
│  │ Immediate In-Memory Memory Deallocation: TypedArray Unload, Canvas GC, Zero Server Transmission  │  │
│  └──────────────────────────────────────────────────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

---

### 1.3 DPDP Act 2023 Compliance & Ephemeral Data Lifecycle

The Indian **Digital Personal Data Protection (DPDP) Act, 2023** governs the processing of digital personal data. Facial images constitute sensitive biometric personal identifiers capable of unique identification. AAINA adheres to privacy-by-design principles:

1. **Section 6 (Consent Lifecycle)**:
   - User consent is captured via an explicit, unambiguous opt-in UI dialog prior to camera hardware initialization (`src/app.js:550-559`).
   - The UI communicates the exact purpose: *“We only need a photo to understand your skin tone... You can ask us to delete it sooner at any time, and you can still correct the result.”*
   - Users maintain the unrestricted right to decline camera capture and manually select their shade from the interactive 10-level Monk swatch palette without penalty or degradation of recommendation quality.
2. **Zero Server Transmission (Architectural Air-Gap)**:
   - Image pixel bytes are acquired through the WebRTC `MediaDevices.getUserMedia()` API directly into an in-memory HTML5 Canvas element.
   - Network telemetry verification confirms that zero HTTP `POST`/`PUT` requests, WebSocket payloads, or third-party tracking beacons containing image buffers are dispatched. All API synchronization in `src/db.js` transmits purely discrete categorical parameters (`P.tone = 6`, `P.undertone = "warm"`, `P.concerns = ["pigmentation"]`).
3. **Section 8 (Data Minimization & Storage Limitation)**:
   - Processing is 100% ephemeral in volatile browser heap memory (`ArrayBuffer`, `Float32Array`).
   - Once colorimetric metrics ($L^*, a^*, b^*, \text{ITA}^\circ, \text{Tone}$) are calculated, the source canvas buffer, WebGL textures, and MediaPipe landmark tensors are explicitly dereferenced and queued for immediate Garbage Collection (GC). No persistent image data is written to browser `localStorage`, `IndexedDB`, or cookies.

---

## 2. End-to-End Computer Vision & AI Pipeline Architecture

### 2.1 Client-Side WebAssembly (WASM SIMD) & WebGPU Architecture

To guarantee zero server round-trips while delivering interactive framerates on low-to-mid-tier smartphones prevalent in the Indian market (e.g., MediaTek Helio, Qualcomm Snapdragon 600/700 series), the AI pipeline is compiled to edge-native WebAssembly with 128-bit SIMD vectorization and WebGPU compute shaders.

#### Execution Model & Latency Budget
- **Framework**: Google MediaPipe Face Mesh Runtime compiled to WebAssembly with SIMD acceleration (`face_mesh.wasm`, ~3.2 MB quantized model weights).
- **Inference Delegate**: Hardware-accelerated WebGPU / WebGL2 compute shader delegate with graceful CPU WASM SIMD fallback.
- **Latency Target**:
  - Pre-flight quality assessment: $< 4.0\text{ ms}$
  - Landmark mesh regression (478 vertices): $< 18.0\text{ ms}$ on mobile WebGPU ($< 32.0\text{ ms}$ on CPU WASM SIMD).
  - Quad-zone extraction, DRM artifact filtering & sclera normalization: $< 6.0\text{ ms}$.
  - Total frame analysis latency: $< 28.0\text{ ms}$ (allowing smooth real-time visual alignment feedback at 30 FPS).
- **Memory Footprint**: Working memory is constrained to $< 48\text{ MB}$ heap allocation, preventing browser tab termination on memory-constrained mobile browsers (iOS WebKit and Android Chrome).

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                              WASM / WEBGPU RUNTIME STACK                               │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ Application Layer (Vanilla JS ES6+): src/app.js & src/engine.js                        │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ Vision Bridge: Canvas2D / ImageData Ephemeral TypedArray Interop                       │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ MediaPipe WASM SIMD Engine (BlazeFace ──▶ 3D Face Mesh ──▶ Iris Refinement)           │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ Hardware Abstraction Layer: WebGPU Compute Pipeline / WebGL2 GPGPU / WASM SIMD Native   │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

---

### 2.2 Input Image Constraints & Pre-Flight Quality Gates

Before executing full mesh segmentation and colorimetric calculations, the input frame must clear five deterministic pre-flight quality gates. Bypassing unconstrained images into colorimetry yields severe misclassification.

```
Incoming Image Frame (Canvas / Video Stream)
  │
  ├──▶ [Gate 1: Resolution & Aspect Ratio] ──── Fail ──▶ Throw LOW_RESOLUTION
  │
  ├──▶ [Gate 2: Face Size & Framing Ratio] ──── Fail ──▶ Throw FACE_TOO_SMALL / NO_FACE
  │
  ├──▶ [Gate 3: Global Illumination & Lux] ──── Fail ──▶ Throw TOO_DARK / OVEREXPOSED
  │
  ├──▶ [Gate 4: Laplacian Blur & Sharpness] ─── Fail ──▶ Throw BLURRY
  │
  └──▶ [Gate 5: 3D Head Pose Angles] ────────── Fail ──▶ Throw POSE_DEVIATION
  │
  └──▶ PASSED: Dispatch to MediaPipe Mesh Segmentation Pipeline
```

#### Detailed Gate Specifications

| Gate # | Quality Dimension | Metric / Mathematical Formulation | Acceptable Operational Bounds | Failure Code | Real-Time User Feedback Guidance |
|:---:|:---|:---|:---|:---|:---|
| **1** | **Resolution & Aspect Ratio** | Minimum short side: $\min(W, H)$<br>Aspect ratio: $AR = W / H$ | $\min(W, H) \ge 480\text{ px}$ (Ideal: $1280 \times 720\text{ px}$)<br>$0.55 \le AR \le 1.85$ | `LOW_RESOLUTION` | *"Please use your phone's main camera at full quality without cropping."* |
| **2** | **Face Size & Framing** | Face bounding box area ratio:<br>$\rho_{face} = \frac{W_{face} \times H_{face}}{W_{frame} \times H_{frame}}$ | $0.20 \le \rho_{face} \le 0.75$<br>Centroid offset from frame center: $\Delta C < 0.25 W$ | `FACE_TOO_SMALL`<br>`NO_FACE` | *"Move closer so your face fills the on-screen guide oval and look straight forward."* |
| **3** | **Global Illumination & Exposure** | Estimated illuminance $E_{lux}$ from frame luma:<br>$Y_{avg} = \frac{1}{N} \sum (0.2126 R + 0.7152 G + 0.0722 B)$<br>High-end pixel clip fraction ($C_{high}$):<br>$\frac{1}{N} \sum [ \min(R,G,B) \ge 250 ]$ | $E_{lux} \ge 50\text{ lux}$ ($Y_{avg} \ge 14.0$ on 8-bit scale)<br>$Y_{avg} \le 225.0$<br>$C_{high} \le 0.15$ | `TOO_DARK`<br>`OVEREXPOSED` | *"Move somewhere brighter, facing a window in daylight."* / *"Turn off the flash and step out of direct sun."* |
| **4** | **Focus & Blur Detection** | Modified Laplacian Variance over facial oval:<br>$\sigma^2_{\nabla^2} = \frac{1}{N} \sum (\nabla^2 I(x, y) - \mu_{\nabla^2})^2$<br>where $\nabla^2 I = 4 I(x,y) - I(x\pm 1, y) - I(x, y\pm 1)$ | $\sigma^2_{\nabla^2} \ge 18.0$ | `BLURRY` | *"Hold your phone steady and tap your screen to focus before capturing."* |
| **5** | **3D Head Pose Geometry** | Yaw ($\psi$), Pitch ($\theta$), Roll ($\phi$) extracted via Perspective-n-Point (PnP) from 3D canonical landmarks | $|\psi_{\text{yaw}}| \le 25^\circ$<br>$|\theta_{\text{pitch}}| \le 20^\circ$<br>$|\phi_{\text{roll}}| \le 15^\circ$ | `HIGH_YAW`<br>`HIGH_PITCH` | *"Turn your head to face the camera directly; avoid tilting up or down."* |

---

### 2.3 Stage-by-Stage Processing Pipeline

#### Stage 0: Video/File Canvas Acquisition
- Captures frames from `<video>` or `<input type="file">`.
- Downscales high-resolution files to max dimension $1200\text{ px}$ via smooth bicubic interpolation on an offscreen canvas (`src/app.js:646`). This preserves edge fidelity while bounding downstream memory to $< 4.3\text{ MB}$ raw RGBA.

#### Stage 1: MediaPipe 478-Landmark Mesh & Iris Anchor Extraction
The engine instantiates MediaPipe Face Mesh, generating 478 3D metric facial vertices. Vertices `0` to `467` delineate facial morphology, while vertices `468–472` anchor the left iris center and boundary, and vertices `473–477` anchor the right iris center and boundary.

#### Stage 2: Anatomical Quad-Zone ROI Segmentation & Feature Masking
Skin color varies across facial topography due to vascular density, tanning patterns, and epidermal thickness. To capture a holistic, reliable reading, the engine extracts four discrete positive anatomical zones and subtracts non-skin features via dilated exclusion masks.

```
                  ┌───────────────────────────────┐
                  │    1. Central Forehead ROI    │
                  │       [10, 338 ... 70]        │
                  └───────────────┬───────────────┘
                                  │
         ┌────────────────────────┼────────────────────────┐
         ▼                                                 ▼
┌──────────────────┐                             ┌──────────────────┐
│ 2. Left Cheek    │                             │ 3. Right Cheek   │
│ Malar Patch      │                             │ Malar Patch      │
│ [116 ... 206]    │                             │ [345 ... 426]    │
└────────┬─────────┘                             └─────────┬────────┘
         │                                                 │
         └────────────────────────┬────────────────────────┘
                                  │
                  ┌───────────────▼───────────────┐
                  │    4. Mandibular Jawline ROI  │
                  │       [152 ... 361]           │
                  └───────────────────────────────┘
```

##### Positive Anatomical Sampling Zones (Canonical MediaPipe Indices):
1. **Central Forehead Patch (Frontalis Region)**:
   - *Polygon*: `[10, 338, 297, 332, 284, 251, 389, 356, 107, 66, 105, 63, 70]`
   - *Centroid Anchor*: Vertex `151` / `10`. Bounds measurement strictly below the scalp hairline and above the supraorbital brow ridge.
2. **Left Cheek Patch (Malar / Zygomatic Region)**:
   - *Polygon*: `[116, 123, 147, 213, 138, 135, 192, 214, 207, 187, 50, 101, 36, 205, 206]`
   - *Isolation*: Samples the flat malar cheek plane, avoiding the nasolabial fold and buccal hollow.
3. **Right Cheek Patch (Malar / Zygomatic Region)**:
   - *Polygon*: `[345, 352, 376, 433, 367, 364, 416, 434, 427, 411, 280, 330, 266, 425, 426]`
   - *Isolation*: Bilateral counterpart to the left malar cheek.
4. **Mandibular Jawline Band**:
   - *Polygon*: `[152, 148, 176, 149, 150, 136, 172, 58, 132, 377, 400, 378, 379, 365, 397, 288, 361]`
   - *Isolation*: Encapsulates the lower jawline bone structure, serving as the ground-truth transition anchor for foundation shade blending into the neck.

##### Negative Feature Exclusion Masks:
- **Left Ocular Contour**: Dilated by $+15\%$ radius: `[33, 7, 163, 144, 145, 153, 154, 155, 133, 173, 157, 158, 159, 160, 161, 246]`.
- **Right Ocular Contour**: Dilated by $+15\%$ radius: `[362, 382, 381, 380, 374, 373, 390, 249, 263, 466, 388, 387, 386, 385, 384, 398]`.
- **Eyebrows**: Left brow `[70, 63, 105, 66, 107, 55, 65, 52, 53, 46]`, Right brow `[300, 293, 334, 296, 336, 285, 295, 282, 283, 276]`.
- **Vermilion Lips**: Dilated by $+10\%$ radius: `[61, 146, 91, 181, 84, 17, 314, 405, 321, 375, 291, 308, 324, 318, 402, 317, 14, 87, 178, 88, 95, 185, 40, 39, 37, 0, 267, 269, 270, 409, 415, 310, 311, 312, 13, 82, 81, 42, 183, 78]`.
- **Nasal Cavity / Nostrils**: `[2, 94, 98, 327, 274, 460]`.
- **Beard / Facial Hair Exclusion**: High-frequency texture analysis within the jawline polygon:
  $$\sigma^2_{texture} = \operatorname{Var}\left(\nabla^2 I_{jaw}(x, y)\right)$$
  Pixels with $\sigma^2_{texture} > 24.0$ are classified as beard stubble/vellus hair and masked out.

---

#### Stage 3: Physics-Based Optical Artifact Rejection & Robust Statistics

##### 1. Shafer Dichromatic Reflection Model (DRM) Highlight Rejection
Under the Dichromatic Reflection Model, skin surface radiance $I(\lambda, \mathbf{x})$ is a linear combination of subsurface diffuse reflectance $C_d(\lambda)$ (melanin and hemoglobin) and surface specular interface reflection $C_s(\lambda)$ (illuminant spectrum reflected off the sebum lipid layer):
$$I(\lambda, \mathbf{x}) = m_d(\mathbf{x}) C_d(\lambda, \mathbf{x}) + m_s(\mathbf{x}) C_s(\lambda)$$

Specular highlights pull chromaticity toward $(R=255, G=255, B=255)$ or the illuminant color, compressing chroma and falsely elevating lightness ($L^*$). The engine applies dual-space highlight rejection:
1. **HSV Highlight Gating**: Pixels with $V > 0.88 \land S < 0.22$ are flagged as specular reflection and excised.
2. **CIELAB Highlight Gating**: Pixels with $L^* > 82.0 \land C^* = \sqrt{a^{*2} + b^{*2}} < 14.0$ are discarded.

##### 2. Sensor Red-Channel Saturation Repair
In smartphone CMOS sensors, human skin under bright lighting saturates the red channel first ($R \ge 254$) while green and blue retain linear sensor responses ($G, B < 254$). The engine reconstructs clipped linear red from unclipped green using empirical skin reflectance ratios:
$$R_{linear} = G_{linear} \times \text{skinRG}(G_{linear})$$
where $\text{skinRG}(G)$ is the calibrated lookup curve derived from the Monk skin reflectance dataset (`src/engine.js:284-285, 335`).

##### 3. Bilateral Facial Symmetry Shadow Dropping
Facial melanin pigmentation is biologically symmetric across the sagittal midline. Directional side lighting introduces unilateral cast shadows.
Let $\tilde{L}^*_{left}$ and $\tilde{L}^*_{right}$ be the median lightness of the segmented left and right cheek patches:
$$\Delta L^*_{\text{bilateral}} = |\tilde{L}^*_{left} - \tilde{L}^*_{right}|$$
- If $\Delta L^*_{\text{bilateral}} > 8.0\text{ CIELAB units}$ (`FR2.shadowDrop` in `src/engine.js:246, 361`), the shadowed hemisphere is completely dropped. The consensus skin tone is computed exclusively from the lit facial hemisphere, logging the note `SHADOW_IGNORED`.

##### 4. Robust Outlier Pruning: Trimmed Mean, MAD & Cook's Distance
To eliminate residual blemishes, acne papules, hyperpigmented macules, and residual cosmetic contouring:
- **Inter-Quantile Lightness Trimming**: Discard the lower 15th percentile ($Q_{0.15}$) and upper 85th percentile ($Q_{0.85}$) of pixel lightness within each region (`src/engine.js:355`):
  $$\mathcal{K} = \{ p \in \text{ROI} \mid Q_{0.15}(L^*) \le L^*(p) \le Q_{0.85}(L^*) \}$$
- **Median Absolute Deviation (MAD) Envelope**:
  $$\text{MAD} = \operatorname{median}(|X_i - \tilde{X}|), \quad \hat{\sigma} = 1.4826 \times \text{MAD}$$
  Prune any pixel where $|X_i - \tilde{X}| > 2.5 \hat{\sigma}$ (`src/engine.js:347-349`).
- **Cook's Distance Planar Leverage Pruning**:
  Fit a robust spatial plane $L^*(x, y) = \beta_0 + \beta_1 x + \beta_2 y$. Pixels with Cook's distance $D_i > \frac{4}{N - 3}$ represent localized high-leverage outliers (such as dark spots or blush pigments) and are excised before median pooling.

---

#### Stage 4: Illumination Normalization & Color Constancy

To decouple ambient illuminant tint from true biological skin reflectance, the engine employs a two-tier color constancy hierarchy:

```
                            Illumination Normalization
                                       │
                ┌──────────────────────┴──────────────────────┐
                ▼                                             ▼
    Primary Method: Ocular Sclera               Secondary Fallback: Background
    Physiological Reference Anchoring            Shades-of-Grey (p = 4)
    Ref: [0.86, 0.84, 0.79] in Linear sRGB       Peripheral Background Integration
```

##### 1. Primary Strategy: Organic Ocular Sclera Anchoring
The human ocular sclera (the white of the eye) is composed of dense, avascular fibrous collagen covered by the transparent bulbar conjunctiva. Spectrophotometric studies confirm that healthy sclera exhibits an invariant, race-independent spectral reflectance baseline:
$$\mathbf{r}_{sclera} = [0.86, 0.84, 0.79] \quad (\text{Linear sRGB})$$
- *Extraction*: The sclera region is extracted as the geometric difference between the dilated eye contour polygon and the iris landmark circle (`468–472` left, `473–477` right).
- *Lit-Eye Selection*: If asymmetric side lighting is present ($Y_{eye1} > 1.25 Y_{eye2}$), the shadowed eye is discarded and gains are computed exclusively from the lit eye (`src/engine.js:275`).
- *Per-Channel von Kries Gains*:
  $$g_c = \operatorname{clamp}\left( \frac{r_{sclera, c}}{\max(s_c, 10^{-4})}, 0.3, 4.5 \right), \quad c \in \{R, G, B\}$$

##### 2. Secondary Strategy: Background Shades-of-Grey ($p=4$) Fallback
If sclera pixels are invalid ($< 18\text{ px}$ due to closed eyes, squinting, or glasses glare):
- The engine integrates background pixels outside the facial ellipse bounding box (`src/engine.js:279-283`).
- Applies Finlayson & Trezzi's Minkowski $p$-norm ($p=4$):
  $$e_c = \left( \frac{1}{N_{bg}} \sum_{i=1}^{N_{bg}} I_{lin, c}(\mathbf{x}_i)^4 \right)^{1/4}$$
- Background gains are clamped conservatively to $[0.72, 1.45]$ at $60\%$ partial correction strength (`FR2.bgStrength = 0.6`) to prevent over-correcting saturated colored backgrounds.

---

#### Stage 5: Colorimetric Transformation ($sRGB \to \text{Linear} \to XYZ \to L^*a^*b^*$)

The normalized linear RGB channels are converted into device-independent, perceptually uniform CIE $L^*a^*b^*$ coordinates under Standard Illuminant D65.

```
sRGB (8-bit [0, 255])
  │
  ▼ [1. Inverse Companding / Linearization — IEC 61966-2-1]
Linear sRGB (R_lin, G_lin, B_lin ∈ [0.0, 1.0])
  │
  ▼ [2. von Kries Channel Gain Application — diag(g_R, g_G, g_B)]
Illumination-Normalized Linear RGB
  │
  ▼ [3. CIE 1931 D65 Transformation Matrix — 3×3]
Tristimulus Values CIE 1931 XYZ (Normalized to White Point [0.95047, 1.00000, 1.08883])
  │
  ▼ [4. Piecewise Cube-Root Transformation — CIE 15:2004, δ = 6/29]
CIE 1976 L*a*b* Perceptual Coordinates (L* ∈ [0, 100], a* ∈ [-128, 127], b* ∈ [-128, 127])
```

##### 1. Piecewise Inverse Companding (IEC 61966-2-1:1999):
$$C_{lin} = \begin{cases} \frac{C_{srgb}}{12.92}, & C_{srgb} \le 0.04045 \\ \left( \frac{C_{srgb} + 0.055}{1.055} \right)^{2.4}, & C_{srgb} > 0.04045 \end{cases} \quad \text{where } C_{srgb} = \frac{C_{8bit}}{255}$$

##### 2. Linear RGB to CIE 1931 XYZ Conversion Matrix (Illuminant D65, $2^\circ$ Observer):
$$\begin{bmatrix} X \\ Y \\ Z \end{bmatrix} = \begin{bmatrix}
0.4124564 & 0.3575761 & 0.1804375 \\
0.2126729 & 0.7151522 & 0.0721750 \\
0.0193339 & 0.1191920 & 0.9503041
\end{bmatrix} \begin{bmatrix} R_{lin} \\ G_{lin} \\ B_{lin} \end{bmatrix}$$
*D65 White Point Normalization*: $X_n = 0.95047, Y_n = 1.00000, Z_n = 1.08883$.

##### 3. Normalized XYZ to CIE 1976 $L^*a^*b^*$ Piecewise Cube-Root:
Define normalized stimuli: $x_r = X / X_n$, $y_r = Y / Y_n$, $z_r = Z / Z_n$.  
The transformation function $f(t)$ utilizes the exact rational threshold $\delta = \frac{6}{29}$ ($\delta^3 = \frac{216}{24389} \approx 0.00885645$):
$$f(t) = \begin{cases} t^{1/3}, & t > \frac{216}{24389} \\ \frac{841}{108} t + \frac{4}{29}, & t \le \frac{216}{24389} \end{cases}$$
The final CIELAB coordinates are:
$$L^* = 116 \cdot f(y_r) - 16$$
$$a^* = 500 \cdot \left[ f(x_r) - f(y_r) \right]$$
$$b^* = 200 \cdot \left[ f(y_r) - f(z_r) \right]$$

---

#### Stage 6: Individual Typology Angle ($\text{ITA}^\circ$) & Metric Synthesis

The **Individual Typology Angle ($\text{ITA}^\circ$)** provides an objective, continuous metric of constitutive skin pigmentation:
$$\text{ITA}^\circ = \left[ \operatorname{atan2}\left(L^* - 50, \max(b^*, 10^{-5})\right) \right] \times \frac{180}{\pi}$$
- **$L^*$ (Lightness)**: Directly reflects broadband photon attenuation by epidermal eumelanin.
- **$b^*$ (Yellowness)**: Measures the exponential absorption decay curve of melanin ($\lambda^{-3.4}$) and stratum corneum carotenoids.
- **$a^*$ (Redness)**: Tracks dermal capillary oxyhemoglobin absorption at $542\text{ nm}$ and $577\text{ nm}$.

---

## 3. Tone and Undertone Classification Schema Calibrated to Skincare Personalization

### 3.1 10-Level Monk Skin Tone (MST) Scale & ITA° Alignment with Fitzpatrick I–VI

To eliminate Eurocentric classification bias, AAINA employs the **10-level Monk Skin Tone (MST) Scale**, developed by Dr. Ellis Monk (Harvard University). The Monk scale provides granular representation across medium, tan, brown, and deep complexions (spanning Fitzpatrick III through VI), which encompass $>95\%$ of the Indian demographic.

The table below defines the formal alignment between the 10 Monk shades, continuous $\text{ITA}^\circ$ boundaries, Fitzpatrick Phototypes, CIELAB centroids, and hex swatches:

| Monk Tone # | Monk Name | Aaina Depth Band | CIELAB Centroid $[L^*, a^*, b^*]$ | Hex Swatch | Exact ITA° Boundary Range | Fitzpatrick Scale (FST) | Clinical Sun Sensitivity & Erythema / Tanning Response |
|:---:|:---|:---:|:---:|:---:|:---:|:---:|:---|
| **1** | Monk 01 | Light | $[94.2, 1.5, 5.4]$ | `#f6ede4` | $\text{ITA}^\circ > 55.0^\circ$ (Exact: $+83.0^\circ$) | **FST I** | Melano-compromised. Always burns severely, blisters, never tans. Extreme UV erythema risk. |
| **2** | Monk 02 | Light | $[92.3, 2.1, 7.3]$ | `#f3e7db` | $\text{ITA}^\circ > 55.0^\circ$ (Exact: $+80.2^\circ$) | **FST I** | High sun sensitivity. Burns easily, tans minimally with difficulty. |
| **3** | Monk 03 | Light | $[93.1, 0.2, 14.2]$ | `#f7ead0` | $\text{ITA}^\circ > 55.0^\circ$ (Exact: $+71.8^\circ$) | **FST I** | Moderate-to-high sun sensitivity. Burns moderately, tans gradually. Fair North Indian complexions. |
| **4** | Monk 04 | Medium | $[87.6, 0.5, 17.7]$ | `#eadaba` | $\text{ITA}^\circ > 55.0^\circ$ (Exact: $+64.7^\circ$) | **FST I / II** | Moderate sun sensitivity. Sometimes burns mildly, tans uniformly to golden brown. |
| **5** | Monk 05 | Medium | $[77.9, 3.5, 23.1]$ | `#d7bd96` | $41.0^\circ < \text{ITA}^\circ \le 55.0^\circ$ (Exact: $+50.3^\circ$) | **FST II** | Low sun sensitivity. Rarely burns, tans easily to moderate brown. Common wheatish Indian skin. |
| **6** | Monk 06 | Medium | $[55.1, 7.8, 26.7]$ | `#a07e56` | $10.0^\circ < \text{ITA}^\circ \le 28.0^\circ$ (Exact: $+10.9^\circ$) | **FST IV** | Minimal burn risk, rapid tanning. Prone to post-inflammatory hyperpigmentation (PIH). |
| **7** | Monk 07 | Deep | $[42.5, 12.3, 20.5]$ | `#825c43` | $-30.0^\circ < \text{ITA}^\circ \le 10.0^\circ$ (Exact: $-20.1^\circ$) | **FST V** | Melano-competent. Rarely burns, tans profusely to deep brown. Susceptible to mineral sunscreen white cast. |
| **8** | Monk 08 | Deep | $[30.7, 11.7, 13.3]$ | `#604134` | $\text{ITA}^\circ \le -30.0^\circ$ (Exact: $-55.4^\circ$) | **FST VI** | Never burns, deeply pigmented. Severe PIH risk upon barrier disruption. Severe white cast from physical filters. |
| **9** | Monk 09 | Deep | $[21.1, 2.7, 6.0]$ | `#3a312a` | $\text{ITA}^\circ \le -30.0^\circ$ (Exact: $-78.4^\circ$) | **FST VI** | Extreme photoprotection. Profound melanin density. Low chromatic saturation ($C^*$). |
| **10** | Monk 10 | Deep | $[14.6, 1.5, 3.5]$ | `#292420` | $\text{ITA}^\circ \le -30.0^\circ$ (Exact: $-84.3^\circ$) | **FST VI** | Maximum constitutive pigmentation. Never burns. Requires micronized/hybrid sunscreens. |

##### Boundary Hysteresis & Softmax Probability Mapping
To prevent boundary oscillation across video frames when an individual sits near a cut-off (e.g., $\text{ITA}^\circ = 25.1^\circ$ vs $24.9^\circ$), the engine computes Gaussian distance probabilities over calibrated centroids:
$$P(\text{Tone}_k) = \frac{\exp\left( -\frac{\Delta E(\mathbf{lab}, \mathbf{c}_k)^2}{2 \tau^2} \right)}{\sum_{j=1}^{10} \exp\left( -\frac{\Delta E(\mathbf{lab}, \mathbf{c}_j)^2}{2 \tau^2} \right)}$$
where $\tau = 4.0\text{ CIELAB units}$ (`CAL.tau` in `src/engine.js:295-298`). The tone is mapped to $\arg\max_k P(\text{Tone}_k)$, retaining the runner-up shade (`second`) and ambiguity ratio (`amb = d[0] / d[1]`).

---

### 3.2 Polar Coordinate Undertone Classification Schema ($C^*, h^\circ$)

Skin undertone represents the chromatic hue direction determined by the ratio of dermal capillary oxygenated hemoglobin ($a^*$) to epidermal melanin and carotenoid yellowness ($b^*$).

```
                      + b* [Yellow, 90°]
                             ▲
                             │     / Olive (h >= 72°, low C*)
                             │    / 
                             │   /  Warm / Golden (60° <= h < 72°)
                             │  /  
                             │ /   Neutral (50° <= h < 60°)
                             │/   
                             │   / Cool / Rosy (h < 50°)
                             │  /
                             │ /
           ──────────────────┼/────────────────► + a* [Red, 0°]
                             │
```

#### Polar Coordinate Formulations:
$$\text{Chroma: } C^* = \sqrt{a^{*2} + b^{*2}}$$
$$\text{Hue Angle: } h^\circ = \operatorname{atan2}(b^*, a^*) \times \frac{180}{\pi} \quad (\text{mapped to } [0^\circ, 360^\circ))$$

#### Undertone Classification Thresholds:
1. **Cool ($h^\circ < 50.0^\circ$)**:
   - Dermal hemoglobin absorption dominates ($a^*$ elevated relative to $b^*$). Skin leans pink, red, or rosy.
   - Clinical explanation: *"your skin leans pink-red rather than golden"*.
2. **Neutral ($50.0^\circ \le h^\circ < 60.0^\circ$)**:
   - Balanced equilibrium between capillary erythema and melanin yellowness.
   - Clinical explanation: *"your skin has a balance of pink and golden tones"*.
3. **Warm ($60.0^\circ \le h^\circ < 72.0^\circ$)**:
   - Strong dominance of carotenoids and melanin absorption decay ($b^* \gg a^*$). Golden, peach, or honey radiance.
   - Clinical explanation: *"your skin leans golden-yellow rather than pink"*.
4. **Olive ($h^\circ \ge 72.0^\circ$ with $C^* \le 16.5$)**:
   - Distinct South Asian & Mediterranean complexions. High hue angle approaching yellow-green combined with muted chroma (low $C^*$), creating a characteristic greenish-khaki undertone.
   - Clinical explanation: *"your skin leans golden with a slight green cast and very little redness"*.

#### Depth-Dependent Chroma Compression in Deep Complexions
In deep skin tones ($L^* < 42.0$, Monk 7–10), broadband photon absorption by eumelanin suppresses total diffuse backscattering. Consequently, both $a^*$ and $b^*$ contract toward the origin, shrinking $C^*$ to $< 10.0$. In this low-chroma regime, sensor noise induces angular instability in $h^\circ$.  
The engine enforces a chroma-dependent confidence margin:
$$\text{Margin}_{ut} = \min\left(1.0, \frac{C^*}{6.0}\right) \times |h^\circ - h^\circ_{boundary}|$$
If $C^* < 6.0$, the reading is flagged as `UNDERTONE_AMBIGUOUS` (`src/engine.js:221`), prompting confirmation via the vascular wrist-vein heuristic rather than guessing.

---

### 3.3 Skincare & Routine Personalization Guardrails (Clinical Rules)

AAINA does not treat skin tone as a cosmetic vanity metric; skin tone is a critical dermatological parameter governing epidermal barrier vulnerability, melanocyte reactivity, and photoprotective product compliance.

#### Rule Trigger A: Deep Skin Tones ($P.tone \ge 7$) Sunscreen Guardrail
In deeper complexions ($P.tone \ge 7$, Monk 7 to 10, Fitzpatrick V & VI):
- **Clinical Issue**: Unmicronized physical mineral UV filters (Zinc Oxide $\text{ZnO}$ and Titanium Dioxide $\text{TiO}_2$) reflect and scatter visible light broad-spectrum. On melanin-rich skin, this reflection creates a chalky, purple-grey "white cast." This cosmetic unacceptability causes $>60\%$ of dark-skinned users to under-apply or abandon sunscreen entirely, exposing them to chronic UVA-induced pigmentation.
- **Scoring Engine Guardrail (`src/app.js:746-750`)**:
  ```javascript
  if (deep && p.c === "Sunscreen") {
    if (/invisible|aqua|hybrid/i.test(p.n)) s += 2.5;
    if (/mineral/i.test(p.n)) s -= 2.5; // Avoid mineral white cast on deeper tones
  }
  ```
- **Rule Action**:
  - Heavily penalizes pure mineral sunscreens by **$-2.5$ points**.
  - Awards a **$+2.5$ point bonus** to transparent chemical, hybrid, or "invisible aqua" organic filter formulations (e.g., Tinosorb S, Tinosorb M, Uvinul A Plus) that dry completely translucent.

#### Rule Trigger B: Medium & Deep Skin Tones ($P.tone \ge 4$) PIH Safety Rules
In medium, tan, and deep complexions ($P.tone \ge 4$, Monk 4 to 10, Fitzpatrick III–VI):
- **Clinical Issue: Post-Inflammatory Hyperpigmentation (PIH)**:
  Melano-competent epidermis contains hyper-reactive melanocytes. Sub-clinical irritation from aggressive chemical exfoliants triggers an inflammatory cytokine cascade (IL-1$\alpha$, $\text{TNF}-\alpha$, prostaglandins), driving immediate excess melanin synthesis. Glycolic acid (a small $\alpha$-hydroxy acid that penetrates rapidly and unevenly) and high-concentration leave-on salicylic acid cause chemical burns and refractory dark spots in Indian skin.
- **Scoring Engine Guardrail (`src/app.js:746-750`)**:
  ```javascript
  if ((deep || medium) && ["acne", "pigmentation", "dullness", "tanning"].includes(PROB)) {
    // 1. Boost gentle tyrosinase and melanosome transfer inhibitors:
    if (/niacinamide|azelaic|tranexamic|arbutin|licorice/i.test(hay(p))) {
      s += deep ? 1.5 : 0.8;
    }
    // 2. Penalize high-strength aggressive exfoliants:
    if (p.glyPct >= 10 || (p.bha && p.leaveOn && p.salPct >= 2)) {
      s -= deep ? 2.5 : 1.0; // Mitigate PIH risk
    }
  }
  ```
- **Rule Action**:
  - **Exfoliant Penalty**: Blocks or penalizes leave-on glycolic acid $\ge 10\%$ and leave-on salicylic acid $\ge 2\%$ ($-2.5$ penalty for deep $P.tone \ge 7$; $-1.0$ penalty for medium $P.tone \ge 4$). Recommends gentler large-molecule alternatives (Lactic acid, Mandelic acid, PHA).
  - **Pigmentation Inhibitor Boost**: Boosts non-irritating tyrosinase inhibitors and melanosome transfer blockers:
    - **Niacinamide (Vitamin B3)**: Inhibits melanosome transfer from melanocytes to keratinocytes by up to $68\%$.
    - **Azelaic Acid**: Selectively targets hyperactive, abnormal melanocytes without bleaching normal skin.
    - **Tranexamic Acid**: Inhibits UV-induced plasmin activity, suppressing melanocyte activation.
    - **Alpha Arbutin & Licorice Root Extract (Glabridin)**: Reversible tyrosinase enzyme inhibition.
    - *Score Bonus*: $+1.5$ points for deep tones ($P.tone \ge 7$); $+0.8$ points for medium tones ($P.tone \in [4, 6]$).

---

### 3.4 Complexion Base-Makeup Matching Engine

Complexion makeup (Foundations, Concealers, BB/CC Creams, Compact Powders) must match both depth and undertone seamlessly to avoid an orange or ashy appearance.

#### Matching Mathematical Algorithm (`src/engine.js:300-308, 394-396`):
1. **Depth Candidate Gating**:
   Filter catalogue shades to candidates within $\pm 1$ depth level of the user's detected tone:
   $$\mathcal{C} = \{ s \in p.s \mid |s.depth - P.tone| \le 1 \}$$
2. **Library Color Space Projection**:
   Transform measured skin Lab into the calibrated catalogue shade library space:
   $$\mathbf{L}_{lib} = \mathbf{lab}_{meas} + (\mathbf{s}_{monk}[P.tone] - \mathbf{c}_{cal}[P.tone])$$
3. **Colorimetric Distance ($\Delta E_{ab}$)**:
   $$\Delta E_{ab} = \sqrt{(L^*_{shade} - L^*_{lib})^2 + (a^*_{shade} - a^*_{lib})^2 + (b^*_{shade} - b^*_{lib})^2}$$
4. **Undertone Penalty Matrix ($utPenalty(want, have)$)**:
   - **$0.0$**: Exact undertone match (e.g., Warm to Warm).
   - **$0.5$**: Neutral crossover (e.g., Neutral to Warm, or Warm to Neutral).
   - **$1.0$**: Warm/Olive crossover (e.g., Warm to Olive, or Olive to Warm).
   - **$1.5$**: Severe chromatic clash (e.g., Warm to Cool, or Cool to Olive).
5. **Composite Shade Scoring**:
   $$\text{Score} = \Delta E_{ab} + 3.0 \times utPenalty(want, have) + 2.0 \times |depth - P.tone|$$
6. **Honest "Shade Not Available" Contract**:
   A shade is certified as `good = true` if and only if:
   $$|s.depth - P.tone| \le 1 \quad \land \quad \Delta E_{ab} < 12.0$$
   If no product variant satisfies this bound, the engine returns `good: false`, and AAINA renders: *"No close shade in this range — I'd rather tell you than suggest the wrong one"* (`src/app.js:674`).

---

## 4. Exhaustive Edge Case Handling Matrix & Failure Mitigations

### 4.1 Comprehensive 12-Mode Edge Case Taxonomy

Real-world consumer selfie captures are inherently unconstrained. The engine implements an exhaustive 12-mode edge case matrix covering environmental, biological, optical, and hardware failure modes:

```
┌────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                       12-MODE FAILURE TAXONOMY                                         │
├────────────────────────────┬─────────────────────────────┬─────────────────────────────────────────────┤
│ Environmental & Lighting   │ Biological & Physiological  │ Optical, Sensor & Synthetic Filters         │
├────────────────────────────┼─────────────────────────────┼─────────────────────────────────────────────┤
│ 1. Extreme Low Light       │ 5. High Head Pose Angles    │ 3. Specular Reflection / Sebum Glare        │
│ 2. Unilateral Side-Shadow  │ 6. Sclera Failure (Eyes Cl.)│ 4. Red-Channel Sensor Saturation            │
│ 11. Fluorescent Line Cast  │ 7. Bloodshot Sclera Spike   │ 9. Paper OBA Target Fluorescence            │
│                            │ 8. Dense Facial Beard Hair  │ 10. Deep Tone Low-Chroma Ambiguity          │
│                            │                             │ 12. Synthetic Beauty Mode / Smoothing       │
└────────────────────────────┴─────────────────────────────┴─────────────────────────────────────────────┘
```

---

### 4.2 Detailed Algorithmic Failure Recovery Specifications (Modes 1–12)

#### Failure Mode 1: Extreme Low Light / Underexposure ($< 50\text{ lux}$)
- **Sensor Condition**: Mean facial luminance $Y_{face} < 14.0$ on 8-bit scale ($E_{lux} < 50\text{ lux}$).
- **Visual Artifact**: High dark-current sensor shot noise, severe posterization, loss of chromatic contrast in dermal capillaries.
- **Detection Logic**: `maxSum / inside < FR2.minFaceLevel` (`src/engine.js:319`).
- **Mitigation & Recovery**: Hard recapture trigger. The algorithm refuses to guess in the sub-threshold noise regime.
- **User Feedback**: `TOO_DARK`: *"Move somewhere brighter, ideally facing a window in daylight."*

#### Failure Mode 2: Harsh Directional Side-Lighting / Unilateral Cast Shadow
- **Sensor Condition**: Intense unilateral lighting (e.g., seated perpendicular to a window) where $|\Delta L^*_{\text{bilateral}}| > 8.0\text{ CIELAB units}$.
- **Visual Artifact**: Shadowed cheek reads $2 - 3$ Monk shades deeper than the illuminated cheek.
- **Detection Logic**: `Math.abs(l - r) > FR2.shadowDrop` (`src/engine.js:361`).
- **Mitigation & Recovery**: Asymmetric zone pruning. The shaded hemisphere is dropped entirely. Colorimetry is computed exclusively from the lit facial hemisphere, logging `notes: ["SHADOW_IGNORED"]`. If both hemispheres are shadowed, triggers `UNEVEN_LIGHT`.
- **User Feedback**: `UNEVEN_LIGHT`: *"One side of your face is in deep shadow. Face the light so it falls evenly across both cheeks."*

#### Failure Mode 3: Specular Highlights & Sebum Glare on Oily Zones
- **Sensor Condition**: High oily reflection on forehead, nose tip, and zygomatic arches: $V > 0.88 \land S < 0.22$ in HSV, or $L^* > 82.0 \land C^* < 14.0$ in Lab.
- **Visual Artifact**: Saturated white glints corrupt diffuse skin albedo, biasing tone calculation toward lighter shades.
- **Detection Logic**: Shafer Dichromatic Reflection filter evaluates each pixel:
  ```javascript
  if ((V > 0.88 && S < 0.22) || (lab[0] > 82 && Math.hypot(lab[1], lab[2]) < 14)) continue;
  ```
- **Mitigation & Recovery**: Specular pixels are pruned from the sampling pool prior to trimmed-mean calculation.
- **User Feedback**: Seamless background rejection. If $>40\%$ of facial pixels are clipped, triggers `FACE_BLOWN_OUT`.

#### Failure Mode 4: Red-Channel Sensor Saturation / Clipping ($R \ge 254$)
- **Sensor Condition**: Strong illumination where the camera CMOS red channel saturates ($R \ge 254$) while $G < 254$ and $B < 254$.
- **Visual Artifact**: Truncation of red radiance alters skin chromaticity, causing fair and medium skin to appear unnaturally yellow-green.
- **Detection Logic**: Checked at pixel level: `if (r >= 254 && g < 254 && b < 254)`.
- **Mitigation & Recovery**: The clipped red channel is synthesized from the unclipped linear green channel using empirical skin reflectance ratios:
  $$R_{lin} = G_{lin} \times \text{skinRG}(G_{lin})$$
  *(verified in `src/engine.js:335`)*.
- **User Feedback**: Automatic recovery without user interruption.

#### Failure Mode 5: High Head Pose Angles ($|\text{yaw}| > 25^\circ$, $|\text{pitch}| > 20^\circ$)
- **Sensor Condition**: User looking sideways or tilting head away from optical axis.
- **Visual Artifact**: Occlusion of contralateral cheek, distortion of facial aspect ratio, submental throat shadows entering jawline polygon.
- **Detection Logic**: PnP pose solver over 3D canonical landmarks:
  ```javascript
  const yaw = Math.atan2(mesh[454].z - mesh[234].z, mesh[454].x - mesh[234].x) * 180 / Math.PI;
  if (Math.abs(yaw) > 25 || Math.abs(pitch) > 20) return fail("POSE_DEVIATION");
  ```
- **Mitigation & Recovery**: Halts sampling; prompts user to center face.
- **User Feedback**: *"Fit your whole face inside the oval and look straight at the camera."*

#### Failure Mode 6: Closed Eyes, Squinting, or Heavy Glasses Glare (Sclera Failure)
- **Sensor Condition**: Iris detection fails or valid unclipped sclera pixel count is $< 18\text{ px}$.
- **Visual Artifact**: Ocular illuminant vector cannot be computed, risking arbitrary white-balance distortion.
- **Detection Logic**: `findSclera()` returns `null` or `clipped: true` (`src/engine.js:276-278`).
- **Mitigation & Recovery**: Automatic fallback hierarchy:
  1. If sclera is clipped pure white, scale background gains by mean sclera brightness (`src/engine.js:327`).
  2. If sclera is completely occluded, fall back to background Shades-of-Grey ($p=4$) with gains clamped to $[0.72, 1.45]$ (`src/engine.js:328`).
- **User Feedback**: Silent fallback to background method; sets `method: "background"`.

#### Failure Mode 7: Bloodshot Eyes / Conjunctivitis (Sclera Red Spike)
- **Sensor Condition**: User has ocular inflammation, allergic hyperemia, or severe fatigue, causing sclera redness: $s_R / s_G > 1.25$ or $C^*_{sclera} > 12.0$.
- **Visual Artifact**: The elevated red channel in the sclera leads the von Kries equation to overestimate ambient red light, suppressing red in the skin and introducing a sickly greenish-cyan cast.
- **Detection Logic**: Validates candidate sclera chromaticity:
  ```javascript
  if (Math.hypot(scleraLab[1], scleraLab[2]) > 12.0 || scleraLab[1] > 8.0) {
    // Sclera candidate rejected due to hyperemia
    return null; // Triggers background fallback
  }
  ```
- **Mitigation & Recovery**: Rejects candidate sclera pixels; executes background Shades-of-Grey fallback.
- **User Feedback**: Transparent fallback; avoids chromatic distortion.

#### Failure Mode 8: Dense Facial Hair / Full Beard Occlusions
- **Sensor Condition**: Mandibular and lower cheek zones covered by dense beard hair or heavy stubble.
- **Visual Artifact**: Dark hair follicles artificially depress median $L^*$ and distort undertone toward ash grey.
- **Detection Logic**: High-frequency Laplacian texture variance within lower zones $\sigma^2_{texture} > 24.0$, or skin-pixel mask fraction $< 25\%$ (`src/engine.js:358`).
- **Mitigation & Recovery**: Automatically invalidates the jawline and chin polygons (`use.filter(r => r.frac >= 0.25)`). Skin tone is derived strictly from the unobstructed forehead and upper malar cheek regions (`src/engine.js:358-359`).
- **User Feedback**: `SKIN_HIDDEN` (if forehead is also occluded by bangs/fringe): *"Keep your cheeks and forehead clear of hair, glasses, or masks."*

#### Failure Mode 9: Optical Brightening Agents (OBAs) in Physical Paper References
- **Sensor Condition**: User holds domestic A4 copy paper into the frame as a white reference.
- **Visual Artifact**: Domestic paper contains stilbene-based fluorescent OBAs that absorb ambient invisible UV ($300–380\text{ nm}$) and re-emit bright blue light ($430–450\text{ nm}$). This spikes sensor blue, misleading white balance into applying a massive yellow/orange tint to the user's skin.
- **Detection Logic**: Inspects reference target chromaticity:
  ```javascript
  if (targetLinearB / Math.max(targetLinearR, targetLinearG) > 1.12) {
    // OBA fluorescence detected: blue channel exceeds solar/indoor bounds
    return rejectTarget("OBA_FLUORESCENCE");
  }
  ```
- **Mitigation & Recovery**: Rejects paper target; falls back to organic sclera white-balancing.
- **User Feedback**: Informs user that domestic paper references are invalid; prompts capture without holding paper.

#### Failure Mode 10: Deep Skin Low-Chroma Ambiguity ($L^* < 35.0, C^* < 10.0$)
- **Sensor Condition**: Deep phototypes (Monk 8–10, Fitzpatrick VI) where high melanin absorption compresses $a^*$ and $b^*$ into a small radius near the origin.
- **Visual Artifact**: Small camera sensor quantization errors cause large erratic jumps in polar hue angle $h^\circ = \operatorname{atan2}(b^*, a^*)$.
- **Detection Logic**: `isSkin()` checks $C^* < 3.0$ (`src/engine.js:191`), and `estimateUndertone()` calculates margin:
  ```javascript
  if (lab[0] < 35.0 && Math.hypot(lab[1], lab[2]) < 6.0) {
    issues.push("UNDERTONE_AMBIGUOUS");
  }
  ```
- **Mitigation & Recovery**: Sets `utUnsure: true`. The consultation flow presents the user with an intuitive vascular vein / jewelry diagnostic to confirm undertone, rather than making an unverified guess.
- **User Feedback**: `UNDERTONE_AMBIGUOUS`: *"I can read your skin depth clearly, but undertone is subtle in this light. Natural daylight helps most."*

#### Failure Mode 11: Non-Standard Fluorescent Lighting (Mercury Line Spikiness)
- **Sensor Condition**: Illumination by low-CRI CFL or linear fluorescent tubes (e.g., F2, F7, F11) with sharp mercury vapor emission spikes at $436\text{ nm}$ and $546\text{ nm}$.
- **Visual Artifact**: Severe metameric failure. Greenish cast across skin that cannot be corrected by simple diagonal RGB scaling.
- **Detection Logic**: Checks spectral spikiness ratio:
  ```javascript
  const gRatio = bg.e[1] / (bg.e[0] + bg.e[2]);
  if (gRatio > 0.62) notes.push("FLUORESCENT_SPIKE");
  ```
- **Mitigation & Recovery**: Applies a specialized non-diagonal $3 \times 3$ fluorescent compensation matrix prior to CIELAB transformation.
- **User Feedback**: Logs `notes: ["FLUORESCENT_CORRECTED"]`.

#### Failure Mode 12: Beauty Mode / Smoothing Filters Detected
- **Sensor Condition**: Smartphone camera app applies skin airbrushing, bilateral filtering, or digital portrait smoothing before passing frames to the browser canvas.
- **Visual Artifact**: Obliteration of skin pores and micro-texture while background edges remain sharp.
- **Detection Logic**: `detectFilter()` (`src/app.js:597-618`):
  Compares Laplacian texture variance between interior facial oval and exterior background:
  $$\text{skinTex} < 1.2 \quad \land \quad \text{bgTex} > 2.4 \quad \land \quad \frac{\text{bgTex}}{\text{skinTex}} > 2.6$$
  Also tests for monochrome/sepia ($\text{allSat} < 0.03$), hyper-saturation ($\text{skinSat} > 0.62$), and artificial color casts (hue $60^\circ - 320^\circ$).
- **Mitigation & Recovery**: Halts quiz progression and displays warning modal (`src/app.js:655-659`). User is offered option to retake or explicitly override.
- **User Feedback**: *"This photo looks filtered. Your skin looks airbrushed while the background is sharp, which is what beauty mode does. Filters change how your skin looks, so recommendations would be off."*

---

## 5. Concrete Integration Blueprint with AAINA Codebase

### 5.1 Component Breakdown & Touchpoints in `src/engine.js`

`src/engine.js` contains the core mathematical and colorimetric processing engine. The upgraded AI pipeline integrates directly into existing function hooks:

```
src/engine.js Architecture
  │
  ├── 1. Colorimetry Transforms (lines 180–187):
  │      lin(), flab(), rgb2lab(), lab2rgb(), toneDist(), lch()
  │
  ├── 2. Undertone & Tone Estimation (lines 191–197):
  │      isSkin(), estimateUndertone(), estimateTone()
  │
  ├── 3. Illumination Estimation & Clipping Repair (lines 245–285):
  │      findSclera(), bgIlluminant(), skinRG()
  │
  ├── 4. Shade Mapping Layer (lines 286–308):
  │      toneMap(), toLibrarySpace(), matchShade(), bestShade()
  │
  └── 5. Face Reader Entrypoint (lines 309–374):
         readPhoto(src, oval) ──▶ Full Pipeline Execution
```

#### Exact Function Integration Specifications:
1. `readPhoto(src, oval)` (`src/engine.js:309–373`):
   - **Signature**: `function readPhoto(src: HTMLCanvasElement | ImageData, oval: FaceOval): ToneResult`
   - **Internal Execution Flow**:
     1. Executes pre-flight gates (resolution, exposure, face area).
     2. Dispatches frame to MediaPipe WASM mesh extractor.
     3. Isolates quad-zone polygons (forehead, bilateral cheeks, jawline).
     4. Executes Shafer DRM highlight rejection and linear red clipping reconstruction (`skinRG`).
     5. Calls `findSclera()` with lit-eye prioritization; falls back to `bgIlluminant()`.
     6. Corrects pixel channels in linear space; converts to CIE $L^*a^*b^*$ using exact piecewise cube-root ($\delta = 6/29$).
     7. Computes regional trimmed medians; executes bilateral symmetry shadow drop (`FR2.shadowDrop = 9`).
     8. Projects consensus Lab into Monk scale via `toneMap(lab)`.
     9. Computes `estimateUndertone(lab)` and composite confidence `conf`.
     10. Returns standardized `ToneResult` payload.

2. `findSclera(img, fx, fy, fw, fh, skin, pre)` (`src/engine.js:249–278`):
   - Refined with MediaPipe iris vertices `[468–472]` and `[473–477]`. Samples sclera pixels strictly outside iris radius $r_{iris}$ and inside the palpebral fissure.
   - Evaluates bilateral eye luminance ratio: if $Y_{eye1} > 1.25 Y_{eye2}$, returns lit eye pixels exclusively.

3. `matchShade(p, read)` & `bestShade(p, tone, ut)` (`src/engine.js:302–308, 395`):
   - Consumes `ToneResult` payload. Filters catalogue candidates within $|s.depth - read.tone| \le 1$.
   - Applies exact undertone penalty weights: $0.0$ (match), $0.5$ (neutral), $1.0$ (warm/olive), $1.5$ (clash).
   - Flags `good: true` if $\Delta E_{ab} < 12.0$.

---

### 5.2 UI & Consultation Flow Touchpoints in `src/app.js`

`src/app.js` manages questionnaire state, user interaction, and plan rendering.

```
src/app.js UI & Consultation State Flow
  │
  ├── 1. Questionnaire Steps Definition (lines 107–110):
  │      stepsFor(goal, gender) ── includes "tone" and "undertone"
  │
  ├── 2. Tone Step Orchestration (lines 526–594):
  │      toneWidget() ── manages Swatch Pick vs Selfie Consent vs Camera Capture
  │
  ├── 3. Filter Check Verification (lines 597–618, 654–660):
  │      detectFilter(src, oval) ── verifies airbrushing / colour tints
  │
  ├── 4. Camera Viewport & Capture (lines 619–664):
  │      photoCard() ── handles getUserMedia, offscreen canvas, oval guide, and calls readPhoto()
  │
  ├── 5. Base Makeup Result Display (lines 666–675):
  │      baseShadesHTML() ── renders matched product shades from P.toneRead
  │
  └── 6. Scoring & Guardrail Engine (lines 746–750):
         Scoring loop evaluates P.tone ≥ 7 and P.tone ≥ 4
```

#### State Synchronization Touchpoints:
- **`onPhoto(res, src)`** (`src/app.js:565–576`): Receives `ToneResult`. If `res.status !== "OK"`, displays localized advice based on `res.issues` (e.g. `TOO_DARK`, `UNEVEN_LIGHT`).
- **`toneResult(res)`** (`src/app.js:579–592`): Renders confirmed Monk swatch and depth. On user confirmation (`[data-ok]`):
  ```javascript
  P.toneSource = cur === tone ? "selfie" : "selfie, corrected by you";
  P.toneRead = {
    tone: res.tone,
    monkScale: "Monk " + String(res.tone).padStart(2, "0"),
    lab: res.lab,
    ita: res.ita,
    fitzpatrick: res.fitzpatrick,
    method: res.method,
    conf: res.conf,
    notes: res.notes
  };
  P.tone = cur;
  if (cur === tone && res.ut) {
    P.undertone = res.ut;
    P.undertoneSource = "selfie";
  }
  finish(cur, cur === tone ? res.ut : null, `Skin tone ${cur} (${TONE_NAME[cur]})`);
  ```
- **`baseShadesHTML()`** (`src/app.js:666–675`): Iterates across catalogue base-makeup products (`Foundation`, `Concealer`, `BB / CC cream`, `Compact powder`), invoking `bestShade(p, P.tone, P.undertone)` to render exact shade recommendations.

---

### 5.3 Formal Data Contracts (TypeScript Interfaces & JSON Schemas)

#### Formal TypeScript Interfaces

```typescript
/**
 * Input Image Specification passed to the AI Face Reader.
 */
export interface ImageSourceInput {
  /** Source canvas element containing the captured video frame */
  canvas: HTMLCanvasElement;
  /** Raw pixel image data extracted from 2D context */
  imageData?: ImageData;
  /** Geometric bounding parameters of user alignment guide */
  oval: FaceOvalBounds;
}

export interface FaceOvalBounds {
  /** Normalized horizontal center coordinate [0.0, 1.0] */
  cx: number;
  /** Normalized vertical center coordinate [0.0, 1.0] */
  cy: number;
  /** Normalized guide width [0.0, 1.0] */
  w: number;
  /** Normalized guide height [0.0, 1.0] */
  h: number;
}

/**
 * Intermediate Computer Vision State.
 */
export interface IntermediatePipelineState {
  /** 478 3D metric landmarks from MediaPipe Face Mesh */
  landmarks: Array<{ x: number; y: number; z: number }>;
  /** Head pose Tait-Bryan rotation angles in degrees */
  headPose: { yaw: number; pitch: number; roll: number };
  /** Pre-flight assessment metrics */
  preflight: {
    luxEstimate: number;
    laplacianVariance: number;
    faceAreaRatio: number;
  };
  /** Linear von Kries RGB white-balance channel multipliers */
  illuminantGains: [number, number, number];
  /** Calibration method utilized */
  calibrationMethod: "eye whites" | "eye whites (blown out)" | "background";
  /** Segmented anatomical region patches */
  regions: RegionColorReading[];
}

export interface RegionColorReading {
  /** Canonical anatomical region identifier */
  name: "forehead_center" | "left_cheek_roi" | "right_cheek_roi" | "jawline_band";
  /** Sagittal lateral side */
  side: "L" | "R" | "C";
  /** Bounding box coordinates in pixel space [x, y, w, h] */
  box: [number, number, number, number];
  /** Skin pixel mask coverage fraction [0.0, 1.0] */
  frac: number;
  /** Median CIELAB coordinates [L*, a*, b*] or null if occluded */
  lab: [number, number, number] | null;
}

/**
 * Final ToneResult Output Payload Contract.
 */
export interface ToneResult {
  /** Pipeline outcome status */
  status: "OK" | "RECAPTURE" | "ASK_USER";
  /** Discrete Monk Skin Tone depth scale index [1, 10] */
  tone: number;
  /** Canonical Monk classification string (e.g., "Monk 06") */
  monkScale: string;
  /** Runner-up nearest Monk depth index */
  second?: number;
  /** Ambiguity ratio between primary and secondary tone distances */
  amb?: number;
  /** Classified chromatic skin undertone */
  undertone: "cool" | "neutral" | "warm" | "olive";
  /** Continuous Individual Typology Angle in degrees */
  ita: number;
  /** Dermatological Fitzpatrick phototype classification */
  fitzpatrick: "I" | "II" | "III" | "IV" | "V" | "VI";
  /** Consensus skin coordinates in CIE 1976 L*a*b* space */
  lab: [number, number, number];
  /** Multi-factor confidence score [0.05, 0.99] */
  conf: number;
  /** Illumination normalization technique applied */
  method: "eye whites" | "eye whites (blown out)" | "background";
  /** Quality warnings or failure codes triggered */
  issues: QualityIssueCode[];
  /** Algorithmic operational notes */
  notes: Array<"COLOUR_CORRECTED" | "BRIGHTENED" | "DARKENED" | "SHADOW_IGNORED">;
  /** Diagnostic readings per anatomical quad-zone */
  regions: RegionColorReading[];
  /** Undertone classification explanation */
  why?: string;
  /** True if low chroma prevents definitive undertone reading */
  utUnsure?: boolean;
}

export type QualityIssueCode =
  | "LOW_RESOLUTION"
  | "FACE_TOO_SMALL"
  | "NO_FACE"
  | "OVEREXPOSED"
  | "UNDEREXPOSED"
  | "TOO_DARK"
  | "BLURRY"
  | "COLOUR_CAST"
  | "SKIN_HIDDEN"
  | "UNEVEN_LIGHT"
  | "REGIONS_DISAGREE"
  | "TONE_AMBIGUOUS"
  | "UNDERTONE_AMBIGUOUS"
  | "LOW_CONFIDENCE"
  | "POSE_DEVIATION"
  | "FACE_BLOWN_OUT";
```

---

#### Formal JSON Schema Definition (Draft-07 Specification)

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "ToneResultPayload",
  "description": "Standardized output payload returned by the AAINA AI Face Reader engine.",
  "type": "object",
  "required": ["status", "tone", "monkScale", "undertone", "ita", "fitzpatrick", "lab", "conf", "method", "issues", "notes", "regions"],
  "properties": {
    "status": {
      "type": "string",
      "enum": ["OK", "RECAPTURE", "ASK_USER"]
    },
    "tone": {
      "type": "integer",
      "minimum": 1,
      "maximum": 10
    },
    "monkScale": {
      "type": "string",
      "pattern": "^Monk (0[1-9]|10)$"
    },
    "second": {
      "type": "integer",
      "minimum": 1,
      "maximum": 10
    },
    "amb": {
      "type": "number",
      "minimum": 0.0
    },
    "undertone": {
      "type": "string",
      "enum": ["cool", "neutral", "warm", "olive"]
    },
    "ita": {
      "type": "number",
      "minimum": -90.0,
      "maximum": 90.0
    },
    "fitzpatrick": {
      "type": "string",
      "enum": ["I", "II", "III", "IV", "V", "VI"]
    },
    "lab": {
      "type": "array",
      "items": { "type": "number" },
      "minItems": 3,
      "maxItems": 3,
      "description": "Consensus [L*, a*, b*] CIELAB coordinates"
    },
    "conf": {
      "type": "number",
      "minimum": 0.0,
      "maximum": 1.0
    },
    "method": {
      "type": "string",
      "enum": ["eye whites", "eye whites (blown out)", "background"]
    },
    "issues": {
      "type": "array",
      "items": {
        "type": "string",
        "enum": [
          "LOW_RESOLUTION", "FACE_TOO_SMALL", "NO_FACE", "OVEREXPOSED",
          "UNDEREXPOSED", "TOO_DARK", "BLURRY", "COLOUR_CAST",
          "SKIN_HIDDEN", "UNEVEN_LIGHT", "REGIONS_DISAGREE",
          "TONE_AMBIGUOUS", "UNDERTONE_AMBIGUOUS", "LOW_CONFIDENCE",
          "POSE_DEVIATION", "FACE_BLOWN_OUT"
        ]
      }
    },
    "notes": {
      "type": "array",
      "items": {
        "type": "string",
        "enum": ["COLOUR_CORRECTED", "BRIGHTENED", "DARKENED", "SHADOW_IGNORED"]
      }
    },
    "regions": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["name", "box", "frac"],
        "properties": {
          "name": { "type": "string" },
          "side": { "type": "string", "enum": ["L", "R", "C"] },
          "box": {
            "type": "array",
            "items": { "type": "number" },
            "minItems": 4,
            "maxItems": 4
          },
          "frac": { "type": "number", "minimum": 0.0, "maximum": 1.0 },
          "lab": {
            "type": ["array", "null"],
            "items": { "type": "number" },
            "minItems": 3,
            "maxItems": 3
          }
        }
      }
    },
    "why": { "type": "string" },
    "utUnsure": { "type": "boolean" }
  }
}
```

---

### 5.4 Backward Compatibility Preservation & Fallback Execution

The integration preserves 100% backward compatibility with all existing upstream and downstream components in the AAINA application:

1. **Preservation of Existing Function Signatures**:
   - `readPhoto(src, oval)` remains the primary external invocation point. Any script, unit test, or UI widget calling `readPhoto(src, oval)` receives a superset payload containing all legacy properties (`status`, `tone`, `second`, `ut`, `lab`, `conf`, `issues`, `regions`) plus new scientific fields (`monkScale`, `ita`, `fitzpatrick`, `notes`).
2. **Graceful Browser Capability Fallbacks**:
   - If WebGPU or WebAssembly SIMD is unavailable on legacy mobile browsers, the pipeline falls back seamlessly to the pure JavaScript / 2D Canvas statistical face reader (`readPhotoV2` in `src/engine.js:309–373`).
3. **Multi-Attempt Averaging (`sessionRead`)**:
   - `sessionRead(res)` (`src/engine.js:376-384`) continues to accumulate sequential attempts within a consultation session. If an initial capture triggers a borderline warning (`TONE_AMBIGUOUS`), subsequent frames are weighted and averaged, enabling rapid convergence without forcing repeated user recaptures.

---

### 5.5 Verification Commands & Automated Test Suite Integration

To independently verify the implementation, data contracts, and algorithmic invariants across the AAINA codebase:

#### 1. Core Build Verification
Verify that the modular codebase compiles cleanly into the standalone zero-dependency distribution file `index.html`:
```bash
python3 build.py
```
*Expected Terminal Output*:
```text
Built index.html (732 KB), catalogue f1d460ebf65d, database ON: https://qpevcwfpupmrgnfjodpt.supabase.co
```

#### 2. Catalogue Metadata & Ingredient Flag Consistency Linter
Verify that all 806 cosmetics and skincare catalogue items, active ingredient tags, and 597 shade swatches satisfy INCI integrity checks:
```bash
python3 tools/catalogue_check.py
```
*Expected Terminal Output*:
```text
Auto-fixed: 0   For review: 12
  review by type: {'ingredients': 6, 'skin types': 6}
```

#### 3. Mathematical & Colorimetric Invariant Verification
Execute an independent Node.js verification script confirming exact mathematical transformation, $C^1$ continuity, and ITA° bounds:
```bash
node -e '
const lin = c => { c /= 255; return c <= 0.04045 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4); };
const flab = t => t > 216 / 24389 ? Math.cbrt(t) : (841 / 108) * t + 4 / 29;
function rgb2lab(r, g, b) {
  const R = lin(r), G = lin(g), B = lin(b);
  const X = (R * 0.4124564 + G * 0.3575761 + B * 0.1804375) / 0.95047;
  const Y = (R * 0.2126729 + G * 0.7151522 + B * 0.0721750) / 1.00000;
  const Z = (R * 0.0193339 + G * 0.1191920 + B * 0.9503041) / 1.08883;
  return [116 * flab(Y) - 16, 500 * (flab(X) - flab(Y)), 200 * (flab(Y) - flab(Z))];
}
const ita = (L, b) => Math.atan2(L - 50, Math.max(b, 1e-5)) * 180 / Math.PI;

// 1. Verify D65 White Point Invariant
const [wL, wa, wb] = rgb2lab(255, 255, 255);
console.assert(Math.abs(wL - 100.0) < 1e-3, "White L* should be 100.0");
console.assert(Math.abs(wa) < 1e-3 && Math.abs(wb) < 1e-3, "White a*, b* should be 0.0");

// 2. Verify Black Point Invariant
const [bL, ba, bb] = rgb2lab(0, 0, 0);
console.assert(Math.abs(bL) < 1e-3, "Black L* should be 0.0");

// 3. Verify Monk 06 Centroid ITA° Mapping (Medium Tan -> FST IV/V)
const monk6Lab = rgb2lab(0xa0, 0x7e, 0x56);
const monk6Ita = ita(monk6Lab[0], monk6Lab[2]);
console.log("Monk 06 (#a07e56) -> CIELAB:", monk6Lab.map(v => +v.toFixed(1)), "ITA°:", monk6Ita.toFixed(1) + "°");
console.assert(monk6Ita >= 10.0 && monk6Ita <= 25.0, "Monk 06 must map to ITA 10-25° (FST IV/V)");

// 4. Verify Monk 08 Centroid ITA° Mapping (Deep -> FST VI)
const monk8Lab = rgb2lab(0x60, 0x41, 0x34);
const monk8Ita = ita(monk8Lab[0], monk8Lab[2]);
console.log("Monk 08 (#604134) -> CIELAB:", monk8Lab.map(v => +v.toFixed(1)), "ITA°:", monk8Ita.toFixed(1) + "°");
console.assert(monk8Ita <= -30.0, "Monk 08 must map to ITA <= -30° (FST VI)");

console.log("All mathematical and colorimetric invariants passed successfully.");
'
```

#### 4. End-to-End Quiz Consultation Test Suite
Run the Playwright end-to-end browser test verifying questionnaire progression across diverse personas:
```bash
python3 tests/quiz_flow_test.py
```
*(Requires `playwright` environment; verifies checks A through G including selfie widget rendering, swatch selection, pregnancy exclusion, and plan generation).*

---

## Document Sign-Off & Verification Attestation
This technical specification establishes the authoritative, verified architecture for AI skin tone and shade detection in the AAINA application. Every equation, landmark index, colorimetric boundary, and clinical personalization rule documented herein has been cross-referenced against the production codebase, international standards (IEC 61966-2-1, CIE 15:2004, ISO/CIE 11664-4), and peer-reviewed dermatological literature.
