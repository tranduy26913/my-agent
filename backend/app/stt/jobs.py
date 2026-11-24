"""Job STT bất đồng bộ (ADR-006): nhận file -> trả job_id ngay -> chép nền -> người dùng hỏi kết quả sau.

Bám mẫu app/ocr/jobs.py (cố ý trùng lặp, xem ADR-006 mục 1). Khác OCR:
- File ghi âm nằm trên ĐĨA (tệp tạm do router ghi) chứ không ở RAM. Job SỞ HỮU tệp đó từ lúc `create`
  được gọi: xóa ở `finally` của worker, và xóa ngay nếu `create` bị từ chối. Không để tệp mồ côi sau job.
- Tiến độ tính bằng giây âm thanh (`done_s / duration_s`) và chỉ ghi DB mỗi PROGRESS_EVERY_S giây
  (một cuộc họp sinh hàng trăm đoạn, không ghi DB từng đoạn).
- Hủy = xóa dòng job. Worker phát hiện ở lần ghi tiến độ kế tiếp và dừng; engine được đóng ngay.
- Job chỉ người tạo xem được. Người khác nhận 404. Admin xem được nhưng phải ghi audit `stt_job_view`
  TRƯỚC khi trả nội dung (ghi lỗi -> không trả; ADR-004 mục 4).
"""

import logging
import threading
import time
import uuid
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, func, select, update
from sqlalchemy.orm import Session

from app.config import settings
from app.llm.base import Usage
from app.observability import DbAuditSink, record_usage
from app.security import UserInfo
from app.stt import audio, files, service
from app.stt.engines import get_engine, resolve_name
from app.stt.errors import FileTooLarge, JobNotFound, SttError, TooManyJobs

log = logging.getLogger("stt.jobs")

ACTIVE = ("queued", "running")
PROGRESS_EVERY_S = 2.0  # test đặt về 0 để kiểm tiến độ và hủy tất định

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
                max_workers=max(1, settings.stt_job_workers), thread_name_prefix="stt-job"
            )
    _executor.submit(fn, *args)


def _audit(db: Session, user_id: int | None, event: str, detail: dict) -> None:
    DbAuditSink(db, user_id, None).log(event, detail)


def _usage(db: Session, user: UserInfo, engine: str) -> None:
    record_usage(db, user, f"local:{engine}", Usage(), purpose="stt")  # engine cục bộ: chi phí 0


# ---------- tạo / đọc / xóa ----------

def create(
    db: Session, user: UserInfo, src_path: str, size: int, *, engine: str | None, language: str | None
):
    """Tạo job và đưa vào hàng đợi. Nhận quyền sở hữu `src_path`: bị từ chối thì tệp bị xóa tại đây."""
    try:
        return _create(db, user, src_path, size, engine=engine, language=language)
    except BaseException:
        files.remove(src_path)
        raise


def _create(
    db: Session, user: UserInfo, src_path: str, size: int, *, engine: str | None, language: str | None
):
    from app.models import SttJob

    if size > settings.stt_max_mb * 1024 * 1024:
        raise FileTooLarge(f"File vượt giới hạn {settings.stt_max_mb:g} MB")
    engine_name = resolve_name(engine)  # tên sai -> 400 ngay
    get_engine(engine_name)  # chưa sẵn sàng -> 503 ngay, không nhận job rồi mới báo lỗi
    audio.require_ffmpeg()  # thiếu ffmpeg -> 503 ngay
    audio.probe(src_path, max_seconds=settings.stt_max_minutes * 60)  # rác -> 400, quá dài -> 422, ngay

    purge_expired(db)
    active = SttJob.status.in_(ACTIVE)
    if db.scalar(select(func.count()).select_from(SttJob).where(active)) >= settings.stt_job_queue_max:
        raise TooManyJobs("Hệ thống đang xử lý quá nhiều ghi âm, thử lại sau ít phút")
    mine = db.scalar(select(func.count()).select_from(SttJob).where(active, SttJob.user_id == user.id))
    if mine >= settings.stt_job_max_active_per_user:
        raise TooManyJobs(
            f"Bạn đang có {mine} ghi âm chưa xong (tối đa {settings.stt_job_max_active_per_user}); "
            "chờ xong rồi gửi tiếp"
        )

    lang = language if language is not None else (settings.stt_language or None)
    now = _now()
    job = SttJob(
        id=uuid.uuid4().hex, user_id=user.id, status="queued", engine=engine_name, language=lang,
        bytes_in=size, created_at=now, expires_at=now + timedelta(days=settings.stt_job_ttl_days),
    )
    db.add(job)
    db.commit()
    _submit(_run, job.id, user, src_path, engine_name, lang)
    return job


def get_for_user(db: Session, user: UserInfo, job_id: str):
    from app.models import SttJob

    job = db.get(SttJob, job_id)
    if job is None or _aware(job.expires_at) <= _now():
        raise JobNotFound("Không tìm thấy job")
    if job.user_id == user.id:
        return job
    if user.role == "admin":
        # Ghi vết xong mới trả nội dung: ghi lỗi -> ngoại lệ -> không lộ gì (fail closed).
        detail = {"job_id": job.id, "owner_id": job.user_id, "actor": user.username}
        _audit(db, user.id, "stt_job_view", detail)
        return job
    raise JobNotFound("Không tìm thấy job")


