"""Ứng dụng FastAPI của backend. Chạy:

    uvicorn app.main:app --port 8000

Cổng 8000 theo docs/06-ke-hoach-zitadel.md (BFF của portal chuyển tiếp tới FastAPI :8000).
Không bật CORS: portal gọi qua proxy phía server (BFF), trình duyệt không gọi thẳng vào đây.

File này DÙNG CHUNG: /api/kb, /api/ocr, /api/me... đều đăng ký router ở `create_app()`.
Mỗi router là một file trong app/api/, chỉ nhận request rồi gọi tầng nghiệp vụ (ADR-004).
"""

import logging
import threading
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api import health, kb, ocr
from app.ocr import jobs

log = logging.getLogger("api")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Chạy nền: DB tắt/chậm không được chặn API khởi động (/readyz sẽ báo 503 đúng tình trạng).
    threading.Thread(target=jobs.startup, name="ocr-startup", daemon=True).start()
    yield


def create_app() -> FastAPI:
    app = FastAPI(title="SVT Agent Platform API", version="0.1.0", lifespan=lifespan)
    app.include_router(health.router)
    app.include_router(ocr.router, prefix="/api/ocr")
    app.include_router(kb.router, prefix="/api/kb")
    # Router nghiệp vụ khác (/api/me...) thêm ở đây, mỗi cái một dòng.
    return app


app = create_app()
