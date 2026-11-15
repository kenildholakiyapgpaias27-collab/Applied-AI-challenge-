"""FastAPI Backend Server for Google Monk Skin Tone Recognition.

Integrates with AAINA frontend to provide real-time AI-based skin tone,
undertone, and Fitzpatrick phototype classification using the Monk Skin Tone Scale.
"""

from __future__ import annotations

import base64
from pathlib import Path
from typing import Any, Dict, List, Optional
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from backend.monk_service import (
    MONK_PALETTE,
    hex_to_rgb,
    match_monk_tone,
    process_image_for_monk_tone,
    rgb_to_lab_8bit,
)

ROOT_DIR = Path(__file__).parent.parent

app = FastAPI(
    title="AAINA AI Monk Skin Tone Service",
    description="Backend API implementing Google's Monk Skin Tone (MST 1-10) recognition engine",
    version="1.0.0",
)

# Enable CORS for local development and cross-origin requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class Base64ImageRequest(BaseModel):
    image: str  # Data URL or pure Base64 string
    crop_center_oval: Optional[bool] = True


class DirectColorRequest(BaseModel):
    hex: Optional[str] = None
    rgb: Optional[List[int]] = None


@app.get("/api/health")
def health_check() -> Dict[str, str]:
    return {"status": "ok", "service": "monk-skin-tone-engine", "version": "1.0.0"}


@app.get("/api/monk-palette")
def get_monk_palette() -> Dict[str, Any]:
    """Returns the official Google Monk Skin Tone 10-level palette with metadata."""
    return {
        "status": "OK",
        "scale": "Google Monk Skin Tone (MST 1-10)",
        "levels_count": 10,
        "palette": MONK_PALETTE,
    }


@app.post("/api/detect-monk-tone")
def detect_monk_tone(payload: Base64ImageRequest) -> Dict[str, Any]:
    """Classify skin tone from a base64 encoded selfie/photo using the Monk Skin Tone scale."""
    raw_str = payload.image
    if not raw_str:
        raise HTTPException(status_code=400, detail="Empty image data provided.")

    if "," in raw_str:
        raw_str = raw_str.split(",", 1)[1]

    try:
        image_bytes = base64.b64decode(raw_str)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid base64 encoding: {str(e)}")

    result = process_image_for_monk_tone(
        image_bytes=image_bytes,
        crop_center_oval=payload.crop_center_oval if payload.crop_center_oval is not None else True,
    )

    if result.get("status") == "ERROR":
        raise HTTPException(status_code=422, detail=result.get("message", "Processing failed."))

    return result


@app.post("/api/detect-monk-tone/upload")
async def detect_monk_tone_upload(file: UploadFile = File(...)) -> Dict[str, Any]:
    """Classify skin tone from an uploaded image file."""
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    result = process_image_for_monk_tone(image_bytes=content, crop_center_oval=True)

    if result.get("status") == "ERROR":
        raise HTTPException(status_code=422, detail=result.get("message", "Processing failed."))

    return result


@app.post("/api/classify-tone")
def classify_direct_color(payload: DirectColorRequest) -> Dict[str, Any]:
    """Directly classify an RGB or Hex color coordinate against Google's Monk scale."""
    if payload.hex:
        r, g, b = hex_to_rgb(payload.hex)
    elif payload.rgb and len(payload.rgb) == 3:
        r, g, b = payload.rgb[0], payload.rgb[1], payload.rgb[2]
    else:
        raise HTTPException(status_code=400, detail="Must provide either 'hex' string or 'rgb' triplet [r, g, b].")

    lab = rgb_to_lab_8bit(r, g, b)
    match_result = match_monk_tone(lab)

    return {
        "status": "OK",
        "input_rgb": [r, g, b],
        "measured_lab": [round(c, 2) for c in lab],
        **match_result,
    }


# Serve the static AAINA application so frontend + backend run on one unified server
INDEX_FILE = ROOT_DIR / "index.html"
SRC_DIR = ROOT_DIR / "src"
ASSETS_DIR = ROOT_DIR / "assets"

if SRC_DIR.exists():
    app.mount("/src", StaticFiles(directory=str(SRC_DIR)), name="src")

if ASSETS_DIR.exists():
    app.mount("/assets", StaticFiles(directory=str(ASSETS_DIR)), name="assets")


@app.get("/", response_class=HTMLResponse)
def serve_index():
    if INDEX_FILE.exists():
        return FileResponse(INDEX_FILE)
    return HTMLResponse("<h1>AAINA Monk Skin Tone Engine Running</h1><p>Visit /docs for API specs.</p>")

