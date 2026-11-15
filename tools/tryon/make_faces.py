#!/usr/bin/env python3
"""Render the six try-on model faces and their face landmarks.

    python3 tools/tryon/make_faces.py

No photographs of real people are used, and no face is based on a real person.
Each face is drawn from MediaPipe's canonical face mesh (tools/tryon/
canonical_face_model.obj, Apache-2.0, see MEDIAPIPE_LICENSE), reshaped per face,
then shaded and painted: skin with the given mid-tone, ambient occlusion from the
mesh depth, multi-scale skin texture, eyes, brows, lips and hair. Because each face
is generated from the mesh, its exact 478 MediaPipe landmark positions are known
and shipped with it, so the model faces work offline with no face tracking.

Writes data/model_faces/<id>.jpg, data/model_faces.json (id, label, base hex,
Monk tone, undertone, file) and data/model_faces_landmarks.json.
Needs numpy, scipy and Pillow. Output is deterministic (fixed seeds).
"""
import json
import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from scipy.ndimage import gaussian_filter

ROOT = Path(__file__).resolve().parents[2]
OBJ = Path(__file__).with_name("canonical_face_model.obj")
OUT = ROOT / "data" / "model_faces"
W, H, SS = 640, 800, 2
W2, H2 = W * SS, H * SS
BG = ("#efe4d6", "#e2d3c1")       # plain warm beige, the same for every face

# Mid-tones sampled from real skin (given), with approximate Monk tone and undertone.
FACES = [
    dict(id="fair-cool", label="Fair · cool", hex="#e6d0cd", monk=3, undertone="cool", sex="f", hair="wavy",
         hair_col="#2e1f18", eyes="#4b3123", cloth="#6f8299", seed=101,
         shape=dict(width=0.96, jaw=0.94, chin=1.03, cheek=0.99, nose=0.95, lips=1.02, mouth=0.97, eye_open=0.85, eye=1.05, brow=0.05)),
    dict(id="light-warm", label="Light · warm", hex="#f3c6a8", monk=4, undertone="warm", sex="f", hair="bun",
         hair_col="#1f1611", eyes="#3f2819", cloth="#b0604c", seed=202,
         shape=dict(width=0.99, jaw=0.97, chin=0.98, cheek=1.03, nose=1.0, lips=1.08, mouth=1.0, eye_open=0.82, eye=1.06, brow=0.0)),
    dict(id="medium-olive", label="Medium · olive", hex="#d39b78", monk=5, undertone="olive", sex="m", hair="short",
         hair_col="#16100c", eyes="#33200f", cloth="#e7e1d6", seed=303,
         shape=dict(width=1.03, jaw=1.07, chin=1.02, cheek=0.98, nose=1.08, lips=0.98, mouth=1.03, eye_open=0.7, eye=0.98, brow=-0.1)),
    dict(id="tan-warm", label="Tan · warm", hex="#ab6f51", monk=6, undertone="warm", sex="f", hair="braid",
         hair_col="#140e0a", eyes="#2f1d10", cloth="#6e5876", seed=404,
         shape=dict(width=0.98, jaw=0.96, chin=1.0, cheek=1.02, nose=1.02, lips=1.1, mouth=0.99, eye_open=0.8, eye=1.05, brow=0.02)),
    dict(id="deep-warm", label="Deep · warm", hex="#91604b", monk=7, undertone="warm", sex="f", hair="straight",
         hair_col="#120d0a", eyes="#2a190d", cloth="#c79a3e", seed=505,
         shape=dict(width=1.0, jaw=0.98, chin=1.01, cheek=1.0, nose=1.05, lips=1.14, mouth=1.02, eye_open=0.82, eye=1.04, brow=0.0)),
    dict(id="very-deep", label="Very deep · neutral", hex="#483026", monk=9, undertone="neutral", sex="f", hair="curly",
         hair_col="#0c0806", eyes="#21140b", cloth="#8b3c49", seed=606,
         shape=dict(width=1.01, jaw=0.99, chin=0.99, cheek=1.02, nose=1.1, lips=1.18, mouth=1.03, eye_open=0.84, eye=1.06, brow=0.0)),
]

OVAL = [10, 338, 297, 332, 284, 251, 389, 356, 454, 323, 361, 288, 397, 365, 379, 378, 400, 377, 152, 148, 176, 149, 150,
        136, 172, 58, 132, 93, 234, 127, 162, 21, 54, 103, 67, 109]
LIPS_OUT = [61, 146, 91, 181, 84, 17, 314, 405, 321, 375, 291, 409, 270, 269, 267, 0, 37, 39, 40, 185]
LIPS_UP = [61, 185, 40, 39, 37, 0, 267, 269, 270, 409, 291, 308, 415, 310, 311, 312, 13, 82, 81, 80, 191, 78]
LIP_LINE = [61, 78, 191, 80, 81, 82, 13, 312, 311, 310, 415, 308, 291]
EYE_R = dict(up=[33, 246, 161, 160, 159, 158, 157, 173, 133], lo=[33, 7, 163, 144, 145, 153, 154, 155, 133])
EYE_L = dict(up=[263, 466, 388, 387, 386, 385, 384, 398, 362], lo=[263, 249, 390, 373, 374, 380, 381, 382, 362])
BROW_R = dict(up=[70, 63, 105, 66, 107], lo=[46, 53, 52, 65, 55])
BROW_L = dict(up=[300, 293, 334, 296, 336], lo=[276, 283, 282, 295, 285])


# ---------------------------------------------------------------- helpers
def hex_rgb(h):
    return np.array([int(h[i:i + 2], 16) for i in (1, 3, 5)], float) / 255


def to_lin(c):
    c = np.asarray(c, float)
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def to_srgb(c):
    c = np.clip(c, 0, 1)
    return np.where(c <= 0.0031308, 12.92 * c, 1.055 * c ** (1 / 2.4) - 0.055)


def nrm(v):
    v = np.array(v, float)
    return v / np.linalg.norm(v)


