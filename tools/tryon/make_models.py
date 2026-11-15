#!/usr/bin/env python3
"""Render the illustrated try-on model faces and their face landmarks.

    python3 tools/tryon/make_models.py

No photographs of real people are used. Each face is drawn from MediaPipe's
canonical face mesh (tools/tryon/canonical_face_model.obj, Apache-2.0, see
MEDIAPIPE_LICENSE), shaded with a simple light model and painted with eyes,
brows, lips and hair. Because the faces are generated from the mesh, the exact
478 MediaPipe landmark positions are known and shipped with each image, so the
model faces work offline with no face tracking at all.

Writes data/tryon_models/<id>.jpg and data/tryon_models.json. Needs numpy and
Pillow. Output is deterministic (fixed seeds).
"""
import json
import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parents[2]
OBJ = Path(__file__).with_name("canonical_face_model.obj")
OUT = ROOT / "data" / "tryon_models"
W, H, SS = 600, 750, 2          # output size and supersampling
W2, H2 = W * SS, H * SS

# Monk 1-10 swatches (same values as MONK_HEX in src/engine.js)
MONK = {1: "#f6ede4", 2: "#f3e7db", 3: "#f7ead0", 4: "#eadaba", 5: "#d7bd96",
        6: "#a07e56", 7: "#825c43", 8: "#604134", 9: "#3a312a", 10: "#292420"}

MODELS = [
    dict(id="ira", name="Ira", tone=2, undertone="neutral", seed=11, yaw=-3, width=0.98, jaw=0.97, lips=1.00,
         hair="#2a1b14", style="long", bg=("#efe6df", "#d9cfc8"), cloth="#7d8a9a", eyes="#4a3222", tint=(1.0, 0.985, 0.985)),
    dict(id="meher", name="Meher", tone=5, undertone="warm", seed=23, yaw=2, width=1.0, jaw=1.0, lips=1.06,
         hair="#17110d", style="bun", bg=("#ece3d6", "#d3c6b4"), cloth="#a5584a", eyes="#3a2416", tint=(1.0, 0.99, 0.96)),
    dict(id="tara", name="Tara", tone=7, undertone="olive", seed=37, yaw=-2, width=1.02, jaw=1.02, lips=1.08,
         hair="#120d0a", style="short", bg=("#e4e8e6", "#c6cdca"), cloth="#2f5d55", eyes="#2c1a10", tint=(0.985, 1.0, 0.97)),
    dict(id="zoya", name="Zoya", tone=9, undertone="warm", seed=41, yaw=3, width=1.01, jaw=0.99, lips=1.12,
         hair="#0c0907", style="curly", bg=("#eee6dc", "#cfc2b2"), cloth="#c9a24a", eyes="#22150c", tint=(1.0, 0.985, 0.97)),
]

# MediaPipe face-mesh contours used for painting (same indices as src/tryon.js)
OVAL = [10, 338, 297, 332, 284, 251, 389, 356, 454, 323, 361, 288, 397, 365, 379, 378, 400, 377, 152, 148, 176, 149, 150,
        136, 172, 58, 132, 93, 234, 127, 162, 21, 54, 103, 67, 109]
LIPS_OUT = [61, 146, 91, 181, 84, 17, 314, 405, 321, 375, 291, 409, 270, 269, 267, 0, 37, 39, 40, 185]
LIPS_IN_UP = [78, 191, 80, 81, 82, 13, 312, 311, 310, 415, 308]
EYE_R = dict(up=[33, 246, 161, 160, 159, 158, 157, 173, 133], lo=[33, 7, 163, 144, 145, 153, 154, 155, 133])
EYE_L = dict(up=[263, 466, 388, 387, 386, 385, 384, 398, 362], lo=[263, 249, 390, 373, 374, 380, 381, 382, 362])
BROW_R = [70, 63, 105, 66, 107, 55, 65, 52, 53, 46]
BROW_L = [300, 293, 334, 296, 336, 285, 295, 282, 283, 276]


def hex_rgb(h):
    return np.array([int(h[i:i + 2], 16) for i in (1, 3, 5)], float) / 255


