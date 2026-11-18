#!/usr/bin/env python3
"""Serve this repo on localhost with caching fully disabled, so a browser (or this session's
test tooling) never shows a stale build after `python3 build.py` regenerates index.html.

    python3 tools/nocache_server.py [port]
"""
import sys
from http.server import HTTPServer, SimpleHTTPRequestHandler


class NoCacheHandler(SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        super().end_headers()


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8743
    HTTPServer(("", port), NoCacheHandler).serve_forever()
