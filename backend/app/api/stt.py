"""Router /api/stt: chỉ nhận request, kiểm tra quyền, gọi app.stt, ghi vết. Không chứa nghiệp vụ (ADR-006).

Riêng tư: KHÔNG ghi tên file hay nội dung văn bản vào audit/usage (ghi âm họp có thể chứa dữ liệu nhạy cảm).
"""

from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends, File, HTTPException, Query, Response, UploadFile
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import UserInfo, get_db, get_stt_user
from app.config import settings
from app.stt import files, jobs
from app.stt.engines import list_engines
from app.stt.errors import SttError

router = APIRouter(tags=["stt"])


class EngineOut(BaseModel):
    name: str
    available: bool


class EnginesOut(BaseModel):
    default: str
    engines: list[EngineOut]


class SegmentOut(BaseModel):
    start: float
    end: float
    text: str


class JobOut(BaseModel):
    job_id: str
    status: Literal["queued", "running", "done", "failed"]
    engine: str
    language: str | None = None
    duration_s: float  # 0 cho tới khi biết thời lượng (sau bước đổi định dạng)
    done_s: float
    error: str | None = None
    created_at: datetime
    started_at: datetime | None = None
    finished_at: datetime | None = None
    expires_at: datetime


class JobDetailOut(JobOut):
    segments: list[SegmentOut] | None = None  # chỉ có khi status = done


def _job_out(job) -> dict:
    return {
        "job_id": job.id, "status": job.status, "engine": job.engine, "language": job.language,
        "duration_s": job.duration_s, "done_s": job.done_s, "error": job.error,
        "created_at": job.created_at, "started_at": job.started_at,
        "finished_at": job.finished_at, "expires_at": job.expires_at,
    }


@router.get("/engines", response_model=EnginesOut)
def engines(user: UserInfo = Depends(get_stt_user)):
    return {"default": settings.stt_engine, "engines": list_engines()}


@router.post("/jobs", status_code=202, response_model=JobOut)
def create_job(
    response: Response,
    file: UploadFile = File(...),
    engine: str | None = Query(None, description="Tên engine; bỏ trống = engine mặc định"),
    language: str | None = Query(None, max_length=16, description="Mã ngôn ngữ (vi, en); trống = mặc định"),
    user: UserInfo = Depends(get_stt_user),
    db: Session = Depends(get_db),
):
    try:
        # Ghi tạm xuống đĩa theo khối (không nạp cả file vào RAM). Từ đây jobs.create giữ quyền sở hữu tệp:
        # bị từ chối hoặc xử lý xong đều xóa tệp.
        path, size = files.save_stream(file.file, int(settings.stt_max_mb * 1024 * 1024))
        job = jobs.create(db, user, path, size, engine=engine, language=language)
    except SttError as e:
        raise HTTPException(e.status_code, str(e)) from e
    response.headers["Location"] = f"/api/stt/jobs/{job.id}"
    return _job_out(job)


@router.get("/jobs", response_model=list[JobOut])
def list_jobs(user: UserInfo = Depends(get_stt_user), db: Session = Depends(get_db)):
    return [_job_out(j) for j in jobs.list_for_user(db, user)]


@router.get("/jobs/{job_id}", response_model=JobDetailOut)
def get_job(job_id: str, user: UserInfo = Depends(get_stt_user), db: Session = Depends(get_db)):
    try:
        job = jobs.get_for_user(db, user, job_id)
    except SttError as e:
        raise HTTPException(e.status_code, str(e)) from e
    out = _job_out(job)
    if job.status == "done":
        out["segments"] = job.result or []
    return out


@router.delete("/jobs/{job_id}", status_code=204)
def delete_job(job_id: str, user: UserInfo = Depends(get_stt_user), db: Session = Depends(get_db)):
    try:
        jobs.delete_for_user(db, user, job_id)
    except SttError as e:
        raise HTTPException(e.status_code, str(e)) from e
