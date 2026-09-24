"""OCR opcional, so usado se o Tesseract estiver instalado."""
from __future__ import annotations

import shutil

_CACHE: dict = {}


def available() -> bool:
    if "ok" in _CACHE:
        return _CACHE["ok"]
    ok = False
    try:
        import pytesseract  # noqa: F401

        ok = shutil.which("tesseract") is not None
        if not ok:
            # instalacao padrao do Windows
            import os

            for guess in (
                r"C:\Program Files\Tesseract-OCR\tesseract.exe",
                r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
            ):
                if os.path.exists(guess):
                    pytesseract.pytesseract.tesseract_cmd = guess
                    ok = True
                    break
    except Exception:
        ok = False
    _CACHE["ok"] = ok
    return ok


def page_text(page, lang: str = "por+eng", dpi: int = 300) -> str:
    """Roda OCR numa pagina e devolve o texto puro (sem layout)."""
    if not available():
        return ""
    try:
        import io

        from ._pdf import fitz
        import pytesseract
        from PIL import Image

        pix = page.get_pixmap(matrix=fitz.Matrix(dpi / 72, dpi / 72))
        img = Image.open(io.BytesIO(pix.tobytes("png")))
        return pytesseract.image_to_string(img, lang=lang) or ""
    except Exception:
        return ""
