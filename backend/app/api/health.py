"""Kiểm tra sống / sẵn sàng. Không cần đăng nhập (cho Docker, cloudflared, giám sát gọi).

- /healthz : tiến trình còn chạy. KHÔNG đụng DB -> DB sập thì tiến trình vẫn "sống",
             tránh bị khởi động lại vô ích.
- /readyz  : sẵn sàng nhận việc = kết nối được Postgres. Lỗi -> 503, không lộ chi tiết
             lỗi ra ngoài (chỉ ghi log).
"""

import logging

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.deps import get_db

log = logging.getLogger("api.health")
router = APIRouter(tags=["health"])


@router.get("/healthz")
def healthz() -> dict:
    return {"status": "ok"}


@router.get("/readyz")
def readyz(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
    except Exception:  # noqa: BLE001 - mọi lỗi kết nối đều có nghĩa là "chưa sẵn sàng"
        log.exception("readyz: không kết nối được DB")
        return JSONResponse({"status": "unavailable", "db": "down"}, status_code=503)
    return {"status": "ok", "db": "up"}