def load_mesh():
    V, F = [], []
    for line in OBJ.read_text().splitlines():
        if line.startswith("v "):
            V.append([float(x) for x in line.split()[1:4]])
        elif line.startswith("f "):
            F.append([int(t.split("/")[0]) - 1 for t in line.split()[1:4]])
    return np.array(V), np.array(F)


def mask_from(draw_fn, blur=0.0):
    im = Image.new("L", (W2, H2), 0)
    draw_fn(ImageDraw.Draw(im))
    a = np.asarray(im, float) / 255
    return gaussian_filter(a, blur) if blur else a


def poly(pts, blur=0.0):
    return mask_from(lambda d: d.polygon([tuple(map(float, p)) for p in pts], fill=255), blur)


def line(pts, width, blur=0.0):
    return mask_from(lambda d: d.line([tuple(map(float, p)) for p in pts], fill=255, width=max(1, int(round(width))), joint="curve"), blur)


def gauss2(xx, yy, cx, cy, rx, ry=None):
    ry = rx if ry is None else ry
    return np.exp(-(((xx - cx) / rx) ** 2 + ((yy - cy) / ry) ** 2) / 2)


def over(img, col, a):
    """alpha-composite a colour (H,W,3 or 3) over img with alpha a (H,W)."""
    a = np.clip(a, 0, 1)[..., None]
    return img * (1 - a) + col * a


