"""Tests unitarios de los validadores de archivos subidos.

Cubren `validate_uploaded_resume` — la extensión, el tamaño y los magic
bytes son las tres capas que previenen que un atacante suba `evil.html`
renombrado a `.pdf` (bypass mime), un PDF de 500MB (DoS de disco), o
un binario totalmente distinto disfrazado con la extensión correcta.
"""

import pytest
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile

from users.models import validate_uploaded_resume


def _make_file(name, content):
    return SimpleUploadedFile(name, content, content_type="application/octet-stream")


class TestResumeValidator:
    def test_accepts_valid_pdf(self):
        pdf = _make_file("cv.pdf", b"%PDF-1.4\n" + b"x" * 100)
        validate_uploaded_resume(pdf)  # no raise

    def test_accepts_valid_docx(self):
        # DOCX es un zip — empieza con la firma PK\x03\x04.
        docx = _make_file("cv.docx", b"PK\x03\x04" + b"x" * 100)
        validate_uploaded_resume(docx)  # no raise

    def test_rejects_html_disguised_as_pdf(self):
        """Bypass anti-mime: extensión .pdf pero contenido HTML."""
        evil = _make_file("cv.pdf", b"<html><script>alert(1)</script></html>")
        with pytest.raises(ValidationError, match="PDF válido"):
            validate_uploaded_resume(evil)

    def test_rejects_executable_extension(self):
        exe = _make_file("cv.exe", b"MZ" + b"x" * 100)
        with pytest.raises(ValidationError, match="Formato no permitido"):
            validate_uploaded_resume(exe)

    def test_rejects_html_extension(self):
        html = _make_file("cv.html", b"<html></html>")
        with pytest.raises(ValidationError, match="Formato no permitido"):
            validate_uploaded_resume(html)

    def test_rejects_oversize_pdf(self):
        # 11 MB PDF — límite es 10 MB.
        big = _make_file("cv.pdf", b"%PDF-1.4\n" + b"x" * (11 * 1024 * 1024))
        with pytest.raises(ValidationError, match="excede"):
            validate_uploaded_resume(big)

    def test_rejects_docx_with_wrong_magic_bytes(self):
        fake = _make_file("cv.docx", b"NOTAZIP" + b"x" * 100)
        with pytest.raises(ValidationError, match="DOCX válido"):
            validate_uploaded_resume(fake)
