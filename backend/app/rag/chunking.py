"""Chia tài liệu thành chunk theo CẤU TRÚC văn bản.

Văn bản hành chính VN có cấu trúc rõ: Chương > Điều > Khoản. Người dùng hỏi và trích dẫn theo Điều,
nên đơn vị chunk tự nhiên là **một Điều (một section heading thấp nhất)**:
- Không gộp hai Điều vào một chunk: trích dẫn sẽ mơ hồ và điểm tương đồng bị "pha loãng".
- Section quá dài mới cắt tiếp theo đoạn văn; đoạn vẫn quá dài mới cắt theo câu.
- Bảng Markdown không bao giờ bị cắt giữa dòng; nếu buộc phải chia bảng thì lặp lại dòng tiêu đề
  ở mỗi phần, để phần sau vẫn biết cột nào là gì.
- Mỗi chunk mang "đường dẫn" heading (Chương II > Điều 5. ...) -> chunk tự đủ nghĩa khi đứng một mình
  (contextual chunking) và dùng luôn làm vị trí trích dẫn.

`chunk_text` (bản cũ, cho file upload không có cấu trúc Markdown) vẫn giữ để tương thích.
"""

import re
from dataclasses import dataclass

MD_HEADING = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
# Dòng in đậm trọn vẹn ("**H1. Lương trả ngày nào?**") = heading giả, cấp thấp nhất (FAQ, biên bản...)
BOLD_HEADING = re.compile(r"^\*\*([^*].*?)\*\*\s*$")
HEADING = re.compile(r"^(#{1,6}\s+.+|[IVX]+\.\s+.+|Điều\s+\d+.*|Chương\s+\w+.*)$", re.IGNORECASE)


@dataclass
class TextChunk:
    content: str
    page: int | None = None
    section: str = ""


# ---------------------------------------------------------------- Markdown theo cấu trúc


def _is_table(block: str) -> bool:
    lines = block.strip().splitlines()
    return len(lines) >= 2 and all(line.lstrip().startswith("|") for line in lines)


def _split_sentences(text: str, size: int, overlap: int) -> list[str]:
    if len(text) <= size:
        return [text]
    pieces, start = [], 0
    while start < len(text):
        end = min(start + size, len(text))
        cut = text.rfind(". ", start, end)  # cố cắt ở ranh giới câu
        if cut > start + size // 2 and end < len(text):
            end = cut + 1
        pieces.append(text[start:end].strip())
        if end >= len(text):
            break
        start = max(end - overlap, start + 1)
    return pieces


def _split_table(block: str, size: int) -> list[str]:
    lines = block.strip().splitlines()
    header, rows = lines[:2], lines[2:]  # dòng tiêu đề + dòng |---|
    head = "\n".join(header)
    parts, buf = [], []
    for row in rows:
        if buf and len(head) + sum(len(r) + 1 for r in buf) + len(row) > size:
            parts.append("\n".join([head, *buf]))
            buf = []
        buf.append(row)
    if buf or not parts:
        parts.append("\n".join([head, *buf]))
    return parts


def _pack(blocks: list[str], size: int, overlap: int) -> list[str]:
    """Gộp các block (đoạn văn / bảng) liên tiếp thành phần ≤ size, không cắt block trừ khi bắt buộc."""
    units: list[str] = []
    for b in blocks:
        if len(b) <= size:
            units.append(b)
        elif _is_table(b):
            units += _split_table(b, size)
        else:
            units += _split_sentences(b, size, overlap)
    out, buf = [], ""
    for u in units:
        if buf and len(buf) + len(u) + 2 > size:
            out.append(buf)
            buf = ""
        buf = f"{buf}\n\n{u}" if buf else u
    if buf:
        out.append(buf)
    return out


def chunk_markdown(text: str, size: int = 1200, overlap: int = 150) -> list[TextChunk]:
    """Chunk Markdown theo heading. Heading cấp 1 (tên văn bản) không đưa vào đường dẫn
    vì tên văn bản đã được thêm riêng ở tiền tố ngữ cảnh khi embed."""
    sections: list[tuple[list[str], list[str]]] = []  # (heading path, các dòng nội dung)
    path: list[tuple[int, str]] = []
    lines_buf: list[str] = []

    def close():
        if any(line.strip() for line in lines_buf):
            sections.append(([h for lvl, h in path if lvl > 1], list(lines_buf)))
        lines_buf.clear()

    for line in text.splitlines():
        m = MD_HEADING.match(line)
        b = BOLD_HEADING.match(line.strip()) if not m else None
        if m or b:
            close()
            level, title = (len(m.group(1)), m.group(2).strip()) if m else (7, b.group(1).strip())
            path = [(lvl, h) for lvl, h in path if lvl < level] + [(level, title)]
        else:
            lines_buf.append(line)
    close()

    chunks: list[TextChunk] = []
    for heading_path, body_lines in sections:
        blocks = [b.strip() for b in re.split(r"\n\s*\n", "\n".join(body_lines)) if b.strip()]
        section = " > ".join(heading_path)
        for piece in _pack(blocks, size, overlap):
            chunks.append(TextChunk(content=piece, section=section))
    return chunks


# ---------------------------------------------------------------- bản cũ cho văn bản thô


def chunk_text(text: str, size: int = 1200, overlap: int = 150, page: int | None = None) -> list[TextChunk]:
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    chunks: list[TextChunk] = []
    heading = ""
    buf = ""

    def flush():
        nonlocal buf
        if buf.strip():
            chunks.append(TextChunk(buf.strip(), page, heading))
        buf = ""

    for para in paragraphs:
        first_line = para.splitlines()[0].strip()
        if HEADING.match(first_line):
            flush()
            heading = first_line.lstrip("# ").strip()
        for piece in _split_sentences(para, size, overlap):
            if len(buf) + len(piece) + 2 > size:
                flush()
            buf = f"{buf}\n\n{piece}" if buf else piece
    flush()
    return chunks
