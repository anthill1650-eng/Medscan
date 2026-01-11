from __future__ import annotations

import io
import re

from PIL import Image, ImageOps
import pytesseract

# HARD-SET TESSERACT PATH (Windows)
pytesseract.pytesseract.tesseract_cmd = r"C:\Users\lydel\AppData\Local\Programs\Tesseract-OCR\tesseract.exe"


def _basic_cleanup(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    return text


def ocr_image_bytes(image_bytes: bytes, *, lang: str = "eng") -> str:
    img = Image.open(io.BytesIO(image_bytes))
    img = ImageOps.grayscale(img)
    img = ImageOps.autocontrast(img)

    config = "--psm 6"
    text = pytesseract.image_to_string(img, lang=lang, config=config)
    return _basic_cleanup(text)
