"""Nạp kho tri thức Markdown có frontmatter (data/knowledge) vào Postgres.

    python -m app.rag.kb_ingest                 # nạp thư mục settings.kb_dir
    python -m app.rag.kb_ingest --exclude SVT-TL-099 --force

Idempotent: băm (nội dung file + tên model embedding). Không đổi -> bỏ qua; đổi -> xóa chunk cũ, nạp lại.
Đổi model embedding hoặc PIPELINE_VERSION cũng làm hash đổi -> tự nạp lại toàn bộ
(vector của hai model khác nhau không so sánh được với nhau).
"""

import argparse
import hashlib
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import yaml
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.rag.chunking import chunk_markdown
from app.rag.embeddings import get_embedder

VISIBILITIES = {"cong-khai", "phong-ban", "han-che"}
# Tăng số này mỗi khi đổi cách chunk/tiền tố -> mọi tài liệu tự được nạp lại ở lần chạy sau.
PIPELINE_VERSION = "2"


@dataclass
class ParsedDoc:
    meta: dict
    body: str


def parse_frontmatter(text: str) -> ParsedDoc:
    if not text.startswith("---"):
        raise ValueError("Thiếu frontmatter")
    _, fm, body = text.split("---", 2)
    meta = yaml.safe_load(fm) or {}
    for key in ("doc_id", "tieu_de", "pham_vi_truy_cap"):
        if not meta.get(key):
            raise ValueError(f"Frontmatter thiếu trường bắt buộc: {key}")
    if meta["pham_vi_truy_cap"] not in VISIBILITIES:
        raise ValueError(f"pham_vi_truy_cap không hợp lệ: {meta['pham_vi_truy_cap']}")
    return ParsedDoc(meta, body.strip())


def _date(v) -> date | None:
    if v in (None, "", "null"):
        return None
    return v if isinstance(v, date) else date.fromisoformat(str(v))


def _list(v) -> list[str]:
    return [str(x) for x in (v or [])]


def context_header(meta: dict, section: str) -> str:
    """Dòng đầu mỗi chunk: chunk đứng một mình vẫn biết mình thuộc văn bản nào, Điều nào.
    Dòng này nằm trong content -> được embed, được full-text index, và LLM nhìn thấy khi trích dẫn."""
    parts = [meta["doc_id"], meta["tieu_de"]]
    if meta.get("so_hieu"):
        parts.append(f"số hiệu {meta['so_hieu']}")
    if section:
        parts.append(section)
    return "[" + " · ".join(parts) + "]"


def ingest_markdown(db: Session, path: Path, force: bool = False, commit: bool = True) -> str:
    """`commit=False`: chỉ flush, để người gọi gộp thêm việc khác (người nạp, audit, thay thế bản cũ)
    vào CÙNG một transaction rồi tự commit. Mặc định giữ nguyên hành vi cũ."""
    from app.models import Chunk, Document

    raw = path.read_bytes()
    fingerprint = f"{settings.embedding_model}|{PIPELINE_VERSION}".encode()
    content_hash = hashlib.sha256(raw + fingerprint).hexdigest()
    parsed = parse_frontmatter(raw.decode("utf-8"))
    m = parsed.meta

    existing = db.execute(select(Document).where(Document.doc_id == m["doc_id"])).scalar_one_or_none()
    if existing and existing.content_hash == content_hash and not force:
        return "skip"

    chunks = chunk_markdown(parsed.body, settings.chunk_size, settings.chunk_overlap)
    if not chunks:
        raise ValueError(f"{path.name}: không có nội dung")
    contents = [f"{context_header(m, c.section)}\n{c.content}" for c in chunks]
    vectors = get_embedder().embed(contents, kind="passage")

    doc = existing or Document(doc_id=m["doc_id"])
    doc.so_hieu = m.get("so_hieu")
    doc.title = m["tieu_de"]
    doc.doc_type = m.get("loai")
    doc.source = str(path.as_posix())
    doc.department = m.get("phong_ban_so_huu") or "General"
    doc.visibility = m["pham_vi_truy_cap"]
    doc.allowed_departments = _list(m.get("phong_ban_duoc_xem"))
    doc.allowed_roles = _list(m.get("vai_tro_duoc_xem"))
    doc.classification = m.get("phan_loai_bao_mat") or "thuong"
    doc.effective_from = _date(m.get("hieu_luc_tu"))
    doc.effective_to = _date(m.get("het_hieu_luc"))
    doc.supersedes = m.get("thay_the")
    doc.superseded_by = m.get("bi_thay_the_boi")
    doc.version = str(m.get("phien_ban")) if m.get("phien_ban") is not None else None
    doc.content_hash = content_hash
    doc.chunks = [
        Chunk(ordinal=i, section=c.section[:256], content=text, embedding=v)
        for i, (c, text, v) in enumerate(zip(chunks, contents, vectors, strict=True))
    ]
    db.add(doc)
    if commit:
        db.commit()
    else:
        db.flush()
    return f"{'update' if existing else 'new'} ({len(chunks)} chunk)"


def ingest_dir(db: Session, directory: Path, exclude: set[str], force: bool = False) -> dict[str, str]:
    results = {}
    for path in sorted(directory.glob("*.md")):
        doc_id = "-".join(path.stem.split("-")[:3])  # SVT-QC-003-quy-che... -> SVT-QC-003
        if doc_id in exclude:
            results[path.name] = "excluded"
            continue
        try:
            results[path.name] = ingest_markdown(db, path, force)
        except ValueError as e:  # một file lỗi không chặn cả lô
            db.rollback()
            results[path.name] = f"ERROR: {e}"
    return results


def main() -> None:
    from app.db import SessionLocal, init_db

    ap = argparse.ArgumentParser(description="Nạp kho tri thức Markdown")
    ap.add_argument("--dir", default=settings.kb_dir)
    ap.add_argument("--exclude", nargs="*", default=[], help="doc_id bỏ qua, vd SVT-TL-099")
    ap.add_argument("--force", action="store_true", help="nạp lại kể cả khi không đổi")
    args = ap.parse_args()

    init_db()
    with SessionLocal() as db:
        for name, status in ingest_dir(db, Path(args.dir), set(args.exclude), args.force).items():
            print(f"{status:<22} {name}")


if __name__ == "__main__":
    main()
