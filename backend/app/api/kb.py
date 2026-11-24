"""Router /api/kb (kho tri thức): schema JSON cho trang portal và hàm chuyển ORM -> schema.

Hợp đồng: portal/src/features/kb/types.ts + api/http.ts. JSON dùng camelCase, Python dùng snake_case.
Kế hoạch: docs/08-ke-hoach-api-kb.md. File này chỉ nhận request, kiểm quyền, gọi app.rag.kb_service
(theo khuôn app/api/ocr.py); nghiệp vụ không nằm ở đây.
"""

import os
from datetime import date, datetime
from typing import Literal

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Response, UploadFile
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, ValidationError
from pydantic.alias_generators import to_camel
from sqlalchemy.orm import Session

from app.api.deps import Actor, get_db, get_kb_admin
from app.config import settings
from app.models import Document
from app.rag import kb_service
from app.rag.kb_service import DocNotFound, KbError

# Mọi endpoint của module này chỉ dành cho admin.
# Xác thực import từ app/api/deps.py, không import thẳng app.security.
router = APIRouter(tags=["kb"])
admin_only = get_kb_admin  # JWT cũ (role admin) hoặc token Zitadel của nhân viên có vai trò admin


class CamelModel(BaseModel):
    """Đọc/ghi JSON camelCase, nhưng trong code vẫn gọi bằng snake_case.

    .NET: tương đương `JsonSerializerOptions { PropertyNamingPolicy = JsonNamingPolicy.CamelCase }`.
    Khác biệt: ở đây đặt trên từng model (qua `alias_generator`), không phải trên serializer toàn cục.
    FastAPI mặc định trả `response_model` theo alias (`response_model_by_alias=True`),
    nên không cần cấu hình thêm.
    `populate_by_name=True` cho phép tạo model bằng snake_case trong code và test.
    """

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


DocStatus = Literal["ready", "processing", "error", "quarantined"]
FileKind = Literal["md", "pdf", "docx", "image", "other"]
Visibility = Literal["cong-khai", "phong-ban", "han-che"]


# ---------- Response ----------

class KbDocumentOut(CamelModel):
    doc_id: str
    so_hieu: str | None
    title: str
    doc_type: str | None
    file_kind: FileKind
    department: str
    # `str` chứ không phải Literal: một dòng DB có giá trị lạ không được làm 500 cả danh sách,
    # vì admin dùng trang này để tìm đúng những dòng hỏng. Quy tắc xem vẫn fail closed ở acl.can_read.
    visibility: str
    allowed_departments: list[str]
    allowed_roles: list[str]
    classified: bool  # classification == "Mat"
    effective_from: date | None
    effective_to: date | None
    supersedes: str | None
    superseded_by: str | None
    version: str | None
    status: DocStatus
    # Backend chưa lưu lý do (processing/error chưa có thật) nên hiện luôn là null.
    # Giao diện chỉ đọc nó qua kiểm tra truthy, nên null thay cho bỏ khoá vẫn đúng.
    status_note: str | None = None
    chunk_count: int
    ocr_pages: int
    source: str
    uploaded_by: str | None  # email người nạp (Zitadel); None nếu nạp từ thư mục data/knowledge
    created_at: datetime


class KbChunkOut(CamelModel):
    ordinal: int
    page: int | None
    section: str
    content: str


class KbHistoryEntryOut(CamelModel):
    at: datetime
    by: str
    text: str


class KbDocumentDetailOut(KbDocumentOut):
    chunks: list[KbChunkOut]
    history: list[KbHistoryEntryOut]
    # True khi lượt xem này đã được ghi audit (tài liệu Mật, ADR-004 mục 4)
    access_logged: bool = False


class AccessCheckOut(CamelModel):
    allowed: bool
    reason: str
    person: str | None


# ---------- Request ----------

class UploadMetaIn(CamelModel):
    """Phần `meta` (chuỗi JSON trong multipart) khi tệp không tự mang đủ thông tin."""

    title: str | None = Field(None, max_length=256)  # độ dài theo cột trong DB: quá thì 422 thay vì 500
    doc_type: str = Field(max_length=32)
    department: str = Field(max_length=64)
    visibility: Visibility  # đầu vào thì kiểm chặt: giá trị lạ -> 422
    allowed_departments: list[str] = Field(default_factory=list)
    allowed_roles: list[str] = Field(default_factory=list)
    classified: bool = False
    effective_from: date | None = None
    supersedes: str | None = Field(None, max_length=64)