def to_lin(c):
    c = np.asarray(c, float)
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def to_srgb(c):
    c = np.clip(c, 0, 1)
    return np.where(c <= 0.0031308, 12.92 * c, 1.055 * c ** (1 / 2.4) - 0.055)


def load_mesh():
    V, F = [], []
    for line in OBJ.read_text().splitlines():
        if line.startswith("v "):
            V.append([float(x) for x in line.split()[1:4]])
        elif line.startswith("f "):
            F.append([int(t.split("/")[0]) - 1 for t in line.split()[1:4]])
    return np.array(V), np.array(F)


def gauss(xx, yy, cx, cy, r):
    return np.exp(-((xx - cx) ** 2 + (yy - cy) ** 2) / (2 * r * r))


def poly_mask(pts, blur=0):
    im = Image.new("L", (W2, H2), 0)
    ImageDraw.Draw(im).polygon([tuple(p) for p in pts], fill=255)
    if blur:
        im = im.filter(ImageFilter.GaussianBlur(blur))
    return np.asarray(im, float) / 255


def line_mask(pts, width, blur=0):
    im = Image.new("L", (W2, H2), 0)
    ImageDraw.Draw(im).line([tuple(p) for p in pts], fill=255, width=int(width), joint="curve")
    if blur:
        im = im.filter(ImageFilter.GaussianBlur(blur))
    return np.asarray(im, float) / 255


def ellipse_mask(cx, cy, rx, ry, blur=0):
    im = Image.new("L", (W2, H2), 0)
    ImageDraw.Draw(im).ellipse([cx - rx, cy - ry, cx + rx, cy + ry], fill=255)
    if blur:
        im = im.filter(ImageFilter.GaussianBlur(blur))
    return np.asarray(im, float) / 255


