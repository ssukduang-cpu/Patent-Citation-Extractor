from __future__ import annotations

import shutil


def tesseract_available() -> bool:
    return shutil.which("tesseract") is not None
