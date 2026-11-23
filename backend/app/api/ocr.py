"""Router /api/ocr: chỉ nhận request, kiểm tra quyền, gọi app.ocr.service, ghi vết. Không chứa nghiệp vụ.

Riêng tư: KHÔNG ghi tên file hay nội dung văn bản vào audit/usage (ảnh có thể chứa dữ liệu nhạy cảm).
"""

from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends, File, HTTPException, Query, Response, UploadFile
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import UserInfo, get_current_user, get_db
from app.config import settings
from app.llm.base import Usage
from app.observability import DbAuditSink, record_usage
from app.ocr import extract, jobs, service
from app.ocr.engines import list_engines
from app.ocr.errors import OcrError
from app.ocr.schemas import SCHEMAS
from app.ocr.schemas.base import EmployeeInfo

router = APIRouter(tags=["ocr"])


class EngineOut(BaseModel):
    name: str
    available: bool


class EnginesOut(BaseModel):
    default: str
    engines: list[EngineOut]


class PageOut(BaseModel):
    page: int
    text: str
    source: Literal["text-layer", "ocr"]
    ms: int


class RecognizeOut(BaseModel):
    engine: str
    kind: Literal["pdf", "image"]
    pages: list[PageOut]
    ocr_pages: int
    ms: int


@router.get("/engines", response_model=EnginesOut)
def engines(user: UserInfo = Depends(get_current_user)):
    return {"default": settings.ocr_engine, "engines": list_engines()}


