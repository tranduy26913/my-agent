"""Thư viện văn bản cho MỌI nhân viên: các tài liệu trong kho mà CHÍNH họ được xem (docs/07 mục 9.2).

Quyền xem lọc ngay trong SQL bằng `acl_sql(principal)` (ADR-001), cùng bộ lọc với bộ truy xuất RAG, nên thư viện
không bao giờ cho thấy một tài liệu mà trợ lý sẽ không đọc cho người đó. Tài liệu bị cách ly thì ẩn.

Chỉ trả metadata. Không trả nội dung chunk, đường dẫn `source`, người nạp, danh sách phòng/vai trò được xem (cấu hình
phân quyền không phải việc của người đọc) và không trả mã tài liệu thay thế mà người đó không xem được.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from sqlalchemy import and_, case, func, or_, select
from sqlalchemy.orm import Session

from app.models import Document
from app.rag.acl import Principal, acl_sql

STATUSES = ("hieu-luc", "het-hieu-luc", "chua-hieu-luc")


@dataclass(frozen=True)
class LibDoc:
    doc_id: str
    so_hieu: str | None
    title: str
    doc_type: str | None
    department: str
    classified: bool
    effective_from: date | None
    effective_to: date | None
    supersedes: str | None
    superseded_by: str | None
    version: str | None
    status: str


@dataclass(frozen=True)
class Facet:
    value: str
    count: int


@dataclass(frozen=True)
class Library:
    items: list[LibDoc]
    total_visible: int  # số tài liệu người này được xem (trước khi lọc)
    doc_types: list[Facet]
    departments: list[Facet]
    statuses: list[Facet]


def _status_expr(today: date):
    """Cùng quy tắc với in_force_sql của bộ truy xuất: còn hiệu lực khi từ <= hôm nay < đến."""
    return case(
        (and_(Document.effective_from.is_not(None), Document.effective_from > today), "chua-hieu-luc"),
        (and_(Document.effective_to.is_not(None), Document.effective_to <= today), "het-hieu-luc"),
        else_="hieu-luc",
    )


def _escape_like(s: str) -> str:
    return s.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def list_library(
    db: Session,
    p: Principal,
    *,
    today: date,
    doc_type: str | None = None,
    department: str | None = None,
    status: str | None = None,
    q: str | None = None,
) -> Library:
    visible = and_(acl_sql(p), Document.quarantined.is_(False))
    state = _status_expr(today)

    # Số đếm cho ô lọc tính trên TẬP ĐƯỢC XEM (chưa lọc), nên không lộ ra tài liệu người này không thấy.
    def facet(col) -> list[Facet]:
        rows = db.execute(select(col, func.count()).where(visible).group_by(col).order_by(func.count().desc(), col))
        return [Facet(str(v), n) for v, n in rows.all() if v]

    doc_types, departments, statuses = facet(Document.doc_type), facet(Document.department), facet(state)
    statuses.sort(key=lambda f: STATUSES.index(f.value))
    visible_ids = set(db.execute(select(Document.doc_id).where(visible)).scalars())

    stmt = select(Document, state).where(visible)
    if doc_type:
        stmt = stmt.where(Document.doc_type == doc_type)
    if department:
        stmt = stmt.where(Document.department == department)
    if status in STATUSES:
        stmt = stmt.where(state == status)
    if q and q.strip():
        like = f"%{_escape_like(q.strip())}%"
        stmt = stmt.where(
            or_(
                Document.title.ilike(like, escape="\\"),
                Document.so_hieu.ilike(like, escape="\\"),
                Document.doc_id.ilike(like, escape="\\"),
            )
        )
    stmt = stmt.order_by(
        case((state == "hieu-luc", 0), (state == "chua-hieu-luc", 1), else_=2),
        Document.doc_type,
        Document.effective_from.desc().nulls_last(),
        Document.doc_id,
    )

    def seen(doc_id: str | None) -> str | None:
        return doc_id if doc_id in visible_ids else None

    items = [
        LibDoc(
            doc_id=d.doc_id,
            so_hieu=d.so_hieu,
            title=d.title,
            doc_type=d.doc_type,
            department=d.department,
            classified=d.classification == "Mat",
            effective_from=d.effective_from,
            effective_to=d.effective_to,
            supersedes=seen(d.supersedes),
            superseded_by=seen(d.superseded_by),
            version=d.version,
            status=st,
        )
        for d, st in db.execute(stmt).all()
    ]
    return Library(items, len(visible_ids), doc_types, departments, statuses)
