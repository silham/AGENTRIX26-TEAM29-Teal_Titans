"""Owner: M6. Text extraction from uploaded knowledge-base documents.

Pure functions over bytes — no DB, no API keys, and no Tesseract/poppler binary
(the OCR paths are monkeypatched).
"""
import io

import pytest

from app.rag import extract
from app.rag.extract import ExtractionError

BODY = (
    "Widows and Orphans Pension Scheme. Applications are processed by the Department of "
    "Pensions, Maligawatte, Colombo 10. Bring a certified death certificate and the "
    "original marriage certificate."
)


# ── sniff_kind ──────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "filename,expected",
    [
        ("a.txt", "text"), ("a.md", "text"), ("a.markdown", "text"),
        ("a.pdf", "pdf"), ("a.docx", "docx"),
        ("a.png", "image"), ("a.JPG", "image"), ("a.tiff", "image"),
    ],
)
def test_sniff_kind_maps_supported_extensions(filename, expected):
    assert extract.sniff_kind(filename) == expected


def test_sniff_kind_rejects_unknown_extension():
    with pytest.raises(ExtractionError, match="Unsupported file type"):
        extract.sniff_kind("payload.exe")


def test_sniff_kind_gives_actionable_advice_for_legacy_doc():
    with pytest.raises(ExtractionError, match=r"\.docx"):
        extract.sniff_kind("circular.doc")


def test_extension_wins_over_a_generic_content_type():
    # Browsers routinely send application/octet-stream for .md and .docx.
    assert extract.sniff_kind("guide.md", "application/octet-stream") == "text"


# ── plain text ──────────────────────────────────────────────────────────────


def test_utf8_text_round_trips():
    result = extract.extract(BODY.encode("utf-8"), "guide.txt")
    assert result.method == "text"
    assert "Department of Pensions" in result.text


def test_bom_is_stripped():
    result = extract.extract(b"\xef\xbb\xbf" + BODY.encode("utf-8"), "guide.txt")
    assert not result.text.startswith("﻿")


def test_non_utf8_falls_back_to_latin1_with_a_warning():
    result = extract.extract((BODY + " café").encode("latin-1"), "guide.txt")
    assert result.text
    assert any("latin-1" in w for w in result.warnings)


def test_empty_upload_is_rejected():
    with pytest.raises(ExtractionError, match="empty"):
        extract.extract(b"", "guide.txt")


def test_too_little_text_is_rejected():
    with pytest.raises(ExtractionError, match="too little to index"):
        extract.extract(b"hello", "guide.txt")


# ── cleanup ─────────────────────────────────────────────────────────────────


def test_clean_text_rejoins_hyphenated_line_breaks():
    assert extract.clean_text("regis-\ntrar") == "registrar"


def test_clean_text_collapses_blank_line_runs():
    assert extract.clean_text("a\n\n\n\n\nb") == "a\n\nb"


# ── docx ────────────────────────────────────────────────────────────────────


def test_docx_extracts_table_cells_not_just_paragraphs():
    """Government forms list requirements in tables — dropping them would lose
    the most important content on the page."""
    docx = pytest.importorskip("docx")
    document = docx.Document()
    document.add_paragraph(BODY)
    table = document.add_table(rows=1, cols=2)
    table.rows[0].cells[0].text = "Death certificate"
    table.rows[0].cells[1].text = "Certified copy from the Registrar General"
    buf = io.BytesIO()
    document.save(buf)

    result = extract.extract(buf.getvalue(), "form.docx")
    assert result.method == "docx"
    assert "Certified copy from the Registrar General" in result.text


# ── pdf ─────────────────────────────────────────────────────────────────────


class _FakePage:
    def __init__(self, text="", images=()):
        self._text = text
        self.images = list(images)

    def extract_text(self):
        return self._text


class _FakeReader:
    is_encrypted = False

    def __init__(self, pages):
        self.pages = pages


class _FakeImage:
    def __init__(self, data):
        self.data = data


def _patch_reader(monkeypatch, reader):
    import pypdf

    monkeypatch.setattr(pypdf, "PdfReader", lambda *_a, **_k: reader)


def test_text_pdf_uses_the_text_layer(monkeypatch):
    _patch_reader(monkeypatch, _FakeReader([_FakePage(BODY)]))
    result = extract.extract(b"%PDF-fake", "circular.pdf")
    assert result.method == "pdf_text"
    assert result.page_count == 1


def test_scanned_pdf_falls_through_to_ocr(monkeypatch):
    """A page below MIN_CHARS_PER_PAGE is treated as scanned, and with poppler
    absent it must still succeed via pypdf's embedded images."""
    _patch_reader(monkeypatch, _FakeReader([_FakePage("", [_FakeImage(b"jpegbytes")])]))
    monkeypatch.setattr(
        extract, "_ocr_image_bytes", lambda _b: BODY, raising=True
    )
    # Simulate poppler not installed.
    import pdf2image

    def _no_poppler(*_a, **_k):
        raise pdf2image.exceptions.PDFInfoNotInstalledError("poppler missing")

    monkeypatch.setattr(pdf2image, "convert_from_bytes", _no_poppler)

    result = extract.extract(b"%PDF-fake", "scan.pdf")
    assert result.method == "pdf_embedded_image_ocr"
    assert any("poppler" in w for w in result.warnings)


def test_scanned_pdf_with_no_ocr_backend_fails_actionably(monkeypatch):
    _patch_reader(monkeypatch, _FakeReader([_FakePage("")]))
    import pdf2image

    monkeypatch.setattr(
        pdf2image,
        "convert_from_bytes",
        lambda *_a, **_k: (_ for _ in ()).throw(RuntimeError("no poppler")),
    )
    with pytest.raises(ExtractionError) as exc:
        extract.extract(b"%PDF-fake", "scan.pdf")
    # The message is stored on the row and shown verbatim to the admin, so it
    # has to say what to do next.
    assert "tesseract" in str(exc.value).lower()


def test_oversized_scanned_pdf_is_rejected_before_ocr(monkeypatch):
    pages = [_FakePage("") for _ in range(extract.MAX_OCR_PAGES + 1)]
    _patch_reader(monkeypatch, _FakeReader(pages))
    with pytest.raises(ExtractionError, match="Split the document"):
        extract.extract(b"%PDF-fake", "big-scan.pdf")


# ── image ───────────────────────────────────────────────────────────────────


def test_image_routes_through_ocr(monkeypatch):
    monkeypatch.setattr(extract, "_ocr_image_bytes", lambda _b: BODY)
    result = extract.extract(b"\x89PNG-fake", "notice.png")
    assert result.method == "image_ocr"
    assert "Department of Pensions" in result.text
