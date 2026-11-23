"""Lưu vết (audit) + đo chi phí + ngân sách theo người dùng."""

from datetime import UTC, datetime
from typing import Protocol

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.llm.base import Usage

# USD / 1M token: (input, output, cache_read). Cache write ~1.25x input. Cập nhật theo bảng giá thực tế.
PRICING = {
    "claude-opus-5-5": (4.00, 20.00, 0.20),
    "claude-sonnet-5-5": (2.00, 10.00, 0.10),
    "claude-haiku-5-5": (0.10, 0.50, 0.01),
    "fake": (0.0, 0.0, 0.0),
}


def cost_usd(model: str, u: Usage) -> float:
    if model.startswith("local:"):  # model chạy cục bộ: không tốn tiền API
        return 0.0
    inp, out, cache_read = PRICING.get(model, PRICING["claude-opus-5-5"])
    return (
        u.input_tokens * inp
        + u.output_tokens * out
        + u.cache_read_tokens * cache_read
        + u.cache_write_tokens * inp * 1.25
    ) / 1_000_000


class AuditSink(Protocol):
    def log(self, event: str, detail: dict) -> None: ...


class ListAuditSink:
    """Dùng trong test."""

    def __init__(self):
        self.events: list[tuple[str, dict]] = []

    def log(self, event: str, detail: dict) -> None:
        self.events.append((event, detail))


class DbAuditSink:
    def __init__(self, db: Session, user_id: int | None, conversation_id: int | None):
        self.db, self.user_id, self.conversation_id = db, user_id, conversation_id

    def log(self, event: str, detail: dict) -> None:
        from app.models import AuditLog

        self.db.add(AuditLog(user_id=self.user_id, conversation_id=self.conversation_id,
                             event=event, detail=detail))
        self.db.commit()


def record_usage(db: Session, user, model: str, usage: Usage, purpose: str = "chat") -> float:
    from app.models import UsageLog

    c = cost_usd(model, usage)
    db.add(UsageLog(
        user_id=user.id, department=user.department, model=model, purpose=purpose,
        input_tokens=usage.input_tokens, output_tokens=usage.output_tokens,
        cache_read_tokens=usage.cache_read_tokens, cache_write_tokens=usage.cache_write_tokens,
        cost_usd=c,
    ))
    db.commit()
    return c


def month_spend(db: Session, user_id: int) -> float:
    from app.models import UsageLog

    start = datetime.now(UTC).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    q = select(func.coalesce(func.sum(UsageLog.cost_usd), 0)).where(
        UsageLog.user_id == user_id, UsageLog.ts >= start
    )
    return float(db.execute(q).scalar_one())
