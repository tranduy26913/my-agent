"""Nghiệp vụ cho /api/admin/audit và /api/admin/usage (docs/07). Không phụ thuộc FastAPI.

Về dữ liệu người thực hiện (bảng users đã bỏ ở giai đoạn 6 của docs/06):
- Sự kiện RAG và OCR ghi `user_id` = employees.id. Sự kiện quản trị kb_* ghi email vào detail["actor"].
- Dòng cũ (trước giai đoạn 6) của kb_*/llm_call có `user_id` là id bảng users đã xoá: không còn tên để hiện,
  nên chỉ hiện "Người dùng #id". Đừng join `user_id` với employees cho các sự kiện đó (sẽ hiện nhầm người).

Quyền riêng tư: `detail` của audit có thể chứa NỘI DUNG (câu hỏi của nhân viên, tham số và kết quả của tool).
Trang quản trị chỉ xem "ai làm gì, lúc nào", nên API trả theo danh sách
trắng từng sự kiện, không trả nội dung.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta

from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session

from app.models import AuditLog, Employee, UsageLog

# Sự kiện ghi user_id = employees.id (còn lại: dòng cũ mang id bảng users đã xoá)
EMPLOYEE_KEYED_EVENTS = frozenset(
    {"rag_ask", "rag_error", "ocr_run", "ocr_extract", "ocr_job_failed", "ocr_job_view"}
)
# Mục đích dùng token ghi user_id = employees.id (còn lại: dòng cũ mang id bảng users đã xoá)
EMPLOYEE_KEYED_PURPOSES = frozenset({"rag", "ocr", "ocr-extract"})

HIGHLIGHT_ALERT = "alert"  # cần chú ý ngay: xem tài liệu Mật, công cụ bị từ chối
HIGHLIGHT_WARN = "warn"

# event -> (nhãn tiếng Việt, mức làm nổi, các khoá detail được phép trả ra)
EVENTS: dict[str, tuple[str, str | None, tuple[str, ...]]] = {
    "kb_upload": (
        "Nạp tài liệu vào kho",
        None,
        ("doc_id", "kind", "bytes", "chunks", "ocr_pages", "supersedes"),
    ),
    "kb_reindex": ("Nạp lại tài liệu", None, ("doc_id", "chunks")),
    "kb_quarantine": ("Cách ly tài liệu", HIGHLIGHT_WARN, ("doc_id", "on")),
    "kb_delete": ("Gỡ tài liệu khỏi kho", HIGHLIGHT_WARN, ("doc_id", "chunks", "classified")),
    "kb_view_classified": ("Xem nội dung tài liệu Mật", HIGHLIGHT_ALERT, ("doc_id", "chunks")),
    "tool_denied": ("Công cụ bị từ chối", HIGHLIGHT_ALERT, ("tool", "step", "is_error")),
    "tool_call": ("Gọi công cụ", None, ("tool", "step", "is_error")),
    "llm_call": ("Gọi mô hình", None, ("model", "step", "stop_reason", "input_tokens", "output_tokens")),
    "refusal": ("Mô hình từ chối trả lời", HIGHLIGHT_WARN, ("step",)),
    "budget_exceeded": ("Vượt ngân sách", HIGHLIGHT_WARN, ("step",)),
    "rag_ask": ("Tra cứu quy chế", None, ("found", "model", "latency_ms", "as_of", "cost_usd")),
    "rag_error": ("Tra cứu lỗi", HIGHLIGHT_WARN, ("error", "model", "latency_ms", "as_of")),
    "ocr_run": ("OCR", None, ("engine", "kind", "pages", "ocr_pages", "ms")),
    "ocr_extract": (
        "Trích xuất từ phiếu",
        None,
        ("schema", "engine", "pages", "errors", "warnings", "needs_review"),
    ),
    "user_create": ("Tạo tài khoản", None, ("target",)),
    "user_deactivate": ("Khoá tài khoản", HIGHLIGHT_WARN, ("target",)),
    "user_reactivate": ("Mở khoá tài khoản", None, ("target",)),
    "user_password_reset": ("Đặt lại mật khẩu", HIGHLIGHT_WARN, ("target",)),
    # ADR-003 mục 8: xem dữ liệu nhân sự của NGƯỜI KHÁC, và các lần bị từ chối. Chỉ ghi phạm vi/số dòng, không nội dung.
    "hr_view": ("Xem dữ liệu nhân sự của người khác", None, ("resource", "scopes", "rows")),
    "hr_denied": ("Bị từ chối xem dữ liệu nhân sự", HIGHLIGHT_WARN, ("resource", "reason")),
}
MAX_TEXT = 200  # chuỗi dài (vd lỗi) bị cắt: có thể chứa nội dung


@dataclass(frozen=True)
class AuditRow:
    id: int
    ts: datetime
    event: str
    actor: str
    label: str
    summary: str
    highlight: str | None
    detail: dict


@dataclass(frozen=True)
class AuditPage:
    items: list[AuditRow]
    next_cursor: int | None
    event_counts: dict[str, int]


def event_label(event: str) -> str:
    return EVENTS[event][0] if event in EVENTS else event


def safe_detail(event: str, detail: dict | None) -> dict:
    """Chỉ các khoá trong danh sách trắng của sự kiện; sự kiện lạ trả rỗng (không biết khoá nào an toàn)."""
    allowed = EVENTS[event][2] if event in EVENTS else ()
    out = {}
    for k in allowed:
        if detail and k in detail:
            v = detail[k]
            out[k] = v[:MAX_TEXT] if isinstance(v, str) else v
    return out


def summarize(event: str, detail: dict) -> str:
    """Một câu ngắn từ phần detail đã lọc."""
    doc = detail.get("doc_id")
    match event:
        case "kb_quarantine":
            return f"{'Cách ly' if detail.get('on') else 'Bỏ cách ly'} {doc}"
        case "kb_upload" | "kb_reindex" | "kb_delete" | "kb_view_classified":
            return str(doc or "")
        case "tool_denied" | "tool_call":
            return str(detail.get("tool") or "")
        case "rag_ask":
            return "Có câu trả lời" if detail.get("found") else "Không tìm thấy trong tài liệu được xem"
        case "rag_error":
            return str(detail.get("error") or "")
        case "llm_call":
            return str(detail.get("model") or "")
        case "hr_view":
            return f"Phạm vi {', '.join(detail.get('scopes') or [])}: {detail.get('rows', 0)} dòng"
        case "hr_denied":
            return str(detail.get("reason") or "")
        case _:
            return str(detail.get("target") or "")


def _day_start(d: date) -> datetime:
    return datetime(d.year, d.month, d.day, tzinfo=UTC)


def _actor_expr():
    """Tên người thực hiện: email Zitadel trong detail["actor"], hoặc email người hỏi (RAG)."""
    return func.coalesce(AuditLog.detail["actor"].astext, AuditLog.detail["email"].astext)


def list_audit(
    db: Session,
    *,
    events: list[str] | None = None,
    actor: str | None = None,
    since: date | None = None,
    until: date | None = None,
    limit: int = 50,
    before_id: int | None = None,
) -> AuditPage:
    limit = max(1, min(limit, 200))
    actor_expr = _actor_expr()
    stmt = (
        select(AuditLog.id, AuditLog.ts, AuditLog.event, AuditLog.detail, actor_expr)
        .order_by(AuditLog.id.desc())
        .limit(limit + 1)
    )
    if events:
        stmt = stmt.where(AuditLog.event.in_(events))
    if actor and actor.strip():
        stmt = stmt.where(actor_expr.ilike(f"%{_escape_like(actor.strip())}%", escape="\\"))
    if since:
        stmt = stmt.where(AuditLog.ts >= _day_start(since))
    if until:
        stmt = stmt.where(AuditLog.ts < _day_start(until) + timedelta(days=1))
    if before_id is not None:
        stmt = stmt.where(AuditLog.id < before_id)

    rows = db.execute(stmt).all()
    more = len(rows) > limit
    rows = rows[:limit]
    items = []
    for id_, ts, event, detail, actor_name in rows:
        d = safe_detail(event, detail)
        highlight = EVENTS[event][1] if event in EVENTS else None
        items.append(
            AuditRow(
                id_,
                ts,
                event,
                actor_name or "hệ thống",
                event_label(event),
                summarize(event, d),
                highlight,
                d,
            )
        )
    counts = dict(db.execute(select(AuditLog.event, func.count()).group_by(AuditLog.event)).all())
    return AuditPage(items, items[-1].id if more and items else None, counts)


def _escape_like(s: str) -> str:
    return s.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


# ---------------------------------------------------------------- chi phí


@dataclass(frozen=True)
class UsageGroup:
    key: str
    name: str
    calls: int
    input_tokens: int
    output_tokens: int
    cost_usd: float
    department: str = ""


@dataclass(frozen=True)
class UsageReport:
    month: str  # YYYY-MM
    months: list[str]
    calls: int
    input_tokens: int
    output_tokens: int
    cost_usd: float
    by_user: list[UsageGroup]
    by_model: list[UsageGroup]
    by_purpose: list[UsageGroup]
    by_day: list[UsageGroup]


def month_bounds(month: str) -> tuple[datetime, datetime]:
    y, m = (int(x) for x in month.split("-"))
    start = datetime(y, m, 1, tzinfo=UTC)
    end = datetime(y + (m == 12), 1 if m == 12 else m + 1, 1, tzinfo=UTC)
    return start, end


def _group(rows, key_fn=lambda r: r[0], name_fn=lambda r: r[0], dept_fn=lambda r: "") -> list[UsageGroup]:
    return [
        UsageGroup(
            str(key_fn(r)), str(name_fn(r)), int(r.calls), int(r.inp), int(r.out), float(r.cost), dept_fn(r)
        )
        for r in rows
    ]


def usage_report(db: Session, month: str | None = None) -> UsageReport:
    """Tổng hợp usage_logs theo tháng (UTC). `month` dạng YYYY-MM, bỏ trống = tháng hiện tại."""
    month = month or datetime.now(UTC).strftime("%Y-%m")
    start, end = month_bounds(month)
    in_month = and_(UsageLog.ts >= start, UsageLog.ts < end)
    agg = (
        func.count().label("calls"),
        func.coalesce(func.sum(UsageLog.input_tokens), 0).label("inp"),
        func.coalesce(func.sum(UsageLog.output_tokens), 0).label("out"),
        func.coalesce(func.sum(UsageLog.cost_usd), 0).label("cost"),
    )

    total = db.execute(select(*agg).where(in_month)).one()
    by_model = db.execute(
        select(UsageLog.model, *agg)
        .where(in_month)
        .group_by(UsageLog.model)
        .order_by(func.sum(UsageLog.cost_usd).desc())
    ).all()
    by_purpose = db.execute(
        select(UsageLog.purpose, *agg)
        .where(in_month)
        .group_by(UsageLog.purpose)
        .order_by(func.count().desc())
    ).all()
    day = func.to_char(func.timezone("UTC", UsageLog.ts), "YYYY-MM-DD")
    by_day = db.execute(select(day, *agg).where(in_month).group_by(day).order_by(day)).all()

    # Theo người: id thuộc hai không gian (employees: purpose rag; users: còn lại)
    # nên nhóm theo cả hai.
    is_emp = UsageLog.purpose.in_(EMPLOYEE_KEYED_PURPOSES)
    user_rows = db.execute(
        select(is_emp.label("emp"), UsageLog.user_id, func.max(UsageLog.department).label("dept"), *agg)
        .where(in_month)
        .group_by(is_emp, UsageLog.user_id)
        .order_by(func.sum(UsageLog.cost_usd).desc(), func.count().desc())
    ).all()
    emp_names = {
        e.id: e.full_name
        for e in db.execute(
            select(Employee).where(Employee.id.in_([r.user_id for r in user_rows if r.emp]))
        ).scalars()
    }

    def person(r) -> str:
        # Dòng cũ không thuộc employees chỉ còn id bảng users đã xoá
        return (emp_names.get(r.user_id) if r.emp else None) or f"Người dùng #{r.user_id}"

    months = [
        r[0]
        for r in db.execute(
            select(func.to_char(func.timezone("UTC", UsageLog.ts), "YYYY-MM").label("m"))
            .group_by("m")
            .order_by("m")
        ).all()
    ]
    return UsageReport(
        month=month,
        months=months,
        calls=int(total.calls),
        input_tokens=int(total.inp),
        output_tokens=int(total.out),
        cost_usd=float(total.cost),
        by_user=_group(
            user_rows,
            key_fn=lambda r: f"{'e' if r.emp else 'u'}{r.user_id}",
            name_fn=person,
            dept_fn=lambda r: r.dept or "",
        ),
        by_model=_group(by_model),
        by_purpose=_group(by_purpose),
        by_day=_group(by_day),
    )
