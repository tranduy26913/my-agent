"""Router /api/admin: nhật ký (audit) và chi phí (usage) cho trang quản trị của portal (docs/07).

Hợp đồng: portal/src/features/audit/types.ts và portal/src/features/usage/types.ts. JSON camelCase.
Chỉ dành cho admin (get_admin). Router chỉ nhận request, kiểm quyền, gọi app.admin_service.
"""

import re
from datetime import date, datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel
from sqlalchemy.orm import Session

from app import admin_service
from app.api.deps import Actor, get_admin, get_db
from app.config import settings

router = APIRouter(tags=["admin"])


class CamelModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class AuditItemOut(CamelModel):
    id: int
    ts: datetime
    event: str
    actor: str
    label: str
    summary: str
    highlight: str | None
    detail: dict


class AuditPageOut(CamelModel):
    items: list[AuditItemOut]
    next_cursor: int | None
    event_counts: dict[str, int]
    event_labels: dict[str, str]


@router.get("/audit", response_model=AuditPageOut)
def audit(
    event: list[str] = Query(default=[], description="Lọc theo loại sự kiện (lặp lại để chọn nhiều)"),
    actor: str | None = Query(
        default=None, max_length=100, description="Một phần email hoặc tên người thực hiện"
    ),
    since: date | None = None,
    until: date | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    before_id: int | None = Query(default=None, ge=1, alias="beforeId", description="Con trỏ phân trang"),
    _admin: Actor = Depends(get_admin),
    db: Session = Depends(get_db),
) -> AuditPageOut:
    if since and until and since > until:
        raise HTTPException(422, "Ngày bắt đầu phải trước hoặc bằng ngày kết thúc")
    page = admin_service.list_audit(
        db, events=event, actor=actor, since=since, until=until, limit=limit, before_id=before_id
    )
    return AuditPageOut(
        items=[AuditItemOut(**vars(r)) for r in page.items],
        next_cursor=page.next_cursor,
        event_counts=page.event_counts,
        event_labels={e: admin_service.event_label(e) for e in page.event_counts},
    )


class UsageGroupOut(CamelModel):
    key: str
    name: str
    department: str
    calls: int
    input_tokens: int
    output_tokens: int
    cost_usd: float


class UsageReportOut(CamelModel):
    month: str
    months: list[str]
    calls: int
    input_tokens: int
    output_tokens: int
    cost_usd: float
    budget_usd_per_user: float
    by_user: list[UsageGroupOut]
    by_model: list[UsageGroupOut]
    by_purpose: list[UsageGroupOut]
    by_day: list[UsageGroupOut]


@router.get("/usage", response_model=UsageReportOut)
def usage(
    month: str | None = Query(default=None, description="YYYY-MM; bỏ trống = tháng hiện tại"),
    _admin: Actor = Depends(get_admin),
    db: Session = Depends(get_db),
) -> UsageReportOut:
    if month is not None and not re.fullmatch(r"\d{4}-(0[1-9]|1[0-2])", month):
        raise HTTPException(422, "month phải có dạng YYYY-MM")
    r = admin_service.usage_report(db, month)

    def out(groups: list[admin_service.UsageGroup]) -> list[UsageGroupOut]:
        return [UsageGroupOut(**vars(g)) for g in groups]

    return UsageReportOut(
        month=r.month,
        months=r.months,
        calls=r.calls,
        input_tokens=r.input_tokens,
        output_tokens=r.output_tokens,
        cost_usd=r.cost_usd,
        budget_usd_per_user=settings.monthly_budget_usd_per_user,
        by_user=out(r.by_user),
        by_model=out(r.by_model),
        by_purpose=out(r.by_purpose),
        by_day=out(r.by_day),
    )
