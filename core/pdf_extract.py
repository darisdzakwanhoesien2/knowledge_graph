"""PDF text extraction (FR-1) used as input to draft generation.

Uses pypdfium2 when available. Documents are always closed, even on error
(NFR: uploaded PDFs and temp files must be cleaned up reliably).
"""

from contextlib import contextmanager

from core.store import content_hash


class PdfExtractionError(RuntimeError):
    pass


@contextmanager
def open_pdf(file_like):
    try:
        import pypdfium2 as pdfium
    except ImportError as exc:
        raise PdfExtractionError(
            "pypdfium2 is required for PDF extraction: pip install pypdfium2"
        ) from exc

    pdf = pdfium.PdfDocument(file_like)
    try:
        yield pdf
    finally:
        try:
            pdf.close()
        except Exception:
            pass


def extract_pdf_text(file_like):
    """Return {text, pages, content_hash}. file_like must be a readable binary stream."""
    with open_pdf(file_like) as pdf:
        pages = []
        for page in pdf:
            text_page = page.get_textpage()
            try:
                pages.append((text_page.get_text_bounded() or "").strip())
            finally:
                text_page.close()
            page.close()

    parts = [f"--- page {i} ---\n{body}" for i, body in enumerate(pages, start=1)]
    text = "\n\n".join(parts)

    return {
        "text": text,
        "pages": len(pages),
        "content_hash": content_hash(text),
    }
