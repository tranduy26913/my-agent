"""Nghiệp vụ kho tri thức cho /api/kb (docs/08-ke-hoach-api-kb.md). Không phụ thuộc FastAPI.

Router (app/api/kb.py) chỉ nhận request, kiểm quyền rồi gọi các hàm ở đây. Nhờ vậy test được bằng một
Session thường, không cần dựng HTTP.

.NET: đây là lớp `KnowledgeBaseService` (application service) còn `db: Session` là `DbContext`.
Khác biệt chính: không có DI container ở tầng này, `db` được truyền vào từng hàm.
"""

import hashlib
import logging
import os
import re
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path

import yaml
from sqlalchemy import delete, func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import settings
from app.models import AuditLog, Chunk, Document
from app.rag.acl import can_read, load_principal
from app.rag.chunking import chunk_markdown, chunk_text
from app.rag.embeddings import get_embedder
from app.rag.ingest import extract_pages  # chỉ gọi, không sửa ingest.py (thuộc phiên làm OCR)
from app.rag.kb_ingest import context_header, ingest_markdown, parse_frontmatter

log = logging.getLogger("kb")

# Các sự kiện audit của module này; `detail.doc_id` trỏ về tài liệu (bước 3-4 sẽ ghi các sự kiện còn lại).
EV_UPLOAD = "kb_upload"
EV_REINDEX = "kb_reindex"
EV_QUARANTINE = "kb_quarantine"
EV_DELETE = "kb_delete"
EV_VIEW_CLASSIFIED = "kb_view_classified"
KB_EVENTS = (EV_UPLOAD, EV_REINDEX, EV_QUARANTINE, EV_DELETE, EV_VIEW_CLASSIFIED)


class DocNotFound(LookupError):
    """Không có tài liệu với doc_id này. Router đổi thành 404."""


class KbError(Exception):
    """Lỗi nghiệp vụ kèm mã HTTP gợi ý (cùng kiểu với OcrError). Router đổi thành HTTPException.

    .NET: tương đương một exception tuỳ biến mà ExceptionFilter / ProblemDetails map ra mã HTTP.
    """

    def __init__(self, message: str, status_code: int = 422):
        super().__init__(message)
        self.status_code = status_code


@dataclass(frozen=True)
class DocRow:
    document: Document
    username: str | None  # email người nạp (documents.uploaded_by); None nếu nạp từ thư mục data/knowledge
    chunk_count: int


@dataclass(frozen=True)
class ChunkRow:
    ordinal: int
    page: int | None
    section: str
    content: str


@dataclass(frozen=True)
class HistoryRow:
    at: datetime
    by: str
    text: str


@dataclass(frozen=True)
class DocDetail:
    row: DocRow
    chunks: list[ChunkRow]
    history: list[HistoryRow]
    access_logged: bool


@dataclass(frozen=True)
class AccessResult:
    allowed: bool
    reason: str
    person: str | None


# ---------------------------------------------------------------- đọc danh sách / một tài liệu

def _rows_stmt():
    """Một truy vấn lấy tài liệu + email người nạp + số chunk (subquery count, không N+1).

    .NET/EF Core: tương đương `.Include(d => d.UploadedBy)` + `d.Chunks.Count` trong projection, EF cũng sinh
    một câu SQL. SQLAlchemy không tự làm vậy: phải viết outerjoin tường minh.
    """
    counts = (
        select(Chunk.document_id, func.count().label("n")).group_by(Chunk.document_id).subquery()
    )
    return (
        select(Document, Document.uploaded_by, func.coalesce(counts.c.n, 0))
        .outerjoin(counts, counts.c.document_id == Document.id)
    )


def list_documents(db: Session) -> list[DocRow]:
    stmt = _rows_stmt().order_by(Document.created_at.desc(), Document.doc_id)
    return [DocRow(d, name, int(n)) for d, name, n in db.execute(stmt).all()]


