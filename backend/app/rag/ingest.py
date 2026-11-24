"""Pipeline nạp tài liệu: trích xuất text (PDF/DOCX/ảnh scan qua OCR) -> chunk -> embed -> lưu.

PDF có lớp text: dùng PyMuPDF đọc trực tiếp (nhanh, chính xác).
PDF scan / ảnh: render trang -> Tesseract OCR (lang vie+eng). Phương án nâng cao: gửi ảnh cho
LLM có vision để đọc bảng/biểu mẫu phức tạp (đắt hơn, dùng khi OCR kém).
"""

import io
from pathlib import Path

from sqlalchemy.orm import Session

from app.config import settings
from app.rag.chunking import TextChunk, chunk_text
from app.rag.embeddings import get_embedder

MIN_TEXT_PER_PAGE = 40  # ít hơn ngưỡng này -> coi là trang scan, chạy OCR


def ocr_image(image) -> str:
    import pytesseract

    return pytesseract.image_to_string(image, lang=settings.ocr_lang)


def extract_pages(data: bytes, filename: str) -> tuple[list[tuple[int, str]], int]:
    """Trả về [(số trang, text)], số trang phải OCR."""
    ext = Path(filename).suffix.lower()
    if ext in {".txt", ".md"}:
        return [(1, data.decode("utf-8", errors="ignore"))], 0
    if ext == ".docx":
        import docx

        d = docx.Document(io.BytesIO(data))
        return [(1, "\n\n".join(p.text for p in d.paragraphs))], 0
    if ext in {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp"}:
        from PIL import Image

        return [(1, ocr_image(Image.open(io.BytesIO(data))))], 1
    if ext == ".pdf":
        import fitz  # PyMuPDF
        from PIL import Image

        pages, ocr_count = [], 0
        with fitz.open(stream=data, filetype="pdf") as pdf:
            for i, page in enumerate(pdf, start=1):
                text = page.get_text()
                if len(text.strip()) < MIN_TEXT_PER_PAGE:
                    pix = page.get_pixmap(dpi=250)
                    img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
                    text = ocr_image(img)
                    ocr_count += 1
                pages.append((i, text))
        return pages, ocr_count
    raise ValueError(f"Định dạng chưa hỗ trợ: {ext}")


def extract_text(data: bytes, filename: str) -> str:
    pages, _ = extract_pages(data, filename)
    return "\n\n".join(t for _, t in pages)


def ingest_document(
    db: Session,
    data: bytes,
    filename: str,
    title: str | None = None,
    department: str = "General",
    visibility: str = "phong-ban",
    allowed_departments: list[str] | None = None,
    allowed_roles: list[str] | None = None,
    uploaded_by: str | None = None,
):
    """File upload không có frontmatter. Mặc định an toàn: chỉ phòng sở hữu xem được (phong-ban)."""
    import hashlib

    from app.models import Chunk, Document

    pages, ocr_pages = extract_pages(data, filename)
    chunks: list[TextChunk] = []
    for page_no, text in pages:
        chunks += chunk_text(text, settings.chunk_size, settings.chunk_overlap, page=page_no)
    if not chunks:
        raise ValueError("Không trích xuất được nội dung từ tài liệu")

    doc_title = title or Path(filename).stem
    # Gắn tiêu đề tài liệu vào nội dung -> chunk biết mình thuộc tài liệu nào
    contents = [f"[{doc_title}{' · ' + c.section if c.section else ''}]\n{c.content}" for c in chunks]
    vectors = get_embedder().embed(contents, kind="passage")
    digest = hashlib.sha256(data).hexdigest()

    doc = Document(
        doc_id=f"UPLOAD-{digest[:12]}", title=doc_title, source=filename, department=department,
        visibility=visibility, allowed_departments=allowed_departments or [department],
        allowed_roles=allowed_roles or [], uploaded_by=uploaded_by, ocr_pages=ocr_pages,
        content_hash=digest,
    )
    doc.chunks = [
        Chunk(ordinal=i, page=c.page, section=c.section[:256], content=text, embedding=v)
        for i, (c, text, v) in enumerate(zip(chunks, contents, vectors, strict=True))
    ]
    db.add(doc)
    db.commit()
    return doc
