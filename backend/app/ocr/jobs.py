"""Job OCR bất đồng bộ (ADR-005): nhận file -> trả job_id ngay -> xử lý nền -> người dùng hỏi kết quả sau.

Quyết định thiết kế:
- File gốc CHỈ nằm trong RAM của tiến trình trong lúc chờ/xử lý, không ghi đĩa, không ghi DB. Hệ quả: nếu máy
  chủ khởi động lại giữa chừng thì job mất -> `recover_interrupted()` đánh dấu failed để người dùng gửi lại.
- Hàng đợi là ThreadPoolExecutor trong tiến trình (đủ cho demo một máy). Muốn nhiều máy thì thay `_submit`
  bằng hàng đợi ngoài (Redis/RQ...), phần còn lại giữ nguyên.
- Hủy = xóa dòng job. Worker kiểm tra dòng còn tồn tại sau mỗi trang (callback progress), mất thì dừng.
- Job chỉ người tạo xem được. Người khác nhận 404 (không lộ job có tồn tại). Admin xem job của người khác được
  nhưng bắt buộc ghi audit `ocr_job_view` TRƯỚC khi trả nội dung (ghi lỗi -> không trả; ADR-004 mục 4).
- Hết hạn (ocr_job_ttl_days) thì coi như không tồn tại và bị dọn lười biếng mỗi lần tạo job mới.
"""

import logging
import threading
import uuid
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, func, select, update
from sqlalchemy.orm import Session

from app.config import settings
from app.llm.base import Usage
from app.observability import DbAuditSink, record_usage
from app.ocr import service
from app.ocr.engines import resolve_name
from app.ocr.errors import FileTooLarge, JobNotFound, OcrError, TooManyJobs
from app.ocr.pdf import sniff_kind
from app.security import UserInfo

log = logging.getLogger("ocr.jobs")

ACTIVE = ("queued", "running")

# Tiến trình worker tự mở session riêng (không dùng session của request đã đóng). Test thay bằng SQLite.
session_factory: Callable[[], Session] | None = None

_executor: ThreadPoolExecutor | None = None
_executor_lock = threading.Lock()


class JobCancelled(Exception):
    """Job bị xóa khi đang chạy; không phải lỗi, worker chỉ việc dừng."""


def _now() -> datetime:
    return datetime.now(UTC)


def _aware(dt: datetime) -> datetime:
    return dt if dt.tzinfo else dt.replace(tzinfo=UTC)  # SQLite trả datetime không múi giờ (đã lưu UTC)


def _factory() -> Session:
    if session_factory is not None:
        return session_factory()
    from app.db import SessionLocal

    return SessionLocal()


def _submit(fn: Callable, *args) -> None:
    """Đưa việc vào hàng đợi nền. Test thay hàm này để chạy đồng bộ."""
    global _executor
    with _executor_lock:
        if _executor is None:
            _executor = ThreadPoolExecutor(
                max_workers=max(1, settings.ocr_job_workers), thread_name_prefix="ocr-job"
            )
    _executor.submit(fn, *args)


def _audit(db: Session, user_id: int | None, event: str, detail: dict) -> None:
    DbAuditSink(db, user_id, None).log(event, detail)


def _usage(db: Session, user: UserInfo, engine: str) -> None:
    record_usage(db, user, f"local:{engine}", Usage(), purpose="ocr")  # engine cục bộ: chi phí 0


# ---------- tạo / đọc / xóa ----------

def create(db: Session, user: UserInfo, data: bytes, *, engine: str | None, pages: str | None):
    from app.models import OcrJob

    if len(data) > settings.ocr_job_max_mb * 1024 * 1024:
        raise FileTooLarge(f"File vượt giới hạn {settings.ocr_job_max_mb:g} MB")
    engine_name = resolve_name(engine)  # tên sai -> 400 ngay
    sniff_kind(data)  # không phải ảnh/PDF -> 400 ngay, không đưa vào hàng đợi

    purge_expired(db)
    active = OcrJob.status.in_(ACTIVE)
    if db.scalar(select(func.count()).select_from(OcrJob).where(active)) >= settings.ocr_job_queue_max:
        raise TooManyJobs("Hệ thống đang xử lý quá nhiều job OCR, thử lại sau ít phút")
    mine = db.scalar(select(func.count()).select_from(OcrJob).where(active, OcrJob.user_id == user.id))
    if mine >= settings.ocr_job_max_active_per_user:
        raise TooManyJobs(
            f"Bạn đang có {mine} job chưa xong (tối đa {settings.ocr_job_max_active_per_user}); "
            "chờ job xong rồi gửi tiếp"
        )

    now = _now()
    job = OcrJob(
        id=uuid.uuid4().hex, user_id=user.id, status="queued", engine=engine_name, bytes_in=len(data),
        created_at=now, expires_at=now + timedelta(days=settings.ocr_job_ttl_days),
    )
    db.add(job)
    db.commit()
    _submit(_run, job.id, user, data, engine_name, pages)
    return job