def list_for_user(db: Session, user: UserInfo, limit: int = 50):
    from app.models import SttJob

    q = (
        select(SttJob)
        .where(SttJob.user_id == user.id, SttJob.expires_at > _now())
        .order_by(SttJob.created_at.desc())
        .limit(limit)
    )
    return list(db.scalars(q))


def delete_for_user(db: Session, user: UserInfo, job_id: str) -> None:
    """Chỉ chủ job được xóa. Job đang chạy bị xóa thì worker tự dừng ở lần ghi tiến độ kế tiếp."""
    from app.models import SttJob

    job = db.get(SttJob, job_id)
    if job is None or job.user_id != user.id:
        raise JobNotFound("Không tìm thấy job")
    db.delete(job)
    db.commit()


def purge_expired(db: Session) -> int:
    from app.models import SttJob

    res = db.execute(delete(SttJob).where(SttJob.expires_at <= _now()))
    db.commit()
    return res.rowcount or 0


def recover_interrupted(db: Session) -> int:
    """Lúc khởi động: job đang chờ/chạy mà tiến trình đã chết sẽ không bao giờ xong -> đánh dấu failed."""
    from app.models import SttJob

    res = db.execute(
        update(SttJob).where(SttJob.status.in_(ACTIVE)).values(
            status="failed", finished_at=_now(),
            error="Máy chủ khởi động lại khi đang xử lý; hãy gửi lại file",
        )
    )
    db.commit()
    return res.rowcount or 0


# ---------- worker ----------

def _finish(db: Session, job_id: str, **values) -> bool:
    """Cập nhật trạng thái cuối. False nếu dòng đã bị xóa (job bị hủy)."""
    from app.models import SttJob

    res = db.execute(update(SttJob).where(SttJob.id == job_id).values(finished_at=_now(), **values))
    db.commit()
    return bool(res.rowcount)


def _run(job_id: str, user: UserInfo, src_path: str, engine: str, language: str | None) -> None:
    from app.models import SttJob

    db = _factory()
    try:
        started = db.execute(
            update(SttJob).where(SttJob.id == job_id).values(status="running", started_at=_now())
        )
        db.commit()
        if not started.rowcount:
            return  # bị hủy khi còn đang chờ

        last = {"t": None}

        def progress(done_s: float, total_s: float) -> None:
            now = time.monotonic()
            first = last["t"] is None
            if not first and done_s < total_s and now - last["t"] < PROGRESS_EVERY_S:
                return
            last["t"] = now
            res = db.execute(
                update(SttJob).where(SttJob.id == job_id).values(done_s=done_s, duration_s=total_s)
            )
            db.commit()
            if not res.rowcount:
                raise JobCancelled

        try:
            result = service.transcribe(src_path, engine=engine, language=language, progress=progress)
        except JobCancelled:
            return
        except SttError as e:
            _fail(db, job_id, user, engine, str(e))
            return
        except Exception:  # noqa: BLE001 - lỗi bất ngờ: ghi log đầy đủ, người dùng chỉ thấy câu chung
            log.exception("STT job %s lỗi bất ngờ", job_id)
            _fail(db, job_id, user, engine, "Lỗi nội bộ khi xử lý")
            return

        stored = _finish(
            db, job_id, status="done", duration_s=result.duration_s, done_s=result.duration_s,
            result=[vars(s) for s in result.segments],
        )
        if stored:
            size = db.scalar(select(SttJob.bytes_in).where(SttJob.id == job_id)) or 0
            _safe(_audit, db, user.id, "stt_run", {
                "engine": result.engine, "bytes": size, "duration_s": result.duration_s,
                "segments": len(result.segments), "ms": result.ms, "job_id": job_id, "actor": user.username,
            })
            _safe(_usage, db, user, result.engine)
    finally:
        files.remove(src_path)  # luôn xóa file ghi âm, dù xong, lỗi hay bị hủy
        db.close()


def _fail(db: Session, job_id: str, user: UserInfo, engine: str, message: str) -> None:
    if _finish(db, job_id, status="failed", error=message[:300]):
        detail = {"engine": engine, "job_id": job_id, "actor": user.username}
        _safe(_audit, db, user.id, "stt_job_failed", detail)


def _safe(fn: Callable, *args) -> None:
    """Ghi vết sau khi job đã xong: lỗi ghi vết chỉ log, không làm mất kết quả người dùng đang chờ."""
    try:
        fn(*args)
    except Exception:  # noqa: BLE001
        log.exception("Không ghi được vết cho job STT")


# ---------- khởi động ----------

def startup() -> None:
    """Tạo bảng stt_jobs, đánh dấu job gián đoạn, dọn tệp tạm. Chạy nền để DB tắt không chặn API."""
    from app.db import engine
    from app.models import SttJob

    try:
        n_files = files.purge_all()  # job dở đã chết nên tệp tạm còn lại không dùng nữa
        if n_files:
            log.warning("Dọn %d tệp tạm STT còn sót", n_files)
    except Exception:  # noqa: BLE001
        log.exception("Không dọn được thư mục tạm STT")
    try:
        SttJob.__table__.create(bind=engine, checkfirst=True)
        db = _factory()
        try:
            n = recover_interrupted(db)
            if n:
                log.warning("Đánh dấu %d job STT bị gián đoạn là failed", n)
        finally:
            db.close()
    except Exception:  # noqa: BLE001
        log.exception("Khởi tạo job STT thất bại (DB chưa sẵn sàng?)")
