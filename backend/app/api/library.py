"""GET /api/kb/library: thư viện văn bản cho trang /tools/van-ban (docs/07 mục 9.2).

Dành cho MỌI nhân viên đang làm việc (get_principal), khác phần còn lại của /api/kb (chỉ admin). Danh tính và quyền
xem lấy từ token + bảng employees; admin cũng chỉ thấy phần mình được xem (ADR-001: không ngoại lệ cho admin).
"""

from datetime import date
from typing import Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_principal
from app.api.kb import CamelModel
from app.rag import library_service
from app.rag.acl import Principal

router = APIRouter(tags=["kb"])


class LibraryDocOut(CamelModel):
    doc_id: str
    so_hieu: str | None
    title: str
    doc_type: str | None
    department: str
    classified: bool  # Mật: người có quyền xem biết nó tồn tại, nhưng trợ lý không đọc nội dung (CTA-CS-007)
    effective_from: date | None
    effective_to: date | None
    supersedes: str | None
    superseded_by: str | None
    version: str | None
    status: Literal["hieu-luc", "het-hieu-luc", "chua-hieu-luc"]


class FacetOut(CamelModel):
    value: str
    count: int


class LibraryOut(CamelModel):
    items: list[LibraryDocOut]
    total_visible: int
    doc_types: list[FacetOut]
    departments: list[FacetOut]
    statuses: list[FacetOut]
    today: date


@router.get("/library", response_model=LibraryOut)
def library(
    type: str | None = Query(default=None, max_length=32, description="Loại văn bản (doc_type)"),
    department: str | None = Query(default=None, max_length=64),
    status: Literal["hieu-luc", "het-hieu-luc", "chua-hieu-luc"] | None = None,
    q: str | None = Query(default=None, max_length=100, description="Một phần tiêu đề, số hiệu hoặc mã"),
    p: Principal = Depends(get_principal),
    db: Session = Depends(get_db),
) -> LibraryOut:
    today = date.today()
    lib = library_service.list_library(db, p, today=today, doc_type=type, department=department, status=status, q=q)
    return LibraryOut(
        items=[LibraryDocOut(**vars(d)) for d in lib.items],
        total_visible=lib.total_visible,
        doc_types=[FacetOut(**vars(f)) for f in lib.doc_types],
        departments=[FacetOut(**vars(f)) for f in lib.departments],
        statuses=[FacetOut(**vars(f)) for f in lib.statuses],
        today=today,
    )