def get_row(db: Session, doc_id: str) -> DocRow:
    found = db.execute(_rows_stmt().where(Document.doc_id == doc_id)).first()
    if found is None:
        raise DocNotFound(doc_id)
    d, name, n = found
    return DocRow(d, name, int(n))


def _audit(actor: str | None, event: str, detail: dict) -> AuditLog:
    """Dòng audit của thao tác quản trị. Người thực hiện là email Zitadel, ghi vào detail["actor"];
    `user_id` để trống (không có bảng người dùng riêng: danh tính nằm ở Zitadel + bảng employees)."""
    if actor:
        detail = {**detail, "actor": actor}
    return AuditLog(user_id=None, event=event, detail=detail)


def history_text(event: str, detail: dict) -> str:
    """Câu tiếng Việt cho một dòng audit. Sự kiện lạ vẫn hiện (tên sự kiện), không giấu."""
    match event:
        case "kb_upload":
            return "Nạp tài liệu vào kho"
        case "kb_reindex":
            return "Nạp lại tài liệu"
        case "kb_quarantine":
            return "Cách ly tài liệu" if detail.get("on") else "Bỏ cách ly tài liệu"
        case "kb_delete":
            return "Gỡ tài liệu khỏi kho"
        case "kb_view_classified":
            return "Quản trị viên xem nội dung tài liệu Mật"
        case _:
            return event


def _history(db: Session, doc_id: str) -> list[HistoryRow]:
    # Chưa có index trên detail->>'doc_id'; bảng audit còn nhỏ. Lớn lên thì thêm index biểu thức.
    stmt = (
        select(AuditLog.ts, AuditLog.event, AuditLog.detail)
        .where(AuditLog.event.in_(KB_EVENTS), AuditLog.detail["doc_id"].astext == doc_id)
        .order_by(AuditLog.ts.desc(), AuditLog.id.desc())
    )
    return [
        HistoryRow(ts, (detail or {}).get("actor") or "hệ thống", history_text(event, detail or {}))
        for ts, event, detail in db.execute(stmt).all()
    ]


def get_detail(db: Session, doc_id: str, actor: str | None) -> DocDetail:
    """Chi tiết một tài liệu: chunk theo thứ tự + lịch sử.

    Ngoại lệ ADR-004 mục 4: admin được xem chunk tài liệu Mật nhưng PHẢI để lại dấu vết. Ghi audit (flush)
    TRƯỚC khi đọc chunk và commit cùng một transaction: ghi log lỗi thì ném lỗi, không có chunk nào được
    trả về (fail closed).
    Giai đoạn này luôn ghi log với tài liệu Mật (chưa có Principal của admin để biết admin có tự `can_read`);
    quy tắc đúng (chỉ ghi khi admin không tự can_read) áp khi có get_principal (docs/08).
    """
    row = get_row(db, doc_id)
    classified = row.document.classification == "Mat"
    if classified:
        info = {"doc_id": doc_id, "chunks": row.chunk_count}
        db.add(_audit(actor, EV_VIEW_CLASSIFIED, info))
        db.flush()

    chunks = [
        ChunkRow(*r)
        for r in db.execute(
            # chỉ chọn 4 cột cần: không kéo cột vector 1024 chiều của mỗi chunk
            select(Chunk.ordinal, Chunk.page, Chunk.section, Chunk.content)
            .where(Chunk.document_id == row.document.id)
            .order_by(Chunk.ordinal)
        ).all()
    ]
    history = _history(db, doc_id)  # đọc sau khi flush nên lượt xem vừa ghi đã nằm trong lịch sử
    if classified:
        db.commit()
    return DocDetail(row, chunks, history, access_logged=classified)


# ---------------------------------------------------------------- kiểm tra quyền đọc

def _fmt(d: date) -> str:
    return d.strftime("%d/%m/%Y")