def get_for_user(db: Session, user: UserInfo, job_id: str):
    from app.models import OcrJob

    job = db.get(OcrJob, job_id)
    if job is None or _aware(job.expires_at) <= _now():
        raise JobNotFound("Không tìm thấy job")
    if job.user_id == user.id:
        return job
    if user.role == "admin":
        # Ghi vết xong mới trả nội dung: ghi lỗi -> ngoại lệ -> không lộ gì (fail closed).
        detail = {"job_id": job.id, "owner_id": job.user_id, "actor": user.username}
        _audit(db, user.id, "ocr_job_view", detail)
        return job
    raise JobNotFound("Không tìm thấy job")


def list_for_user(db: Session, user: UserInfo, limit: int = 50):
    from app.models import OcrJob

    q = (
        select(OcrJob)
        .where(OcrJob.user_id == user.id, OcrJob.expires_at > _now())
        .order_by(OcrJob.created_at.desc())
        .limit(limit)
    )
    return list(db.scalars(q))


def delete_for_user(db: Session, user: UserInfo, job_id: str) -> None:
    """Chỉ chủ job được xóa. Job đang chạy bị xóa thì worker tự dừng ở trang kế tiếp."""
    from app.models import OcrJob

    job = db.get(OcrJob, job_id)
    if job is None or job.user_id != user.id:
        raise JobNotFound("Không tìm thấy job")
    db.delete(job)
    db.commit()


def purge_expired(db: Session) -> int:
    from app.models import OcrJob

    res = db.execute(delete(OcrJob).where(OcrJob.expires_at <= _now()))
    db.commit()
    return res.rowcount or 0


def recover_interrupted(db: Session) -> int:
    """Lúc khởi động: job đang chờ/chạy mà tiến trình đã chết sẽ không bao giờ xong -> đánh dấu failed."""
    from app.models import OcrJob

    res = db.execute(
        update(OcrJob).where(OcrJob.status.in_(ACTIVE)).values(
            status="failed", finished_at=_now(),
            error="Máy chủ khởi động lại khi đang xử lý; hãy gửi lại file",
        )
    )
    db.commit()
    return res.rowcount or 0


# ---------- worker ----------

def _finish(db: Session, job_id: str, **values) -> bool:
    """Cập nhật trạng thái cuối. False nếu dòng đã bị xóa (job bị hủy)."""
    from app.models import OcrJob

    res = db.execute(update(OcrJob).where(OcrJob.id == job_id).values(finished_at=_now(), **values))
    db.commit()
    return bool(res.rowcount)


def _run(job_id: str, user: UserInfo, data: bytes, engine: str, pages: str | None) -> None:
    from app.models import OcrJob

    db = _factory()
    try:
        started = db.execute(
            update(OcrJob).where(OcrJob.id == job_id).values(status="running", started_at=_now())
        )
        db.commit()
        if not started.rowcount:
            return  # bị hủy khi còn đang chờ

        def progress(done: int, total: int) -> None:
            res = db.execute(
                update(OcrJob).where(OcrJob.id == job_id).values(pages_done=done, pages_total=total)
            )
            db.commit()
            if not res.rowcount:
                raise JobCancelled

        try:
            result = service.recognize(
                data, engine=engine, pages=pages, progress=progress,
                max_pages=settings.ocr_job_max_pages, max_mb=settings.ocr_job_max_mb,
            )
        except JobCancelled:
            return
        except OcrError as e:
            _fail(db, job_id, user, engine, str(e))
            return
        except Exception:  # noqa: BLE001 - lỗi bất ngờ: ghi log đầy đủ, người dùng chỉ thấy câu chung
            log.exception("OCR job %s lỗi bất ngờ", job_id)
            _fail(db, job_id, user, engine, "Lỗi nội bộ khi xử lý")
            return

        stored = _finish(
            db, job_id, status="done", kind=result.kind, pages_done=len(result.pages),
            pages_total=len(result.pages), result=[vars(p) for p in result.pages],
        )
        if stored:
            _safe(_audit, db, user.id, "ocr_run", {
                "engine": result.engine, "kind": result.kind, "bytes": len(data), "pages": len(result.pages),
                "ocr_pages": result.ocr_pages, "ms": result.ms, "job_id": job_id, "async": True,
                "actor": user.username,
            })
            _safe(_usage, db, user, result.engine)
    finally:
        db.close()


def _fail(db: Session, job_id: str, user: UserInfo, engine: str, message: str) -> None:
    if _finish(db, job_id, status="failed", error=message[:300]):
        detail = {"engine": engine, "job_id": job_id, "actor": user.username}
        _safe(_audit, db, user.id, "ocr_job_failed", detail)


def _safe(fn: Callable, *args) -> None:
    """Ghi vết sau khi job đã xong: lỗi ghi vết chỉ log, không làm mất kết quả người dùng đang chờ."""
    try:
        fn(*args)
    except Exception:  # noqa: BLE001
        log.exception("Không ghi được vết cho job OCR")


# ---------- khởi động ----------

def startup() -> None:
    """Tạo bảng ocr_jobs nếu chưa có + đánh dấu job bị gián đoạn. Chạy nền để DB tắt không chặn API."""
    from app.db import engine
    from app.models import OcrJob

    try:
        OcrJob.__table__.create(bind=engine, checkfirst=True)
        db = _factory()
        try:
            n = recover_interrupted(db)
            if n:
                log.warning("Đánh dấu %d job OCR bị gián đoạn là failed", n)
        finally:
            db.close()
    except Exception:  # noqa: BLE001
        log.exception("Khởi tạo job OCR thất bại (DB chưa sẵn sàng?)")