def smooth_curve(pts, n=60):
    """Catmull-Rom through pts -> n points."""
    pts = np.asarray(pts, float)
    p = np.vstack([pts[0], pts, pts[-1]])
    out = []
    for i in range(1, len(p) - 2):
        for t in np.linspace(0, 1, max(2, n // (len(pts) - 1)), endpoint=False):
            t2, t3 = t * t, t * t * t
            out.append(0.5 * ((2 * p[i]) + (-p[i - 1] + p[i + 1]) * t + (2 * p[i - 1] - 5 * p[i] + 4 * p[i + 1] - p[i + 2]) * t2
                              + (-p[i - 1] + 3 * p[i] - 3 * p[i + 1] + p[i + 2]) * t3))
    out.append(pts[-1])
    return np.array(out)


# ---------------------------------------------------------------- mesh shaping
def shape_mesh(V, sh):
    V = V.copy()
    for eye in (EYE_R, EYE_L):
        idx = eye["up"] + eye["lo"]
        ec = V[idx].mean(0)
        w = np.exp(-((V[:, 0] - ec[0]) ** 2 / (2 * 1.6 ** 2) + (V[:, 1] - ec[1]) ** 2 / (2 * 0.9 ** 2)))
        V[:, 1] = ec[1] + (V[:, 1] - ec[1]) * (1 + sh["eye_open"] * w)
        k = 1 + (sh["eye"] - 1) * w
        V[:, 0] = ec[0] + (V[:, 0] - ec[0]) * k
        V[:, 1] = ec[1] + (V[:, 1] - ec[1]) * k
    brow = np.exp(-((V[:, 1] - 4.6) ** 2) / 1.2) * (np.abs(V[:, 0]) > 1.2)
    V[:, 1] += sh["brow"] * brow
    V[:, 0] *= sh["width"]
    jawk = np.clip((-V[:, 1] - 3.5) / 5.0, 0, 1)
    V[:, 0] *= 1 + (sh["jaw"] - 1) * jawk
    cheek = np.exp(-((V[:, 1] + 1.2) ** 2) / 8)
    V[:, 0] *= 1 + (sh["cheek"] - 1) * cheek
    mouth = V[[13, 14]].mean(0)
    below = V[:, 1] < mouth[1]
    V[below, 1] = mouth[1] + (V[below, 1] - mouth[1]) * sh["chin"]
    nose = np.exp(-(V[:, 0] ** 2) / 3.0 - ((V[:, 1] + 1.2) ** 2) / 4.0)
    V[:, 0] *= 1 + (sh["nose"] - 1) * nose
    lipz = np.exp(-((V[:, 0] - mouth[0]) ** 2 / 9 + (V[:, 1] - mouth[1]) ** 2 / 1.2))
    V[:, 1] = mouth[1] + (V[:, 1] - mouth[1]) * (1 + (sh["lips"] - 1) * lipz)
    V[:, 0] = mouth[0] + (V[:, 0] - mouth[0]) * (1 + (sh["mouth"] - 1) * lipz)
    return V


def raster(P2, Vz, F, vn):
    zbuf = np.full((H2, W2), -1e9)
    N = np.zeros((H2, W2, 3))
    M = np.zeros((H2, W2))
    for f in F:
        p = P2[f]
        x0, y0 = np.floor(p.min(0)).astype(int)
        x1, y1 = np.ceil(p.max(0)).astype(int)
        x0, y0, x1, y1 = max(x0, 0), max(y0, 0), min(x1, W2 - 1), min(y1, H2 - 1)
        if x1 < x0 or y1 < y0:
            continue
        gy, gx = np.mgrid[y0:y1 + 1, x0:x1 + 1].astype(float)
        d = (p[1, 1] - p[2, 1]) * (p[0, 0] - p[2, 0]) + (p[2, 0] - p[1, 0]) * (p[0, 1] - p[2, 1])
        if abs(d) < 1e-9:
            continue
        w0 = ((p[1, 1] - p[2, 1]) * (gx - p[2, 0]) + (p[2, 0] - p[1, 0]) * (gy - p[2, 1])) / d
        w1 = ((p[2, 1] - p[0, 1]) * (gx - p[2, 0]) + (p[0, 0] - p[2, 0]) * (gy - p[2, 1])) / d
        w2 = 1 - w0 - w1
        inside = (w0 >= -1e-6) & (w1 >= -1e-6) & (w2 >= -1e-6)
        if not inside.any():
            continue
        z = w0 * Vz[f[0]] + w1 * Vz[f[1]] + w2 * Vz[f[2]]
        sub = zbuf[y0:y1 + 1, x0:x1 + 1]
        upd = inside & (z > sub)
        sub[upd] = z[upd]
        n = w0[..., None] * vn[f[0]] + w1[..., None] * vn[f[1]] + w2[..., None] * vn[f[2]]
        N[y0:y1 + 1, x0:x1 + 1][upd] = n[upd]
        M[y0:y1 + 1, x0:x1 + 1][upd] = 1
    N /= np.linalg.norm(N, axis=2, keepdims=True) + 1e-9
    return N, zbuf, M


# ---------------------------------------------------------------- hair
def strands(layer, rng, curves, col, n_alpha=(26, 70), width=(1, 3), jitter=0.12):
    """draw many soft strands; curves: list of control-point arrays"""
    d = ImageDraw.Draw(layer, "RGBA")
    base = np.asarray(col)
    for c in curves:
        pts = smooth_curve(c, n=40)
        k = rng.uniform(1 - jitter * 2.5, 1 + jitter * 4)
        rgb = tuple(int(v) for v in np.clip(base * k * 255, 0, 255))
        a = int(rng.uniform(*n_alpha))
        d.line([tuple(p) for p in pts], fill=rgb + (a,), width=int(rng.integers(width[0], width[1] + 1)), joint="curve")


def hair_layer(f, rng, geo):
    """returns (back_rgb, back_a, front_rgb, front_a) in linear RGB"""
    hcx, hcy, hrx, hry, hairline, P2, fw = geo["hcx"], geo["hcy"], geo["hrx"], geo["hry"], geo["hairline"], geo["P2"], geo["fw"]
    col = hex_rgb(f["hair_col"])
    style = f["hair"]
    top = hcy - hry * 1.07
    back = Image.new("L", (W2, H2), 0)
    front = Image.new("L", (W2, H2), 0)
    bd, fd = ImageDraw.Draw(back), ImageDraw.Draw(front)
    arc = lambda rx, ry, a0, a1, n=50, cy=hcy: [(hcx + rx * math.cos(t), cy - ry * math.sin(t)) for t in np.linspace(a0, a1, n)]
    part = hcx + hrx * {"wavy": 0.22, "straight": 0.0, "short": -0.3, "bun": 0.0, "curly": 0.1}.get(style, 0)
    hl = list(hairline)
    curves_back, curves_front = [], []
    if style in ("straight", "wavy"):
        wide = 1.5 if style == "wavy" else 1.34
        drop = H2 * (0.98 if style == "straight" else 0.9)
        wv = (lambda y: math.sin(y / (hry * 0.16)) * hrx * 0.07) if style == "wavy" else (lambda y: 0.0)
        right = [(hcx + hrx * 1.14, hcy - hry * 0.35), (hcx + hrx * (1.12 + (wide - 1.3) * 0.5), hcy + hry * 0.25),
                 (hcx + hrx * (wide - 0.05), hcy + hry * 1.0), (hcx + hrx * wide, drop - hry * 0.3), (hcx + hrx * (wide - 0.12), drop)]
        right = [(x + wv(y), y) for x, y in right]
        left = [(2 * hcx - x, y) for x, y in right][::-1]
        top_arc = arc(hrx * 1.18, hry * 1.14, math.pi * 0.95, math.pi * 0.05, 30)
        outline = smooth_curve(left + top_arc + right, 160)
        ends = [(hcx + hrx * (wide - 0.12) - k * (2 * hrx * (wide - 0.12)) / 16, drop + (hry * 0.05 if k % 2 else 0)) for k in range(17)]
        bd.polygon([tuple(p) for p in outline] + ends, fill=255)
        fd.polygon(hl + arc(hrx * 1.17, hry * 1.12, -0.05, math.pi * 1.05), fill=255)
        for sd in (-1, 1):       # curtains framing the face, over the shoulders
            c = [(hcx + sd * hrx * 0.97, P2[234, 1] - hry * 0.55), (hcx + sd * hrx * 1.12, P2[234, 1]), (hcx + sd * hrx * 1.18, P2[152, 1]),
                 (hcx + sd * hrx * (wide - 0.1), drop), (hcx + sd * hrx * 0.95, drop), (hcx + sd * hrx * 0.98, P2[152, 1] + hry * 0.15),
                 (hcx + sd * hrx * 0.9, P2[234, 1] + hry * 0.2)]
            c = [(x + wv(y) * 0.7, y) for x, y in c]
            fd.polygon([tuple(p) for p in smooth_curve(c, 60)], fill=255)
        for i in range(1500):
            sd = -1 if i % 2 else 1
            x0 = part + rng.normal(0, hrx * 0.025)
            u = rng.uniform(0, 1)
            ex = hcx + sd * hrx * (0.88 + (wide - 0.9) * u)
            c = [(x0, top + hry * 0.03), (hcx + sd * hrx * (0.5 + 0.5 * u), top + hry * 0.22), (hcx + sd * hrx * (1.02 + 0.12 * u), hcy - hry * 0.25),
                 (ex + wv(hcy + hry * 0.5), hcy + hry * 0.5), (ex + wv(drop) + sd * rng.uniform(0, hrx * 0.08), drop + rng.uniform(0, hry * 0.06))]
            (curves_front if u < 0.5 else curves_back).append(c)
    elif style == "bun":
        fd.polygon(hl + arc(hrx * 1.06, hry * 1.03, -0.03, math.pi * 1.03)[::-1][::-1], fill=255)
        bx, by, br = hcx + hrx * 0.05, top - hry * 0.12, hrx * 0.42
        bd.ellipse([bx - br, by - br * 0.85, bx + br, by + br * 0.85], fill=255)
        for i in range(700):
            side = rng.uniform(-1, 1)
            hx, hy = hl[int(rng.uniform(0, len(hl) - 1))]
            curves_front.append([(hx, hy), (hx + (hcx - hx) * 0.3, hy - hry * 0.35), (hcx + side * hrx * 0.2, top + hry * 0.02)])
        for i in range(260):
            a0 = rng.uniform(0, 2 * math.pi)
            r0 = br * rng.uniform(0.2, 0.95)
            curves_back.append([(bx + r0 * math.cos(a0 + k * 0.6), by + r0 * 0.85 * math.sin(a0 + k * 0.6)) for k in range(5)])
    elif style == "short":
        out = arc(hrx * 1.1, hry * 1.04, math.pi * 1.02, -0.02)
        fd.polygon(hl + out[::-1], fill=255)
        # short sides above the ears
        for side in (-1, 1):
            fd.polygon([(hcx + side * hrx * 0.93, P2[234, 1] - hry * 0.42), (hcx + side * hrx * 1.08, P2[234, 1] - hry * 0.42),
                        (hcx + side * hrx * 1.05, P2[234, 1] - hry * 0.02), (hcx + side * hrx * 0.97, P2[234, 1] + hry * 0.02)], fill=255)
        for i in range(900):
            hx, hy = hl[int(rng.uniform(0, len(hl) - 1))]
            curves_front.append([(hx + rng.normal(0, 4), hy + 4), (hx + (part - hx) * 0.3, hy - hry * 0.3), (part + rng.normal(0, hrx * 0.08), top - hry * 0.02)])
    elif style == "curly":
        bd.ellipse([hcx - hrx * 1.62, top - hry * 0.18, hcx + hrx * 1.62, hcy + hry * 1.18], fill=255)
        fd.polygon(hl + arc(hrx * 1.12, hry * 1.06, -0.05, math.pi * 1.05)[::-1][::-1], fill=255)
        for k in range(160):
            a0 = rng.uniform(-0.15, math.pi * 1.15)
            rr = rng.uniform(1.18, 1.58)
            x, y = hcx + hrx * rr * math.cos(a0), hcy + hry * 0.15 - hry * rr * 0.98 * math.sin(a0)
            rad = rng.uniform(0.09, 0.16) * hrx
            bd.ellipse([x - rad, y - rad, x + rad, y + rad], fill=255)
    elif style == "braid":
        # sleek, pulled back, with one braid over the shoulder
        fd.polygon(hl + arc(hrx * 1.07, hry * 1.04, -0.03, math.pi * 1.03), fill=255)
        for i in range(700):
            hx, hy = hl[int(rng.uniform(0, len(hl) - 1))]
            curves_front.append([(hx, hy), (hx + (hcx - hx) * 0.25, hy - hry * 0.35), (hcx + hrx * rng.uniform(0.3, 0.7), top + hry * 0.25),
                                 (hcx + hrx * 0.95, P2[234, 1] - hry * 0.1)])
        n = 11
        x0, y0 = hcx + hrx * 1.16, P2[152, 1] - hry * 0.2
        x1, y1 = hcx + hrx * 1.3, H2 * 0.97
        # hair swept back behind the ear into the braid
        bd.polygon([(hcx + hrx * 0.9, P2[234, 1] - hry * 0.55), (hcx + hrx * 1.12, P2[234, 1] - hry * 0.3), (x0 + hrx * 0.14, y0),
                    (x0 - hrx * 0.12, y0), (hcx + hrx * 0.98, P2[234, 1] + hry * 0.2)], fill=255)
        for j in range(160):
            curves_back.append([(hcx + hrx * rng.uniform(0.9, 1.08), P2[234, 1] - hry * 0.45), (hcx + hrx * 1.1, P2[234, 1]), (x0 + rng.normal(0, hrx * 0.04), y0)])
        for k in range(n):
            t_ = k / (n - 1)
            bx = x0 + (x1 - x0) * t_ ** 0.8 + (hrx * 0.05 if k % 2 else -hrx * 0.05)
            by = y0 + (y1 - y0) * t_
            rx_, ry_ = hrx * (0.2 - 0.05 * t_), (y1 - y0) / n * 0.75
            fd.ellipse([bx - rx_, by - ry_, bx + rx_, by + ry_], fill=255)
            for j in range(26):
                a0 = rng.uniform(-0.6, 0.6) + (0.5 if k % 2 else -0.5)
                curves_front.append([(bx - rx_ * math.cos(a0), by - ry_ * 0.9), (bx + rx_ * 0.2 * math.sin(a0), by), (bx + rx_ * math.cos(a0), by + ry_ * 0.9)])
    back_a = gaussian_filter(np.asarray(back, float) / 255, 2.6 * SS)
    front_a = gaussian_filter(np.asarray(front, float) / 255, 2.4 * SS)

    # strand texture
    lin_col = to_lin(col)
    tex_b = Image.new("RGBA", (W2, H2), (0, 0, 0, 0))
    tex_f = Image.new("RGBA", (W2, H2), (0, 0, 0, 0))
    light = np.clip(col * 1.9 + 0.06, 0, 1)
    strands(tex_b, rng, curves_back, light, n_alpha=(30, 90), width=(1, 3))
    strands(tex_f, rng, curves_front, light, n_alpha=(34, 100), width=(1, 3))
    if True:
        dd = ImageDraw.Draw(front, None)
        for k in range(160):
            hx, hy = hl[int(rng.uniform(1, len(hl) - 2))]
            dd.line([(hx, hy - 6 * SS), (hx + rng.normal(0, 3) * SS, hy + rng.uniform(2, 7) * SS)], fill=int(rng.uniform(60, 140)), width=SS)
        front_a = np.maximum(front_a, gaussian_filter(np.asarray(front, float) / 255, 0.6 * SS) * 0.6)
    if style == "curly":
        dd = ImageDraw.Draw(tex_b, "RGBA")
        for k in range(2600):
            x = rng.uniform(hcx - hrx * 1.6, hcx + hrx * 1.6)
            y = rng.uniform(top - hry * 0.2, hcy + hry * 1.2)
            r = rng.uniform(4, 11) * SS
            c = tuple(int(v) for v in np.clip(light * rng.uniform(0.5, 1.2) * 255, 0, 255))
            dd.arc([x - r, y - r, x + r, y + r], rng.uniform(0, 360), rng.uniform(0, 360) + rng.uniform(120, 260), fill=c + (int(rng.uniform(30, 90)),), width=SS)
    tb = np.asarray(tex_b, float) / 255
    tf = np.asarray(tex_f, float) / 255
    yy, xx = np.mgrid[0:H2, 0:W2].astype(float)
    # sphere-ish shading over the head, darker low down and at the sides, a soft sheen band on top
    nx = np.clip((xx - hcx) / (hrx * 1.5), -1, 1)
    shade = (0.78 + 0.32 * (1 - np.abs(nx) ** 2)) * (1.05 - 0.35 * np.clip((yy - hcy) / H2 * 2, 0, 1))
    sheen = np.exp(-(((yy - (top + hry * 0.45)) / (hry * 0.12)) ** 2) - ((xx - hcx + hrx * 0.25) / (hrx * 0.7)) ** 2) * 0.10

    def paint(alpha_mask, tex):
        base = lin_col * shade[..., None]
        t = to_lin(tex[..., :3])
        rgb = base * (1 - tex[..., 3:4]) + t * tex[..., 3:4] * shade[..., None]
        rgb = rgb + sheen[..., None] * (0.5 + 2 * lin_col.mean())
        return rgb, alpha_mask
    br, ba = paint(back_a, tb)
    fr, fa = paint(front_a, tf)
    return br, ba, fr, fa


# ---------------------------------------------------------------- render one face
def render(f):
    rng = np.random.default_rng(f["seed"])
    V0, F = load_mesh()
    V = shape_mesh(V0, f["shape"])
    s = 0.39 * W2 / 15.4
    cx, cy = W2 / 2, 0.44 * H2
    P2 = np.stack([cx + s * V[:, 0], cy - s * (V[:, 1] + 0.6)], 1)
    tri = V[F]
    fn = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
    if fn[np.where((F == 1).any(1))[0]][:, 2].mean() < 0:
        fn = -fn
    vn = np.zeros_like(V)
    for k in range(3):
        np.add.at(vn, F[:, k], fn)
    vn /= np.linalg.norm(vn, axis=1, keepdims=True) + 1e-9
    meshN, meshZ, meshM = raster(P2, V[:, 2] * s, F, vn)

    yy, xx = np.mgrid[0:H2, 0:W2].astype(float)
    oval = P2[OVAL]
    hx0, hx1 = oval[:, 0].min(), oval[:, 0].max()
    hcx, hrx = (hx0 + hx1) / 2, (hx1 - hx0) / 2 * 1.04
    hcy = P2[10, 1] + (P2[152, 1] - P2[10, 1]) * 0.42
    hry = (P2[152, 1] - P2[10, 1]) * 0.62
    fw = hx1 - hx0

    # ---- normals: head ellipsoid, neck, ears, then the mesh on top ----
    N = np.zeros((H2, W2, 3))
    N[..., 2] = 1
    skin = np.zeros((H2, W2))
    occl = np.ones((H2, W2))
    male = f["sex"] == "m"
    nw = hrx * (0.78 if male else 0.68)
    ntop = hcy + hry * math.sqrt(max(0.0, 1 - (nw / hrx) ** 2)) - 2 * SS
    neck = (np.abs(xx - hcx) < nw) & (yy > ntop)
    nxn = np.clip((xx - hcx) / nw, -1, 1)
    N[neck] = np.stack([nxn[neck] * 0.85, np.full(neck.sum(), -0.1), np.sqrt(1 - (nxn[neck] * 0.85) ** 2)], 1)
    skin[neck] = 1
    chin_y = P2[152, 1]
    occl = np.where(neck, 0.42 + 0.58 * np.clip((yy - chin_y) / (0.45 * hry), 0, 1) ** 0.8, occl)
    ears = np.zeros((H2, W2))
    if f["hair"] in ("short", "bun", "braid"):
        for sd in (-1, 1):
            ex, ey = hcx + sd * hrx * 0.98, P2[234, 1] + 0.06 * hry
            e = ((xx - ex) / (0.15 * hrx)) ** 2 + ((yy - ey) / (0.27 * hry)) ** 2 < 1
            inner = ((xx - ex - sd * 0.02 * hrx) / (0.08 * hrx)) ** 2 + ((yy - ey) / (0.17 * hry)) ** 2 < 1
            N[e] = np.array([sd * 0.6, 0.0, 0.8])
            skin[e] = 1
            ears[e] = 1
            occl[e] = 0.86
            occl[inner] = 0.66
    dx, dy = (xx - hcx) / hrx, (yy - hcy) / hry
    head = dx * dx + dy * dy < 1
    nz = np.sqrt(np.clip(1 - dx * dx - dy * dy, 0, 1))
    N[head] = np.stack([dx[head], -dy[head], nz[head]], 1)
    skin[head] = 1
    occl[head] = 1
    soft = gaussian_filter(np.asarray(Image.fromarray((meshM * 255).astype(np.uint8)).filter(ImageFilter.MinFilter(9)), float) / 255, 5 * SS)[..., None]
    N = N * (1 - soft) + meshN * soft
    N /= np.linalg.norm(N, axis=2, keepdims=True) + 1e-9
    skin = np.maximum(skin, meshM)

    # ambient occlusion from the mesh depth: concave areas (eye sockets, beside the nose, under the lip) get darker
    zm = np.where(meshM > 0, meshZ, 0)
    sig = 0.03 * fw
    avg = gaussian_filter(zm, sig) / np.maximum(gaussian_filter(meshM, sig), 1e-3)
    conc = np.clip((avg - zm) / (0.035 * fw), 0, 1) * soft[..., 0]
    ao = 1 - 0.5 * conc ** 0.85
    sig2 = 0.008 * fw
    avg2 = gaussian_filter(zm, sig2) / np.maximum(gaussian_filter(meshM, sig2), 1e-3)
    ao *= 1 - 0.35 * np.clip((avg2 - zm) / (0.008 * fw), 0, 1) * soft[..., 0]

    # ---- lighting (same for all faces): soft key from upper left, fill from the right, wrap lighting ----
    L1, L2 = nrm([-0.3, 0.38, 0.87]), nrm([0.45, 0.05, 0.89])
    wrap = lambda d, w: np.clip((d + w) / (1 + w), 0, 1)
    def light_of(Nv):
        return 0.30 + 0.06 * Nv[..., 1] + 0.56 * wrap(Nv @ L1, 0.25) + 0.20 * wrap(Nv @ L2, 0.3)
    EXP = np.array([0.88, 1.0, 1.12])          # warmer shadows (light scattering under the skin)
    f0 = light_of(np.array([0.0, 0.0, 1.0])) ** EXP
    base_lin = to_lin(hex_rgb(f["hex"]))
    alb_base = np.clip(base_lin / f0, 0, 1)     # so a front-lit cheek renders at the given mid-tone

    # ---- albedo: base + natural variation ----
    alb = np.ones((H2, W2, 3)) * alb_base
    light_skin = max(0.0, (6 - f["monk"]) / 4)
    red = alb_base * np.array([1.07, 0.9, 0.9])
    for c in (205, 425):
        alb = over(alb, red, gauss2(xx, yy, P2[c, 0], P2[c, 1], 0.1 * fw) * (0.25 + 0.3 * light_skin))
    alb = over(alb, red, gauss2(xx, yy, P2[4, 0], P2[4, 1], 0.06 * fw) * (0.2 + 0.25 * light_skin))
    peri = alb_base * np.array([0.82, 0.78, 0.84])
    for up, lo in ((EYE_R["up"], EYE_R["lo"]), (EYE_L["up"], EYE_L["lo"])):
        ecx = P2[up + lo][:, 0].mean()
        alb = over(alb, peri, gauss2(xx, yy, ecx, P2[lo][:, 1].max() + 0.03 * fw, 0.075 * fw, 0.035 * fw) * 0.55)
        alb = over(alb, alb_base * 0.9, gauss2(xx, yy, ecx, P2[up][:, 1].min() - 0.02 * fw, 0.08 * fw, 0.03 * fw) * 0.4)
    for c in (61, 291):
        alb = over(alb, alb_base * np.array([0.88, 0.85, 0.85]), gauss2(xx, yy, P2[c, 0], P2[c, 1], 0.035 * fw) * 0.5)
    alb = over(alb, alb_base * np.array([0.93, 0.92, 0.92]), neck.astype(float) * 0.6)
    alb = over(alb, red * 0.95, ears * 0.5)

    # lips: darker and redder than the skin, deeper skin has deeper, cooler lips
    t = (f["monk"] - 3) / 6
    lipf = np.array([0.82, 0.56, 0.58]) * (1 - t) + np.array([0.74, 0.58, 0.64]) * t
    lip_col = alb_base * lipf * (1 - 0.18 * t)
    lipm = poly(P2[LIPS_OUT], blur=1.6 * SS)
    upm = poly(P2[LIPS_UP], blur=1.0 * SS)
    lipcol = np.ones((H2, W2, 3)) * lip_col * (1 - 0.13 * upm[..., None])
    lines_ = 1 + 0.06 * gaussian_filter(np.sin(xx / (0.006 * fw)) * rng.uniform(0.6, 1, (H2, W2)), [3 * SS, 0.6 * SS])
    alb = over(alb, lipcol * lines_[..., None], lipm * 0.94)

    # brows: hair strokes
    hair_lin = to_lin(hex_rgb(f["hair_col"]))
    brow_img = Image.new("L", (W2, H2), 0)
    bdraw = ImageDraw.Draw(brow_img)
    thick = 1.25 if male else 1.0
    for b, sd in ((BROW_R, -1), (BROW_L, 1)):
        up, lo = P2[b["up"]], P2[b["lo"]]
        mid = (up + lo) / 2
        mid[:, 1] = mid[:, 1] * 1.0
        inner = mid[-1] if abs(mid[-1, 0] - hcx) < abs(mid[0, 0] - hcx) else mid[0]
        for k in range(int(420 * thick)):
            u = rng.uniform(0, 1)
            i = u * (len(mid) - 1)
            j = int(min(i, len(mid) - 2))
            fr = i - j
            pu = up[j] * (1 - fr) + up[j + 1] * fr
            pl = lo[j] * (1 - fr) + lo[j + 1] * fr
            v = rng.uniform(-0.1, 1.05) * thick
            p = pl + (pu - pl) * min(v, 1.1)
            dist_in = np.linalg.norm(p - inner) / (np.linalg.norm(mid[0] - mid[-1]) + 1e-6)
            ang = (math.radians(-70) if dist_in < 0.25 else math.radians(-25)) if sd > 0 else (math.radians(-110) if dist_in < 0.25 else math.radians(-155))
            ln = rng.uniform(0.018, 0.034) * fw
            q = (p[0] + ln * math.cos(ang), p[1] + ln * math.sin(ang))
            bdraw.line([tuple(p), q], fill=int(rng.uniform(120, 230)), width=SS)
    brow = gaussian_filter(np.asarray(brow_img, float) / 255, 0.6 * SS)
    alb = over(alb, hair_lin * 1.1, brow * 0.85)

    # skin texture: soft mottling, mid detail and pores, strongest on the nose and cheeks
    def noise(sig, amp):
        n = gaussian_filter(rng.normal(0, 1, (H2, W2)), sig)
        return n / (n.std() + 1e-9) * amp
    pore_map = 0.5 + 0.9 * (gauss2(xx, yy, P2[4, 0], P2[4, 1], 0.12 * fw) + gauss2(xx, yy, P2[205, 0], P2[205, 1], 0.1 * fw) + gauss2(xx, yy, P2[425, 0], P2[425, 1], 0.1 * fw))
    texture = 1 + noise(22 * SS, 0.022) + noise(3 * SS, 0.012) + noise(0.7 * SS, 0.016 - 0.007 * (f["monk"] - 3) / 6) * pore_map
    hue = noise(14 * SS, 0.012)
    alb = alb * texture[..., None]
    alb[..., 0] *= 1 + hue
    alb = np.clip(alb, 0, 1)

    # ---- shading ----
    lt = light_of(N) * occl * ao
    lt = gaussian_filter(lt, 0.7 * SS)
    sss = np.stack([lt ** EXP[0], lt ** EXP[1], lt ** EXP[2]], -1)
    Hh = nrm(L1 + np.array([0, 0, 1]))
    tzone = 0.6 + gauss2(xx, yy, P2[6, 0], P2[6, 1], 0.06 * fw, 0.25 * fw) + 0.6 * gauss2(xx, yy, P2[151, 0], P2[151, 1], 0.18 * fw, 0.08 * fw)
    spec = (0.035 * np.clip(N @ Hh, 0, 1) ** 18 * tzone * (1 + noise(1.2 * SS, 0.18))) * (0.6 + 0.6 * (f["monk"] / 9))
    spec += 0.08 * np.clip(N @ Hh, 0, 1) ** 40 * gauss2(xx, yy, P2[14, 0], P2[14, 1] + 0.01 * fw, 0.05 * fw, 0.012 * fw)   # lower-lip highlight
    skin_rgb = alb * sss + spec[..., None]

    # ---- background, clothes, hair ----
    tb = (yy / H2)[..., None]
    img = to_lin(hex_rgb(BG[0])) * (1 - tb) + to_lin(hex_rgb(BG[1])) * tb
    img = img * (1 - 0.1 * (((xx - W2 / 2) / W2) ** 2 + ((yy - H2 * 0.45) / H2) ** 2))[..., None]
    side_pts = [127, 162, 21, 54, 103, 67, 109, 10, 338, 297, 332, 284, 251, 389, 356]
    brow_y = P2[[105, 334]][:, 1].mean()
    ctrl = []
    for i in side_pts:             # follow the forehead's arch, a fixed distance below the mesh edge
        x, y = P2[i]
        c = max(0.0, 1 - abs(x - hcx) / (0.62 * fw))
        ctrl.append((x + (hcx - x) * 0.04, y + (0.035 if male else 0.045) * fw - (0.07 if male else 0.085) * fw * c ** 1.6))
    hairline = [tuple(p) for p in smooth_curve(ctrl, 60)]
    geo = dict(hcx=hcx, hcy=hcy, hrx=hrx, hry=hry, hairline=hairline, P2=P2, fw=fw)

    hb_rgb, hb_a, hf_rgb, hf_a = hair_layer(f, rng, geo)
    img = img * (1 - hb_a[..., None]) + hb_rgb * hb_a[..., None]

    # clothes: shoulders with a neckline (a collar for the man)
    sy = chin_y + hry * 0.42
    cl = mask_from(lambda d: (d.rounded_rectangle([hcx - hrx * 2.6, sy, hcx + hrx * 2.6, H2 + 300], radius=int(hrx * 1.2), fill=255),
                              d.ellipse([hcx - nw * 1.3, sy - nw * 0.9, hcx + nw * 1.3, sy + nw * (0.55 if male else 0.85)], fill=0)), 1.2 * SS)
    cloth = to_lin(hex_rgb(f["cloth"]))
    cshade = 0.72 + 0.28 * np.clip(1 - np.abs(xx - hcx) / (hrx * 2.8), 0, 1) - 0.1 * np.clip((yy - sy) / H2, 0, 1)
    cfold = 1 + 0.05 * gaussian_filter(np.sin((xx - hcx) / (hrx * 0.22) + yy / (hry * 0.9)), 4 * SS)
    sk = gaussian_filter(skin, 1.0 * SS)[..., None]
    img = img * (1 - sk) + skin_rgb * sk
    img = over(img, cloth * (cshade * cfold)[..., None], cl)
    if male:
        for sd in (-1, 1):
            col_m = poly([(hcx + sd * nw * 0.15, sy + nw * 0.55), (hcx + sd * nw * 1.25, sy - nw * 0.25), (hcx + sd * nw * 1.55, sy + nw * 0.05),
                          (hcx + sd * nw * 0.6, sy + nw * 0.95)], blur=1.0 * SS)
            img = over(img, cloth * 1.04, col_m)
            img = img * (1 - 0.18 * gaussian_filter(line([(hcx + sd * nw * 0.15, sy + nw * 0.55), (hcx + sd * nw * 1.25, sy - nw * 0.25)], 2 * SS), 2 * SS))[..., None]

    # ---- eyes ----
    iris_pts = []
    for eye in (EYE_R, EYE_L):
        up, lo = P2[eye["up"]], P2[eye["lo"]]
        polyp = np.concatenate([up, lo[::-1][1:-1]])
        em = poly(polyp, blur=0.7 * SS)
        ew = np.linalg.norm(up[-1] - up[0])
        ecx = (up[:, 0].mean() + lo[:, 0].mean()) / 2
        top_y, bot_y = up[:, 1].min(), lo[:, 1].max()
        eh = bot_y - top_y
        icx, icy = ecx, top_y + eh * 0.56
        r = min(0.24 * ew, 0.72 * eh)
        d = np.sqrt((xx - icx) ** 2 + (yy - icy) ** 2)
        ang = np.arctan2(yy - icy, xx - icx)
        inner_c = up[-1] if abs(up[-1, 0] - hcx) < abs(up[0, 0] - hcx) else up[0]
        sclera = to_lin(hex_rgb("#ece3dc")) * (0.62 + 0.38 * np.clip(1 - np.abs(xx - ecx) / (0.62 * ew), 0, 1))[..., None]
        sclera = over(sclera, to_lin(hex_rgb("#c98f8a")), gauss2(xx, yy, inner_c[0], inner_c[1], 0.07 * ew) * 0.6)
        icol = to_lin(hex_rgb(f["eyes"]))
        fib = 1 + 0.25 * np.sin(ang * 46 + rng.uniform(0, 6)) * np.clip(d / r, 0, 1) + 0.12 * np.sin(ang * 17)
        iris_rgb = icol * (1.35 - 0.6 * np.clip(d / r, 0, 1) ** 2)[..., None] * fib[..., None]
        iris_rgb = over(iris_rgb, icol * 0.35, np.clip((d / r - 0.86) / 0.14, 0, 1))        # limbal ring
        ia = np.clip((r - d) / (0.7 * SS), 0, 1)
        pa = np.clip((0.4 * r - d) / (0.6 * SS), 0, 1)
        eye_rgb = over(sclera, iris_rgb, ia)
        eye_rgb = over(eye_rgb, to_lin(hex_rgb("#070505")), pa)
        lid = np.clip((yy - top_y) / (0.55 * eh), 0, 1)
        eye_rgb = eye_rgb * (0.45 + 0.55 * lid)[..., None]
        eye_rgb = over(eye_rgb, np.array([1.0, 0.98, 0.96]), gauss2(xx, yy, icx - 0.32 * r, icy - 0.36 * r, 0.11 * r) * 0.95)
        eye_rgb = over(eye_rgb, np.array([0.8, 0.8, 0.82]), gauss2(xx, yy, icx + 0.35 * r, icy + 0.3 * r, 0.06 * r) * 0.4)
        img = over(img, eye_rgb, em)
        # lash line, lashes, crease, lower lid
        lw = (0.05 if male else 0.07) * ew
        img = over(img, to_lin(hex_rgb("#0b0807")), line(up, lw, blur=0.6 * SS) * 0.95)
        lash = Image.new("L", (W2, H2), 0)
        ld = ImageDraw.Draw(lash)
        outer_c = up[0] if abs(up[0, 0] - hcx) > abs(up[-1, 0] - hcx) else up[-1]
        upc = smooth_curve(up, 40)
        for k in range(0 if male else 70):
            q = upc[int(rng.uniform(2, len(upc) - 2))]
            tt = abs(q[0] - inner_c[0]) / (abs(outer_c[0] - inner_c[0]) + 1e-6)
            out_dir = np.sign(outer_c[0] - inner_c[0])
            ln = (0.07 + 0.09 * tt) * ew
            a = math.radians(-90 + out_dir * (15 + 50 * tt))
            ld.line([tuple(q), (q[0] + ln * math.cos(a), q[1] + ln * math.sin(a))], fill=int(rng.uniform(150, 240)), width=SS)
        img = over(img, to_lin(hex_rgb("#0b0807")), gaussian_filter(np.asarray(lash, float) / 255, 0.5 * SS) * 0.9)
        crease = line(up - np.array([0, 0.36 * eh]), 0.05 * ew, blur=2.4 * SS)
        img = img * (1 - 0.3 * crease)[..., None]
        img = img * (1 - 0.35 * line(lo, 0.03 * ew, blur=0.8 * SS))[..., None]
        img = over(img, to_lin(hex_rgb("#7a4a40")), line(lo, 0.015 * ew, blur=0.6 * SS) * 0.25)
        iris_pts.append((icx, icy, r))

    # nostrils and mouth line
    for alar in (98, 327):
        nx_ = P2[alar, 0] * 0.58 + P2[2, 0] * 0.42
        ny_ = P2[alar, 1] * 0.42 + P2[2, 1] * 0.58
        nm = mask_from(lambda d: d.ellipse([nx_ - 0.03 * fw, ny_ - 0.013 * fw, nx_ + 0.03 * fw, ny_ + 0.013 * fw], fill=255), 1.4 * SS)
        img = img * (1 - 0.62 * nm)[..., None]
    ml = line(smooth_curve(P2[LIP_LINE], 40), 0.006 * fw + SS, blur=0.9 * SS)
    img = img * (1 - 0.6 * ml)[..., None]

    # stubble for the man: fine dark dots on the jaw, chin and upper lip
    if male:
        jaw = [P2[i] for i in (234, 93, 132, 58, 172, 136, 150, 149, 176, 148, 152, 377, 400, 378, 379, 365, 397, 288, 361, 323, 454)]
        top_line = [(P2[454, 0], P2[454, 1] + 0.08 * fw), (P2[425, 0], P2[2, 1] + 0.06 * fw), (P2[2, 0], P2[2, 1] + 0.005 * fw),
                    (P2[205, 0], P2[2, 1] + 0.06 * fw), (P2[234, 0], P2[234, 1] + 0.08 * fw)]
        beard = poly(jaw + top_line, blur=6 * SS) * (1 - poly(P2[LIPS_OUT], blur=1.5 * SS))
        dots = (rng.random((H2, W2)) < 0.12).astype(float)
        dots = gaussian_filter(dots, 0.5 * SS) * 3
        img = img * (1 - 0.1 * beard)[..., None]
        img = over(img, hair_lin, np.clip(dots, 0, 1) * beard * 0.4)

    # hair over the forehead edge
    shadow = np.clip(gaussian_filter(hf_a, 4 * SS) - hf_a, 0, 1)
    img = img * (1 - 0.4 * shadow * skin)[..., None]
    img = img * (1 - hf_a[..., None]) + hf_rgb * hf_a[..., None]

    # a touch of film grain so it doesn't look airbrushed
    img = img * (1 + gaussian_filter(rng.normal(0, 0.012, (H2, W2)), 0.5))[..., None]
    out = (to_srgb(img) * 255 + 0.5).astype(np.uint8)
    pic = Image.fromarray(out).resize((W, H), Image.LANCZOS)

    pts = (P2 / np.array([W2, H2])).tolist()
    for (icx, icy, r) in iris_pts:
        ring = [(icx, icy), (icx + r, icy), (icx, icy - r), (icx - r, icy), (icx, icy + r)]
        pts += [[x / W2, y / H2] for x, y in ring]
    return pic, [[round(x, 4), round(y, 4)] for x, y in pts]


def main(only=None):
    OUT.mkdir(parents=True, exist_ok=True)
    meta, lms = [], {}
    for f in FACES:
        if only and f["id"] not in only:
            continue
        pic, lm = render(f)
        pic.save(OUT / f"{f['id']}.jpg", quality=88, optimize=True, progressive=True)
        meta.append({"id": f["id"], "label": f["label"], "hex": f["hex"], "monk": f["monk"], "undertone": f["undertone"],
                     "file": f"data/model_faces/{f['id']}.jpg"})
        lms[f["id"]] = lm
        print(f"{f['id']}: {f['label']}, Monk ~{f['monk']}, {len(lm)} landmarks")
    if only:
        return
    (ROOT / "data" / "model_faces.json").write_text(json.dumps({
        "source": "Rendered by tools/tryon/make_faces.py from MediaPipe's canonical face mesh (Apache-2.0). "
                  "No photographs of real people; no face is based on a real person.",
        "size": [W, H], "faces": meta}, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    (ROOT / "data" / "model_faces_landmarks.json").write_text(json.dumps(lms, separators=(",", ":")))


if __name__ == "__main__":
    import sys
    main(set(sys.argv[1:]) or None)