class DocIdsIn(CamelModel):
    doc_ids: list[str] = Field(min_length=1, max_length=kb_service.MAX_BATCH)


class QuarantineIn(CamelModel):
    on: bool


# ---------- Chuyển đổi ----------

_FILE_KIND_BY_EXT: dict[str, FileKind] = {
    ".md": "md",
    ".pdf": "pdf",
    ".docx": "docx",
    ".png": "image", ".jpg": "image", ".jpeg": "image", ".tif": "image", ".tiff": "image", ".bmp": "image",
}


def file_kind_of(source: str) -> FileKind:
    """Suy ra loại tệp từ đuôi của `source` (DB không có cột này)."""
    return _FILE_KIND_BY_EXT.get(os.path.splitext(source)[1].lower(), "other")


def to_kb_document(doc: Document, username: str | None, chunk_count: int) -> KbDocumentOut:
    """ORM `Document` -> schema trả về. MỌI trường suy ra (status, fileKind, classified) gom ở đây.

    `username` (email người nạp) và `chunk_count` do người gọi truyền vào: số chunk lấy bằng subquery
    count(chunks) trong cùng MỘT truy vấn, tránh N+1.

    .NET: đây là AutoMapper profile / hàm `ToDto()` (Entity -> DTO). Điểm khác EF Core: entity ở đây
    không tự nạp thuộc tính điều hướng (lazy load) nên hai giá trị phụ phải được truyền vào tường minh.
    """
    return KbDocumentOut(
        doc_id=doc.doc_id,
        so_hieu=doc.so_hieu,
        title=doc.title,
        doc_type=doc.doc_type,
        file_kind=file_kind_of(doc.source),
        department=doc.department,
        visibility=doc.visibility,
        allowed_departments=list(doc.allowed_departments or []),
        allowed_roles=list(doc.allowed_roles or []),
        classified=doc.classification == "Mat",
        effective_from=doc.effective_from,
        effective_to=doc.effective_to,
        supersedes=doc.supersedes,
        superseded_by=doc.superseded_by,
        version=doc.version,
        status="quarantined" if doc.quarantined else "ready",
        chunk_count=chunk_count,
        ocr_pages=doc.ocr_pages or 0,
        source=doc.source,
        uploaded_by=username,
        created_at=doc.created_at,
    )


def to_kb_detail(detail: kb_service.DocDetail) -> KbDocumentDetailOut:
    base = to_kb_document(detail.row.document, detail.row.username, detail.row.chunk_count)
    return KbDocumentDetailOut(
        **base.model_dump(),
        chunks=[KbChunkOut(**vars(c)) for c in detail.chunks],
        history=[KbHistoryEntryOut(**vars(h)) for h in detail.history],
        access_logged=detail.access_logged,
    )


# ---------- Endpoint chỉ đọc ----------
# Dùng `def` thường (không `async def`): FastAPI chạy chúng trong thread pool nên truy vấn DB đồng bộ
# không chặn event loop. (.NET: ở đây phải tự chọn; Entity Framework có sẵn SaveChangesAsync, còn
# SQLAlchemy Session đồng bộ thì `def` + thread pool là cách đơn giản và đúng.)

@router.get("/documents", response_model=list[KbDocumentOut])
def list_documents(user: Actor = Depends(admin_only), db: Session = Depends(get_db)):
    return [to_kb_document(r.document, r.username, r.chunk_count) for r in kb_service.list_documents(db)]


# ---------- Thao tác ghi hàng loạt ----------
# Khai báo TRƯỚC các route `/documents/{doc_id}...` để các đường dẫn tĩnh `documents:reindex` và
# `documents:delete` không bao giờ bị hiểu nhầm là một doc_id (thứ tự khai báo quyết định, giống route
# constraint của ASP.NET Core: route cụ thể phải được ưu tiên hơn route có tham số).