@router.post("/recognize", response_model=RecognizeOut)
def recognize(
    file: UploadFile = File(...),
    engine: str | None = Query(None, description="Tên engine; bỏ trống = engine mặc định"),
    pages: str | None = Query(None, description="Trang cần đọc, vd 1,3-5; bỏ trống = tất cả"),
    user: UserInfo = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    limit = int(settings.ocr_max_mb * 1024 * 1024)
    data = file.file.read(limit + 1)  # đọc dư 1 byte để biết là vượt, không nạp cả file khổng lồ
    if len(data) > limit:
        raise HTTPException(413, f"File vượt giới hạn {settings.ocr_max_mb:g} MB")
    try:
        result = service.recognize(data, engine=engine, pages=pages)
    except OcrError as e:
        raise HTTPException(e.status_code, str(e)) from e

    DbAuditSink(db, user.id, None).log("ocr_run", {
        "engine": result.engine, "kind": result.kind, "bytes": len(data),
        "pages": len(result.pages), "ocr_pages": result.ocr_pages, "ms": result.ms,
    })
    record_usage(db, user, f"local:{result.engine}", Usage(), purpose="ocr")  # engine cục bộ: chi phí 0
    return {
        "engine": result.engine, "kind": result.kind, "ocr_pages": result.ocr_pages, "ms": result.ms,
        "pages": [vars(p) for p in result.pages],
    }


# ---------- Job bất đồng bộ ----------

class JobOut(BaseModel):
    job_id: str
    status: Literal["queued", "running", "done", "failed"]
    engine: str
    kind: Literal["pdf", "image"] | None = None
    pages_total: int
    pages_done: int
    error: str | None = None
    created_at: datetime
    started_at: datetime | None = None
    finished_at: datetime | None = None
    expires_at: datetime


class JobDetailOut(JobOut):
    pages: list[PageOut] | None = None  # chỉ có khi status = done
    ocr_pages: int | None = None


def _job_out(job) -> dict:
    return {
        "job_id": job.id, "status": job.status, "engine": job.engine, "kind": job.kind,
        "pages_total": job.pages_total, "pages_done": job.pages_done, "error": job.error,
        "created_at": job.created_at, "started_at": job.started_at,
        "finished_at": job.finished_at, "expires_at": job.expires_at,
    }


@router.post("/jobs", status_code=202, response_model=JobOut)
def create_job(
    response: Response,
    file: UploadFile = File(...),
    engine: str | None = Query(None, description="Tên engine; bỏ trống = engine mặc định"),
    pages: str | None = Query(None, description="Trang cần đọc, vd 1,3-5; bỏ trống = tất cả"),
    user: UserInfo = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    limit = int(settings.ocr_job_max_mb * 1024 * 1024)
    data = file.file.read(limit + 1)
    if len(data) > limit:
        raise HTTPException(413, f"File vượt giới hạn {settings.ocr_job_max_mb:g} MB")
    try:
        job = jobs.create(db, user, data, engine=engine, pages=pages)
    except OcrError as e:
        raise HTTPException(e.status_code, str(e)) from e
    response.headers["Location"] = f"/api/ocr/jobs/{job.id}"
    return _job_out(job)


@router.get("/jobs", response_model=list[JobOut])
def list_jobs(user: UserInfo = Depends(get_current_user), db: Session = Depends(get_db)):
    return [_job_out(j) for j in jobs.list_for_user(db, user)]


@router.get("/jobs/{job_id}", response_model=JobDetailOut)
def get_job(job_id: str, user: UserInfo = Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        job = jobs.get_for_user(db, user, job_id)
    except OcrError as e:
        raise HTTPException(e.status_code, str(e)) from e
    out = _job_out(job)
    if job.status == "done":
        out["pages"] = job.result or []
        out["ocr_pages"] = sum(1 for p in job.result or [] if p["source"] == "ocr")
    return out


@router.delete("/jobs/{job_id}", status_code=204)
def delete_job(job_id: str, user: UserInfo = Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        jobs.delete_for_user(db, user, job_id)
    except OcrError as e:
        raise HTTPException(e.status_code, str(e)) from e


# ---------- Trích xuất có cấu trúc ----------

class SchemaOut(BaseModel):
    id: str
    title: str
    description: str


class FindingOut(BaseModel):
    code: str
    severity: Literal["error", "warning", "info"]
    message: str
    field: str | None = None
    rule: str | None = None
    over_amount: int | None = None


class ExtractOut(BaseModel):
    schema_id: str
    data: dict
    findings: list[FindingOut]
    needs_review: bool
    engine: str
    kind: Literal["pdf", "image"]
    pages: int
    ocr_pages: int
    llm_model: str
    ms: int


@router.get("/schemas", response_model=list[SchemaOut])
def list_schemas(user: UserInfo = Depends(get_current_user)):
    return [{"id": s.id, "title": s.title, "description": s.description} for s in SCHEMAS.values()]


def _employee_lookup(db: Session):
    """Tra danh bạ theo mã NV để biết tên và cấp bậc (định mức khách sạn). Không trả thêm gì ra ngoài."""
    from app.models import Employee

    def lookup(code: str) -> EmployeeInfo | None:
        emp = db.execute(select(Employee).where(Employee.code == code)).scalar_one_or_none()
        if emp is None:
            return None
        roles = set(emp.roles or [])
        return EmployeeInfo(
            code=emp.code, full_name=emp.full_name, active=emp.status == "dang-lam",
            truong_phong_tro_len=bool(roles & {"truong-phong", "executive"}),
        )

    return lookup


@router.post("/extract", response_model=ExtractOut)
def extract_document(
    file: UploadFile = File(...),
    schema_id: str = Query("cong-tac-phi", description="Loại tài liệu cần trích xuất (xem GET /schemas)"),
    engine: str | None = Query(None, description="Engine OCR; bỏ trống = mặc định"),
    pages: str | None = Query(None, description="Trang cần đọc, vd 1,3-5; bỏ trống = tất cả"),
    user: UserInfo = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """OCR -> LLM chép ra JSON -> đối chiếu OCR -> kiểm tra quy định.

    Chỉ kết luận `needs_review`, không bao giờ duyệt chi.
    """
    limit = int(settings.ocr_max_mb * 1024 * 1024)
    data = file.file.read(limit + 1)
    if len(data) > limit:
        raise HTTPException(413, f"File vượt giới hạn {settings.ocr_max_mb:g} MB")
    try:
        res = extract.extract(
            data, schema_id, engine=engine, pages=pages, employee_lookup=_employee_lookup(db)
        )
    except OcrError as e:
        raise HTTPException(e.status_code, str(e)) from e

    counts = {sev: sum(1 for f in res.findings if f.severity == sev) for sev in ("error", "warning")}
    DbAuditSink(db, user.id, None).log("ocr_extract", {
        "schema": res.schema_id, "engine": res.engine, "llm": res.llm_model, "kind": res.kind,
        "pages": res.pages, "ocr_pages": res.ocr_pages,
        "errors": counts["error"], "warnings": counts["warning"],
        "needs_review": res.needs_review, "ms": res.ms,
    })
    record_usage(db, user, res.llm_model, res.usage, purpose="ocr-extract")
    return {
        "schema_id": res.schema_id, "data": res.data, "findings": [vars(f) for f in res.findings],
        "needs_review": res.needs_review, "engine": res.engine, "kind": res.kind, "pages": res.pages,
        "ocr_pages": res.ocr_pages, "llm_model": res.llm_model, "ms": res.ms,
    }
