from __future__ import annotations

import re

SAFE_CHARS_RE = re.compile(r"[^A-Za-z0-9._-]")


def sanitize_filename(name: str) -> str:
    sanitized = SAFE_CHARS_RE.sub("_", name.strip())
    if not sanitized:
        return "file"
    return sanitized[:255]