def _deny_reason(visibility: str, depts: list[str], roles: list[str], p) -> str:
    """Vì sao `can_read` từ chối. Chỉ để giải thích; quyết định allow/deny luôn do can_read."""
    in_dept = p.department in depts
    has_role = bool(p.roles & set(roles))
    if visibility == "phong-ban":
        return f"Phòng {p.department} và vai trò của người này đều không nằm trong danh sách được xem"
    if visibility == "han-che":
        if not depts and not roles:
            return ("Văn bản hạn chế nhưng chưa khai báo phòng hay vai trò nào: "
                    "cấu hình lỗi nên không ai xem được")
        missing = []
        if depts and not in_dept:
            missing.append(f"phòng ban phù hợp (cần một trong: {', '.join(depts)})")
        if roles and not has_role:
            missing.append(f"vai trò phù hợp (cần một trong: {', '.join(roles)})")
        return "Văn bản hạn chế cần thoả cả phòng ban và vai trò; người này thiếu " + " và ".join(missing)
    return f"Phạm vi xem '{visibility}' không hợp lệ nên bị từ chối (fail closed)"


def _allow_reason(visibility: str, depts: list[str], p) -> str:
    if visibility == "cong-khai":
        return "Văn bản công khai, mọi nhân viên đang làm việc đều xem được"
    if visibility == "phong-ban":
        return f"Thuộc phòng {p.department} được xem" if p.department in depts else "Có vai trò được xem"
    return "Thoả cả điều kiện phòng ban và vai trò"


def check_access(db: Session, doc_id: str, email: str, today: date | None = None) -> AccessResult:
    """Người có `email` đọc được tài liệu này không, theo ĐÚNG luật lọc của trợ lý.

    Dùng lại `load_principal` + `can_read` (không viết lại quy tắc). Thứ tự: danh bạ -> nghỉ việc ->
    phạm vi xem (ADR-001) -> cách ly -> ngày hiệu lực (cùng điều kiện với retriever.in_force_sql).
    """
    row = get_row(db, doc_id)
    d = row.document
    today = today or date.today()

    p = load_principal(db, email)
    if p is None:
        return AccessResult(False, "Email này không có trong danh bạ nhân viên", None)
    person = p.full_name or None
    if not p.active:
        return AccessResult(False, "Nhân viên đã nghỉ việc, không xem được tài liệu nào", person)

    depts, roles = list(d.allowed_departments or []), list(d.allowed_roles or [])
    if not can_read(p, d.visibility, depts, roles):
        return AccessResult(False, _deny_reason(d.visibility, depts, roles, p), person)

    if d.quarantined:
        return AccessResult(False, "Tài liệu đang bị cách ly nên trợ lý không truy xuất cho ai", person)
    if d.effective_from and d.effective_from > today:
        return AccessResult(False, f"Tài liệu chưa đến ngày hiệu lực (từ {_fmt(d.effective_from)})", person)
    if d.effective_to and d.effective_to <= today:
        return AccessResult(
            False,
            f"Tài liệu đã hết hiệu lực từ {_fmt(d.effective_to)}; "
            "trợ lý chỉ nhắc tới khi người dùng hỏi đích danh văn bản này",
            person,
        )
    return AccessResult(True, _allow_reason(d.visibility, depts, p), person)


# ================================================================ upload (bước 3)

@dataclass(frozen=True)
class DocMeta:
    """Thông tin người nạp điền tay khi tệp không tự mang đủ (khớp UploadMetaIn ở tầng API)."""

    doc_type: str
    department: str
    visibility: str
    title: str | None = None
    allowed_departments: list[str] = field(default_factory=list)
    allowed_roles: list[str] = field(default_factory=list)
    classified: bool = False
    effective_from: date | None = None
    supersedes: str | None = None


