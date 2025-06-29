import re
import os
import json
import fitz
from io import BytesIO
from .cv_keywords import *


def extract_text_from_pdf(file_bytes: bytes) -> str:
    try:
        doc = fitz.open(stream=file_bytes, filetype="pdf")
        text = ""
        for page in doc:
            text += page.get_text()
        doc.close()
        return text
    except Exception as e:
        print("❌ Error extrayendo texto del PDF:", e)
        return ""




