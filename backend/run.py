#!/usr/bin/env python3
"""Run script for AAINA Google Monk Skin Tone Backend Service.

Usage:
    python3 backend/run.py [--port 8000] [--host 0.0.0.0]
"""

import argparse
import os
import sys
from pathlib import Path

# If uvicorn/fastapi is installed under Python 3.13 on macOS, re-exec if needed
try:
    import uvicorn
    import fastapi
except ImportError:
    py313 = Path("/Library/Frameworks/Python.framework/Versions/3.13/bin/python3")
    if py313.exists() and sys.executable != str(py313):
        os.execv(str(py313), [str(py313)] + sys.argv)
    raise

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Start AAINA Monk Skin Tone Service")
    parser.add_argument("--port", type=int, default=8000, help="Port to listen on (default: 8000)")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="Host interface (default: 0.0.0.0)")
    args = parser.parse_args()

    print(f"Starting AAINA Monk Skin Tone Engine on http://{args.host}:{args.port}")
    print(f"API Docs available at: http://localhost:{args.port}/docs")
    uvicorn.run("backend.app:app", host=args.host, port=args.port, reload=False)