# MIME hợp lệ theo đuôi. Trình duyệt hay gửi .md là text/plain hoặc để trống; octet-stream/trống coi như
# "không khai báo" (MIME do client tự khai, không đáng tin). Chốt chặn thật là magic bytes bên dưới.
_UNDECLARED = {"", "application/octet-stream"}
_DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
_MIME_BY_EXT: dict[str, set[str]] = {
    ".md": {"text/markdown", "text/x-markdown", "text/plain"},
    ".pdf": {"application/pdf"},
    ".docx": {_DOCX_MIME},
    ".png": {"image/png"},
    ".jpg": {"image/jpeg"},
    ".jpeg": {"image/jpeg"},
}
_MAGIC: dict[str, bytes] = {
    ".pdf": b"%PDF-", ".docx": b"PK\x03\x04", ".png": b"\x89PNG\r\n\x1a\n", ".jpg": b"\xff\xd8\xff",
    ".jpeg": b"\xff\xd8\xff",
}
_BOM = b"\xef\xbb\xbf"
# Giới hạn độ dài cột trong DB -> báo 422 rõ ràng thay vì để Postgres ném DataError (500)
_FRONTMATTER_LIMITS = {
    "doc_id": 64, "tieu_de": 256, "so_hieu": 64, "loai": 32, "phong_ban_so_huu": 64, "phien_ban": 16,
    "thay_the": 64,
}
_DOC_ID_RE = re.compile(r"^[A-Z][A-Z0-9]*-[A-Z]+-\d+")


def check_file(filename: str, content_type: str | None, data: bytes) -> str:
    """Kiểm tra đuôi, MIME và magic bytes. Trả về đuôi (chữ thường, có dấu chấm)."""
    ext = os.path.splitext(os.path.basename(filename or ""))[1].lower()
    if ext not in _MIME_BY_EXT:
        raise KbError(f"Không nhận tệp '{ext or filename}'. Dùng Markdown, PDF, Word hoặc ảnh PNG/JPG", 415)
    mime = (content_type or "").split(";")[0].strip().lower()
    if mime not in _UNDECLARED and mime not in _MIME_BY_EXT[ext]:
        raise KbError(f"Loại nội dung '{mime}' không khớp đuôi tệp {ext}", 415)
    if not data:
        raise KbError("Tệp rỗng", 422)
    magic = _MAGIC.get(ext)
    if magic and not data.startswith(magic):
        raise KbError(f"Nội dung tệp không phải định dạng {ext} thật", 415)
    return ext


def derive_doc_id(filename: str, sha: str) -> str:
    """Mã tài liệu khi tệp không mang doc_id: tiền tố dạng SVT-TB-018 ở tên tệp, không có thì UPLOAD-<sha>."""
    stem = os.path.splitext(os.path.basename(filename or ""))[0]
    m = _DOC_ID_RE.match(stem)
    return m.group(0) if m else f"UPLOAD-{sha[:12]}"


def _to_date(v) -> date | None:
    if v in (None, "", "null"):
        return None
    if isinstance(v, datetime):
        return v.date()
    return v if isinstance(v, date) else date.fromisoformat(str(v))


def _frontmatter_meta(data: bytes) -> dict:
    """Đọc frontmatter của tệp .md. Lỗi định dạng -> KbError 422, không để ValueError/YAMLError thành 500."""
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as e:
        raise KbError("Tệp Markdown phải mã hoá UTF-8", 422) from e
    if not text.startswith("---"):
        raise KbError("Tệp Markdown không có frontmatter: hãy điền thông tin tài liệu (meta)", 422)
    try:
        meta = parse_frontmatter(text).meta
        if not isinstance(meta["doc_id"], str):
            raise ValueError("doc_id phải là chuỗi")
        for key, limit in _FRONTMATTER_LIMITS.items():
            if meta.get(key) is not None and len(str(meta[key])) > limit:
                raise ValueError(f"{key} dài quá {limit} ký tự")
        _to_date(meta.get("hieu_luc_tu"))
    except (ValueError, TypeError, yaml.YAMLError) as e:
        raise KbError(f"Frontmatter không hợp lệ: {e}", 422) from e
    return meta