def render(m):
    rng = np.random.default_rng(m["seed"])
    V, F = load_mesh()
    V = V.copy()
    # gentle per-model shape changes
    V[:, 0] *= m["width"]
    jawk = np.clip((-V[:, 1] - 4.0) / 5.0, 0, 1)
    V[:, 0] *= 1 + (m["jaw"] - 1) * jawk
    mouth = V[[13, 14]].mean(0)
    lipz = np.exp(-((V[:, 0] - mouth[0]) ** 2 / 9 + (V[:, 1] - mouth[1]) ** 2 / 1.2))
    V[:, 1] = mouth[1] + (V[:, 1] - mouth[1]) * (1 + (m["lips"] - 1) * lipz)
    for eye in (EYE_R, EYE_L):       # open the eyes a little (the canonical mesh is nearly closed there)
        idx = eye["up"] + eye["lo"]
        ec = V[idx].mean(0)
        w = np.exp(-((V[:, 0] - ec[0]) ** 2 / (2 * 1.6 ** 2) + (V[:, 1] - ec[1]) ** 2 / (2 * 0.9 ** 2)))
        V[:, 1] = ec[1] + (V[:, 1] - ec[1]) * (1 + 0.75 * w)
    a = math.radians(m["yaw"])
    R = np.array([[math.cos(a), 0, math.sin(a)], [0, 1, 0], [-math.sin(a), 0, math.cos(a)]])
    V = V @ R.T

    s = 0.44 * W2 / 15.4
    cx, cy = W2 / 2, 0.47 * H2
    P2 = np.stack([cx + s * V[:, 0], cy - s * (V[:, 1] + 0.6)], 1)

    # vertex normals, oriented towards the viewer
    tri = V[F]
    fn = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
    if fn[np.where((F == 1).any(1))[0]][:, 2].mean() < 0:
        fn = -fn
    vn = np.zeros_like(V)
    for k in range(3):
        np.add.at(vn, F[:, k], fn)
    vn /= np.linalg.norm(vn, axis=1, keepdims=True) + 1e-9

    # ---- head, neck and mesh normals in one normal map ----
    yy, xx = np.mgrid[0:H2, 0:W2].astype(float)
    N = np.zeros((H2, W2, 3))
    skinA = np.zeros((H2, W2))                  # where skin is
    occl = np.ones((H2, W2))                    # ambient occlusion

    oval = P2[OVAL]
    hx0, hx1 = oval[:, 0].min(), oval[:, 0].max()
    hcx = (hx0 + hx1) / 2
    hrx = (hx1 - hx0) / 2 * 1.04
    hcy = P2[10, 1] + (P2[152, 1] - P2[10, 1]) * 0.42
    hry = (P2[152, 1] - P2[10, 1]) * 0.62
    # neck
    nw = hrx * 0.7
    ntop = hcy + hry * math.sqrt(1 - (nw / hrx) ** 2) - 2 * SS   # neck meets the jaw line with no step
    neck = (np.abs(xx - hcx) < nw) & (yy > ntop)
    nxn = np.clip((xx - hcx) / nw, -1, 1)
    N[neck] = np.stack([nxn[neck] * 0.9, np.full(neck.sum(), -0.05), np.sqrt(1 - (nxn[neck] * 0.9) ** 2)], 1)
    skinA[neck] = 1
    chin_y = P2[152, 1]
    occl = np.where(neck, 0.5 + 0.5 * np.clip((yy - chin_y) / (0.35 * hry), 0, 1) ** 0.7, occl)
    # ears
    for side in (-1, 1):
        ex = hcx + side * hrx * 0.97
        ey = P2[234, 1] + 0.05 * hry
        e = ((xx - ex) / (0.16 * hrx)) ** 2 + ((yy - ey) / (0.26 * hry)) ** 2 < 1
        N[e] = np.array([side * 0.55, 0.0, 0.83])
        skinA[e] = 1
        occl[e] = 0.82
    # head ellipse
    dx, dy = (xx - hcx) / hrx, (yy - hcy) / hry
    head = dx * dx + dy * dy < 1
    nz = np.sqrt(np.clip(1 - dx * dx - dy * dy, 0, 1))
    N[head] = np.stack([dx[head], -dy[head], nz[head]], 1)
    skinA[head] = 1
    occl[head] = 1

    # rasterise the mesh (Phong-interpolated normals, z-buffer)
    zbuf = np.full((H2, W2), -1e9)
    meshN = np.zeros((H2, W2, 3))
    meshM = np.zeros((H2, W2))
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
        z = w0 * V[f[0], 2] + w1 * V[f[1], 2] + w2 * V[f[2], 2]
        sub = zbuf[y0:y1 + 1, x0:x1 + 1]
        upd = inside & (z > sub)
        sub[upd] = z[upd]
        n = w0[..., None] * vn[f[0]] + w1[..., None] * vn[f[1]] + w2[..., None] * vn[f[2]]
        meshN[y0:y1 + 1, x0:x1 + 1][upd] = n[upd]
        meshM[y0:y1 + 1, x0:x1 + 1][upd] = 1
    meshN /= np.linalg.norm(meshN, axis=2, keepdims=True) + 1e-9
    soft = np.asarray(Image.fromarray((meshM * 255).astype(np.uint8)).filter(ImageFilter.MinFilter(9))
                      .filter(ImageFilter.GaussianBlur(10)), float)[..., None] / 255
    N = N * (1 - soft) + meshN * soft
    N /= np.linalg.norm(N, axis=2, keepdims=True) + 1e-9
    skinA = np.maximum(skinA, meshM)

    # ---- albedo ----
    base = to_lin(hex_rgb(MONK[m["tone"]])) * np.array(m["tint"])
    alb = np.ones((H2, W2, 3)) * base
    fw = hx1 - hx0
    red = to_lin(hex_rgb(MONK[m["tone"]])) * np.array([1.06, 0.9, 0.88])
    for c in (205, 425):
        g = gauss(xx, yy, P2[c, 0], P2[c, 1], 0.09 * fw)[..., None] * 0.55
        alb = alb * (1 - g) + red * g
    g = gauss(xx, yy, P2[4, 0], P2[4, 1], 0.05 * fw)[..., None] * 0.35
    alb = alb * (1 - g) + red * g
    for c in (145, 374):     # slightly darker under the eyes
        g = gauss(xx, yy, P2[c, 0], P2[c, 1] + 0.035 * fw, 0.05 * fw)[..., None] * 0.35
        alb = alb * (1 - g) + base * np.array([0.8, 0.74, 0.78]) * g
    # lips
    lipcol = base * np.array([0.78, 0.5, 0.52]) if m["tone"] <= 5 else base * np.array([0.72, 0.52, 0.52])
    lipm = poly_mask(P2[LIPS_OUT], blur=2.5 * SS)[..., None]
    upper = (yy < P2[13, 1])[..., None] * 0.12
    alb = alb * (1 - lipm) + lipcol * (1 - upper) * lipm
    # brows
    hair = to_lin(hex_rgb(m["hair"]))
    for b in (BROW_R, BROW_L):
        bm = poly_mask(P2[b], blur=2.2 * SS)
        strands = rng.random((H2, W2)) < 0.35
        bm = (bm * np.where(strands, 1.0, 0.7))[..., None] * 0.88
        alb = alb * (1 - bm) + hair * bm

    # ---- shading ----
    def nrm(v):
        v = np.array(v, float)
        return v / np.linalg.norm(v)
    L1, L2 = nrm([-0.45, 0.45, 0.78]), nrm([0.6, 0.05, 0.6])
    Hh = nrm(L1 + np.array([0, 0, 1]))
    d1 = np.clip(N @ L1, 0, 1)
    d2 = np.clip(N @ L2, 0, 1)
    amb = 0.32 + 0.1 * np.clip(N[..., 1], -1, 1)
    light = (amb + 0.62 * d1 + 0.18 * d2) * occl
    sss = np.stack([light ** 0.9, light ** 1.05, light ** 1.12], -1)    # warmer shadows
    spec = 0.06 * np.clip(N @ Hh, 0, 1) ** 28
    skin = alb * sss + spec[..., None] * (1 - lipm * 0.3)

    # ---- background and clothes ----
    t = (yy / H2)[..., None]
    bg = to_lin(hex_rgb(m["bg"][0])) * (1 - t) + to_lin(hex_rgb(m["bg"][1])) * t
    vign = 1 - 0.18 * (((xx - W2 / 2) / W2) ** 2 + ((yy - H2 / 2) / H2) ** 2)[..., None]
    img = bg * vign

    # back hair (behind head)
    hairim = Image.new("L", (W2, H2), 0)
    hd = ImageDraw.Draw(hairim)
    top = hcy - hry * 1.08
    if m["style"] in ("long", "curly"):
        drop = H2 * (0.98 if m["style"] == "long" else 0.82)
        wide = 1.38 if m["style"] == "long" else 1.62
        hd.rounded_rectangle([hcx - hrx * wide, top + hry * 0.25, hcx + hrx * wide, drop], radius=int(hrx * 0.9), fill=255)
        hd.ellipse([hcx - hrx * wide, top, hcx + hrx * wide, top + hry * 1.6], fill=255)
    elif m["style"] == "bun":
        hd.ellipse([hcx - hrx * 0.55, top - hry * 0.42, hcx + hrx * 0.55, top + hry * 0.38], fill=255)
    hb = np.asarray(hairim.filter(ImageFilter.GaussianBlur(3 * SS)), float)[..., None] / 255

    # clothes
    cl = Image.new("L", (W2, H2), 0)
    cd = ImageDraw.Draw(cl)
    sy = P2[152, 1] + hry * 0.36
    cd.rounded_rectangle([hcx - hrx * 2.3, sy, hcx + hrx * 2.3, H2 + 200], radius=int(hrx * 1.1), fill=255)
    cd.ellipse([hcx - nw * 1.35, sy - nw * 1.0, hcx + nw * 1.35, sy + nw * 0.75], fill=0)
    clm = np.asarray(cl.filter(ImageFilter.GaussianBlur(2 * SS)), float)[..., None] / 255

    hair_lin = hair * (0.8 + 0.4 * rng.random((H2, W2, 1)) ** 3)
    sheen = gauss(xx, yy, hcx - hrx * 0.35, top + hry * 0.35, hrx * 0.5)[..., None] * 0.09
    hair_shaded = hair_lin * (0.75 + 0.5 * (1 - yy / H2)[..., None] * 0.6) + sheen

    img = img * (1 - hb) + hair_shaded * hb
    sk = skinA[..., None]
    sk = np.asarray(Image.fromarray((skinA * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(1.5 * SS)), float)[..., None] / 255
    img = img * (1 - sk) + skin * sk
    cloth = to_lin(hex_rgb(m["cloth"])) * (0.7 + 0.35 * np.clip(1 - (xx - hcx) / (hrx * 4), 0, 1))[..., None]
    img = img * (1 - clm) + cloth * clm

    # ---- eyes ----
    iris_pts = []
    for eye in (EYE_R, EYE_L):
        poly = np.concatenate([P2[eye["up"]], P2[eye["lo"]][::-1][1:-1]])
        em = poly_mask(poly, blur=0.8 * SS)[..., None]
        c0, c1 = P2[eye["up"][0]], P2[eye["up"][-1]]
        ew = np.linalg.norm(c1 - c0)
        ecx = (P2[eye["up"]][:, 0].mean() + P2[eye["lo"]][:, 0].mean()) / 2
        ecy = (P2[eye["up"]][:, 1].min() + P2[eye["lo"]][:, 1].max()) / 2
        eh = P2[eye["lo"]][:, 1].max() - P2[eye["up"]][:, 1].min()
        r = min(0.24 * ew, 0.62 * eh)
        scl = to_lin(hex_rgb("#efe7e1")) * (0.72 + 0.28 * np.clip(1 - np.abs(xx - ecx) / (0.6 * ew), 0, 1))[..., None]
        icol = to_lin(hex_rgb(m["eyes"]))
        idist = np.sqrt((xx - ecx) ** 2 + (yy - ecy) ** 2)
        iris = np.clip((r - idist) / (0.8 * SS), 0, 1)[..., None]
        ring = np.clip(idist / r, 0, 1)[..., None]
        icolv = icol * (1.25 - 0.55 * ring)
        pupil = np.clip((0.42 * r - idist) / (0.6 * SS), 0, 1)[..., None]
        eye_img = scl * (1 - iris) + icolv * iris
        eye_img = eye_img * (1 - pupil) + to_lin(hex_rgb("#0a0706")) * pupil
        glint = gauss(xx, yy, ecx - 0.3 * r, ecy - 0.35 * r, 0.12 * r)[..., None]
        eye_img = eye_img + glint * 0.9
        lidshadow = np.clip((yy - P2[eye["up"]][:, 1].min()) / (0.45 * eh), 0, 1)[..., None]
        eye_img = eye_img * (0.55 + 0.45 * lidshadow)
        img = img * (1 - em) + eye_img * em
        # lash line, crease and lower lid
        lash = line_mask(P2[eye["up"]], 0.075 * ew, blur=0.7 * SS)[..., None]
        img = img * (1 - 0.92 * lash) + to_lin(hex_rgb("#0b0807")) * 0.92 * lash
        crease = line_mask(P2[eye["up"]] - np.array([0, 0.33 * eh]), 0.06 * ew, blur=3 * SS)[..., None]
        img = img * (1 - 0.22 * crease)
        lo = line_mask(P2[eye["lo"]], 0.025 * ew, blur=0.8 * SS)[..., None]
        img = img * (1 - 0.3 * lo)
        iris_pts.append((ecx, ecy, r))

    # nostrils and mouth line
    for alar in (98, 327):
        nx_ = P2[alar, 0] * 0.58 + P2[2, 0] * 0.42
        ny_ = P2[alar, 1] * 0.45 + P2[2, 1] * 0.55
        nm = ellipse_mask(nx_, ny_, 0.028 * fw, 0.014 * fw, blur=1.6 * SS)[..., None]
        img = img * (1 - 0.6 * nm)
    ml = line_mask(P2[LIPS_IN_UP], 0.008 * fw + SS, blur=1.0 * SS)[..., None]
    img = img * (1 - 0.55 * ml)

    # ---- hair cap / fringe over the forehead edge ----
    cap = Image.new("L", (W2, H2), 0)
    capd = ImageDraw.Draw(cap)
    hairline = []
    side_pts = [127, 162, 21, 54, 103, 67, 109, 10, 338, 297, 332, 284, 251, 389, 356]
    brow_y = P2[[105, 334]][:, 1].mean()
    for i in side_pts:
        x, y = P2[i]
        k = 0.24 if i in (10, 109, 338, 67, 297) else 0.12
        hairline.append((x, y + (brow_y - y) * k))
    if m["style"] in ("long", "curly", "short"):
        part = hcx + hrx * (0.18 if m["style"] != "short" else -0.25)
        hairline[7] = (part, hairline[7][1] - hry * 0.05)
    outer = [(hcx + hrx * 1.12 * math.cos(t_), hcy - hry * 1.02 * math.sin(t_)) for t_ in np.linspace(math.pi * 1.06, -0.06, 40)]
    capd.polygon(hairline + outer[::-1], fill=255)
    if m["style"] == "long":
        for side in (-1, 1):
            capd.polygon([(hcx + side * hrx * 0.98, P2[234, 1] - hry * 0.4), (hcx + side * hrx * 1.3, P2[234, 1] - hry * 0.4),
                          (hcx + side * hrx * 1.34, H2 * 0.95), (hcx + side * hrx * 0.92, H2 * 0.95), (hcx + side * hrx * 0.9, P2[234, 1] + hry * 0.4)], fill=255)
    if m["style"] == "curly":
        for k_ in range(70):
            ang = rng.uniform(-0.05, math.pi * 1.05)
            rr = rng.uniform(1.0, 1.32)
            x, y = hcx + hrx * rr * math.cos(ang) * 1.12, hcy - hry * rr * math.sin(ang) * 0.98
            rad = rng.uniform(0.07, 0.13) * hrx
            capd.ellipse([x - rad, y - rad, x + rad, y + rad], fill=255)
    capm = np.asarray(cap.filter(ImageFilter.GaussianBlur(2.2 * SS)), float)[..., None] / 255
    strands = np.asarray(Image.fromarray((rng.random((H2 // 6, W2)) * 255).astype(np.uint8)).resize((W2, H2), Image.BILINEAR), float)[..., None] / 255
    hair_top = hair * (0.7 + 0.6 * strands ** 2) + gauss(xx, yy, hcx - hrx * 0.3, hcy - hry * 0.75, hrx * 0.35)[..., None] * 0.07
    img = img * (1 - capm) + hair_top * capm

    # skin texture (fine luminance noise only on skin)
    noise = rng.normal(0, 1, (H2 // 2, W2 // 2))
    noise = np.asarray(Image.fromarray(((noise * 0.25 + 0.5).clip(0, 1) * 255).astype(np.uint8)).resize((W2, H2), Image.BICUBIC), float) / 255 - 0.5
    img = img * (1 + (noise * 0.07)[..., None] * sk * (1 - capm))

    out = (to_srgb(img) * 255 + 0.5).astype(np.uint8)
    pic = Image.fromarray(out).resize((W, H), Image.LANCZOS)

    # landmarks: 468 mesh points + 10 iris points, normalised to the image
    pts = (P2 / np.array([W2, H2])).tolist()
    for (ecx, ecy, r) in iris_pts:
        ring = [(ecx, ecy), (ecx + r, ecy), (ecx, ecy - r), (ecx - r, ecy), (ecx, ecy + r)]
        pts += [[x / W2, y / H2] for x, y in ring]
    return pic, [[round(x, 4), round(y, 4)] for x, y in pts]


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    meta = []
    for m in MODELS:
        pic, lm = render(m)
        pic.save(OUT / f"{m['id']}.jpg", quality=86, optimize=True, progressive=True)
        meta.append({"id": m["id"], "name": m["name"], "tone": m["tone"], "undertone": m["undertone"],
                     "file": f"data/tryon_models/{m['id']}.jpg", "w": W, "h": H, "landmarks": lm})
        print(f"{m['id']}: Monk {m['tone']} {m['undertone']}, {len(lm)} landmarks")
    (ROOT / "data" / "tryon_models.json").write_text(json.dumps({
        "source": "Illustrated faces rendered by tools/tryon/make_models.py from MediaPipe's canonical face mesh "
                  "(Apache-2.0). No photographs of real people.",
        "models": meta}, separators=(",", ":")))


if __name__ == "__main__":
    main()
