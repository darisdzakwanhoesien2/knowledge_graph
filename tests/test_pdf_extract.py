"""End-to-end check: build a tiny valid PDF, then extract its text."""

import io
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.pdf_extract import extract_pdf_text


def build_pdf(pages_text):
    buf = io.BytesIO()
    objects = []

    def add(body):
        objects.append(body)
        return len(objects)

    font_id = add(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")

    content_ids = []
    for text in pages_text:
        stream = (f"BT /F1 18 Tf 72 770 Td ({text}) Tj ET").encode("latin-1")
        content_ids.append(add(b"<< /Length %d >>\nstream\n%s\nendstream" % (len(stream), stream)))

    catalog_id = len(objects) + 1
    pages_id = catalog_id + 1
    first_page_id = pages_id + 1
    kids = " ".join(f"{first_page_id + i} 0 R" for i in range(len(pages_text)))
    page_count = len(pages_text)

    add(f"<< /Type /Catalog /Pages {pages_id} 0 R >>".encode())
    add(f"<< /Type /Pages /Kids [{kids}] /Count {page_count} >>".encode())

    for cid in content_ids:
        add(
            f"<< /Type /Page /Parent {pages_id} 0 R /MediaBox [0 0 612 792] "
            f"/Resources << /Font << /F1 {font_id} 0 R >> >> "
            f"/Contents {cid} 0 R >>".encode())

    out = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for i, body in enumerate(objects, start=1):
        offsets.append(len(out))
        out += b"%d 0 obj\n" % i + body + b"\nendobj\n"

    xref_pos = len(out)
    out += b"xref\n0 %d\n" % (len(objects) + 1)
    out += b"0000000000 65535 f \n"
    for off in offsets[1:]:
        out += ("%010d 00000 n \n" % off).encode()
    out += (b"trailer\n<< /Size %d /Root %d 0 R >>\nstartxref\n%d\n%%%%EOF\n"
            % (len(objects) + 1, catalog_id, xref_pos))

    return bytes(out)


def main():
    pdf_bytes = build_pdf([
        "Convex optimization studies convex functions.",
        "Gradient descent converges under smoothness assumptions.",
    ])
    result = extract_pdf_text(io.BytesIO(pdf_bytes))
    assert result["pages"] == 2, result
    assert "convex functions" in result["text"]
    assert "--- page 2 ---" in result["text"]
    assert len(result["content_hash"]) == 64
    print("PDF extraction OK:", result["pages"], "pages,",
          len(result["text"]), "chars, hash", result["content_hash"][:12])


if __name__ == "__main__":
    main()