def _strip_frontmatter(text: str) -> str:
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) == 3:
            return parts[2]
    return text


def build_chunks(
    data: bytes, ext: str, doc_id: str, title: str, so_hieu: str | None = None
) -> tuple[list[Chunk], int]:
    """Tệp -> các Chunk đã embed (chưa gắn vào DB) và số trang phải OCR. Dùng chung cho upload và reindex.

    .md  : chunk theo heading (chunk_markdown), bỏ frontmatter nếu có.
    khác : trích trang bằng extract_pages (PDF text-layer, scan -> OCR, DOCX, ảnh) rồi chunk_text từng trang.
    Việc nặng CPU (OCR, embed) nên hàm này chạy đồng bộ; router dùng `def` để chạy trong thread pool.
    """
    if ext == ".md":
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError as e:
            raise KbError("Tệp Markdown phải mã hoá UTF-8", 422) from e
        pieces = chunk_markdown(_strip_frontmatter(text).strip(), settings.chunk_size, settings.chunk_overlap)
        ocr_pages = 0
    else:
        try:
            pages, ocr_pages = extract_pages(data, f"tai-lieu{ext}")
        except Exception as e:  # noqa: BLE001 - thư viện PDF/DOCX/OCR ném nhiều loại lỗi khác nhau
            if type(e).__name__ == "TesseractNotFoundError":
                raise KbError("Dịch vụ OCR chưa sẵn sàng (chưa cài Tesseract)", 503) from e
            log.warning("Không đọc được nội dung tệp %s: %s", ext, type(e).__name__)
            raise KbError("Không đọc được nội dung tệp (tệp hỏng hoặc không đúng định dạng)", 422) from e
        pieces = []
        for page_no, text in pages:
            pieces += chunk_text(text, settings.chunk_size, settings.chunk_overlap, page=page_no)
    pieces = [c for c in pieces if c.content.strip()]
    if not pieces:
        raise KbError("Không trích xuất được nội dung từ tài liệu", 422)

    head = {"doc_id": doc_id, "tieu_de": title, "so_hieu": so_hieu}  # giống tiền tố của kb_ingest
    texts = [f"{context_header(head, c.section)}\n{c.content}" for c in pieces]
    vectors = get_embedder().embed(texts, kind="passage")
    chunks = [
        Chunk(ordinal=i, page=c.page, section=c.section[:256], content=t, embedding=v)
        for i, (c, t, v) in enumerate(zip(pieces, texts, vectors, strict=True))
    ]
    return chunks, ocr_pages


def save_original(data: bytes, sha: str, ext: str) -> tuple[Path, bool]:
    """Lưu bản gốc vào upload_dir/<sha256><đuôi>. Trả (đường dẫn, mới tạo?). Ghi tạm rồi đổi tên nên không
    bao giờ để lại tệp ghi dở. Cùng nội dung = cùng tên tệp (có thể được nhiều tài liệu dùng chung)."""
    dest = Path(settings.upload_dir) / f"{sha}{ext}"
    if dest.exists():
        return dest, False
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_name(dest.name + ".part")
    tmp.write_bytes(data)
    os.replace(tmp, dest)
    return dest, True


def _supersede(db: Session, old_id: str, new_id: str, new_from: date | None, today: date) -> None:
    """Gán bản cũ: superseded_by = bản mới, effective_to = ngày bản mới có hiệu lực. Chưa commit: nằm cùng
    transaction với việc nạp bản mới, nên không bao giờ có cảnh bản mới lỗi mà bản cũ đã bị đóng."""
    if old_id == new_id:
        raise KbError("Tài liệu không thể thay thế chính nó", 422)
    old = db.execute(select(Document).where(Document.doc_id == old_id)).scalar_one_or_none()
    if old is None:
        raise KbError(f"Không tìm thấy tài liệu bị thay thế: {old_id}", 422)
    if old.superseded_by and old.superseded_by != new_id:
        raise KbError(f"{old_id} đã bị thay thế bởi {old.superseded_by}", 409)
    cutoff = new_from or today
    old.superseded_by = new_id
    if old.effective_to is None or old.effective_to > cutoff:
        old.effective_to = cutoff


