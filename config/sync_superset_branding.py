#!/usr/bin/env python3
"""Download ATP branding assets from S3 and generate favicon + dark-mode logo."""

from __future__ import annotations

import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

from PIL import Image

BRANDING_DIR = Path("/app/superset/static/assets/images/branding")
LOGO_PATH = BRANDING_DIR / "logo.png"
LOGO_DARK_PATH = BRANDING_DIR / "logo-dark.png"
FAVICON_PATH = BRANDING_DIR / "favicon.png"


def _download(url: str, destination: Path) -> None:
    print(f"Downloading {url}")
    try:
        with urllib.request.urlopen(url, timeout=30) as response:
            destination.write_bytes(response.read())
    except urllib.error.URLError as exc:
        raise SystemExit(f"Failed to download {url}: {exc}") from exc
    print(f"Saved {destination}")


def _make_dark_logo(source: Path, destination: Path) -> None:
    image = Image.open(source).convert("RGBA")
    pixels = image.load()
    width, height = image.size

    for y in range(height):
        for x in range(width):
            red, green, blue, alpha = pixels[x, y]
            if alpha < 32:
                continue

            # Keep ATP red accent visible on dark backgrounds.
            if red > 150 and green < 100 and blue < 100:
                continue

            luminance = 0.299 * red + 0.587 * green + 0.114 * blue
            if luminance < 90:
                red, green, blue = 245, 245, 245
            elif luminance < 170:
                red, green, blue = 200, 200, 200
            else:
                red, green, blue = 170, 170, 170

            pixels[x, y] = (int(red), int(green), int(blue), alpha)

    image.save(destination)
    print(f"Generated dark logo at {destination}")


def _make_favicon(source: Path, destination: Path) -> None:
    image = Image.open(source).convert("RGBA")
    image.thumbnail((64, 64), Image.Resampling.LANCZOS)
    canvas = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    offset_x = (64 - image.width) // 2
    offset_y = (64 - image.height) // 2
    canvas.paste(image, (offset_x, offset_y), image)
    canvas.save(destination)
    print(f"Generated favicon at {destination}")


def main() -> int:
    logo_key = os.environ.get("SUPERSET_LOGO_S3_KEY")
    if not logo_key:
        print("SUPERSET_LOGO_S3_KEY is not set; skipping branding sync.")
        return 0

    BRANDING_DIR.mkdir(parents=True, exist_ok=True)

    bucket = os.environ.get("SUPERSET_LOGO_S3_BUCKET", "for-superset")
    endpoint = os.environ.get("MINIO_ENDPOINT", "http://rustfs:9000").rstrip("/")
    logo_url = f"{endpoint}/{bucket}/{logo_key.lstrip('/')}"
    _download(logo_url, LOGO_PATH)

    dark_key = os.environ.get("SUPERSET_LOGO_S3_KEY_DARK")
    if dark_key:
        dark_url = f"{endpoint}/{bucket}/{dark_key.lstrip('/')}"
        _download(dark_url, LOGO_DARK_PATH)
    else:
        _make_dark_logo(LOGO_PATH, LOGO_DARK_PATH)

    favicon_key = os.environ.get("SUPERSET_FAVICON_S3_KEY", "ATP_TLP.jpg")
    favicon_url = f"{endpoint}/{bucket}/{favicon_key.lstrip('/')}"
    favicon_source = BRANDING_DIR / Path(favicon_key).name
    _download(favicon_url, favicon_source)
    _make_favicon(favicon_source, FAVICON_PATH)

    return 0


if __name__ == "__main__":
    sys.exit(main())