def _batch_response(items: list[kb_service.BatchItem], verb: str) -> Response:
    """Cả lô thành công: 204 như hợp đồng. Có tài liệu lỗi: 207 Multi-Status kèm `detail` (người đọc thấy
    ngay) và `results` từng tài liệu; các tài liệu còn lại vẫn đã được xử lý."""
    failed = [i for i in items if not i.ok]
    if not failed:
        return Response(status_code=204)
    detail = f"{verb} lỗi {len(failed)}/{len(items)} tài liệu: " + "; ".join(
        f"{i.doc_id} ({i.error})" for i in failed
    )
    results = [{"docId": i.doc_id, "ok": i.ok, "error": i.error} for i in items]
    return JSONResponse(status_code=207, content={"detail": detail, "results": results})


_BATCH_RESPONSES = {207: {"description": "Một số tài liệu lỗi; các tài liệu còn lại đã xử lý xong"}}


@router.post("/documents:reindex", status_code=204, responses=_BATCH_RESPONSES)
def reindex_documents(body: DocIdsIn, user: Actor = Depends(admin_only), db: Session = Depends(get_db)):
    # Đồng bộ: embed nặng CPU, lô lớn có thể lâu (trạng thái `processing` thật + hàng đợi: để sau, docs/08)
    return _batch_response(kb_service.reindex_documents(db, body.doc_ids, user.email), "Nạp lại")


@router.post("/documents:delete", status_code=204, responses=_BATCH_RESPONSES)
def delete_documents(body: DocIdsIn, user: Actor = Depends(admin_only), db: Session = Depends(get_db)):
    return _batch_response(kb_service.delete_documents(db, body.doc_ids, user.email), "Xoá")


@router.put("/documents/{doc_id}/quarantine", status_code=204)
def set_quarantine(
    doc_id: str, body: QuarantineIn, user: Actor = Depends(admin_only), db: Session = Depends(get_db)
):
    try:
        kb_service.set_quarantine(db, doc_id, body.on, user.email)
    except DocNotFound as e:
        raise HTTPException(404, "Không tìm thấy tài liệu") from e
    return Response(status_code=204)


@router.get("/documents/{doc_id}", response_model=KbDocumentDetailOut)
def get_document(doc_id: str, user: Actor = Depends(admin_only), db: Session = Depends(get_db)):
    try:
        detail = kb_service.get_detail(db, doc_id, actor=user.email)
    except DocNotFound as e:
        raise HTTPException(404, "Không tìm thấy tài liệu") from e
    return to_kb_detail(detail)


@router.get("/documents/{doc_id}/access", response_model=AccessCheckOut)
def check_access(
    doc_id: str,
    email: str = Query(..., min_length=3, description="Email nhân viên cần kiểm tra"),
    user: Actor = Depends(admin_only),
    db: Session = Depends(get_db),
):
    try:
        res = kb_service.check_access(db, doc_id, email)
    except DocNotFound as e:
        raise HTTPException(404, "Không tìm thấy tài liệu") from e
    return AccessCheckOut(allowed=res.allowed, reason=res.reason, person=res.person)


# ---------- Upload ----------

@router.post("/documents", status_code=201, response_model=KbDocumentOut)
def upload_document(
    file: UploadFile = File(...),
    meta: str | None = Form(None, description="Chuỗi JSON UploadMeta; bỏ trống khi .md đã có frontmatter"),
    user: Actor = Depends(admin_only),
    db: Session = Depends(get_db),
):
    # `def` thường: embed và OCR nặng CPU, chạy trong thread pool để không chặn event loop.
    limit = int(settings.max_upload_mb * 1024 * 1024)
    data = file.file.read(limit + 1)  # đọc dư 1 byte để biết là vượt, không nạp cả tệp khổng lồ vào RAM
    if len(data) > limit:
        raise HTTPException(413, f"Tệp vượt giới hạn {settings.max_upload_mb:g} MB")

    doc_meta = None
    if meta and meta.strip():
        try:
            m = UploadMetaIn.model_validate_json(meta)
        except ValidationError as e:
            first = e.errors()[0]
            where = ".".join(str(p) for p in first["loc"])
            raise HTTPException(422, f"meta không hợp lệ ({where}): {first['msg']}") from e
        doc_meta = kb_service.DocMeta(**m.model_dump())
    try:
        row = kb_service.upload_document(
            db, data=data, filename=file.filename or "", content_type=file.content_type,
            meta=doc_meta, actor=user.email,
        )
    except KbError as e:
        raise HTTPException(e.status_code, str(e)) from e
    return to_kb_document(row.document, row.username, row.chunk_count)