def _check_meta(meta: DocMeta) -> None:
    if meta.visibility == "han-che" and not meta.allowed_departments and not meta.allowed_roles:
        raise KbError("Văn bản hạn chế cần khai báo ít nhất một phòng ban hoặc vai trò được xem", 422)


def upload_document(
    db: Session, *, data: bytes, filename: str, content_type: str | None, meta: DocMeta | None,
    actor: str | None, today: date | None = None,
) -> DocRow:
    """Nạp một tài liệu mới. Toàn bộ ghi DB (tài liệu, chunk, thay thế bản cũ, audit) trong MỘT transaction.

    Nhánh xử lý:
      - .md có frontmatter và meta = None -> kb_ingest.ingest_markdown (commit=False) trên bản đã lưu;
      - còn lại -> dùng meta (tệp không tự mang đủ thông tin);
      - .md không frontmatter mà không có meta, hoặc tệp khác không có meta -> 422.
    Trùng doc_id -> 409 (kiểm trước, và bắt cả IntegrityError khi hai request chạy đua).
    """
    today = today or date.today()
    ext = check_file(filename, content_type, data)
    if ext == ".md":
        data = data.removeprefix(_BOM)  # BOM đứng trước "---" làm ingest_markdown báo thiếu frontmatter
    sha = hashlib.sha256(data).hexdigest()

    use_frontmatter = ext == ".md" and meta is None
    if use_frontmatter:
        fm = _frontmatter_meta(data)
        doc_id, title = fm["doc_id"], str(fm["tieu_de"])
        supersedes, eff_from = fm.get("thay_the"), _to_date(fm.get("hieu_luc_tu"))
    elif meta is None:
        raise KbError("Tệp này không tự mang thông tin: cần điền loại, phòng ban và phạm vi xem (meta)", 422)
    else:
        _check_meta(meta)
        doc_id = derive_doc_id(filename, sha)
        title = (meta.title or "").strip() or os.path.splitext(os.path.basename(filename))[0]
        supersedes, eff_from = meta.supersedes, meta.effective_from
        if len(title) > 256:
            raise KbError("Tiêu đề dài quá 256 ký tự", 422)

    if db.execute(select(Document.id).where(Document.doc_id == doc_id)).first():
        raise KbError(f"Mã tài liệu {doc_id} đã có trong kho", 409)

    path, created = save_original(data, sha, ext)
    try:
        if supersedes:
            _supersede(db, str(supersedes), doc_id, eff_from, today)
        if use_frontmatter:
            try:
                ingest_markdown(db, path, commit=False)
            except (ValueError, yaml.YAMLError) as e:
                raise KbError(f"Không nạp được tệp: {e}", 422) from e
            doc = db.execute(select(Document).where(Document.doc_id == doc_id)).scalar_one()
            doc.uploaded_by = actor
            n_chunks = db.execute(
                select(func.count()).select_from(Chunk).where(Chunk.document_id == doc.id)
            ).scalar_one()
            ocr_pages = 0
        else:
            chunks, ocr_pages = build_chunks(data, ext, doc_id, title)
            depts, roles = list(meta.allowed_departments), list(meta.allowed_roles)
            if meta.visibility == "phong-ban" and not depts and not roles:
                depts = [meta.department]  # mặc định an toàn như ingest_document: chỉ phòng sở hữu xem
            doc = Document(
                doc_id=doc_id, title=title, doc_type=meta.doc_type, source=path.as_posix(),
                department=meta.department, visibility=meta.visibility,
                allowed_departments=depts, allowed_roles=roles,
                classification="Mat" if meta.classified else "thuong",
                effective_from=meta.effective_from, supersedes=meta.supersedes,
                uploaded_by=actor, ocr_pages=ocr_pages, content_hash=sha,
            )
            doc.chunks = chunks
            n_chunks = len(chunks)
            db.add(doc)
        # Riêng tư: không ghi tên tệp vào audit (cùng nguyên tắc với /api/ocr)
        db.add(_audit(actor, EV_UPLOAD, {
            "doc_id": doc_id, "kind": ext.lstrip("."), "bytes": len(data), "chunks": n_chunks,
            "ocr_pages": ocr_pages, "supersedes": supersedes,
        }))
        db.commit()
    except IntegrityError as e:  # hai request cùng doc_id chạy đua, lọt qua bước kiểm trước
        db.rollback()
        if created:
            path.unlink(missing_ok=True)
        raise KbError(f"Mã tài liệu {doc_id} đã có trong kho", 409) from e
    except BaseException:
        db.rollback()
        if created:
            path.unlink(missing_ok=True)
        raise
    return get_row(db, doc_id)


# ================================================================ thao tác hàng loạt (bước 4)

MAX_BATCH = 200


@dataclass(frozen=True)
class BatchItem:
    doc_id: str
    error: str | None = None  # None = thành công

    @property
    def ok(self) -> bool:
        return self.error is None


def _get_doc(db: Session, doc_id: str) -> Document:
    doc = db.execute(select(Document).where(Document.doc_id == doc_id)).scalar_one_or_none()
    if doc is None:
        raise DocNotFound(doc_id)
    return doc


def _run_batch(db: Session, doc_ids: list[str], action) -> list[BatchItem]:
    """Chạy `action(db, doc_id)` cho từng tài liệu, MỖI tài liệu một transaction: một tài liệu lỗi thì
    rollback riêng nó, các tài liệu còn lại vẫn được xử lý. Trùng id trong lô chỉ chạy một lần.

    .NET: như vòng `foreach` mà mỗi vòng có `using var tx = db.Database.BeginTransaction()` riêng,
    thay vì một `SaveChanges` cho cả lô.
    """
    items: list[BatchItem] = []
    for doc_id in dict.fromkeys(doc_ids):
        try:
            action(db, doc_id)
            items.append(BatchItem(doc_id))
        except DocNotFound:
            db.rollback()
            items.append(BatchItem(doc_id, "Không tìm thấy tài liệu"))
        except KbError as e:
            db.rollback()
            items.append(BatchItem(doc_id, str(e)))
        except Exception:
            db.rollback()
            log.exception("Thao tác hàng loạt lỗi ở %s", doc_id)
            items.append(BatchItem(doc_id, "Lỗi không xác định (xem nhật ký máy chủ)"))
    return items


# ---- nạp lại

def _reindex_one(db: Session, doc_id: str, actor: str | None) -> None:
    """Cắt đoạn và tạo vector lại từ bản gốc (`source`), GIỮ NGUYÊN metadata trong DB.

    Cố ý không dùng ingest_markdown(force=True): nó ghi đè mọi cột từ frontmatter, kể cả `superseded_by` và
    `effective_to` do upload bản mới đặt trong DB (frontmatter của bản cũ không có), nên nạp lại sẽ làm bản
    cũ "sống lại". Muốn cập nhật metadata từ frontmatter thì dùng `python -m app.rag.kb_ingest --force`.
    Vector mới tính xong rồi mới đụng DB: lỗi thì chunk cũ còn nguyên.
    """
    doc = _get_doc(db, doc_id)
    path = Path(doc.source)
    if not path.is_file():
        raise KbError("Không tìm thấy tệp gốc để nạp lại", 409)
    ext = path.suffix.lower()
    if ext not in _MIME_BY_EXT:
        raise KbError(f"Không nạp lại được tệp {ext or 'không đuôi'}", 422)

    chunks, ocr_pages = build_chunks(path.read_bytes(), ext, doc.doc_id, doc.title, doc.so_hieu)
    # xoá chunk cũ bằng một câu DELETE (không nạp vector cũ lên RAM như gán doc.chunks = ...)
    db.execute(delete(Chunk).where(Chunk.document_id == doc.id))
    for c in chunks:
        c.document_id = doc.id
    db.add_all(chunks)
    doc.ocr_pages = ocr_pages
    db.add(_audit(actor, EV_REINDEX, {"doc_id": doc_id, "chunks": len(chunks)}))
    db.commit()


def reindex_documents(
    db: Session, doc_ids: list[str], actor: str | None
) -> list[BatchItem]:
    return _run_batch(db, doc_ids, lambda s, d: _reindex_one(s, d, actor))


# ---- cách ly

def set_quarantine(
    db: Session, doc_id: str, on: bool, actor: str | None
) -> bool:
    """Bật/tắt cờ cách ly (retriever.py đã lọc `quarantined` trong SQL). Trả True nếu có đổi.
    Đặt lại đúng giá trị hiện tại thì không làm gì và không ghi audit."""
    doc = _get_doc(db, doc_id)
    if doc.quarantined == on:
        return False
    doc.quarantined = on
    db.add(_audit(actor, EV_QUARANTINE, {"doc_id": doc_id, "on": on}))
    db.commit()
    return True


# ---- xoá

def _remove_stored_file(db: Session, source: str) -> None:
    """Xoá bản gốc, nhưng CHỈ khi nó nằm trong upload_dir và không còn tài liệu nào khác trỏ tới
    (hai lần upload cùng nội dung dùng chung một tệp). Không bao giờ đụng data/knowledge."""
    try:
        path = Path(source).resolve()
        if not path.is_relative_to(Path(settings.upload_dir).resolve()):
            return
        still_used = select(func.count()).select_from(Document).where(Document.source == source)
        if db.execute(still_used).scalar_one():
            return
        path.unlink(missing_ok=True)
    except OSError as e:  # tệp mồ côi vô hại hơn là làm lỗi một thao tác xoá đã commit
        log.warning("Không xoá được bản gốc của tài liệu đã gỡ: %s", type(e).__name__)


def _delete_one(db: Session, doc_id: str, actor: str | None) -> None:
    doc = _get_doc(db, doc_id)
    source = doc.source
    n_chunks = db.execute(
        select(func.count()).select_from(Chunk).where(Chunk.document_id == doc.id)
    ).scalar_one()
    # gỡ liên kết từ các tài liệu khác (không để trỏ vào tài liệu đã xoá). effective_to của bản cũ giữ nguyên:
    # không biết giá trị trước khi bị đặt, và đoán sai còn tệ hơn để nguyên.
    db.execute(update(Document).where(Document.superseded_by == doc_id).values(superseded_by=None))
    db.execute(update(Document).where(Document.supersedes == doc_id).values(supersedes=None))
    classified = doc.classification == "Mat"
    # DELETE trực tiếp thay vì db.delete(doc): ORM sẽ nạp cả collection chunks (kèm vector) để xoá từng dòng
    db.execute(delete(Chunk).where(Chunk.document_id == doc.id))
    db.execute(delete(Document).where(Document.id == doc.id))
    db.add(_audit(actor, EV_DELETE, {
        "doc_id": doc_id, "chunks": n_chunks, "classified": classified,
    }))
    db.commit()
    _remove_stored_file(db, source)  # sau commit: DB lỗi thì tệp vẫn còn để thử lại


def delete_documents(
    db: Session, doc_ids: list[str], actor: str | None
) -> list[BatchItem]:
    return _run_batch(db, doc_ids, lambda s, d: _delete_one(s, d, actor))
